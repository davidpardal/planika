# -*- coding: utf-8 -*-
"""Datos troceados para la web (core.js + detalles por bloques) y una página estática por plan con schema.org/Event."""
import html
import json
import os
import re
import unicodedata
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

from . import seo
from .classify import CATEGORIES
from .util import is_permanent, iso, today

SITE_URL = (os.environ.get("PLANIKA_SITE_URL") or "https://planikaapp.com").rstrip("/")
# Analítica sin cookies (Cloudflare Web Analytics). El token es público por diseño: viaja en el HTML de cada página.
BEACON = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
          'data-cf-beacon=\'{"token":"4da50e67f6794aa597670cd65c807dde"}\'></script>')
CHUNK = 250  # planes por bloque de detalles
CAT_NAME = {k: n for k, n, _ in CATEGORIES}
CAT_ICON = {k: i for k, _, i in CATEGORIES}
CAT_KEYS = [k for k, _, _ in CATEGORIES]
LD_TYPE = {"musica": "MusicEvent", "escena": "TheaterEvent", "expos": "ExhibitionEvent", "cine": "ScreeningEvent",
           "deporte": "SportsEvent", "gastro": "FoodEvent", "infantil": "ChildrensEvent", "fiestas": "Festival",
           "charlas": "EducationEvent"}
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
_COMBINING = re.compile("[\u0300-\u036f]")
_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


# ---------------------------------------------------------------- utilidades

def event_slug(title):
    """Mismo algoritmo que slug() de app.js: la web calcula el nombre del archivo sin que viaje en los datos."""
    s = _COMBINING.sub("", unicodedata.normalize("NFD", str(title or ""))).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60].strip("-")


def event_file(e):
    s = event_slug(e["title"])
    return "%s%s.html" % (s + "-" if s else "", e["id"])


def unique_ids(events):
    """Quita planes con id repetido (rompen favoritos, enlaces y páginas); se queda con el primero."""
    seen = set()
    out = []
    for e in events:
        if e["id"] in seen or not _ID_RE.match(e["id"]):
            continue
        seen.add(e["id"])
        out.append(e)
    return out


def next_session(e, t0):
    if not e.get("sessions"):
        return e["start"]
    for d in e["sessions"]:
        if d >= t0:
            return d
    return e["sessions"][-1]


def _span(e):
    try:
        return (datetime.strptime(e["end"], "%Y-%m-%d") - datetime.strptime(e["start"], "%Y-%m-%d")).days
    except ValueError:
        return 0


def default_order(events, t0=None):
    """Orden de la lista por defecto de la web: así la primera pantalla solo necesita el bloque 0 de detalles."""
    t0 = t0 or iso(today())

    def key(e):
        # Las visitas permanentes van al final: no tapan los planes con fecha.
        perm = 1 if is_permanent(e) else 0
        return (perm, max(next_session(e, t0), t0), 0 if e.get("sessions") else min(99, _span(e)), e.get("time") or "99")
    return sorted(events, key=key)


def safe_url(u):
    u = (u or "").strip()
    return u if re.match(r"^https?://", u, re.I) else ""


def _trim(row):
    while row and row[-1] in ("", 0, None):
        row.pop()
    return row


def fmt_day(day):
    d = datetime.strptime(day, "%Y-%m-%d")
    return "%s %d %s %d" % (DIAS[d.weekday()], d.day, MESES[d.month - 1], d.year)


def _dshort(day):
    d = datetime.strptime(day, "%Y-%m-%d")
    return "%d %s" % (d.day, MESES[d.month - 1])


def short_when(e, t0):
    """Fecha corta para títulos: "21 nov", "21 nov–3 dic", "hasta el 15 ene"; vacío en visitas permanentes."""
    if is_permanent(e):
        return ""
    if e.get("sessions"):
        return _dshort(next_session(e, t0))
    if e["end"] != e["start"]:
        if e["start"] < t0:
            return "hasta el " + _dshort(e["end"])
        return "%s–%s" % (_dshort(e["start"]), _dshort(e["end"]))
    return _dshort(e["start"])


def clip(s, n):
    """Recorta en una palabra sin pasar de n caracteres (con "…")."""
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    cut = s[: n - 1].rsplit(" ", 1)[0].rstrip(" ,.;:-–·")
    return (cut or s[: n - 1]) + "…"


def seo_title(e, t0, place):
    """Título de la ficha: plan · fecha corta · lugar, sin pasar de ~60 caracteres (más " · Planika")."""
    tail = " · ".join(x for x in (short_when(e, t0), clip(place, 26)) if x)
    base = e.get("title_es") or e["title"]
    room = max(24, 58 - len(tail) - 3)
    base = clip(base, room)
    return "%s · %s" % (base, tail) if tail else base


def price_num(e):
    if e.get("free"):
        return 0.0
    m = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(e.get("price") or "").replace(",", "."))]
    # "De 0 a 18 €" (gratis para algunos): el precio de pago más bajo, no 0, que haría pasar el plan por gratuito
    paid = [x for x in m if x > 0]
    return min(paid) if paid else None


# ---------------------------------------------------------------- datos troceados

def write_data(out_dir, payload):
    """Escribe core.js (lo necesario para filtrar, ordenar, calendario y mapa) y d/<n>.js (descripción, enlaces, imagen).

    payload["events"] debe venir ya en default_order(). Devuelve (bytes de core.js, número de bloques)."""
    events = payload["events"]
    src_names = []
    for e in events:
        if e["source"] not in src_names:
            src_names.append(e["source"])
    rows = []
    for e in events:
        flags = (1 if e.get("free") else 0) | (2 if safe_url(e.get("tickets_url")) else 0)
        rows.append(_trim([
            e["id"], e["title"], CAT_KEYS.index(e["category"]) if e["category"] in CAT_KEYS else len(CAT_KEYS) - 1,
            e.get("subtype") or "", e["start"], e["end"], e.get("time") or "", e["province_code"],
            e.get("city") or "", e.get("venue") or "",
            None if e.get("lat") is None else round(e["lat"], 5), None if e.get("lon") is None else round(e["lon"], 5),
            e.get("price") or "", flags, e.get("audience") or "", src_names.index(e["source"]),
            e.get("sessions") or 0, e.get("title_es") or ""]))
    version = payload["updated_at"]
    core = {k: payload[k] for k in ("updated_at", "from", "to", "days", "categories", "provinces", "sources")}
    core.update({"v": version, "chunk": CHUNK, "srcNames": src_names, "events": rows})
    os.makedirs(out_dir, exist_ok=True)
    core_path = os.path.join(out_dir, "core.js")
    with open(core_path, "w", encoding="utf-8") as fh:
        # Si un bloque de detalles llega antes que app.js, se guarda en cola
        fh.write("window.PLANIKA_D=window.PLANIKA_D||function(v,n,r){(window.PLANIKA_Q=window.PLANIKA_Q||[]).push([v,n,r])};\n")
        fh.write("window.PLANES_CORE=")
        json.dump(core, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    d_dir = os.path.join(out_dir, "d")
    os.makedirs(d_dir, exist_ok=True)
    for fn in os.listdir(d_dir):
        if fn.endswith(".js"):
            os.remove(os.path.join(d_dir, fn))
    n_chunks = 0
    for n, i in enumerate(range(0, len(events), CHUNK)):
        det = [_trim([e.get("description") or "", safe_url(e.get("url")), safe_url(e.get("tickets_url")),
                      safe_url(e.get("image")), e.get("address") or ""]) for e in events[i:i + CHUNK]]
        with open(os.path.join(d_dir, "%d.js" % n), "w", encoding="utf-8") as fh:
            fh.write("PLANIKA_D(%s,%d," % (json.dumps(version), n))
            json.dump(det, fh, ensure_ascii=False, separators=(",", ":"))
            fh.write(");\n")
        n_chunks += 1
    return os.path.getsize(core_path), n_chunks


# ---------------------------------------------------------------- schema.org/Event

def _ld_date(e, day):
    t = e.get("time") or ""
    if not re.match(r"^\d\d:\d\d$", t) or ZoneInfo is None:
        return day
    try:
        tz = ZoneInfo("Atlantic/Canary" if e["province_code"] in ("35", "38") else "Europe/Madrid")
        return datetime.strptime(day + " " + t, "%Y-%m-%d %H:%M").replace(tzinfo=tz).isoformat()
    except Exception:  # noqa: BLE001 - sin base de zonas horarias se publica solo la fecha
        return day


def event_jsonld(e, canonical, t0=None):
    t0 = t0 or iso(today())
    if is_permanent(e):
        return place_jsonld(e, canonical)
    start = next_session(e, t0)
    end = start if e.get("sessions") else e["end"]
    place = {"@type": "Place", "name": e.get("venue") or e.get("city") or e.get("province") or "España",
             "address": {"@type": "PostalAddress", "addressCountry": "ES"}}
    if e.get("address"):
        place["address"]["streetAddress"] = e["address"]
    if e.get("city"):
        place["address"]["addressLocality"] = e["city"]
    if e.get("province"):
        place["address"]["addressRegion"] = e["province"]
    if e.get("lat") is not None and e.get("lon") is not None:
        place["geo"] = {"@type": "GeoCoordinates", "latitude": e["lat"], "longitude": e["lon"]}
    ld = {"@context": "https://schema.org", "@type": LD_TYPE.get(e["category"], "Event"),
          "name": e.get("title_es") or e["title"], "startDate": _ld_date(e, start), "endDate": end,
          "eventStatus": "https://schema.org/EventScheduled",
          "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "location": place, "url": canonical}
    if e.get("description"):
        ld["description"] = e["description"]
    if safe_url(e.get("image")):
        ld["image"] = [safe_url(e["image"])]
    tickets = safe_url(e.get("tickets_url"))
    if e.get("free") or tickets:
        # Sin "availability": las fuentes no dicen si quedan entradas y no se inventa.
        offer = {"@type": "Offer", "url": tickets or safe_url(e.get("url")) or canonical, "priceCurrency": "EUR"}
        p = price_num(e)
        if p is not None:
            offer["price"] = ("%.2f" % p).rstrip("0").rstrip(".") if p else "0"
        ld["offers"] = offer
    return ld


def place_jsonld(e, canonical):
    """Las visitas permanentes (museos, monumentos, espacios naturales) no son eventos: Google pide no marcarlas
    como Event. Se describen como TouristAttraction con su dirección y coordenadas."""
    addr = {"@type": "PostalAddress", "addressCountry": "ES"}
    if e.get("address"):
        addr["streetAddress"] = e["address"]
    if e.get("city"):
        addr["addressLocality"] = e["city"]
    if e.get("province"):
        addr["addressRegion"] = e["province"]
    ld = {"@context": "https://schema.org", "@type": "TouristAttraction", "name": e.get("title_es") or e["title"],
          "url": canonical, "address": addr}
    if e.get("lat") is not None and e.get("lon") is not None:
        ld["geo"] = {"@type": "GeoCoordinates", "latitude": e["lat"], "longitude": e["lon"]}
    if e.get("description"):
        ld["description"] = e["description"]
    if safe_url(e.get("image")):
        ld["image"] = [safe_url(e["image"])]
    if safe_url(e.get("url")):
        ld["sameAs"] = safe_url(e["url"])
    if e.get("free"):
        ld["isAccessibleForFree"] = True
    return ld


# ---------------------------------------------------------------- una página por plan

_EVENT_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(seo_title)s · Planika</title><meta name="description" content="%(desc)s">
<link rel="canonical" href="%(canonical)s">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta name="robots" content="%(robots)s">
<meta property="og:title" content="%(title)s"><meta property="og:description" content="%(desc)s">
<meta property="og:url" content="%(canonical)s"><meta property="og:image" content="%(og_image)s">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="%(title)s"><meta name="twitter:description" content="%(desc)s"><meta name="twitter:image" content="%(og_image)s"><meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="../styles.css"><link rel="icon" href="../icon.svg" type="image/svg+xml">
<script type="application/ld+json">%(jsonld)s</script>
%(analytics)s
</head><body>
<header class="hero evhero"><div class="wrap"><a class="evbrand" href="../">Planika</a>
<p class="tagline">%(cat)s en %(province)s</p></div></header>
<main class="wrap">
%(crumbs)s
<article class="card pop%(pop)d evpage">%(img)s<div class="body">
<div class="badges"><span class="badge">%(cat)s</span>%(price)s</div>
<h1>%(title)s</h1>
<div class="when">📅 %(when)s</div>%(sessions)s
<div class="where">📍 %(where)s</div>
%(body)s
<div class="actions">%(actions)s</div>
<div class="src">Fuente: %(source)s%(srclink)s. %(updated)sComprueba siempre fechas y precios en la web del organizador.</div>
</div></article>
<nav class="foot evnav"><h2 class="sticker">Más planes</h2>%(related)s
<p>%(city_link)s<a href="../p/%(prov_file)s">Todos los planes en %(province)s</a> · <a href="../t/%(cat_key)s.html">%(cat)s en toda España</a> · <a href="../promociona-tu-evento.html">Publica tu evento gratis</a> · <a href="../">Buscar en Planika</a> · <a href="../privacidad.html">Privacidad y cookies</a> · <a href="../aviso-legal.html">Aviso legal</a></p></nav>
</main></body></html>
"""


def _pop(eid):
    h = 0
    for ch in str(eid):
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h % 4


def _when(e, t0):
    if is_permanent(e):
        return "Visita permanente"
    t = (" · " + e["time"]) if e.get("time") else ""
    if e.get("sessions"):
        return fmt_day(next_session(e, t0)) + t
    if e["end"] != e["start"]:
        if e["start"] < t0:
            return "Hasta el " + fmt_day(e["end"]) + t
        return "%s – %s%s" % (fmt_day(e["start"]), fmt_day(e["end"]), t)
    return fmt_day(e["start"]) + t


def _gcal(e, t0):
    from urllib.parse import quote
    start = next_session(e, t0)
    end = start if e.get("sessions") else e["end"]
    if is_permanent(e):
        # Un recordatorio de un día, no un bloque de un año en el calendario.
        start = end = t0
    if re.match(r"^\d\d:\d\d$", e.get("time") or ""):
        hh = int(e["time"][:2]) + 2
        s = start.replace("-", "") + "T" + e["time"].replace(":", "") + "00"
        d2 = datetime.strptime(start, "%Y-%m-%d")
        if hh >= 24:
            hh -= 24
            d2 = d2.fromordinal(d2.toordinal() + 1)
        f = d2.strftime("%Y%m%d") + "T%02d%s00" % (hh, e["time"][3:])
    else:
        s = start.replace("-", "")
        d2 = datetime.strptime(end, "%Y-%m-%d")
        f = d2.fromordinal(d2.toordinal() + 1).strftime("%Y%m%d")
    loc = ", ".join(x for x in (e.get("venue"), e.get("address"), e.get("city"), e.get("province")) if x)
    return ("https://calendar.google.com/calendar/render?action=TEMPLATE&text=%s&dates=%s/%s&location=%s&ctz=Europe/Madrid"
            % (quote(e.get("title_es") or e["title"]), s, f, quote(loc)))


def event_page(e, related=(), t0=None, prov_slug="", city=None, title_place=None, updated="", indexable=None):
    """city: (nombre, archivo sin .html) si la ciudad tiene página propia. title_place: lugar para el <title>
    (se usa la sala cuando hay varios planes con el mismo nombre y fecha en la misma ciudad)."""
    t0 = t0 or iso(today())
    esc = html.escape
    title = e.get("title_es") or e["title"]
    canonical = "%s/e/%s" % (SITE_URL, event_file(e))
    if indexable is None:
        indexable = seo.is_indexable(e)
    cat = "%s %s" % (CAT_ICON.get(e["category"], "✨"), CAT_NAME.get(e["category"], "Otros planes"))
    where = " · ".join(x for x in (e.get("venue"), e.get("address"), e.get("city"),
                                   e.get("province") if e.get("province") != e.get("city") else "") if x)
    when = _when(e, t0)
    place = e.get("city") or e.get("province") or "España"
    desc = clip("%s. %s. %s" % (when, where or place, e.get("description") or "Fechas, lugar y enlace a la web oficial en Planika."), 158)
    image = safe_url(e.get("image"))
    tickets, url = safe_url(e.get("tickets_url")), safe_url(e.get("url"))
    actions = []
    if tickets:
        actions.append('<a class="btn primary" href="%s" target="_blank" rel="noopener">🎫 Entradas</a>' % esc(tickets))
    if url and url != tickets:
        actions.append('<a class="btn" href="%s" target="_blank" rel="noopener">Más info ↗</a>' % esc(url))
    actions.append('<a class="btn" href="%s" target="_blank" rel="noopener">＋ Google Calendar</a>' % esc(_gcal(e, t0)))
    actions.append('<a class="btn" href="../?e=%s">Abrir en Planika</a>' % esc(e["id"]))
    sessions = ""
    if e.get("sessions"):
        up = [d for d in e["sessions"] if d >= t0] or e["sessions"][-1:]
        sessions = '<div class="sessions">Fechas: %s%s</div>' % (
            ", ".join(fmt_day(d) for d in up[:12]), (" y %d más" % (len(up) - 12)) if len(up) > 12 else "")
    price = '<span class="badge free">Gratis</span>' if e.get("free") else (
        '<span class="badge">%s</span>' % esc(e["price"]) if e.get("price") else "")
    if is_permanent(e):
        price += '<span class="badge">Permanente</span>'
    rel = ""
    if related:
        rel = "<ul>%s</ul>" % "".join('<li><a href="%s">%s</a> · %s%s</li>' % (
            esc(event_file(r)), esc(r.get("title_es") or r["title"]), esc(_when(r, t0)),
            (" · " + esc(r["city"])) if r.get("city") else "") for r in related)
    ld_event = event_jsonld(e, canonical, t0)
    ld_event.pop("@context", None)
    crumbs = [{"@type": "ListItem", "position": 1, "name": "Inicio", "item": SITE_URL + "/"}]
    if prov_slug:
        crumbs.append({"@type": "ListItem", "position": 2, "name": e.get("province") or "Provincia",
                       "item": "%s/p/%s.html" % (SITE_URL, prov_slug)})
    if city:
        crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": city[0],
                       "item": "%s/c/%s.html" % (SITE_URL, city[1])})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": title, "item": canonical})
    ld_doc = {"@context": "https://schema.org", "@graph": [ld_event,
              {"@type": "BreadcrumbList", "itemListElement": crumbs}]}
    ld = json.dumps(ld_doc, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return _EVENT_PAGE % dict(
        title=esc(title), seo_title=esc(seo_title(e, t0, title_place or place)), desc=esc(desc), canonical=esc(canonical),
        robots="index,follow,max-image-preview:large" if indexable else "noindex,follow",
        updated=('<span class="upd">Agenda actualizada el %s. </span>' % esc(updated)) if updated else "",
        city_link=('<a href="../c/%s.html">Planes en %s</a> · ' % (esc(city[1]), esc(city[0]))) if city else "",
        og_image=esc(image or SITE_URL + "/og.jpg"), jsonld=ld, analytics=BEACON, cat=esc(cat), cat_key=esc(e["category"]),
        crumbs=('<nav class="crumbs" aria-label="Migas de pan"><a href="../">Inicio</a> › '
                + ('<a href="../p/%s.html">%s</a> › ' % (esc(prov_slug), esc(e.get("province") or "Provincia")) if prov_slug else '')
                + ('<a href="../c/%s.html">%s</a> › ' % (esc(city[1]), esc(city[0])) if city else '')
                + '<span aria-current="page">%s</span></nav>' % esc(title)),
        province=esc(e.get("province") or "España"), prov_file=esc(prov_slug) + ".html", pop=_pop(e["id"]),
        img=('<img src="%s" alt="%s" fetchpriority="high" decoding="async" onerror="this.remove()">' % (esc(image), esc(title))) if image else "",
        price=price, when=esc(when), sessions=sessions, where=esc(where or place),
        body=('<p class="desc">%s</p>' % esc(e["description"])) if e.get("description") else "",
        actions="".join(actions), source=esc(e["source"]), related=rel,
        srclink=(' · <a href="%s" target="_blank" rel="noopener">ver en la web oficial ↗</a>' % esc(url or tickets)) if (url or tickets) else "")


def _event_digest(e, t0, indexable):
    """Huella de lo que muestra la ficha del propio plan (no de la lista de "Más planes", que rota a diario)."""
    keys = ("title", "title_es", "start", "end", "time", "venue", "address", "city", "province", "description",
            "price", "free", "image", "url", "tickets_url", "category", "source")
    core = [e.get(k) for k in keys] + [_when(e, t0), [d for d in e.get("sessions") or [] if d >= t0], indexable]
    return seo.digest(json.dumps(core, ensure_ascii=False, sort_keys=True))


def write_event_pages(site_dir, events, prov_slugs, cities=None, updated=""):
    """Una página por plan en site/e/. prov_slugs: código de provincia -> nombre de archivo (sin .html) de su página.
    cities: (código de provincia, ciudad normalizada) -> (nombre, archivo) de las ciudades con página propia.

    Devuelve [(ruta, indexable, huella)]."""
    from .util import norm
    t0 = iso(today())
    cities = cities or {}
    # Planes que compartirían título (mismo nombre, fecha y ciudad): en el <title> se usa la sala.
    seen_titles = {}
    for e in events:
        k = (seo_title(e, t0, e.get("city") or e.get("province") or "España"))
        seen_titles[k] = seen_titles.get(k, 0) + 1
    out_dir = os.path.join(site_dir, "e")
    os.makedirs(out_dir, exist_ok=True)
    for fn in os.listdir(out_dir):
        if fn.endswith(".html"):
            os.remove(os.path.join(out_dir, fn))
    groups = {}
    for e in events:
        groups.setdefault((e["province_code"], e["category"]), []).append(e)
    pos = {}
    for items in groups.values():
        for idx, e in enumerate(items):
            pos[e["id"]] = idx
    pages = []
    for e in events:
        same = groups[(e["province_code"], e["category"])]
        i = pos[e["id"]]
        related, seen = [], {e["id"]}
        for r in same[i + 1:i + 7] + same[:6]:
            if r["id"] not in seen:
                seen.add(r["id"])
                related.append(r)
        related = related[:6]
        fn = event_file(e)
        place = e.get("city") or e.get("province") or "España"
        title_place = None
        if seen_titles.get(seo_title(e, t0, place), 0) > 1:
            title_place = e.get("venue") or e.get("address") or None
        indexable = seo.is_indexable(e)
        city = cities.get((e["province_code"], norm(e.get("city") or "")))
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(event_page(e, related, t0, prov_slugs.get(e["province_code"], ""), city=city,
                                title_place=title_place, updated=updated, indexable=indexable))
        pages.append(("e/" + fn, indexable, _event_digest(e, t0, indexable)))
    return pages
