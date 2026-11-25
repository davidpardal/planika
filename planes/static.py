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
from .util import SMALL_WORDS, clean_title, country, display_title, is_permanent, iso, norm, series_split, today

SITE_URL = (os.environ.get("PLANIKA_SITE_URL") or "https://planikaapp.com").rstrip("/")
# GA4 se carga desde consent.js únicamente tras aceptación explícita.
# i18n.js: idioma de la interfaz (menús, botones y pie) en las páginas generadas; el contenido sigue en español
BEACON = '<script defer src="/consent.js"></script><script defer src="/i18n.js"></script>'
CHUNK = 250  # planes por bloque de detalles
CAT_NAME = {k: n for k, n, _ in CATEGORIES}
CAT_ICON = {k: i for k, _, i in CATEGORIES}
CAT_KEYS = [k for k, _, _ in CATEGORIES]
# App instalable en todas las páginas: quien llega a una ficha desde Google también puede instalarla, y lo
# que visita queda guardado para verlo sin conexión (site/sw.js). Va con la analítica en la cabecera.
PWA_HEAD = ('<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/apple-touch-icon.png">'
            '<script>if("serviceWorker"in navigator)addEventListener("load",function(){navigator.serviceWorker.register("/sw.js")})</script>')
BEACON += PWA_HEAD
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


def _shown_title(e):
    """Título limpio para la web (r[18]) solo cuando difiere del que ya viaja: e["title"] no se cambia porque de él
    sale el nombre del archivo de la ficha (slug() de app.js), que Google ya tiene indexado."""
    t = display_title(e)
    return "" if t == (e.get("title_es") or e["title"]) else t


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


_CLIP_TAIL = re.compile(r"(?:\s+(?:%s))+$" % "|".join(sorted(SMALL_WORDS, key=len, reverse=True)), re.I)


def clip(s, n):
    """Recorta en una palabra sin pasar de n caracteres (con "…"), sin dejar un paréntesis o unas comillas
    abiertos ni una palabra suelta al final («Concierto de la Orquesta de…» -> «Concierto de la Orquesta…»)."""
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    cut = s[: n - 1].rsplit(" ", 1)[0] if " " in s[: n - 1] else ""
    if cut.count("(") > cut.count(")") and cut.rfind("(") > 8:  # «Museo San Telmo (exposición…» -> «Museo San Telmo…»
        cut = cut[:cut.rfind("(")]
    # Comillas abiertas: se quitan solo si queda casi todo (lo entrecomillado suele ser el título de verdad)
    for o, c in (("«", "»"), ("“", "”"), ('"', None)):
        open_ = cut.count(o) % 2 if c is None else cut.count(o) > cut.count(c)
        if open_ and cut.rfind(o) >= 0.6 * n:
            cut = cut[:cut.rfind(o)]
    cut = _CLIP_TAIL.sub("", cut.rstrip(" ,.;:-–·+&/")).rstrip(" ,.;:-–·+&/")
    first = cut[:1]
    if (first in "\"'" and cut.count(first) % 2) or (first in "«“" and not any(x in cut for x in "»”")):
        cut = cut[1:]  # comillas abiertas al principio que ya no se cierran
    return (cut or s[: n - 1]) + "…"


TITLE_MAX = 65   # caracteres del título de la ficha sin " | Planika" (Google corta hacia los 60-65)
NAME_MIN = 30    # el nombre del plan es lo que se busca: no se recorta por debajo de esto


def title_when(e, t0):
    """Fecha del <title>: «sáb 27 feb» (con el día de la semana, que es lo que se mira al elegir plan),
    «21 nov–3 dic», «hasta el 15 ene»; vacío en visitas permanentes."""
    s = short_when(e, t0)
    if s and "–" not in s and not s.startswith("hasta"):
        day = next_session(e, t0) if e.get("sessions") else e["start"]
        s = "%s %s" % (DIAS[datetime.strptime(day, "%Y-%m-%d").weekday()], s)
    return s


# Primera palabra de los nombres de ciclo, club o tipo de acto: «Curso de Derechos Humanos: "Islam y democracia"»,
# «Documental: "Gaza"», «Conferència "Egipte…"». Lo concreto es lo que va detrás.
_GENERIC = set("""curso cursos ciclo cicle club taller talleres tallers concierto conciertos concert concerts conferencia
conferencias documental documentales exposicion exposicio exposiciones expo festival fest jaialdia tertulia tertulias
visita visitas charla charlas xerrada xerrades cine cinema cineforum ballet teatro teatre proyeccion presentacion
presentacio mesa jornada jornadas jornades encuentro encuentros seminario temporada programa muestra mostra feria fira
mercado mercat ruta recital espectaculo espectacle obra opera musical danza dansa monologo monologos lectura
cuentacuentos contacontes ipuin kontzertua kontzertuak erakusketa hitzaldia tailerra zinema antzerkia bisita gala
homenaje candlelight cinefórum""".split())
_OPEN_Q = {'"': '"', "«": "»", "“": "”", "'": "'’", "‘": "’'", "`": "´'"}


def _series_label(prefix, place):
    """¿Lo de antes de los dos puntos o de las comillas es un ciclo, un club o el tipo de acto, y no un artista?
    «Ciclo Bernaola 2026-2027», «Club de lectura infantil», «CANDLELIGHT Vitoria-Gasteiz», «Documental» sí;
    «Jordi Meca», «Ainara Ortega & Joaquín Chacón» no (es lo que se busca)."""
    words = re.findall(r"[^\W\d_]+", prefix)
    if not words:
        return True
    if re.search(r"\b(?:19|20)\d\d\b", prefix) or (place and norm(place) in norm(prefix)) or norm(words[0]) in _GENERIC:
        return True
    return any(w.islower() and w not in SMALL_WORDS for w in words)


def _quoted(name):
    """«Conferència "Egipte. Deir El-Medina"» -> ("Conferència", "Egipte. Deir El-Medina", resto)."""
    for i, ch in enumerate(name):
        if ch in _OPEN_Q and (i == 0 or name[i - 1] in " :"):
            for j in range(i + 1, len(name)):
                if name[j] in _OPEN_Q[ch] and (j + 1 == len(name) or not name[j + 1].isalpha()):
                    q = name[i + 1:j].strip()
                    return (name[:i].strip(" :-–"), q, name[j + 1:].strip()) if len(q) >= 4 else None
            return None
    return None


def _short_names(name, place):
    """Nombres más cortos y concretos para el <title> cuando el entero no cabe, del mejor al peor."""
    out = []
    parts = series_split(name)
    if parts and _series_label(parts[0], place) and not parts[1][:1].islower():
        out.append(parts[1])
    q = _quoted(name)
    if q and _series_label(q[0], place) and not q[1][:1].islower():
        post = q[2]
        out.append(q[1] + (" " + post if re.fullmatch(r"\([^()]{2,40}\)", post) else ""))
        out.append(q[1])
    out = [clean_title(x) for x in out]  # «EIDOLON. ENTRE LA REALIDAD Y LOS SUEÑOS» -> «Eidolon. Entre la Realidad…»
    return [x for x in out if x and x != name]


def seo_title(e, t0, place, full=False):
    """Título de la ficha: «Ara Malikian en Vitoria-Gasteiz · sáb 27 feb» (más " | Planika"), en unos 60 caracteres.

    Lo que se busca es el nombre y la ciudad («ara malikian vitoria»), así que van primero y nunca se cortan a
    media palabra. Si no cabe todo, por orden: se quita el día de la semana; de «Ciclo Bernaola 2026-2027: Trío
    Zukan» queda «Trío Zukan»; se recorta el final del nombre (no por debajo de NAME_MIN); y, en último caso, se
    quita la fecha. La ciudad no se repite si el nombre ya la lleva («Feria de Navidad de Bilbao»).
    full: el nombre no se recorta nunca (planes que solo se distinguen por el final del nombre)."""
    when, day = title_when(e, t0), short_when(e, t0)
    place = " ".join(str(place or "").split())

    def tails(name):
        where = (" en " + place) if place and norm(place) not in norm(name) else ""
        return where, [where + ((" · " + w) if w else "") for w in (when, day)]  # con y sin día de la semana

    name = " ".join(display_title(e).split())
    where, ts = tails(name)
    if full:
        return name + ts[0]
    for tail in ts:
        if len(name) + len(tail) <= TITLE_MAX:
            return name + tail
    alts = _short_names(name, place)
    for alt in alts:
        where, ts = tails(alt)
        for tail in ts:
            if len(alt) + len(tail) <= TITLE_MAX:
                return alt + tail
    if alts:  # tampoco cabe: se recorta el nombre concreto, no el del ciclo
        name = alts[-1]
    where, ts = tails(name)
    room = TITLE_MAX - len(ts[-1])
    if room >= NAME_MIN:
        short = clip(name, room)
        return short + (ts[0] if len(short) + len(ts[0]) <= TITLE_MAX else ts[-1])
    return clip(name, max(NAME_MIN, TITLE_MAX - len(where))) + where


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
        flags = (1 if e.get("free") else 0) | (2 if safe_url(e.get("tickets_url")) else 0) | (4 if e.get("xmas") else 0)
        rows.append(_trim([
            e["id"], e["title"], CAT_KEYS.index(e["category"]) if e["category"] in CAT_KEYS else len(CAT_KEYS) - 1,
            e.get("subtype") or "", e["start"], e["end"], e.get("time") or "", e["province_code"],
            e.get("city") or "", e.get("venue") or "",
            None if e.get("lat") is None else round(e["lat"], 5), None if e.get("lon") is None else round(e["lon"], 5),
            e.get("price") or "", flags, e.get("audience") or "", src_names.index(e["source"]),
            e.get("sessions") or 0, e.get("title_es") or "", _shown_title(e)]))
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
             "address": {"@type": "PostalAddress", "addressCountry": country(e.get("province_code"))}}
    if e.get("address"):
        place["address"]["streetAddress"] = e["address"]
    if e.get("city"):
        place["address"]["addressLocality"] = e["city"]
    if e.get("province"):
        place["address"]["addressRegion"] = e["province"]
    if e.get("lat") is not None and e.get("lon") is not None:
        place["geo"] = {"@type": "GeoCoordinates", "latitude": e["lat"], "longitude": e["lon"]}
    ld = {"@context": "https://schema.org", "@type": LD_TYPE.get(e["category"], "Event"),
          "name": display_title(e), "startDate": _ld_date(e, start), "endDate": end,
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
    addr = {"@type": "PostalAddress", "addressCountry": country(e.get("province_code"))}
    if e.get("address"):
        addr["streetAddress"] = e["address"]
    if e.get("city"):
        addr["addressLocality"] = e["city"]
    if e.get("province"):
        addr["addressRegion"] = e["province"]
    ld = {"@context": "https://schema.org", "@type": "TouristAttraction", "name": display_title(e),
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


def stamp_index(site_dir):
    """Pone ?v=<huella> en los recursos que carga la portada (estilos, datos y app).

    Si el navegador guarda en caché un index.html de una versión y un app.js de otra, la app se rompe
    (p. ej. busca un elemento que ya no existe y la lista no se pinta). Con la huella en la URL, cada
    index.html carga siempre los archivos de su misma versión."""
    import hashlib
    path = os.path.join(site_dir, "index.html")
    try:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
    except OSError:
        return False
    out = page
    for name in ("styles.css", "i18n.js", "app.js", "data/core.js", "data/d/0.js"):
        try:
            with open(os.path.join(site_dir, name), "rb") as fh:
                v = hashlib.sha1(fh.read()).hexdigest()[:10]
        except OSError:
            continue
        out = re.sub(r'((?:href|src)=")%s(?:\?v=[^"]*)?"' % re.escape(name), r'\g<1>%s?v=%s"' % (name, v), out)
    if out != page:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
    return out != page


# ---------------------------------------------------------------- una página por plan

_EVENT_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(seo_title)s | Planika</title><meta name="description" content="%(desc)s">
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
<p>%(city_link)s<a href="../p/%(prov_file)s">Todos los planes en %(province)s</a> · <a href="../t/%(cat_key)s.html">%(cat)s en toda España</a> · <a href="../promociona-tu-evento.html">Publica tu evento gratis</a> · <a href="../">Buscar en Planika</a> · <a href="../privacidad.html">Privacidad y cookies</a> · <a href="../privacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="../aviso-legal.html">Aviso legal</a> · <a href="https://www.instagram.com/planikaapp/" target="_blank" rel="noopener">Instagram</a></p></nav>
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
            % (quote(display_title(e)), s, f, quote(loc)))


def event_page(e, related=(), t0=None, prov_slug="", city=None, title_place=None, updated="", indexable=None, title_full=False):
    """city: (nombre, archivo sin .html) si la ciudad tiene página propia. title_place: lugar para el <title>
    (se usa la sala cuando hay varios planes con el mismo nombre y fecha en la misma ciudad). title_full: el
    <title> lleva el nombre entero (planes que solo se distinguen por el final del nombre)."""
    t0 = t0 or iso(today())
    esc = html.escape
    title = display_title(e)
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
    # Lo añade a «Crear tu plan» en la app (se guarda en el móvil); nofollow: no es una página para buscadores
    actions.append('<a class="btn" href="../?add=%s" rel="nofollow">＋ Mi plan</a>' % esc(e["id"]))
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
            esc(event_file(r)), esc(display_title(r)), esc(_when(r, t0)),
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
        title=esc(title), seo_title=esc(seo_title(e, t0, title_place or place, title_full)), desc=esc(desc), canonical=esc(canonical),
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
        srclink=(' · <a href="%s" target="_blank" rel="noopener">%s ↗</a>' % (
            esc(url or tickets), "ver la fuente" if e.get("source") == "Selección Planika" else "ver en la web oficial"))
                 if (url or tickets) else "")


def _event_digest(e, t0, indexable):
    """Huella de lo que muestra la ficha del propio plan (no de la lista de "Más planes", que rota a diario)."""
    keys = ("title", "title_es", "start", "end", "time", "venue", "address", "city", "province", "description",
            "price", "free", "image", "url", "tickets_url", "category", "source")
    core = [e.get(k) for k in keys] + [_when(e, t0), [d for d in e.get("sessions") or [] if d >= t0], indexable,
                                       display_title(e), title_when(e, t0)]
    return seo.digest(json.dumps(core, ensure_ascii=False, sort_keys=True))


def write_event_pages(site_dir, events, prov_slugs, cities=None, updated=""):
    """Una página por plan en site/e/. prov_slugs: código de provincia -> nombre de archivo (sin .html) de su página.
    cities: (código de provincia, ciudad normalizada) -> (nombre, archivo) de las ciudades con página propia.

    Devuelve [(ruta, indexable, huella)]."""
    from .util import norm
    t0 = iso(today())
    cities = cities or {}
    # Planes que compartirían título: primero se prueba con el nombre entero (cursos que solo se distinguen por
    # el nivel del final: «…iniciació», «…avançat»); si aún coinciden (mismo nombre, fecha y ciudad), con la sala.
    from collections import Counter
    def where(e):
        return e.get("city") or e.get("province") or "España"
    seen_titles = Counter(seo_title(e, t0, where(e)) for e in events)
    seen_full = Counter(seo_title(e, t0, where(e), True) for e in events if seen_titles[seo_title(e, t0, where(e))] > 1)
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
        title_place, title_full = None, False
        if seen_titles[seo_title(e, t0, place)] > 1:
            title_full = True
            if seen_full[seo_title(e, t0, place, True)] > 1:
                title_place = e.get("venue") or e.get("address") or None
        indexable = seo.is_indexable(e)
        city = cities.get((e["province_code"], norm(e.get("city") or "")))
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(event_page(e, related, t0, prov_slugs.get(e["province_code"], ""), city=city,
                                title_place=title_place, updated=updated, indexable=indexable, title_full=title_full))
        pages.append(("e/" + fn, indexable, _event_digest(e, t0, indexable)))
    return pages


# ---------------------------------------------------------------- fichas que desaparecen

GONE_DAYS = 60  # días que sigue publicada (con aviso y noindex) la ficha de un plan que ya no está en la agenda

_GONE_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s (%(state)s) · Planika</title><meta name="description" content="%(desc)s">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="%(canonical)s">%(refresh)s
<meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="../styles.css"><link rel="icon" href="../icon.svg" type="image/svg+xml">
%(analytics)s
</head><body>
<header class="hero evhero"><div class="wrap"><a class="evbrand" href="../">Planika</a>
<p class="tagline">%(cat)s en %(province)s</p></div></header>
<main class="wrap">
<article class="card evpage"><div class="body">
<div class="badges"><span class="badge">%(cat)s</span><span class="badge">%(badge)s</span></div>
<h1>%(title)s</h1>
<div class="when">📅 %(when)s</div>
<div class="where">📍 %(where)s</div>
<p class="desc">%(msg)s</p>
<div class="actions">%(actions)s</div>
</div></article>
<nav class="foot evnav"><h2 class="sticker">%(rel_title)s</h2>%(related)s
<p>%(links)s</p></nav>
</main></body></html>
"""


def ficha_meta(e):
    """Lo mínimo para rehacer la ficha de un plan cuando ya no esté en la agenda."""
    m = {"id": e["id"], "t": e.get("title_es") or e["title"], "s": e["start"], "e": e["end"], "k": e["category"],
         "pc": e["province_code"], "p": e.get("province") or "", "c": e.get("city") or "", "v": e.get("venue") or ""}
    return {k: v for k, v in m.items() if v != ""}


def _gone_when(m):
    if m["s"] == m["e"]:
        return fmt_day(m["s"])
    return "del %s al %s" % (fmt_day(m["s"]), fmt_day(m["e"]))


def gone_page(fn, m, t0, upcoming=(), prov_slug="", city=None, moved_to=None):
    """Ficha de un plan que ya no está en la agenda: aviso, planes parecidos próximos y enlaces, con noindex.
    Si el plan sigue en la agenda con otra dirección (cambió el título), redirige a su ficha nueva."""
    from .util import norm
    esc = html.escape
    title = clean_title(m["t"], m.get("v") or "", m.get("c") or "")
    cat = "%s %s" % (CAT_ICON.get(m["k"], "✨"), CAT_NAME.get(m["k"], "Otros planes"))
    where = " · ".join(x for x in (m.get("v"), m.get("c"), m.get("p") if m.get("p") != m.get("c") else "") if x) or "España"
    canonical, refresh = "%s/e/%s" % (SITE_URL, fn), ""
    if moved_to:
        state, badge = "ha cambiado", "Ficha actualizada"
        msg = "La ficha de este plan ha cambiado de dirección."
        canonical = "%s/e/%s" % (SITE_URL, moved_to)
        refresh = '\n<meta http-equiv="refresh" content="0; url=%s">' % esc(moved_to)
        actions = '<a class="btn primary" href="%s">Ver la ficha actualizada</a>' % esc(moved_to)
    elif m["e"] < t0:
        state, badge = "ya pasó", "Ya pasó"
        msg = "Este plan ya pasó. Abajo tienes planes parecidos en los próximos días."
        actions = '<a class="btn primary" href="../">Buscar planes en Planika</a>'
    else:
        state, badge = "ya no está en la agenda", "Ya no está en la agenda"
        msg = ("Este plan ya no aparece en la agenda de la que lo tomamos: puede que se haya cancelado, cambiado de fecha "
               "o que la fuente lo haya retirado. Consulta la web del organizador antes de ir.")
        actions = '<a class="btn primary" href="../">Buscar planes en Planika</a>'
    # Parecidos: misma ciudad y tipo, luego misma provincia y tipo, luego misma provincia.
    pool, seen = [], set()
    ncity = norm(m.get("c") or "")
    for test in (lambda e: e["category"] == m["k"] and norm(e.get("city") or "") == ncity and ncity,
                 lambda e: e["category"] == m["k"], lambda e: True):
        for e in upcoming:
            if len(pool) >= 6:
                break
            if e["province_code"] == m["pc"] and e["id"] not in seen and test(e):
                seen.add(e["id"])
                pool.append(e)
    related = ""
    if pool:
        related = "<ul>%s</ul>" % "".join('<li><a href="%s">%s</a> · %s%s</li>' % (
            esc(event_file(r)), esc(display_title(r)), esc(_when(r, t0)),
            (" · " + esc(r["city"])) if r.get("city") else "") for r in pool)
    links = []
    if city:
        links.append('<a href="../c/%s.html">Planes en %s</a>' % (esc(city[1]), esc(city[0])))
    if prov_slug:
        links.append('<a href="../p/%s.html">Todos los planes en %s</a>' % (esc(prov_slug), esc(m.get("p") or "la provincia")))
    links.append('<a href="../t/%s.html">%s en toda España</a>' % (esc(m["k"]), esc(cat)))
    links.append('<a href="../">Buscar en Planika</a>')
    return _GONE_PAGE % dict(
        title=esc(title), state=state, badge=badge, msg=esc(msg), canonical=esc(canonical), refresh=refresh,
        desc=esc(clip("%s. %s. %s" % (title, _gone_when(m), msg), 158)), analytics=BEACON, cat=esc(cat),
        province=esc(m.get("p") or "España"), when=esc(_gone_when(m)), where=esc(where), actions=actions,
        rel_title="Planes parecidos próximos" if pool else "Más planes", related=related, links=" · ".join(links))


def write_gone_pages(site_dir, events, state_path, prov_slugs, cities=None, t0=None):
    """Mantiene GONE_DAYS días las fichas de los planes que han salido de la agenda (ya pasaron, se cancelaron o
    cambiaron de dirección), para que quien llegue desde Google o un enlace compartido no se encuentre un 404.
    El estado (fichas publicadas y fecha en que desaparecieron) se guarda en state_path entre ejecuciones.
    Devuelve el número de fichas de este tipo escritas."""
    from datetime import timedelta
    from .util import norm
    t0 = t0 or iso(today())
    cities = cities or {}
    try:
        with open(state_path, encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        old = {}
    current = {event_file(e): e for e in events}
    by_id = {e["id"]: fn for fn, e in current.items()}
    # Mismo plan con otro id (algunas fuentes lo cambian de un día a otro, o se unió con su duplicado de otra fuente):
    # mismo nombre, mismo día y misma provincia.
    # Solo si la clave es única a ambos lados: hay muchos planes distintos con el mismo nombre el mismo día
    # (p. ej. los «Taller de pilates» de cada centro cívico de Barcelona) y no se debe mandar a otro.
    by_key, dup = {}, set()
    for fn, e in current.items():
        k = (norm(e.get("title_es") or e["title"]), e["start"], e["province_code"])
        if k in by_key:
            dup.add(k)
        by_key[k] = fn
    old_keys = {}
    for m in old.values():
        k = (norm(m.get("t") or ""), m.get("s"), m.get("pc"))
        old_keys[k] = old_keys.get(k, 0) + 1
    for k, c in old_keys.items():
        if c > 1:
            dup.add(k)
    for k in dup:
        by_key.pop(k, None)
    limit = iso(datetime.strptime(t0, "%Y-%m-%d") - timedelta(days=GONE_DAYS))
    upcoming = sorted((e for e in events if not is_permanent(e) and e["end"] >= t0),
                      key=lambda e: (max(e["start"], t0), e.get("time") or "99"))
    state = {fn: ficha_meta(e) for fn, e in current.items()}
    out_dir = os.path.join(site_dir, "e")
    n = 0
    for fn, m in old.items():
        if fn in current or not (fn.endswith(".html") and _ID_RE.match(fn[:-5])):
            continue
        gone = m.get("g") or t0
        if gone < limit:
            continue  # pasado el plazo, la dirección deja de existir (404)
        m = dict(m, g=gone)
        state[fn] = m
        moved = by_id.get(m.get("id")) or by_key.get((norm(m.get("t") or ""), m.get("s"), m.get("pc")))
        city = cities.get((m.get("pc"), norm(m.get("c") or "")))
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(gone_page(fn, m, t0, upcoming, prov_slugs.get(m.get("pc"), ""), city, moved))
        n += 1
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:  # una ficha por línea: el diff diario en git es pequeño
        fh.write("{\n" + ",\n".join("%s:%s" % (json.dumps(k, ensure_ascii=False), json.dumps(state[k], ensure_ascii=False, sort_keys=True))
                                     for k in sorted(state)) + "\n}\n")
    os.replace(tmp, state_path)
    return n
