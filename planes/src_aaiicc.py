# -*- coding: utf-8 -*-
"""Agenda Cultural de Andalucía (Junta de Andalucía, Agencia Andaluza de Instituciones Culturales).

Reúne la programación cultural de las ocho provincias andaluzas: teatros y auditorios públicos y municipales,
museos, filmotecas, bibliotecas, flamenco, fiestas… No publica API ni datos abiertos, así que se lee su listado
público (/actividades): diez tarjetas por página, recorrido una vez por temática para saber el tipo de plan.
Cada tarjeta trae la fecha (o el rango «del … al …»), el título, el espacio con municipio y provincia, la hora
en texto libre («A las 21:00», «27/11/2026 - 20:30», «Sin determinar») y la imagen. No se abre la ficha de cada
plan: lo que no está en la tarjeta (precio, descripción) se queda vacío en vez de suponerlo.

Las temáticas se leen del propio formulario de filtros, así que un cambio de identificadores no rompe nada;
si la suma de las temáticas no llega al total del listado general, se recorre también el listado general para
los planes sin temática (y su tipo lo decide el título).
"""
import html
import re
import time
from datetime import date

from .classify import classify
from .util import event, http_text, norm, parse_time

NAME = "Agenda Cultural de Andalucía"
HOME = "https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia/"
HOST = "https://www.juntadeandalucia.es"
LIST = HOST + "/aaiicc/agendaculturaldeandalucia/actividades"
PER_PAGE = 10
MAX_PAGES = 150  # por temática; hoy la más grande ronda las 40
PAUSE = 0.3  # segundos entre páginas, para no cargar el servidor

# temática del filtro (en minúsculas y sin tildes) -> (tipos para classify, categoría si el título no aclara nada)
TOPICS = {
    "agenda infantil y juvenil": ([], "infantil"),
    "cine y audiovisual": ([], "cine"),
    "cursos y formacion": ([], "charlas"),
    "espectaculos": ([], "escena"),  # teatro, danza, humor… y también conciertos: manda el título
    "exposiciones": (["exposiciones"], "expos"),
    "fiestas y tradiciones": ([], "fiestas"),
    "flamenco": (["flamenco"], "musica"),
    "libros y literatura": ([], "charlas"),
    "monumentos y espacios culturales": ([], "naturaleza"),
}
# temáticas cuya categoría no depende del título (una exposición de carteles de cine sigue siendo una exposición)
FIXED = {"agenda infantil y juvenil", "exposiciones", "cursos y formacion", "libros y literatura"}

PROVINCES = {"almeria": "Almería", "cadiz": "Cádiz", "cordoba": "Córdoba", "granada": "Granada",
             "huelva": "Huelva", "jaen": "Jaén", "malaga": "Málaga", "sevilla": "Sevilla"}
ARTICLES = {"la", "el", "los", "las"}
MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_DATE = re.compile(r"(\d{1,2})\s+(%s)\s+(\d{4})" % "|".join(MONTHS), re.I)
_EVENT_A = re.compile(r'<a href="(/aaiicc/agendaculturaldeandalucia/evento/[^"#?]+)"[^>]*>(.*?)</a>', re.S)
_PLACE_A = re.compile(r'<a href="/aaiicc/agendaculturaldeandalucia/espacios/[^"]+"[^>]*>(.*?)</a>', re.S)
_TOTAL = re.compile(r">\s*(\d+)\s+Actividades\s*<")
_NO_TIME = re.compile(r"sin determinar|por determinar|consultar", re.I)


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _iso(m):
    return "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(2).lower()], int(m.group(1)))


def split_place(s):
    """«Teatro Central - Sevilla» -> (venue, city, province). La provincia solo si se nombra o la ciudad es capital."""
    s = _text(s)
    venue, _, place = s.rpartition(" - ")
    if not _:
        venue, place = "", s
    province = ""
    article = ""
    for grp in re.findall(r"\(([^()]*)\)", place):
        g = norm(grp)
        if g in PROVINCES:
            province = PROVINCES[g]
        elif g in ARTICLES:
            article = grp.strip().capitalize()
    city = re.sub(r"\s*\([^()]*\)", "", place).strip(" .,")
    if article:
        city = "%s %s" % (article, city)
    if not province and norm(city) in PROVINCES:
        province = PROVINCES[norm(city)]
    # «Sevilla. Plaza de San Francisco» o «Alcalá de Guadaíra. Teatro …»: el municipio va delante del espacio
    head, dot, rest = venue.partition(". ")
    if dot and rest and norm(head) in (norm(city), norm(re.sub(r"\s*\([^()]*\)", "", place))):
        venue = rest
    if re.match(r"(?i)espacio por determinar|por determinar|-$", venue.strip()):
        venue = ""
    return venue.strip(), city, province


def parse_cards(page_html):
    """Tarjetas de una página del listado -> dicts con url, título, fechas, lugar, hora e imagen."""
    out = []
    for chunk in page_html.split("<article")[1:]:
        chunk = chunk.split("</article>")[0]
        link = next((m for m in _EVENT_A.finditer(chunk) if _text(m.group(2))), None)
        if not link:
            continue
        url, title = link.group(1), _text(link.group(2))
        # la fecha (o el rango) va en la tarjeta antes del título; así un título con fecha no la confunde
        dates = [_iso(m) for m in _DATE.finditer(_text(chunk[:link.start()]))]
        if not dates:
            continue
        place = _PLACE_A.search(chunk)
        venue, city, province = split_place(place.group(1)) if place else ("", "", "")
        rest = chunk[place.end():] if place else chunk
        when = _text(" ".join(re.findall(r"<p>(.*?)</p>", rest, re.S)))
        img = re.search(r'<img[^>]+src="([^"]+)"', chunk)
        out.append({
            "url": HOST + url, "slug": url.rsplit("/", 1)[-1], "title": title,
            "start": dates[0], "end": dates[1] if len(dates) > 1 else dates[0],
            "venue": venue, "city": city, "province": province,
            "when": "" if _NO_TIME.search(when) else when,
            "image": (HOST + img.group(1)) if img and img.group(1).startswith("/") else (img.group(1) if img else ""),
        })
    return out


def topics(page_html):
    """Opciones del filtro de temática: [(id, nombre)]."""
    m = re.search(r'<select[^>]*name="topic"[^>]*>(.*?)</select>', page_html, re.S)
    if not m:
        return []
    return [(v, _text(n)) for v, n in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)<', m.group(1))
            if v and v != "All"]


def total(page_html):
    m = _TOTAL.search(page_html)
    return int(m.group(1)) if m else 0


def crawl(params, first=None):
    """Recorre las páginas de un listado (con sus filtros) hasta que deja de haber tarjetas nuevas."""
    seen, cards = set(), []
    page_html = first
    n_total = 0
    for page in range(MAX_PAGES):
        if page_html is None:
            q = dict(params)
            if page:
                q["page"] = page
            page_html = http_text(LIST, params=q, retries=3, timeout=(15, 60))
            time.sleep(PAUSE)
        if page == 0:
            n_total = total(page_html)
        new = [c for c in parse_cards(page_html) if c["slug"] not in seen]
        page_html = None
        if not new:
            break
        for c in new:
            seen.add(c["slug"])
            cards.append(c)
        if n_total and len(cards) >= n_total:
            break
    return cards, n_total


def to_event(c, topic=""):
    types, fallback = TOPICS.get(norm(topic), ([], None))
    if norm(topic) in FIXED and fallback:
        cat = fallback
    else:
        cat = classify(types, c["title"])
        if cat == "otros" and fallback:
            cat = fallback
    # en exposiciones y ciclos largos la «hora» es el horario de apertura: solo vale para funciones de pocos días
    short = (date.fromisoformat(c["end"]) - date.fromisoformat(c["start"])).days <= 3
    return event(
        NAME, c["slug"], c["title"], c["start"], end=c["end"],
        time=parse_time(c["when"]) if short else "",
        subtype=topic, category=cat, province=c["province"] or None, city=c["city"],
        venue=c["venue"], url=c["url"], image=c["image"],
    )


def fetch(log):
    first = http_text(LIST, retries=3, timeout=(15, 60))
    n_all = total(first)
    found = {}
    by_topic = {}
    for tid, tname in topics(first):
        try:
            cards, n = crawl({"topic": tid})
        except Exception as exc:  # noqa: BLE001 - una temática caída no tira las demás
            log("%s: temática «%s» sin respuesta (%s)" % (NAME, tname, exc.__class__.__name__))
            continue
        by_topic[tname] = len(cards)
        for c in cards:
            found.setdefault(c["slug"], (c, tname))
    if len(found) < n_all * 0.97:  # planes sin temática (o una temática que falló): listado general
        cards, _ = crawl({}, first=first)
        for c in cards:
            found.setdefault(c["slug"], (c, ""))
    out = []
    for c, tname in found.values():
        ev = to_event(c, tname)
        if ev:
            out.append(ev)
    if not out:
        raise RuntimeError("el listado no ha devuelto ninguna tarjeta legible")
    log("%s: %d eventos (listado: %d; por temática: %s)" % (
        NAME, len(out), n_all, ", ".join("%s %d" % kv for kv in by_topic.items())))
    return out
