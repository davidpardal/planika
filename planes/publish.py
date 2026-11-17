# -*- coding: utf-8 -*-
"""Salidas derivadas: agrupación de sesiones, salud de fuentes, feeds RSS, páginas estáticas y sitemap."""
import html
import json
import os
import re
from datetime import datetime, timedelta

from . import static
from .classify import CATEGORIES
from .util import PROVINCIAS, is_permanent, iso, norm, today

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
    health["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
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
            html.escape(e["title"]), html.escape(e.get("url") or e.get("tickets_url") or SITE_URL + "/?e=" + e["id"]),
            e["id"], html.escape(CAT_NAME.get(e["category"], "Otros")), html.escape(body))
    return ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<rss version=\"2.0\"><channel><title>%s</title><link>%s</link>"
            "<description>%s</description><language>es</language><lastBuildDate>%s</lastBuildDate>%s</channel></rss>\n") % (
        html.escape(title), html.escape(link), html.escape(desc),
        datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0100"), "".join(item(e) for e in items))


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
        items = [e for e in soon if e["category"] == key][:120]
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
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="%(canonical)s">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="%(seo_title)s"><meta property="og:description" content="%(desc)s"><meta property="og:url" content="%(canonical)s">
<meta property="og:image" content="%(site)s/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="%(seo_title)s"><meta name="twitter:description" content="%(desc)s"><meta name="twitter:image" content="%(site)s/og.jpg"><meta name="theme-color" content="#ffd23f">
<link rel="stylesheet" href="../styles.css"><link rel="icon" href="../icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="RSS %(title)s" href="%(rss)s">
<script type="application/ld+json">%(jsonld)s</script>
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="../" style="text-decoration:none;color:inherit"><h1>Planika</h1></a></div>
<p class="tagline">%(title)s</p><p class="lead">%(desc)s</p>
<p class="meta"><a class="btn primary" href="../?%(params)s">Abrir en la app con filtros y calendario</a> &nbsp; <a class="btn" href="%(rss)s">RSS</a></p></div></header>
<main class="wrap"><h2 style="margin:22px 0 10px">Próximos planes (%(count)d)</h2>
<div class="list">%(cards)s</div>
%(more)s
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p>%(links)s</p>
<p><a href="../promociona-tu-evento.html">¿Organizas un evento? Publícalo gratis en Planika</a></p></nav>
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
<header class="hero"><div class="wrap"><div class="brand"><a href="./" style="text-decoration:none;color:inherit"><h1>Planika</h1></a></div>
<p class="tagline">Promociona tu evento gratis</p>
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
<h2 style="margin:26px 0 10px">Precios</h2>
<div class="list">
<article class="card"><div class="body"><div class="badges"><span class="badge">Publicar</span></div><h3>0 €</h3><p class="desc">Tu evento publicado con ficha propia y en todos los listados que le correspondan. Gratis, para siempre.</p></div></article>
<article class="card"><div class="body"><div class="badges"><span class="badge">Destacado</span><span class="badge free">Muy pronto</span></div><h3>9,90 € por evento</h3><p class="desc">Primero en tu provincia y tu categoría, con insignia de destacado y foto grande.</p></div></article>
<article class="card"><div class="body"><div class="badges"><span class="badge">Pack Sala</span><span class="badge free">Muy pronto</span></div><h3>29 € al mes</h3><p class="desc">Todos los eventos de tu sala destacados, sin límite.</p></div></article>
</div>
<h2 style="margin:26px 0 10px">Preguntas frecuentes</h2>
%(faq)s
<p class="meta" style="margin-top:26px"><a class="btn primary" href="%(form)s" target="_blank" rel="noopener">Publica tu evento gratis</a></p>
<p class="src">Al enviar el formulario confirmas que tienes derecho a publicar el evento y su imagen. La exactitud de fechas, horarios y precios es responsabilidad del organizador.</p>
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p><a href="./">Inicio</a> · <a href="p/alava.html">Planes en Álava</a> · <a href="t/musica.html">Música y conciertos</a></p></nav>
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


def _itemlist_ld(items, limit=20):
    """JSON-LD ItemList con los primeros planes de la página, enlazando a la ficha de cada plan."""
    els = [{"@type": "ListItem", "position": i, "url": "%s/e/%s" % (SITE_URL, static.event_file(e)),
            "name": e.get("title_es") or e["title"]} for i, e in enumerate(items[:limit], 1)]
    ld = {"@context": "https://schema.org", "@type": "ItemList",
          "numberOfItems": len(items), "itemListElement": els}
    return json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def _card(e):
    when = _when_short(e)
    if e.get("sessions") and not is_permanent(e):
        when = "%s (+%d fechas)" % (e["sessions"][0], len(e["sessions"]) - 1)
    where = " · ".join(x for x in (e.get("venue"), e.get("city"), e.get("province")) if x)
    link = "../e/" + static.event_file(e)  # la ficha propia del plan: enlazado interno para buscadores
    badges = ("<span class=\"badge free\">Gratis</span>" if e.get("free") else "") + (
        "<span class=\"badge\">Permanente</span>" if is_permanent(e) else "")
    return ("<article class=\"card\"><div class=\"body\"><div class=\"badges\"><span class=\"badge\">%s %s</span>%s</div>"
            "<h3><a href=\"%s\">%s</a></h3><div class=\"when\">📅 %s%s</div>"
            "<div class=\"where\">📍 %s</div>%s<div class=\"src\">Fuente: %s</div></div></article>") % (
        CAT_ICON.get(e["category"], "✨"), html.escape(CAT_NAME.get(e["category"], "Otros")),
        badges,
        html.escape(link), html.escape(e.get("title_es") or e["title"]), when, " · " + e["time"] if e.get("time") else "",
        html.escape(where), ("<p class=\"desc\">%s</p>" % html.escape(e["description"])) if e.get("description") else "",
        html.escape(e["source"]))


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


def write_pages(site_dir, events):
    t0 = iso(today())
    def upcoming(items):
        # Primero la agenda con fecha; después las visitas permanentes.
        return sorted(items, key=lambda e: (1 if is_permanent(e) else 0, max(e["start"], t0), e.get("time") or "99", e.get("title") or ""))
    pages = []
    prov_dir = os.path.join(site_dir, "p")
    type_dir = os.path.join(site_dir, "t")
    os.makedirs(prov_dir, exist_ok=True)
    os.makedirs(type_dir, exist_ok=True)
    prov_links = []
    prov_links_up = []
    prov_pages = []
    for code, name, ccaa in PROVINCIAS:
        items = upcoming([e for e in events if e["province_code"] == code])
        if not items:
            continue
        prov_pages.append((code, name, ccaa, items))
        prov_links.append("<a href=\"%s.html\">%s</a> (%d)" % (slug(name), html.escape(name), len(items)))
        prov_links_up.append("<a href=\"../p/%s.html\">%s</a> (%d)" % (slug(name), html.escape(name), len(items)))
    type_links = ["<a href=\"%s.html\">%s %s</a>" % (k, i, html.escape(n)) for k, n, i in CATEGORIES]
    # Páginas combinadas provincia × tipo ("Música y conciertos en Álava"): solo con
    # suficientes planes, para no generar páginas pobres que nadie busca.
    combos = {}
    for code, name, ccaa, items in prov_pages:
        for key, cname, _ in CATEGORIES:
            sub = [e for e in items if e["category"] == key]
            if len(sub) >= 5:
                combos[(code, key)] = sub

    def combo_links_prov(code, name):
        return ["<a href=\"%s-%s.html\">%s en %s</a>" % (slug(name), k, html.escape(cn), html.escape(name))
                for k, cn, _ in CATEGORIES if (code, k) in combos]

    def combo_links_cat(key):
        return ["<a href=\"../p/%s-%s.html\">%s en %s</a>" % (slug(n), key, html.escape(CAT_NAME[key]), html.escape(n))
                for c, n, _, _ in prov_pages if (c, key) in combos]
    for code, name, ccaa, items in prov_pages:
        fn = slug(name) + ".html"
        desc = "Agenda de planes de ocio en %s (%s): %d planes próximos entre conciertos, teatro, exposiciones, deporte, ferias y fiestas." % (name, ccaa, len(items))
        body = _PAGE % dict(
            title="Planes en %s" % name, seo_title="Planes y eventos en %s: conciertos, teatro, exposiciones y más" % name, site=SITE_URL, desc=html.escape(desc), canonical="%s/p/%s" % (SITE_URL, fn),
            rss="../feeds/provincia-%s.xml" % code, params="prov=%s" % code, count=len(items),
            jsonld=_itemlist_ld(items), analytics=static.BEACON,
            cards="".join(_card(e) for e in items[:60]),
            more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?prov=%s\">Ver todos en la app</a>.</p>" % (len(items), code)) if len(items) > 60 else "",
            links=" · ".join(["<a href=\"../t/%s.html\">%s</a>" % (k, html.escape(n)) for k, n, _ in CATEGORIES] + combo_links_prov(code, name) + prov_links))
        with open(os.path.join(prov_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
        pages.append("p/" + fn)
        # Páginas de intención de búsqueda: "planes este fin de semana en X" y "planes gratis en X"
        base = slug(name)
        fri, sun = weekend_window(today())
        a, b = iso(fri), iso(sun)
        extras = (
            ("fin-de-semana", "Planes este fin de semana en %s" % name,
             "Qué hacer este fin de semana en %s: %%d planes del %s al %s." % (name, fmt_es(fri), fmt_es(sun)),
             [e for e in items if in_window(e, a, b)], "prov=%s&from=%s&to=%s" % (code, a, b)),
            ("gratis", "Planes gratis en %s" % name,
             "Planes gratis en %s: %%d actividades gratuitas próximas, entre conciertos, exposiciones, talleres y fiestas." % name,
             [e for e in items if e.get("free") and not is_permanent(e)], "prov=%s&free=1" % code),
        )
        made = []
        for suffix, ttl, dsc, sub, params in extras:
            if len(sub) < 3:
                continue
            efn = "%s-%s.html" % (base, suffix)
            ebody = _PAGE % dict(
                title=ttl, seo_title=ttl + " · conciertos, teatro y más", site=SITE_URL, desc=html.escape(dsc % len(sub)),
                canonical="%s/p/%s" % (SITE_URL, efn), rss="../feeds/provincia-%s.xml" % code, params=params, count=len(sub),
                jsonld=_itemlist_ld(sub), analytics=static.BEACON, cards="".join(_card(e) for e in sub[:60]),
                more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?%s\">Ver todos en la app</a>.</p>" % (len(sub), params)) if len(sub) > 60 else "",
                links="<a href=\"%s\">Todos los planes en %s</a> · %s" % (fn, html.escape(name), " · ".join(
                    "<a href=\"%s-%s.html\">%s</a>" % (base, x, l) for x, l in (("fin-de-semana", "Fin de semana"), ("gratis", "Gratis")) if x != suffix)))
            with open(os.path.join(prov_dir, efn), "w", encoding="utf-8") as fh:
                fh.write(ebody)
            pages.append("p/" + efn)
            made.append((efn, {"fin-de-semana": "Planes este fin de semana", "gratis": "Planes gratis"}[suffix]))
        if made:  # enlazado interno desde la página de la provincia
            path = os.path.join(prov_dir, fn)
            txt = open(path, encoding="utf-8").read()
            nav = "<p>%s</p>" % " · ".join("<a href=\"%s\">%s en %s</a>" % (f, l, html.escape(name)) for f, l in made)
            open(path, "w", encoding="utf-8").write(txt.replace("</main></body></html>", nav + "</main></body></html>", 1))
    prov_by_code = {c: (n, a) for c, n, a, _ in prov_pages}
    for (code, key), sub in sorted(combos.items()):
        name, ccaa = prov_by_code[code]
        base = slug(name)
        fn = "%s-%s.html" % (base, key)
        ttl = "%s en %s" % (CAT_NAME[key], name)
        desc = "%s en %s (%s): %d planes próximos con fechas, lugar, entradas y calendario." % (CAT_NAME[key], name, ccaa, len(sub))
        sib = ["<a href=\"%s.html\">Todos los planes en %s</a>" % (base, html.escape(name)),
               "<a href=\"../t/%s.html\">%s en toda España</a>" % (key, html.escape(CAT_NAME[key]))]
        sib += ["<a href=\"%s-%s.html\">%s en %s</a>" % (base, k2, html.escape(CAT_NAME[k2]), html.escape(name))
                for k2, _, _ in CATEGORIES if k2 != key and (code, k2) in combos]
        body = _PAGE % dict(
            title=ttl, seo_title=ttl, site=SITE_URL, desc=html.escape(desc), canonical="%s/p/%s" % (SITE_URL, fn),
            rss="../feeds/provincia-%s.xml" % code, params="prov=%s&cat=%s" % (code, key), count=len(sub),
            jsonld=_itemlist_ld(sub), analytics=static.BEACON,
            cards="".join(_card(e) for e in sub[:60]),
            more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?prov=%s&cat=%s\">Ver todos en la app</a>.</p>" % (len(sub), code, key)) if len(sub) > 60 else "",
            links=" · ".join(sib))
        with open(os.path.join(prov_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
        pages.append("p/" + fn)
    for key, name, icon in CATEGORIES:
        items = upcoming([e for e in events if e["category"] == key])
        fn = key + ".html"
        desc = "%s en toda España: %d planes próximos por provincia, con fechas, entradas y calendario." % (name, len(items))
        body = _PAGE % dict(
            title="%s %s" % (icon, name), seo_title="%s en España: agenda de planes por provincia" % name, site=SITE_URL, desc=html.escape(desc), canonical="%s/t/%s" % (SITE_URL, fn),
            rss="../feeds/tipo-%s.xml" % key, params="cat=%s" % key, count=len(items),
            jsonld=_itemlist_ld(items), analytics=static.BEACON,
            cards="".join(_card(e) for e in items[:60]),
            more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?cat=%s\">Ver todos en la app</a>.</p>" % (len(items), key)) if len(items) > 60 else "",
            links=" · ".join(type_links + combo_links_cat(key) + prov_links_up))
        with open(os.path.join(type_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
        pages.append("t/" + fn)
    with open(os.path.join(site_dir, "promociona-tu-evento.html"), "w", encoding="utf-8") as fh:
        fh.write(_promo_page())
    pages.append("promociona-tu-evento.html")
    prov_slugs = {code: slug(name) for code, name, _ in PROVINCIAS}
    event_pages = static.write_event_pages(site_dir, events, prov_slugs)
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">")
        lm = "<lastmod>%s</lastmod>" % iso(today())
        fh.write("<url><loc>%s/</loc>%s</url>" % (SITE_URL, lm))
        for p in pages:
            fh.write("<url><loc>%s/%s</loc>%s</url>" % (SITE_URL, p, lm))
        for p in event_pages:
            fh.write("<url><loc>%s/%s</loc>%s</url>" % (SITE_URL, p, lm))
        fh.write("</urlset>\n")
    with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE_URL)
    return pages + event_pages
