# -*- coding: utf-8 -*-
"""Agenda Cultural de Andalucía (Junta de Andalucía, Agencia Andaluza de Instituciones Culturales).

Reúne la programación cultural de las ocho provincias andaluzas: teatros y auditorios públicos y municipales,
museos, filmotecas, bibliotecas, flamenco, fiestas… No publica API ni datos abiertos, así que se lee su listado
público (/actividades): diez tarjetas por página, recorrido una vez por temática para saber el tipo de plan.
Cada tarjeta trae la fecha (o el rango «del … al …»), el título, el espacio con municipio y provincia, la hora
en texto libre («A las 21:00», «27/11/2026 - 20:30», «Sin determinar») y la imagen. No se abre la ficha de cada
plan: lo que no está en la tarjeta (precio, descripción) se queda vacío en vez de suponerlo. Cada plan enlaza a su
ficha oficial; las imágenes no se usan (ver USE_IMAGES).

Se recorre cada combinación de temática y provincia (tres páginas a la vez): así cada plan sale con su tipo y
su provincia aunque la tarjeta no diga el municipio. Temáticas y provincias se leen del propio formulario de
filtros, así que un cambio de identificadores no rompe nada. Se descartan las actividades escolares y lo que dura
más de medio año (tours y visitas de todo el año, clases, programas de curso): no son planes con fecha. Las
exposiciones pueden durar hasta un año.
"""
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from .classify import classify
from .util import event, http_text, norm, parse_time

NAME = "Agenda Cultural de Andalucía"
HOME = "https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia/"
HOST = "https://www.juntadeandalucia.es"
LIST = HOST + "/aaiicc/agendaculturaldeandalucia/actividades"
PER_PAGE = 10
MAX_PAGES = 60  # por temática y provincia; hoy la combinación más grande ronda las 15 páginas
PAUSE = 0.3  # segundos entre páginas de cada hilo, para no cargar el servidor
# Las imágenes de las tarjetas no se publican hasta que la Agencia confirme que se pueden reutilizar: otras webs
# de la AAIICC reservan todos los derechos de sus contenidos. Fecha, título, lugar y enlace son datos del plan.
USE_IMAGES = False
WORKERS = 3  # el servidor tarda ~4 s por página: tres a la vez dejan la fuente en 2-3 minutos
# días: lo que dura más (tours de todo el año, clases, programas de curso, ciclos de temporada) no es un plan con
# fecha; las exposiciones sí pueden durar meses, hasta un año
MAX_SPAN, MAX_SPAN_EXPO = 180, 365
_SCHOOL = re.compile(r"\bescolar(es)?\b|centros educativos|para estudiantes|actividades educativas|\bprimaria\b|\bsecundaria\b")

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
# si un plan sale en varias temáticas, manda la primera de esta lista (un espectáculo infantil es infantil)
ORDER = ["agenda infantil y juvenil", "exposiciones", "flamenco", "cine y audiovisual", "libros y literatura",
         "cursos y formacion", "fiestas y tradiciones", "espectaculos", "monumentos y espacios culturales"]
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


def options(page_html, name):
    """Opciones de un filtro del formulario (topic, province): [(id, nombre)]."""
    m = re.search(r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % name, page_html, re.S)
    if not m:
        return []
    return [(v, _text(n)) for v, n in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)<', m.group(1))
            if v and v != "All"]


def topics(page_html):
    return options(page_html, "topic")


def total(page_html):
    m = _TOTAL.search(page_html)
    return int(m.group(1)) if m else 0


def skip(c, topic=""):
    """Lo que no es un plan para el público: actividades escolares y ofertas de todo el año (tours, clases, ciclos)."""
    if _SCHOOL.search(norm(c["title"])):
        return True
    expo = norm(topic) == "exposiciones" or "exposici" in norm(c["title"])
    return (date.fromisoformat(c["end"]) - date.fromisoformat(c["start"])).days > (MAX_SPAN_EXPO if expo else MAX_SPAN)


def to_event(c, topic="", province=""):
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
        subtype=topic, category=cat, province=province or c["province"] or None, city=c["city"],
        venue=c["venue"], url=c["url"], image=c["image"] if USE_IMAGES else "",
    )


def _page(params, page):
    q = dict(params)
    if page:
        q["page"] = page
    text = http_text(LIST, params=q, retries=3, timeout=(15, 60))
    time.sleep(PAUSE)
    return text


def _priority(topic_name):
    n = norm(topic_name)
    return ORDER.index(n) if n in ORDER else len(ORDER)


def fetch(log):
    first = http_text(LIST, retries=3, timeout=(15, 60))
    n_all = total(first)
    tops = sorted(topics(first), key=lambda t: _priority(t[1]))
    provs = options(first, "province")
    if not tops or not provs:
        raise RuntimeError("el formulario de filtros ha cambiado (temáticas: %d, provincias: %d)" % (len(tops), len(provs)))
    combos = [(t, p) for t in tops for p in provs]
    pages = {}  # (combo, página) -> html
    failed = []

    def get(job):
        (t, p), n = job
        try:
            return job, _page({"topic": t[0], "province": p[0]}, n)
        except Exception as exc:  # noqa: BLE001 - una página caída no tira las demás
            return job, exc

    # 1) primera página de cada temática × provincia: trae el total y las diez primeras tarjetas
    with ThreadPoolExecutor(WORKERS) as ex:
        for job, res in ex.map(get, [(c, 0) for c in combos]):
            if isinstance(res, Exception):
                failed.append(job)
            else:
                pages[job] = res
    # 2) el resto de páginas de las combinaciones con más de diez planes
    more = [(c, n) for (c, n0), h in list(pages.items()) for n in range(1, min(MAX_PAGES, -(-total(h) // PER_PAGE)))]
    with ThreadPoolExecutor(WORKERS) as ex:
        for job, res in ex.map(get, more):
            if isinstance(res, Exception):
                failed.append(job)
            else:
                pages[job] = res
    found, by_topic, by_prov, skipped = {}, {}, {}, 0
    for c, n in sorted(pages, key=lambda j: (combos.index(j[0]), j[1])):
        (tid, tname), (pid, pname) = c
        for card in parse_cards(pages[(c, n)]):
            if card["slug"] in found:
                continue
            if skip(card, tname):
                found[card["slug"]] = None
                skipped += 1
                continue
            found[card["slug"]] = (card, tname, pname)
            by_topic[tname] = by_topic.get(tname, 0) + 1
            by_prov[pname] = by_prov.get(pname, 0) + 1
    out = []
    for item in found.values():
        if item:
            ev = to_event(*item)
            if ev:
                out.append(ev)
    if not out:
        raise RuntimeError("el listado no ha devuelto ninguna tarjeta legible")
    if failed and len(failed) > len(pages) // 4:
        raise RuntimeError("%d de %d páginas sin respuesta" % (len(failed), len(failed) + len(pages)))
    log("%s: %d eventos de %d en el listado (%d descartados: escolares o de todo el año; %d páginas leídas%s)" % (
        NAME, len(out), n_all, skipped, len(pages), (", %d sin respuesta" % len(failed)) if failed else ""))
    log("  -> por temática: %s" % ", ".join("%s %d" % kv for kv in by_topic.items()))
    log("  -> por provincia: %s" % ", ".join("%s %d" % kv for kv in by_prov.items()))
    return out
