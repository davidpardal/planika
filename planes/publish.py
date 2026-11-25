# -*- coding: utf-8 -*-
"""Salidas derivadas: agrupación de sesiones, salud de fuentes, feeds RSS, páginas estáticas y sitemap."""
import html
import json
import os
import re
from datetime import datetime, timedelta

from . import legal, seo, static
from .classify import CATEGORIES
from .util import PROVINCIAS, display_title, is_permanent, iso, norm, now_madrid, stamp, today

SITE_URL = static.SITE_URL  # configurable con la variable de entorno PLANIKA_SITE_URL
CAT_NAME = {k: n for k, n, _ in CATEGORIES}
CAT_ICON = {k: i for k, _, i in CATEGORIES}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")

# ---------------------------------------------------------------- sesiones


def group_sessions(events):
    """Une las funciones repetidas de un mismo plan (mismo título, lugar y provincia) en una sola tarjeta."""
    groups = {}
    singles = []
    for e in events:
        if e.get("sessions"):
            singles.append(e)
            continue
        if e["start"] != e["end"]:
            singles.append(e)
            continue
        key = (norm(e["title"])[:60], norm(e.get("venue") or e.get("city"))[:40], e["province_code"])
        groups.setdefault(key, []).append(e)
    out = list(singles)
    merged = 0
    for key, items in groups.items():
        if len(items) < 2:
            out.extend(items)
            continue
        items.sort(key=lambda x: (x["start"], x["time"]))
        base = dict(items[0])
        sessions = []
        for it in items:
            if it["start"] not in sessions:
                sessions.append(it["start"])
        if len(sessions) < 2:
            out.extend(items)
            continue
        base["sessions"] = sessions
        base["end"] = sessions[-1]
        for k in ("tickets_url", "image", "description", "price"):
            if not base.get(k):
                base[k] = next((it[k] for it in items if it.get(k)), base.get(k))
        out.append(base)
        merged += len(items) - 1
    return out, merged

# ---------------------------------------------------------------- salud de fuentes


def update_health(path, source_meta):
    try:
        with open(path, encoding="utf-8") as fh:
            health = json.load(fh)
    except (OSError, ValueError):
        health = {"history": {}}
    hist = health.setdefault("history", {})
    day = iso(today())
    alerts = []
    for s in source_meta:
        h = hist.setdefault(s["key"], [])
        h = [x for x in h if x["date"] != day][-29:]
        prev = [x["count"] for x in h[-7:]]
        h.append({"date": day, "count": s["count"], "error": s.get("error", "")})
        hist[s["key"]] = h
        if s["key"] in ("ticketmaster", "lorca"):
            continue  # opcional o fuente parada conocida
        if s.get("stale_from"):
            alerts.append("%s: hoy no ha respondido; se muestran los planes de la descarga del %s" % (s["name"], s["stale_from"]))
            continue
        if prev:
            ref = sorted(prev)[len(prev) // 2]
            if s["count"] == 0 and ref > 0:
                alerts.append("%s: 0 eventos (antes %d)%s" % (s["name"], ref, " · " + s["error"] if s.get("error") else ""))
            elif ref >= 20 and s["count"] < ref * 0.4:
                alerts.append("%s: %d eventos, un %d%% menos que los últimos días (%d)" % (s["name"], s["count"], round(100 - 100.0 * s["count"] / ref), ref))
        elif s.get("error"):
            alerts.append("%s: error %s" % (s["name"], s["error"]))
    health["updated_at"] = stamp()
    health["alerts"] = alerts
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(health, fh, ensure_ascii=False, indent=1)
    return alerts

# ---------------------------------------------------------------- RSS


def _when_short(e):
    if is_permanent(e):
        return "Visita permanente"
    return e["start"] if e["start"] == e["end"] else "%s – %s" % (e["start"], e["end"])


def _rss(title, link, desc, items):
    def item(e):
        when = _when_short(e)
        where = " · ".join(x for x in (e.get("venue"), e.get("city"), e.get("province")) if x)
        body = "%s%s. %s%s" % (when, " " + e["time"] if e.get("time") else "", where, (". " + e["description"]) if e.get("description") else "")
        return ("<item><title>%s</title><link>%s</link><guid isPermaLink=\"false\">%s</guid><category>%s</category>"
                "<description>%s</description></item>") % (
            html.escape(display_title(e)), html.escape(e.get("url") or e.get("tickets_url") or SITE_URL + "/?e=" + e["id"]),
            e["id"], html.escape(CAT_NAME.get(e["category"], "Otros")), html.escape(body))
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss version=\"2.0\"><channel><title>%s</title><link>%s</link>"
            "<description>%s</description><language>es</language><lastBuildDate>%s</lastBuildDate>%s</channel></rss>\n") % (
        html.escape(title), html.escape(link), html.escape(desc),
        now_madrid().strftime("%a, %d %b %Y %H:%M:%S %z"), "".join(item(e) for e in items))


def write_feeds(out_dir, events, days=30):
    os.makedirs(out_dir, exist_ok=True)
    limit = iso(today() + timedelta(days=days))
    # El feed nacional es la agenda de los próximos días: las visitas permanentes
    # (sin fecha) no deben ocupar esos 150 huecos. Sí entran en el feed de su
    # provincia, detrás de lo fechado, para que una provincia sin agenda no quede vacía.
    soon = [e for e in events if e["start"] <= limit and not is_permanent(e)]
    soon.sort(key=lambda e: (max(e["start"], iso(today())), e.get("time") or ""))
    permanents = [e for e in events if is_permanent(e)]
    permanents.sort(key=lambda e: e["title"])
    written = []
    with open(os.path.join(out_dir, "todos.xml"), "w", encoding="utf-8") as fh:
        fh.write(_rss("Planika · próximos planes en España", SITE_URL, "Planes de los próximos %d días" % days, soon[:150]))
    written.append("todos.xml")
    for code, name, _ in PROVINCIAS:
        dated = [e for e in soon if e["province_code"] == code]
        extra = [e for e in permanents if e["province_code"] == code]
        items = (dated + extra)[:120]
        if not items:
            continue
        fn = "provincia-%s.xml" % code
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(_rss("Planika · %s" % name, "%s/?prov=%s" % (SITE_URL, code), "Planes de ocio en %s los próximos %d días" % (name, days), items))
        written.append(fn)
    for key, name, _ in CATEGORIES:
        items = [e for e in soon if in_cat(e, key)][:120]
        if not items:
            continue
        fn = "tipo-%s.xml" % key
        with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(_rss("Planika · %s" % name, "%s/?cat=%s" % (SITE_URL, key), "%s en toda España los próximos %d días" % (name, days), items))
        written.append(fn)
    return written

# ---------------------------------------------------------------- páginas estáticas


_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(seo_title)s · Planika</title><meta name="description" content="%(desc)s">
<meta name="robots" content="%(robots)s">
<link rel="canonical" href="%(canonical)s">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="%(seo_title)s"><meta property="og:description" content="%(desc)s"><meta property="og:url" content="%(canonical)s">
<meta property="og:image" content="%(site)s/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="%(seo_title)s"><meta name="twitter:description" content="%(desc)s"><meta name="twitter:image" content="%(site)s/og.jpg"><meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="%(up)sstyles.css"><link rel="icon" href="%(up)sicon.svg" type="image/svg+xml">
%(rss_link)s<script type="application/ld+json">%(jsonld)s</script>
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="%(home)s" style="text-decoration:none;color:inherit"><span class="brandname">Planika</span></a></div>
<h1 class="tagline">%(h1)s</h1><p class="lead">%(lead)s</p>
<p class="meta"><a class="btn primary" href="%(home)s?%(params)s">Abrir en la app con filtros y calendario</a>%(rss_btn)s%(updated)s</p></div></header>
<main class="wrap">%(crumbs)s
%(intro)s
<h2 style="margin:22px 0 10px">%(list_title)s</h2>
%(cards)s
%(more)s
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2>%(links)s
<p><a href="%(up)spromociona-tu-evento.html">¿Organizas un evento? Publícalo gratis en Planika</a> · <a href="%(up)sprivacidad.html">Privacidad y cookies</a> · <a href="%(up)sprivacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="%(up)saviso-legal.html">Aviso legal</a> · <a href="https://www.instagram.com/planikaapp/" target="_blank" rel="noopener">Instagram</a></p></nav>
</main></body></html>
"""


# Formulario de envío de eventos para organizadores (Google Forms).
# Se rellena al crear el formulario; si está vacío, la página enlaza a "#".
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdEWQEESXI2jmjLywT5KY1SXj1azAQlnmSiwE2ubjnrvDe6ZA/viewform"

_PROMO = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Promociona tu evento gratis · Planika</title><meta name="description" content="¿Organizas conciertos, teatro, fiestas o talleres? Publica tu evento gratis en Planika: ficha propia en Google, en tu provincia y tu categoría, con enlace a tus entradas.">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="%(site)s/promociona-tu-evento.html">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="Promociona tu evento gratis"><meta property="og:description" content="Publica tu evento en Planika: ficha propia, en tu provincia y tu categoría, con enlace a tus entradas. Gratis y sin registro."><meta property="og:url" content="%(site)s/promociona-tu-evento.html">
<meta property="og:image" content="%(site)s/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Promociona tu evento gratis · Planika"><meta name="twitter:description" content="Publica tu evento en Planika: ficha propia, en tu provincia y tu categoría, con enlace a tus entradas. Gratis y sin registro."><meta name="twitter:image" content="%(site)s/og.jpg"><meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="styles.css"><link rel="icon" href="icon.svg" type="image/svg+xml">
<script type="application/ld+json">%(jsonld)s</script>
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="./" style="text-decoration:none;color:inherit"><span class="brandname">Planika</span></a></div>
<h1 class="tagline">Promociona tu evento gratis</h1>
<p class="lead">¿Organizas conciertos, teatro, fiestas, exposiciones o talleres? Publica tu evento en Planika y llega a la gente que está buscando planes en tu provincia.</p>
<p class="meta"><a class="btn primary" href="%(form)s" target="_blank" rel="noopener">Publica tu evento</a> &nbsp; <a class="btn" href="./">Explorar Planika</a></p>
<p class="meta">Más de 12.000 planes publicados · 52 provincias · Actualización diaria</p></div></header>
<main class="wrap">
<h2 style="margin:22px 0 10px">Qué consigues</h2>
<div class="list">
<article class="card"><div class="body"><h3>🔎 Ficha propia en Google</h3><p class="desc">Tu evento con página propia y datos estructurados (fecha, lugar y entradas) para que Google lo entienda y pueda mostrarlo destacado.</p></div></article>
<article class="card"><div class="body"><h3>📍 En tu provincia y tu categoría</h3><p class="desc">Apareces en los listados de tu provincia y de tu tipo de plan, y también en los de «este fin de semana» y «planes gratis» si te encajan.</p></div></article>
<article class="card"><div class="body"><h3>🎫 Entradas y calendario</h3><p class="desc">Botón directo a tu venta de entradas y botón para añadir el evento a Google Calendar.</p></div></article>
<article class="card"><div class="body"><h3>🆓 Gratis y sin registro</h3><p class="desc">Sin cuentas ni contraseñas: rellenas el formulario, lo revisamos y queda publicado.</p></div></article>
</div>
<h2 style="margin:26px 0 10px">Cómo funciona</h2>
<ol>
<li><strong>Rellena el formulario</strong> con los datos de tu evento: título, fecha, lugar, precio y enlace de entradas.</li>
<li><strong>Lo revisamos</strong> para evitar spam y errores. Si falta algo, te escribimos.</li>
<li><strong>Publicado en 24 horas.</strong> Planika se actualiza cada día; tu evento entra en el siguiente ciclo.</li>
</ol>
<h2 style="margin:26px 0 10px">¿Cuánto cuesta?</h2>
<div class="list">
<article class="card"><div class="body"><div class="badges"><span class="badge">Publicar</span><span class="badge free">Gratis</span></div><h3>0 €</h3><p class="desc">Tu evento publicado con ficha propia y en todos los listados que le correspondan. Gratis, para siempre.</p></div></article>
</div>
<h2 style="margin:26px 0 10px">Preguntas frecuentes</h2>
%(faq)s
<p class="meta" style="margin-top:26px"><a class="btn primary" href="%(form)s" target="_blank" rel="noopener">Publica tu evento gratis</a></p>
<p class="src">Al enviar el formulario confirmas que tienes derecho a publicar el evento y su imagen. La exactitud de fechas, horarios y precios es responsabilidad del organizador.</p>
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p><a href="./">Inicio</a> · <a href="planes-este-fin-de-semana.html">Planes este fin de semana</a> · <a href="t/musica.html">Conciertos</a> · <a href="privacidad.html">Privacidad y cookies</a> · <a href="privacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="aviso-legal.html">Aviso legal</a> · <a href="https://www.instagram.com/planikaapp/" target="_blank" rel="noopener">Instagram</a></p></nav>
</main></body></html>
"""

_FAQ = [
    ("¿Cuánto cuesta publicar un evento en Planika?",
     "Publicar es gratis: tu evento tendrá ficha propia y aparecerá en los listados de su provincia y categoría sin coste. Más adelante ofreceremos opciones de destacado de pago para quien quiera más visibilidad."),
    ("¿Cuándo se publica mi evento?",
     "Revisamos cada envío a mano para evitar spam. Planika se regenera cada día, así que un evento aprobado suele estar publicado en unas 24 horas."),
    ("¿Puedo poner mi enlace de venta de entradas?",
     "Sí. La ficha de tu evento incluye un botón de entradas con tu enlace, y otro para que el público lo añada a su Google Calendar."),
    ("¿Saldrá mi evento el primero en Google?",
     "Nadie puede garantizar la primera posición. Lo que sí hacemos es dar a tu evento una ficha con los datos estructurados que Google usa para mostrar eventos, que es donde un evento local tiene opciones reales de salir arriba: en su propio nombre y en búsquedas de su zona."),
    ("¿Puedo corregir o retirar mi evento?",
     "Sí: vuelve a enviar el formulario indicando el cambio, o responde al correo de confirmación, y lo actualizamos en el siguiente ciclo diario."),
]


def _promo_page():
    ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q,
                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in _FAQ]}
    faq_html = "".join("<h3>%s</h3><p>%s</p>" % (html.escape(q), html.escape(a)) for q, a in _FAQ)
    return _PROMO % dict(site=SITE_URL, form=html.escape(FORM_URL or "#"), analytics=static.BEACON,
                         jsonld=json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
                         faq=faq_html)

_SOURCES = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fuentes de datos · Planika</title><meta name="description" content="De dónde salen los planes de Planika: portales de datos abiertos, agendas oficiales y APIs públicas, con el número de planes de cada fuente.">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="%(site)s/fuentes.html">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="Fuentes de datos de Planika"><meta property="og:description" content="Portales de datos abiertos, agendas oficiales y APIs públicas de las que sale la agenda de Planika."><meta property="og:url" content="%(site)s/fuentes.html">
<meta property="og:image" content="%(site)s/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="Fuentes de datos · Planika"><meta name="twitter:description" content="Portales de datos abiertos, agendas oficiales y APIs públicas de las que sale la agenda de Planika."><meta name="twitter:image" content="%(site)s/og.jpg"><meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="styles.css"><link rel="icon" href="icon.svg" type="image/svg+xml">
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="./" style="text-decoration:none;color:inherit"><span class="brandname">Planika</span></a></div>
<h1 class="tagline">Fuentes de datos</h1>
<p class="lead">Los datos proceden de portales de datos abiertos y APIs públicas, más una selección de visitas permanentes (museos, monumentos, espacios naturales y salas) con enlace a su web oficial y unas pocas grandes citas con fecha comprobada a mano en webs públicas («Selección Planika»).</p>
<p class="meta"><a class="btn primary" href="./">Explorar Planika</a>%(updated)s</p></div></header>
<main class="wrap">
<h2 style="margin:22px 0 10px">%(n)d fuentes, %(total)s planes</h2>
<ul id="sources">%(items)s</ul>
<p>Cada plan enlaza al organizador. Comprueba siempre fechas, horarios y precios en la fuente original.</p>
<p>Mapas y ubicación de las salas: datos © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">colaboradores de OpenStreetMap</a> (licencia ODbL).</p>
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p><a href="./">Inicio</a> · <a href="promociona-tu-evento.html">Publica tu evento</a> · <a href="privacidad.html">Privacidad y cookies</a> · <a href="privacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="aviso-legal.html">Aviso legal</a> · <a href="https://www.instagram.com/planikaapp/" target="_blank" rel="noopener">Instagram</a> · <a href="https://github.com/davidpardal/planika">Código en GitHub</a></p></nav>
</main></body></html>
"""


def _sources_page(sources, updated_at=""):
    # Solo fuentes con planes; los errores de descarga no se muestran al público (van a las alertas y al historial de salud).
    sources = [s for s in sources if int(s.get("count") or 0) > 0]
    items = []
    for s in sources:
        items.append("<li><a href=\"%s\" target=\"_blank\" rel=\"noopener\">%s</a> · %d planes</li>"
                     % (html.escape(s.get("home") or "#", quote=True), html.escape(s.get("name") or ""), int(s.get("count") or 0)))
    total = sum(int(s.get("count") or 0) for s in sources)
    upd = ""
    if updated_at:
        upd = " &nbsp; Actualizado el %s" % html.escape(_upd_text(updated_at, hour=True))
    return _SOURCES % dict(site=SITE_URL, analytics=static.BEACON, items="".join(items), n=len(sources),
                           total="{:,}".format(total).replace(",", "."), updated=upd)


# ---------------------------------------------------------------- piezas comunes de los hubs

# Cómo busca la gente cada tipo de plan (títulos y H1 de las páginas por tipo).
CAT_INTENT = {
    "musica": "Conciertos", "escena": "Teatro y danza", "expos": "Exposiciones", "cine": "Cine",
    "deporte": "Deporte", "gastro": "Ferias, mercados y gastronomía", "infantil": "Planes con niños",
    "navidad": "Planes de Navidad", "fiestas": "Fiestas y tradiciones", "naturaleza": "Rutas y visitas guiadas",
    "charlas": "Charlas, libros y talleres", "otros": "Otros planes",
}
FIRST_PAGE = 60      # tarjetas en la primera página de cada hub
ARCHIVE_PAGE = 150   # planes por página en el listado completo de cada provincia
CITY_MIN = 40        # planes con fecha para que una ciudad (sin provincia del mismo nombre) tenga página
SUB_MIN = {"fin-de-semana": 3, "gratis": 3}  # mínimo de planes de las subpáginas de intención; las de tipo, 5
SUB_LABEL = {"fin-de-semana": "Planes este fin de semana", "gratis": "Planes gratis"}
FESTIVAL_RX = re.compile(r"\b(festival|festivala|festivalak|festivales|festivals)\b")
_MES_CORTO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]


# Secciones de temporada de la página de Navidad. Solo se muestran con al menos 3 planes; se buscan en todos
# los planes (un belén puede estar clasificado como exposición) y, si hace falta, dentro de unas fechas.
_XMAS = re.compile(r"\b(navidad|navidenos?|navidenas?|nadal|nadalencs?|gabon|gabonetako|christmas|xmas|reyes magos|olentzero)")
XMAS_SECTIONS = [
    ("mercados", "Mercados de Navidad", re.compile(
        r"\b(mercados? de navidad|mercadillos? navidenos?|mercado navideno|feria de navidad|mercats? de nadal|mercat nadalenc|"
        r"fira de nadal|fires de nadal|christmas market|gabonetako azoka|gabon azoka)"), None, False),
    ("belenes", "Belenes", re.compile(
        r"\b(belenes|belen (de navidad|monumental|viviente|napolitano|municipal|artesanal|tradicional|en movimiento)|"
        r"pessebres?|jaiotzak?|naixement)\b"), None, False),
    ("olentzero-y-reyes", "Olentzero, Papá Noel y Reyes Magos", re.compile(
        r"\b(cabalgatas?|cavalcadas?|reyes magos|reis mags|reis d.orient|olentzero|mari domingi|papa noel|pare noel|erregeak)"), None, False),
    ("luces", "Encendido de luces", re.compile(r"\b(encendido|alumbrado|iluminacion|enllumenat|argiztapen)"), None, True),
    ("nochevieja", "Nochevieja y Año Nuevo", re.compile(
        r"\b(nochevieja|fin de ano|cap d.any|urtezahar|campanadas|san silvestre|sant silvestre|ano nuevo|any nou|urte berri)"),
     ("12-26", "01-01"), False),
]


# Cómo se nombra cada sección en el título (corto) y en la descripción de la página.
XMAS_LABELS = {"mercados": ("mercados", "mercados de Navidad"), "belenes": ("belenes", "belenes"),
               "olentzero-y-reyes": ("cabalgatas", "Olentzero, Papá Noel y Reyes Magos"),
               "luces": ("luces", "encendido de luces"), "nochevieja": ("Nochevieja", "Nochevieja")}


def xmas_sections(events, t0):
    """[(ancla, título, planes)] con los planes de cada tema navideño que aún no han terminado."""
    out = []
    for key, title, rx, window, needs_xmas in XMAS_SECTIONS:
        items = []
        for e in events:
            if is_permanent(e) or e["end"] < t0:
                continue
            text = norm(e.get("title_es") or e["title"])
            if not rx.search(text):
                continue
            if needs_xmas and not (e["category"] == "navidad" or _XMAS.search(text)):
                continue
            if window:
                # Ventana de fechas que cruza el año (26 dic - 1 ene): el plan tiene que tocarla.
                days = e.get("sessions") or [e["start"], e["end"]]
                if not any(d[5:] >= window[0] or d[5:] <= window[1] for d in days):
                    continue
            items.append(e)
        if len(items) >= 3:
            out.append((key, title, items))
    return out


def season_year(t0):
    """Año de la temporada de Navidad: en enero todavía es la del año anterior."""
    y, m = int(t0[:4]), int(t0[5:7])
    return y - 1 if m == 1 else y


# ---------------------------------------------------------------- puente de diciembre

_DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
PUENTE_DESDE = "10-01"  # la página del puente se indexa desde el 1 de octubre hasta su último día
PUENTE_MIN = 20         # con menos planes publicados, la página no se indexa ni se enlaza


def puente_diciembre(year):
    """(primer día, último día) del puente de la Constitución (6 dic) y la Inmaculada (8 dic) de `year`.
    Se alarga hasta el fin de semana pegado: si el 6 cae en domingo o lunes, empieza el sábado; si el 8 cae
    en viernes o sábado, acaba el domingo. 2026: sábado 5 – martes 8."""
    from datetime import date
    a, b = date(year, 12, 6), date(year, 12, 8)
    a -= timedelta(days={6: 1, 0: 2}.get(a.weekday(), 0))
    b += timedelta(days={4: 2, 5: 1}.get(b.weekday(), 0))
    return a, b


def puente_estado(t0):
    """(año, primer día, último día, en temporada). Fuera de temporada, el año es el del último puente ya pasado."""
    y = int(t0[:4])
    a, b = puente_diciembre(y)
    if "%d-%s" % (y, PUENTE_DESDE) <= t0 <= iso(b):
        return y, a, b, True
    if t0 < "%d-%s" % (y, PUENTE_DESDE):
        y -= 1
        a, b = puente_diciembre(y)
    return y, a, b, False


def puente_planes(events, t0):
    """Planes del puente si estamos en temporada y hay al menos PUENTE_MIN; si no, lista vacía.
    Decide a la vez si la página del puente se indexa y si se enlaza (hubs y portada)."""
    _, a, b, season = puente_estado(t0)
    if not season:
        return []
    items = [e for e in events if in_window(e, iso(a), iso(b))]
    return items if len(items) >= PUENTE_MIN else []


def puente_rango(a, b):
    """«del sábado 5 al martes 8 de diciembre»."""
    return "del %s %d al %s %d de diciembre" % (_DIAS_LARGOS[a.weekday()], a.day, _DIAS_LARGOS[b.weekday()], b.day)


def in_cat(e, key):
    """¿Va el plan en la página del tipo `key`? Navidad incluye los planes con tema navideño de cualquier tipo."""
    return e["category"] == key or (key == "navidad" and bool(e.get("xmas")))


def fmt_n(n):
    return "{:,}".format(n).replace(",", ".")


def _join_es(xs):
    xs = [x for x in xs if x]
    return xs[0] if len(xs) == 1 else (", ".join(xs[:-1]) + " y " + xs[-1] if xs else "")


def _itemlist(items, limit=20):
    """ItemList con los primeros planes de la página, enlazando a la ficha de cada plan."""
    els = [{"@type": "ListItem", "position": i, "url": "%s/e/%s" % (SITE_URL, static.event_file(e)),
            "name": display_title(e)} for i, e in enumerate(items[:limit], 1)]
    return {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": els}


def _jsonld(items, crumbs):
    graph = [_itemlist(items)]
    if crumbs:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i, "name": n, "item": SITE_URL + "/" + u}
            for i, (n, u) in enumerate(crumbs, 1)]})
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def _crumbs_html(crumbs, up):
    """crumbs: [(nombre, ruta desde la raíz)]; el último es la página actual."""
    if len(crumbs) < 2:
        return ""
    parts = ['<a href="%s">%s</a>' % (html.escape(up + u if u else (up or "./")), html.escape(n)) for n, u in crumbs[:-1]]
    parts.append('<span aria-current="page">%s</span>' % html.escape(crumbs[-1][0]))
    return '<nav class="crumbs hub" aria-label="Migas de pan">%s</nav>' % " › ".join(parts)


def _card(e, up="../", t0=None):
    t0 = t0 or iso(today())
    when = static._when(e, t0)
    if e.get("sessions") and not is_permanent(e):
        more = len([d for d in e["sessions"] if d >= t0]) - 1
        if more > 0:
            when += " (+%d fechas)" % more
    where = " · ".join(x for x in (e.get("venue"), e.get("city"), e.get("province")) if x)
    link = up + "e/" + static.event_file(e)  # la ficha propia del plan: enlazado interno para buscadores
    badges = ("<span class=\"badge free\">Gratis</span>" if e.get("free") else "") + (
        "<span class=\"badge\">Permanente</span>" if is_permanent(e) else "")
    desc = static.clip(e.get("description") or "", 220)
    return ("<article class=\"card\"><div class=\"body\"><div class=\"badges\"><span class=\"badge\">%s %s</span>%s</div>"
            "<h3><a href=\"%s\">%s</a></h3><div class=\"when\">📅 %s%s</div>"
            "<div class=\"where\">📍 %s</div>%s%s</div></article>") % (
        CAT_ICON.get(e["category"], "✨"), html.escape(CAT_NAME.get(e["category"], "Otros")),
        badges,
        html.escape(link), html.escape(display_title(e)), html.escape(when), "",
        html.escape(where), ("<p class=\"desc\">%s</p>" % html.escape(desc)) if desc else "",
        ("<div class=\"src\">Fuente: %s</div>" % html.escape(e["source"])) if e.get("source") else "")


def prerender_index(site_dir, events, t0=None, n=24):
    """Pinta en la portada (index.html) los primeros planes de la lista y el recuento, en HTML estático.
    Sin esto la portada llega vacía hasta que se descargan los datos (core.js, varios MB): los buscadores
    ven una página sin planes y en el móvil el contenido tarda en aparecer. La app sustituye esta lista
    por la suya en cuanto carga. Los eventos llegan ya en el orden por defecto (static.default_order)."""
    t0 = t0 or iso(today())
    path = os.path.join(site_dir, "index.html")
    try:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
    except OSError:
        return False
    items = [e for e in events if not is_permanent(e) and e["end"] >= t0]
    cards = "".join(_card(e, "", t0).replace('<article class="card">', '<article class="card pop%d">' % (i % 4), 1)
                    for i, e in enumerate(items[:n]))
    out = re.sub(r'(<section id="list" class="list" aria-live="polite">).*?(</section>)',
                 lambda m: m.group(1) + cards + m.group(2), page, count=1, flags=re.S)
    out = re.sub(r'(<h2 class="count" id="count" aria-live="polite">).*?(</h2>)',
                 lambda m: m.group(1) + "%s planes" % fmt_n(len(items)) + m.group(2), out, count=1, flags=re.S)
    # Enlace a la página del puente de diciembre solo en temporada: la portada es lo que Google visita cada día,
    # así descubre la página a tiempo (si no, solo la enlazan las páginas de provincia).
    puente = '<a href="puente-diciembre.html">Puente de diciembre</a> · ' if puente_planes(events, t0) else ""
    out = re.sub(r'(<span id="puenteLink">).*?(</span>)', lambda m: m.group(1) + puente + m.group(2), out, count=1, flags=re.S)
    if out != page:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(out)
    return out != page


def _cards(items, up, t0=None):
    return "<div class=\"list\">%s</div>" % "".join(_card(e, up, t0) for e in items[:FIRST_PAGE])


def _compact(items, up, t0):
    """Lista ligera (título, fecha y lugar) para las páginas del listado completo."""
    rows = []
    for e in items:
        where = e.get("city") or e.get("province") or ""
        rows.append("<li><a href=\"%se/%s\">%s</a> · %s%s</li>" % (
            up, html.escape(static.event_file(e)), html.escape(display_title(e)),
            html.escape(static._when(e, t0)), (" · " + html.escape(where)) if where else ""))
    return "<ul class=\"compact\">%s</ul>" % "".join(rows)


def _intro(items, scope, t0, cities=True, soon=True):
    """Resumen con datos reales de la página: cuántos planes hay, de qué tipo, dónde y cuántos son gratis.
    Así cada hub tiene un texto propio y no una plantilla que solo cambia el nombre."""
    from collections import Counter
    dated = [e for e in items if not is_permanent(e)]
    perm = len(items) - len(dated)
    out = []
    first = "Hay %s planes con fecha %s" % (fmt_n(len(dated)), scope)
    if perm:
        first += " y %s visitas permanentes (museos, monumentos y espacios naturales)" % fmt_n(perm)
    out.append(first + ".")
    cats = Counter(e["category"] for e in dated).most_common(3)
    if len(cats) > 1:
        out.append("Lo que más hay: %s." % _join_es(["%s (%s)" % (CAT_NAME.get(k, k).lower(), fmt_n(n)) for k, n in cats]))
    if cities:
        cc = Counter(e.get("city") for e in dated if e.get("city")).most_common(3)
        if len(cc) > 1:
            out.append("Localidades con más agenda: %s." % _join_es(["%s (%s)" % (c, fmt_n(n)) for c, n in cc]))
    vv = [(v, n) for v, n in Counter(e.get("venue") for e in dated if e.get("venue")).most_common(3) if n >= 3]
    if vv:
        out.append("Lugares con más fechas: %s." % _join_es([v for v, _ in vv]))
    free = sum(1 for e in dated if e.get("free"))
    if free:
        out.append("%s son gratis." % fmt_n(free))
    week = iso(datetime.strptime(t0, "%Y-%m-%d") + timedelta(days=7))
    n_soon = sum(1 for e in dated if in_window(e, t0, week)) if soon else 0
    if n_soon:
        out.append("%s se celebran en los próximos 7 días." % fmt_n(n_soon))
    return "<p class=\"intro\">%s</p>" % html.escape(" ".join(out))


def _p(links):
    links = [l for l in links if l]
    return ("<p>%s</p>" % " · ".join(links)) if links else ""


def _render(site_dir, path, up, *, seo_title, h1, desc, items, crumbs, params, t0, updated,
            intro="", cards=None, list_title=None, more="", links="", rss="", robots="index,follow,max-image-preview:large",
            tail="", write=True):
    if rss and not os.path.exists(os.path.normpath(os.path.join(site_dir, os.path.dirname(path), rss))):
        rss = ""  # sin planes en los próximos 30 días no hay feed: no se enlaza
    page = _PAGE % dict(
        seo_title=html.escape(seo_title), h1=html.escape(h1), desc=html.escape(desc), lead=html.escape(desc),
        robots=robots, canonical="%s/%s" % (SITE_URL, path), site=SITE_URL, up=up, home=up or "./",
        rss_link=('<link rel="alternate" type="application/rss+xml" title="RSS %s" href="%s">\n' % (html.escape(h1), rss)) if rss else "",
        rss_btn=(' &nbsp; <a class="btn" href="%s">RSS</a>' % rss) if rss else "",
        updated=(' &nbsp; <span class="upd">Actualizado el %s</span>' % html.escape(updated)) if updated else "",
        jsonld=_jsonld(items, crumbs), analytics=static.BEACON, params=html.escape(params),
        crumbs=_crumbs_html(crumbs, up), intro=intro,
        list_title=list_title or "Próximos planes (%s)" % fmt_n(len(items)),
        cards=cards if cards is not None else _cards(items, up, t0), more=more, links=links)
    if tail:
        page = page.replace("</body>", tail + "\n</body>", 1)
    if write:
        with open(os.path.join(site_dir, path), "w", encoding="utf-8") as fh:
            fh.write(page)
    return page


SWITCH_HOUR = "07:00"  # hora de Madrid a la que las páginas «hoy» y «fin de semana» pasan al día siguiente

_NEXT_DAY_JS = """<script>(function(){var T=document.getElementById('next-day');if(!T||!window.Intl||!T.content)return;var o={};
try{new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date()).forEach(function(x){o[x.type]=x.value;});}catch(e){return;}
var now=o.year+'-'+o.month+'-'+o.day+'T'+o.hour+':'+o.minute,m=document.querySelector('main.wrap');if(now<T.getAttribute('data-at')||!m)return;
if(now>=T.getAttribute('data-stale')){m.innerHTML='<p class="intro">Estamos actualizando esta página. Mientras tanto, tienes todos los planes al día en la <a href="./">app de Planika</a>.</p>';return;}
var f=T.content;document.title=T.getAttribute('data-title');
[['lead','p.lead'],['meta','p.meta']].forEach(function(k){var n=f.querySelector('[data-k="'+k[0]+'"]'),el=document.querySelector(k[1]);if(n&&el)el.outerHTML=n.innerHTML;});
var mm=f.querySelector('[data-k="main"]');if(mm)m.innerHTML=mm.innerHTML;})();</script>"""


def next_day_block(page, day):
    """Guarda la versión de `day` (la página entera ya generada) dentro de un <template> que el navegador
    activa solo a las 07:00 de ese día (hora de Madrid). Así la página «hoy» cambia de día a su hora
    aunque la actualización diaria se retrase. Si la página tiene ya más de un día de retraso, avisa y
    manda a la app, que filtra por fecha en el propio móvil."""
    title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
    lead = re.search(r'<p class="lead">.*?</p>', page, re.S).group(0)
    meta = re.search(r'<p class="meta">.*?</p>', page, re.S).group(0)
    main = re.search(r'<main class="wrap">(.*)</main>', page, re.S).group(1)
    stale = iso(datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1))
    return ('<template id="next-day" data-at="%sT%s" data-stale="%sT%s" data-title="%s">'
            '<div data-k="lead">%s</div><div data-k="meta">%s</div><div data-k="main">%s</div></template>\n%s'
            % (day, SWITCH_HOUR, stale, SWITCH_HOUR, title.replace('"', "&quot;"), lead, meta, main, _NEXT_DAY_JS))


_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fmt_es(d):
    return "%d de %s" % (d.day, _MESES[d.month - 1])


def weekend_window(t0_date):
    """(viernes, domingo) del fin de semana en curso o, si aún no ha empezado, del próximo; en fin de semana arranca hoy."""
    wd = t0_date.weekday()
    fri = t0_date - timedelta(days=wd - 4) if wd >= 4 else t0_date + timedelta(days=4 - wd)
    sun = fri + timedelta(days=2)
    return max(fri, t0_date), sun


def in_window(e, a, b):
    """¿Ocurre el plan entre a y b (ISO)? Con funciones sueltas cuenta cada fecha; los rangos largos (exposiciones…) no."""
    if is_permanent(e):
        return False
    if e.get("sessions"):
        return any(a <= d <= b for d in e["sessions"])
    if e["start"] > b or e["end"] < a:
        return False
    return e["start"] >= a or (datetime.strptime(e["end"], "%Y-%m-%d") - datetime.strptime(e["start"], "%Y-%m-%d")).days <= 14


def _short_range(a, b):
    a, b = datetime.strptime(a, "%Y-%m-%d"), datetime.strptime(b, "%Y-%m-%d")
    if a == b:
        return "%d %s" % (a.day, _MES_CORTO[a.month - 1])
    if a.month == b.month:
        return "%d–%d %s" % (a.day, b.day, _MES_CORTO[a.month - 1])
    return "%d %s–%d %s" % (a.day, _MES_CORTO[a.month - 1], b.day, _MES_CORTO[b.month - 1])


def find_cities(events):
    """Ciudades con mucha agenda que no tienen una provincia del mismo nombre (Bilbao, Donostia, Vitoria…).
    Devuelve {(código de provincia, ciudad normalizada): (nombre, archivo sin .html)}."""
    from collections import Counter, defaultdict
    prov = {c: n for c, n, _ in PROVINCIAS}
    count, names = Counter(), defaultdict(Counter)
    for e in events:
        if is_permanent(e) or not e.get("city"):
            continue
        k = (e["province_code"], norm(e["city"]))
        count[k] += 1
        names[k][e["city"]] += 1
    out = {}
    for (code, ncity), n in count.items():
        pname = norm(prov.get(code, ""))
        if n < CITY_MIN or not ncity or ncity == pname or ncity in pname or pname in ncity:
            continue
        name = names[(code, ncity)].most_common(1)[0][0]
        out[(code, ncity)] = (name, slug(name))
    return out


def _upd_text(updated_at, hour=False):
    """"24 nov 2026" (hour: "24 nov 2026 a las 6:50"). updated_at va en hora de Madrid."""
    try:
        d = datetime.strptime((updated_at or "")[:10], "%Y-%m-%d")
    except ValueError:
        d = datetime.combine(today(), datetime.min.time())
    out = "%d %s %d" % (d.day, _MES_CORTO[d.month - 1], d.year)
    m = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", updated_at or "")
    return out + (" a las %d:%s" % (int(m.group(1)), m.group(2)) if hour and m else "")


# ---------------------------------------------------------------- todas las páginas

LAST_RUN = {"gone": 0}  # cifras de la última generación, para el registro de fetch_events.py


def write_pages(site_dir, events, sources=None, updated_at="", state_path=None, fichas_path=None):
    """Genera hubs, fichas, sitemaps y robots.txt. state_path: archivo donde se guarda la huella de cada URL
    para que el lastmod del sitemap solo cambie cuando cambia la página (None: sin memoria entre ejecuciones).
    fichas_path: archivo con las fichas publicadas, para mantener con aviso las de planes que salen de la agenda
    (None: no se mantienen)."""
    t0 = iso(today())
    upd = _upd_text(updated_at)
    entries = [("", "paginas", seo.digest((updated_at or t0)[:10]))]  # la portada cambia con cada actualización de datos
    pages = []

    def upcoming(items):
        # Primero la agenda con fecha; después las visitas permanentes.
        return sorted(items, key=lambda e: (1 if is_permanent(e) else 0, max(e["start"], t0), e.get("time") or "99", e.get("title") or ""))

    def done(path, page):
        pages.append(path)
        entries.append((path, "paginas", seo.digest(page)))

    for sub_dir in ("p", "t", "c"):
        d = os.path.join(site_dir, sub_dir)
        os.makedirs(d, exist_ok=True)
        for fn in os.listdir(d):  # las páginas que hoy no tocan no se quedan publicadas con datos viejos
            if fn.endswith(".html"):
                os.remove(os.path.join(d, fn))
    fri, sun = weekend_window(today())
    wa, wb = iso(fri), iso(sun)
    wrange = _short_range(wa, wb)
    cities = find_cities(events)
    by_code = {}
    for e in events:
        by_code.setdefault(e["province_code"], []).append(e)
    prov_pages = [(code, name, ccaa, upcoming(by_code[code])) for code, name, ccaa in PROVINCIAS if by_code.get(code)]
    # Ciudades con página propia: sus planes y sus subpáginas de intención (finde, gratis y tipo de plan),
    # porque se busca «qué hacer en Bilbao este fin de semana» o «conciertos en Vitoria», no por provincia.
    city_items = {k: upcoming([e for e in by_code.get(k[0], []) if norm(e.get("city") or "") == k[1]]) for k in cities}
    city_subs = {}
    for k, items in city_items.items():
        for suf, sub in (("fin-de-semana", [e for e in items if in_window(e, wa, wb)]),
                         ("gratis", [e for e in items if e.get("free") and not is_permanent(e)])):
            if len(sub) >= SUB_MIN[suf]:
                city_subs[k + (suf,)] = sub
        for key, _, _ in CATEGORIES:
            sub = [e for e in items if in_cat(e, key)]
            if len(sub) >= 5 and key != "otros":  # «Otros planes en Getxo» no es algo que se busque
                city_subs[k + (key,)] = sub
    mes = "%s %s" % (_MESES[int(t0[5:7]) - 1], t0[:4])
    prov_slug = {code: slug(name) for code, name, _ in PROVINCIAS}
    prov_name = {code: name for code, name, _ in PROVINCIAS}
    # Páginas combinadas provincia × tipo ("Conciertos en Álava"): solo con suficientes planes.
    combos = {}
    for code, name, ccaa, items in prov_pages:
        for key, _, _ in CATEGORIES:
            sub = [e for e in items if in_cat(e, key)]
            if len(sub) >= 5:
                combos[(code, key)] = sub
    # Subpáginas de intención por provincia: fin de semana y gratis (solo con al menos 3 planes).
    extras = {}
    for code, name, ccaa, items in prov_pages:
        we = [e for e in items if in_window(e, wa, wb)]
        fr = [e for e in items if e.get("free") and not is_permanent(e)]
        if len(we) >= 3:
            extras[(code, "fin-de-semana")] = we
        if len(fr) >= 3:
            extras[(code, "gratis")] = fr
    nat_links = ['<a href="%splanes-hoy.html">Qué hacer hoy</a>', '<a href="%splanes-este-fin-de-semana.html">Planes este fin de semana</a>',
                 '<a href="%splanes-gratis.html">Planes gratis</a>']
    # Puente de diciembre: página propia desde octubre hasta el último día del puente, enlazada desde todos los hubs.
    p_year, p_a, p_b, p_season = puente_estado(t0)
    pa, pb = iso(p_a), iso(p_b)
    puente_items = upcoming(puente_planes(events, t0))
    puente_on = bool(puente_items)
    if puente_on:
        nat_links.insert(2, '<a href="%spuente-diciembre.html">Puente de diciembre</a>')
    festivals = [e for e in upcoming(events) if not is_permanent(e) and FESTIVAL_RX.search(norm(e.get("title_es") or e["title"]))]
    if len(festivals) >= 20:
        nat_links.append('<a href="%sfestivales.html">Festivales</a>')

    def nat(up):
        return [l % up for l in nat_links]

    def type_links(up):
        return ['<a href="%st/%s.html">%s</a>' % (up, k, html.escape(CAT_INTENT[k])) for k, _, _ in CATEGORIES]

    def prov_links(up, sub=None):
        out = []
        for code, name, _, items in prov_pages:
            if sub and (code, sub) in extras:
                out.append('<a href="%sp/%s-%s.html">%s</a> (%s)' % (up, prov_slug[code], sub, html.escape(name), fmt_n(len(extras[(code, sub)]))))
            elif not sub:
                out.append('<a href="%sp/%s.html">%s</a> (%s)' % (up, prov_slug[code], html.escape(name), fmt_n(len(items))))
        return out

    def city_links(up, code=None, sub=None):
        """Enlaces a las ciudades (de una provincia si se da `code`); con `sub`, a su subpágina si la tiene."""
        out = []
        for (c, nc), (n, f) in sorted(cities.items(), key=lambda x: x[1][0]):
            if code not in (None, c):
                continue
            if sub and (c, nc, sub) in city_subs:
                out.append('<a href="%sc/%s-%s.html">%s en %s</a> (%s)' % (up, f, sub, html.escape(SUB_LABEL.get(sub) or CAT_INTENT[sub]),
                                                                          html.escape(n), fmt_n(len(city_subs[(c, nc, sub)]))))
            elif not sub:
                out.append('<a href="%sc/%s.html">Planes en %s</a>' % (up, f, html.escape(n)))
        return out

    # ---- provincias, con listado completo paginado (todas las fichas a 3 clics de la portada)
    for code, name, ccaa, items in prov_pages:
        base = prov_slug[code]
        fn = "p/%s.html" % base
        rest = items[FIRST_PAGE:]
        n_arch = (len(rest) + ARCHIVE_PAGE - 1) // ARCHIVE_PAGE
        arch = ["p/%s-pagina-%d.html" % (base, k) for k in range(2, n_arch + 2)]

        def pager(cur, up="../"):
            if not arch:
                return ""
            links = ['<a href="%s%s">1</a>' % (up, fn) if cur != 1 else "<strong>1</strong>"]
            for k, a in enumerate(arch, 2):
                links.append("<strong>%d</strong>" % k if k == cur else '<a href="%s%s">%d</a>' % (up, a, k))
            return ('<nav class="pages" aria-label="Páginas"><p>Todos los planes en %s (%s), por fecha: página %s</p></nav>'
                    % (html.escape(name), fmt_n(len(items)), " · ".join(links)))
        crumbs = [("Inicio", ""), (name, fn)]
        sib = [('<a href="%s-%s.html">%s en %s</a>' % (base, suf, lab, html.escape(name))) for suf, lab in
               (("fin-de-semana", "Planes este fin de semana"), ("gratis", "Planes gratis")) if (code, suf) in extras]
        sib += ['<a href="%s-%s.html">%s en %s</a>' % (base, k, html.escape(CAT_INTENT[k]), html.escape(name))
                for k, _, _ in CATEGORIES if (code, k) in combos]
        page = _render(site_dir, fn, "../", seo_title="Qué hacer en %s: planes y eventos (%s)" % (name, mes), h1="Planes en %s" % name,
                       desc="Agenda de planes en %s (%s): %s planes próximos entre conciertos, teatro, exposiciones, deporte, ferias y fiestas, con fechas y enlace oficial."
                            % (name, ccaa, fmt_n(len(items))),
                       items=items, crumbs=crumbs, params="prov=%s" % code, t0=t0, updated=upd,
                       intro=_intro(items, "en %s" % name, t0), more=pager(1, "../"), rss="../feeds/provincia-%s.xml" % code,
                       links=_p(sib) + _p(city_links("../", code)) + _p(nat("../")) + _p(type_links("../")) + _p(prov_links("../")))
        done(fn, page)
        for k, a in enumerate(arch, 2):
            chunk = rest[(k - 2) * ARCHIVE_PAGE:(k - 1) * ARCHIVE_PAGE]
            first, last = FIRST_PAGE + (k - 2) * ARCHIVE_PAGE + 1, FIRST_PAGE + (k - 2) * ARCHIVE_PAGE + len(chunk)
            page = _render(site_dir, a, "../", seo_title="Planes en %s · página %d" % (name, k), h1="Planes en %s · página %d" % (name, k),
                           desc="Planes en %s del %s al %s (de %s), ordenados por fecha." % (name, fmt_n(first), fmt_n(last), fmt_n(len(items))),
                           items=chunk, crumbs=crumbs + [("Página %d" % k, a)], params="prov=%s" % code, t0=t0, updated=upd,
                           cards=_compact(chunk, "../", t0), list_title="Planes del %s al %s" % (fmt_n(first), fmt_n(last)),
                           more=pager(k, "../"), links=_p(['<a href="%s.html">Planes en %s</a>' % (base, html.escape(name))] + sib))
            done(a, page)

    # ---- provincia: este fin de semana y gratis
    for (code, suf), sub in extras.items():
        name, base = prov_name[code], prov_slug[code]
        fn = "p/%s-%s.html" % (base, suf)
        if suf == "fin-de-semana":
            ttl, h1 = "Qué hacer este fin de semana en %s (%s)" % (name, wrange), "Planes este fin de semana en %s" % name
            dsc = "Qué hacer este fin de semana en %s: %s planes del %s al %s." % (name, fmt_n(len(sub)), fmt_es(fri), fmt_es(sun))
            params = "prov=%s&from=%s&to=%s" % (code, wa, wb)
        else:
            ttl, h1 = "Planes gratis en %s: actividades gratuitas" % name, "Planes gratis en %s" % name
            dsc = "Planes gratis en %s: %s actividades gratuitas próximas, entre conciertos, exposiciones, talleres y fiestas." % (name, fmt_n(len(sub)))
            params = "prov=%s&free=1" % code
        other = "gratis" if suf == "fin-de-semana" else "fin-de-semana"
        links = ['<a href="%s.html">Todos los planes en %s</a>' % (base, html.escape(name))]
        if (code, other) in extras:
            links.append('<a href="%s-%s.html">%s en %s</a>' % (base, other, "Planes gratis" if other == "gratis" else "Planes este fin de semana", html.escape(name)))
        links.append('<a href="../%s">%s en toda España</a>' % ("planes-este-fin-de-semana.html" if suf == "fin-de-semana" else "planes-gratis.html",
                                                                  "Planes este fin de semana" if suf == "fin-de-semana" else "Planes gratis"))
        page = _render(site_dir, fn, "../", seo_title=ttl, h1=h1, desc=dsc, items=sub,
                       crumbs=[("Inicio", ""), (name, "p/%s.html" % base), (h1, fn)], params=params, t0=t0, updated=upd,
                       intro=_intro(sub, ("este fin de semana en %s" if suf == "fin-de-semana" else "gratis en %s") % name, t0, soon=suf != "fin-de-semana"),
                       rss="../feeds/provincia-%s.xml" % code,
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"../?%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(sub)), html.escape(params))) if len(sub) > FIRST_PAGE else "",
                       links=_p(links) + _p(city_links("../", code, suf)))
        done(fn, page)

    # ---- provincia × tipo
    for (code, key), sub in sorted(combos.items()):
        name, base = prov_name[code], prov_slug[code]
        fn = "p/%s-%s.html" % (base, key)
        intent = CAT_INTENT[key]
        ccaa = next(a for c, _, a, _ in prov_pages if c == code)
        sib = ['<a href="%s.html">Todos los planes en %s</a>' % (base, html.escape(name)),
               '<a href="../t/%s.html">%s en toda España</a>' % (key, html.escape(intent))]
        sib += ['<a href="%s-%s.html">%s en %s</a>' % (base, k2, html.escape(CAT_INTENT[k2]), html.escape(name))
                for k2, _, _ in CATEGORIES if k2 != key and (code, k2) in combos]
        page = _render(site_dir, fn, "../", seo_title="%s en %s: agenda y próximas fechas" % (intent, name), h1="%s en %s" % (intent, name),
                       desc="%s en %s (%s): %s planes próximos con fechas, lugar, entradas y calendario." % (intent, name, ccaa, fmt_n(len(sub))),
                       items=sub, crumbs=[("Inicio", ""), (name, "p/%s.html" % base), ("%s en %s" % (intent, name), fn)],
                       params="prov=%s&cat=%s" % (code, key), t0=t0, updated=upd, intro=_intro(sub, "de %s en %s" % (intent.lower(), name), t0),
                       rss="../feeds/provincia-%s.xml" % code,
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"../?prov=%s&amp;cat=%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(sub)), code, key)) if len(sub) > FIRST_PAGE else "",
                       links=_p(sib) + _p(city_links("../", code, key)))
        done(fn, page)

    # ---- ciudades con mucha agenda y sin provincia del mismo nombre
    from urllib.parse import quote
    for (code, ncity), (cname, cfile) in sorted(cities.items(), key=lambda x: x[1][1]):
        items = city_items[(code, ncity)]
        pname, base = prov_name[code], prov_slug[code]
        fn = "c/%s.html" % cfile
        params = "prov=%s&city=%s" % (code, quote(cname))
        own = ['<a href="%s-%s.html">%s en %s</a>' % (cfile, suf, html.escape(SUB_LABEL.get(suf) or CAT_INTENT[suf]), html.escape(cname))
               for suf in ["fin-de-semana", "gratis"] + [k for k, _, _ in CATEGORIES] if (code, ncity, suf) in city_subs]
        links = ['<a href="../p/%s.html">Todos los planes en %s</a>' % (base, html.escape(pname))]
        links += ['<a href="../p/%s-%s.html">%s en %s</a>' % (base, suf, lab, html.escape(pname)) for suf, lab in
                  (("fin-de-semana", "Planes este fin de semana"), ("gratis", "Planes gratis")) if (code, suf) in extras]
        page = _render(site_dir, fn, "../", seo_title="Qué hacer en %s: planes y eventos (%s)" % (cname, mes), h1="Planes en %s" % cname,
                       desc="Agenda de planes en %s (%s): %s planes próximos entre conciertos, teatro, exposiciones, deporte y fiestas, con fechas y enlace oficial."
                            % (cname, pname, fmt_n(len(items))),
                       items=items, crumbs=[("Inicio", ""), (pname, "p/%s.html" % base), (cname, fn)], params=params,
                       t0=t0, updated=upd, intro=_intro(items, "en %s" % cname, t0, cities=False),
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"../?%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(items)), html.escape(params))) if len(items) > FIRST_PAGE else "",
                       links=_p(own) + _p(links) + _p([l for l in city_links("../") if 'c/%s.html"' % cfile not in l]))
        done(fn, page)

    # ---- ciudad: este fin de semana, gratis y por tipo de plan
    for (code, ncity, suf), sub in sorted(city_subs.items(), key=lambda x: (cities[x[0][:2]][1], x[0][2])):
        cname, cfile = cities[(code, ncity)]
        pname, base = prov_name[code], prov_slug[code]
        fn = "c/%s-%s.html" % (cfile, suf)
        params = "prov=%s&city=%s" % (code, quote(cname))
        if suf == "fin-de-semana":
            ttl, h1 = "Qué hacer este fin de semana en %s (%s)" % (cname, wrange), "Planes este fin de semana en %s" % cname
            dsc = "Qué hacer este fin de semana en %s: %s planes del %s al %s." % (cname, fmt_n(len(sub)), fmt_es(fri), fmt_es(sun))
            params += "&from=%s&to=%s" % (wa, wb)
            scope, nat_fn, nat_lab = "este fin de semana en %s" % cname, "planes-este-fin-de-semana.html", "Planes este fin de semana"
        elif suf == "gratis":
            ttl, h1 = "Planes gratis en %s: actividades gratuitas" % cname, "Planes gratis en %s" % cname
            dsc = "Planes gratis en %s: %s actividades gratuitas próximas, con fechas, lugar y enlace oficial." % (cname, fmt_n(len(sub)))
            params += "&free=1"
            scope, nat_fn, nat_lab = "gratis en %s" % cname, "planes-gratis.html", "Planes gratis"
        else:
            intent = CAT_INTENT[suf]
            ttl, h1 = "%s en %s: agenda y próximas fechas" % (intent, cname), "%s en %s" % (intent, cname)
            dsc = "%s en %s (%s): %s planes próximos con fechas, lugar, entradas y calendario." % (intent, cname, pname, fmt_n(len(sub)))
            params += "&cat=%s" % suf
            scope, nat_fn, nat_lab = "de %s en %s" % (intent.lower(), cname), "t/%s.html" % suf, intent
        links = ['<a href="%s.html">Todos los planes en %s</a>' % (cfile, html.escape(cname))]
        links += ['<a href="%s-%s.html">%s en %s</a>' % (cfile, s2, html.escape(SUB_LABEL.get(s2) or CAT_INTENT[s2]), html.escape(cname))
                  for s2 in ["fin-de-semana", "gratis"] + [k for k, _, _ in CATEGORIES] if s2 != suf and (code, ncity, s2) in city_subs]
        up_prov = (code, suf) in extras or (code, suf) in combos
        links2 = (['<a href="../p/%s-%s.html">%s en %s</a>' % (base, suf, html.escape(SUB_LABEL.get(suf) or CAT_INTENT[suf]), html.escape(pname))]
                  if up_prov else []) + ['<a href="../%s">%s en toda España</a>' % (nat_fn, html.escape(nat_lab))]
        page = _render(site_dir, fn, "../", seo_title=ttl, h1=h1, desc=dsc, items=sub,
                       crumbs=[("Inicio", ""), (pname, "p/%s.html" % base), (cname, "c/%s.html" % cfile), (h1, fn)],
                       params=params, t0=t0, updated=upd, intro=_intro(sub, scope, t0, cities=False, soon=suf != "fin-de-semana"),
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"../?%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(sub)), html.escape(params))) if len(sub) > FIRST_PAGE else "",
                       links=_p(links) + _p(links2))
        done(fn, page)

    # ---- tipos de plan en toda España
    for key, cname, icon in CATEGORIES:
        items = upcoming([e for e in events if in_cat(e, key)])
        fn = "t/%s.html" % key
        intent = CAT_INTENT[key]
        combo = ['<a href="../p/%s-%s.html">%s en %s</a>' % (prov_slug[c], key, html.escape(intent), html.escape(n))
                 for c, n, _, _ in prov_pages if (c, key) in combos]
        seo_t, h1, desc = ("%s en España: agenda por provincia" % intent, "%s %s en España" % (icon, intent),
                           "%s en toda España: %s planes próximos por provincia, con fechas, entradas y calendario." % (intent, fmt_n(len(items))))
        intro = _intro(items, "de Navidad en España" if key == "navidad" else "de %s en España" % intent.lower(), t0)
        if key == "navidad":
            secs = xmas_sections(upcoming(events), t0)
            yr = season_year(t0)
            short = [XMAS_LABELS[k][0] for k, _, _ in secs if k != "luces"][:4]
            names = [XMAS_LABELS[k][1] for k, _, _ in secs]
            seo_t = "Navidad %d en España: %s" % (yr, _join_es(short) if short else "planes y agenda")
            h1 = "%s Planes de Navidad %d en España" % (icon, yr)
            desc = "Navidad %d en España: %s planes%s, por provincia y con fechas." % (
                yr, fmt_n(len(items)), (" entre " + _join_es(names)) if names else "")
            if secs:
                nav = " · ".join('<a href="#%s">%s (%s)</a>' % (k, html.escape(t), fmt_n(len(it))) for k, t, it in secs)
                blocks = []
                for k, t, it in secs:
                    byp = {}
                    for e in it:
                        byp[e.get("province") or "España"] = byp.get(e.get("province") or "España", 0) + 1
                    provs = " · ".join("%s (%d)" % (html.escape(n), c) for n, c in sorted(byp.items(), key=lambda x: -x[1])[:8])
                    blocks.append('<section id="%s"><h2 style="margin:26px 0 10px">%s (%s)</h2><div class="list">%s</div>'
                                  '<p class="hint">Por provincia: %s</p></section>'
                                  % (k, html.escape(t), fmt_n(len(it)), "".join(_card(e, "../", t0) for e in it[:9]), provs))
                intro += '<nav class="pages" aria-label="Secciones"><p>En esta página: %s</p></nav>%s' % (nav, "".join(blocks))
        page = _render(site_dir, fn, "../", seo_title=seo_t, h1=h1, desc=desc,
                       items=items, crumbs=[("Inicio", ""), (intent, fn)], params="cat=%s" % key, t0=t0, updated=upd,
                       intro=intro, rss="../feeds/tipo-%s.xml" % key,
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"../?cat=%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(items)), key)) if len(items) > FIRST_PAGE else "",
                       links=_p(combo) + _p(city_links("../", None, key)) + _p(type_links("../")) + _p(nat("../")) + _p(prov_links("../")))
        done(fn, page)

    # ---- páginas nacionales por intención de búsqueda
    def dated_pages(day):
        """Las páginas que dependen del día: «hoy» y «este fin de semana»."""
        d = datetime.strptime(day, "%Y-%m-%d").date()
        f, s = weekend_window(d)
        a, b = iso(f), iso(s)
        return [
            ("planes-hoy.html", "Qué hacer hoy en España (%d %s)" % (d.day, _MES_CORTO[d.month - 1]), "Planes para hoy en España",
             [e for e in upcoming(events) if in_window(e, day, day)], "from=%s&to=%s" % (day, day), None, "hoy"),
            ("planes-este-fin-de-semana.html", "Qué hacer este fin de semana en España (%s)" % _short_range(a, b),
             "Planes este fin de semana en España",
             [e for e in upcoming(events) if in_window(e, a, b)], "from=%s&to=%s" % (a, b), "fin-de-semana", "este fin de semana"),
        ]

    t1 = iso(datetime.strptime(t0, "%Y-%m-%d") + timedelta(days=1))
    tomorrow = {x[0]: x for x in dated_pages(t1)}
    national = dated_pages(t0) + [
        ("planes-gratis.html", "Planes gratis en España: actividades gratuitas", "Planes gratis en España",
         [e for e in upcoming(events) if e.get("free") and not is_permanent(e)], "free=1", "gratis", "gratis"),
    ]
    if len(festivals) >= 20:
        national.append(("festivales.html", "Festivales en España: próximas fechas", "Festivales en España", festivals, "q=festival", None, "de festivales"))

    def national_page(fn, ttl, h1, items, params, sub, scope, day, tail="", write=True):
        byp = {}
        for e in items:
            byp[e["province_code"]] = byp.get(e["province_code"], 0) + 1
        plinks = []
        for code, name, _, _ in prov_pages:
            if not byp.get(code):
                continue
            target = "p/%s-%s.html" % (prov_slug[code], sub) if sub and (code, sub) in extras else "p/%s.html" % prov_slug[code]
            plinks.append('<a href="%s">%s</a> (%s)' % (target, html.escape(name), fmt_n(byp[code])))
        page = _render(site_dir, fn, "", seo_title=ttl, h1=h1,
                       desc="%s: %s planes %s en toda España, por provincia, con fechas, lugar y enlace oficial." % (h1, fmt_n(len(items)), scope),
                       items=items, crumbs=[("Inicio", ""), (h1, fn)], params=params, t0=day, updated=upd, tail=tail, write=write,
                       intro=_intro(items, "%s en España" % scope, day, soon=sub not in (None, "fin-de-semana") or fn == "festivales.html") if items else "<p class=\"intro\">Ahora mismo no hay planes con estas condiciones; prueba con las provincias o los tipos de plan.</p>",
                       more=("<p class=\"hint\">Se muestran %d de %s. <a href=\"./?%s\">Ver todos en la app</a>.</p>" % (FIRST_PAGE, fmt_n(len(items)), html.escape(params))) if len(items) > FIRST_PAGE else "",
                       links=_p(["Por provincia: " + " · ".join(plinks)] if plinks else []) + _p(city_links("", None, sub) if sub else city_links("")) + _p([l for l in nat("") if fn not in l]) + _p(type_links("")))
        return page

    for fn, ttl, h1, items, params, sub, scope in national:
        tail = ""
        nxt = tomorrow.get(fn)
        if nxt and nxt[4] != params:  # mañana cambia el día o el fin de semana: se prepara ya esa versión
            tail = next_day_block(national_page(*nxt, day=t1, write=False), t1)
        done(fn, national_page(fn, ttl, h1, items, params, sub, scope, t0, tail=tail))

    # ---- puente de diciembre: la URL es siempre la misma (sin año) para que gane fuerza de un año a otro.
    # Fuera de temporada se queda como página noindex que manda a la agenda, en vez de dar un 404.
    fn = "puente-diciembre.html"
    rango = puente_rango(p_a, p_b)
    params = "from=%s&to=%s" % (pa, pb)
    if puente_on:
        items = puente_items
        days, d = [], p_a
        while d <= p_b:
            di = iso(d)
            n = sum(1 for e in items if in_window(e, di, di))
            days.append('<a href="./?from=%s&amp;to=%s">%s %d</a> (%s)' % (di, di, _DIAS_LARGOS[d.weekday()].capitalize(), d.day, fmt_n(n)))
            d += timedelta(days=1)
        intro = _intro(items, rango, t0, soon=False)
        intro += '<nav class="pages" aria-label="Días del puente"><p>Por día: %s</p></nav>' % " · ".join(days)
        free = [e for e in items if e.get("free")]
        if free:
            intro += ('<p class="hint"><a href="./?%s&amp;free=1">Ver los %s planes gratis del puente en la app</a></p>'
                      % (html.escape(params), fmt_n(len(free))))
        xmas = [e for e in items if in_cat(e, "navidad")]
        # Primero lo más buscado (mercados, belenes, luces, cabalgatas) y después talleres y demás.
        xmas.sort(key=lambda e: 0 if any(rx.search(norm(e.get("title_es") or e["title"])) for _, _, rx, _, _ in XMAS_SECTIONS) else 1)
        if len(xmas) >= 3:
            intro += ('<section id="navidad"><h2 style="margin:26px 0 10px">Navidad en el puente (%s)</h2><div class="list">%s</div>'
                      '<p class="hint"><a href="t/navidad.html">Todos los planes de Navidad: mercados, belenes, luces y cabalgatas</a></p></section>'
                      % (fmt_n(len(xmas)), "".join(_card(e, "", t0) for e in xmas[:6])))
        byp = {}
        for e in items:
            byp.setdefault(e["province_code"], []).append(e)
        order = sorted(byp, key=lambda c: (-len(byp[c]), prov_name.get(c, "")))
        secs, rest = [], []
        for code in order:
            its, name = byp[code], prov_name.get(code, "España")
            if len(its) < 5:
                rest.append('<a href="./?prov=%s&amp;%s">%s</a> (%d)' % (code, html.escape(params), html.escape(name), len(its)))
                continue
            secs.append('<section id="%s"><h3 style="margin:22px 0 8px">Puente de diciembre en %s (%s)</h3>%s'
                        '<p class="hint"><a href="./?prov=%s&amp;%s">Ver los %s planes del puente en %s en la app</a> · '
                        '<a href="p/%s.html">Toda la agenda de %s</a></p></section>'
                        % (prov_slug[code], html.escape(name), fmt_n(len(its)), _compact(its[:8], "", t0), code, html.escape(params),
                           fmt_n(len(its)), html.escape(name), prov_slug[code], html.escape(name)))
        if rest:
            secs.append("<p>Otras provincias: %s</p>" % " · ".join(rest))
        page = _render(site_dir, fn, "", seo_title="Puente de diciembre %d: qué hacer del %d al %d de diciembre" % (p_year, p_a.day, p_b.day),
                       h1="Planes para el puente de diciembre %d" % p_year,
                       desc="Qué hacer en el puente de diciembre de %d, %s: %s planes en toda España por provincia%s, con fechas, lugar y enlace oficial."
                            % (p_year, rango, fmt_n(len(items)), (" (%s gratis)" % fmt_n(len(free))) if free else ""),
                       items=items, crumbs=[("Inicio", ""), ("Puente de diciembre", fn)], params=params, t0=t0, updated=upd,
                       intro=intro, cards="".join(secs), list_title="Planes del puente por provincia",
                       links=_p([l for l in nat("") if fn not in l]) + _p(type_links("")))
        done(fn, page)
    else:
        if p_season:
            msg = ("Todavía hay pocos planes publicados para el puente de diciembre de %d (%s). Los iremos añadiendo cada día; "
                   "mientras tanto, mira qué hacer este fin de semana." % (p_year, rango))
        else:
            msg = ("El puente de diciembre de %d ya pasó. Publicaremos los planes del próximo puente a partir de octubre; "
                   "mientras tanto, mira qué hacer este fin de semana." % p_year)
        _render(site_dir, fn, "", seo_title="Puente de diciembre: planes y agenda", h1="Puente de diciembre", desc=msg,
                items=[], crumbs=[("Inicio", ""), ("Puente de diciembre", fn)], params="", t0=t0, updated=upd,
                robots="noindex,follow", intro="", cards=_p(nat("") + ['<a href="t/navidad.html">Planes de Navidad</a>']),
                list_title="Planes para hoy y los próximos días", links=_p(type_links("")))

    # ---- páginas fijas
    promo = _promo_page()
    with open(os.path.join(site_dir, "promociona-tu-evento.html"), "w", encoding="utf-8") as fh:
        fh.write(promo)
    done("promociona-tu-evento.html", promo)
    src_page = _sources_page(sources or [], updated_at)
    with open(os.path.join(site_dir, "fuentes.html"), "w", encoding="utf-8") as fh:
        fh.write(src_page)
    entries.append(("fuentes.html", "paginas", seo.digest(src_page)))
    pages.append("fuentes.html")
    for fn in legal.write_legal_pages(site_dir):
        with open(os.path.join(site_dir, fn), encoding="utf-8") as fh:
            done(fn, fh.read())

    # ---- fichas: todas se publican; al sitemap solo van las indexables
    event_pages = static.write_event_pages(site_dir, events, prov_slug, cities, upd)
    if fichas_path:  # las fichas de planes que ya no están: noindex y fuera del sitemap
        LAST_RUN["gone"] = static.write_gone_pages(site_dir, events, fichas_path, prov_slug, cities, t0)
    for path, indexable, h in event_pages:
        if indexable:
            entries.append((path, "fichas", h))
    seo.write_sitemaps(site_dir, entries, SITE_URL, state_path)
    with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(seo.robots_txt(SITE_URL))
    return pages + [p for p, _, _ in event_pages]
