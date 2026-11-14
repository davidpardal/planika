# -*- coding: utf-8 -*-
"""Salidas derivadas: agrupación de sesiones, salud de fuentes, feeds RSS, páginas estáticas y sitemap."""
import html
import json
import os
import re
from datetime import datetime, timedelta

from . import static
from .classify import CATEGORIES
from .util import PROVINCIAS, iso, norm, today

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


def _rss(title, link, desc, items):
    def item(e):
        when = e["start"] if e["start"] == e["end"] else "%s – %s" % (e["start"], e["end"])
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
    soon = [e for e in events if e["start"] <= limit]
    soon.sort(key=lambda e: (max(e["start"], iso(today())), e["time"]))
    written = []
    with open(os.path.join(out_dir, "todos.xml"), "w", encoding="utf-8") as fh:
        fh.write(_rss("Planika · próximos planes en España", SITE_URL, "Planes de los próximos %d días" % days, soon[:150]))
    written.append("todos.xml")
    for code, name, _ in PROVINCIAS:
        items = [e for e in soon if e["province_code"] == code][:120]
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
<title>%(title)s · Planika</title><meta name="description" content="%(desc)s">
<link rel="canonical" href="%(canonical)s"><link rel="stylesheet" href="../styles.css"><link rel="icon" href="../icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="RSS %(title)s" href="%(rss)s">
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="../" style="text-decoration:none;color:inherit"><h1>Planika</h1></a></div>
<p class="tagline">%(title)s</p><p class="lead">%(desc)s</p>
<p class="meta"><a class="btn primary" href="../?%(params)s">Abrir en la app con filtros y calendario</a> &nbsp; <a class="btn" href="%(rss)s">RSS</a></p></div></header>
<main class="wrap"><h2 style="margin:22px 0 10px">Próximos planes (%(count)d)</h2>
<div class="list">%(cards)s</div>
%(more)s
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p>%(links)s</p></nav>
</main></body></html>
"""


def _card(e):
    when = e["start"] if e["start"] == e["end"] else "%s – %s" % (e["start"], e["end"])
    if e.get("sessions"):
        when = "%s (+%d fechas)" % (e["sessions"][0], len(e["sessions"]) - 1)
    where = " · ".join(x for x in (e.get("venue"), e.get("city"), e.get("province")) if x)
    link = "../e/" + static.event_file(e)  # la ficha propia del plan: enlazado interno para buscadores
    return ("<article class=\"card\"><div class=\"body\"><div class=\"badges\"><span class=\"badge\">%s %s</span>%s</div>"
            "<h3><a href=\"%s\">%s</a></h3><div class=\"when\">📅 %s%s</div>"
            "<div class=\"where\">📍 %s</div>%s<div class=\"src\">Fuente: %s</div></div></article>") % (
        CAT_ICON.get(e["category"], "✨"), html.escape(CAT_NAME.get(e["category"], "Otros")),
        "<span class=\"badge free\">Gratis</span>" if e.get("free") else "",
        html.escape(link), html.escape(e.get("title_es") or e["title"]), when, " · " + e["time"] if e.get("time") else "",
        html.escape(where), ("<p class=\"desc\">%s</p>" % html.escape(e["description"])) if e.get("description") else "",
        html.escape(e["source"]))


def write_pages(site_dir, events):
    t0 = iso(today())
    def upcoming(items):
        return sorted(items, key=lambda e: (max(e["start"], t0), e.get("time") or "99"))
    pages = []
    prov_dir = os.path.join(site_dir, "p")
    type_dir = os.path.join(site_dir, "t")
    os.makedirs(prov_dir, exist_ok=True)
    os.makedirs(type_dir, exist_ok=True)
    prov_links = []
    prov_pages = []
    for code, name, ccaa in PROVINCIAS:
        items = upcoming([e for e in events if e["province_code"] == code])
        if not items:
            continue
        prov_pages.append((code, name, ccaa, items))
        prov_links.append("<a href=\"%s.html\">%s</a> (%d)" % (slug(name), html.escape(name), len(items)))
    type_links = ["<a href=\"%s.html\">%s %s</a>" % (k, i, html.escape(n)) for k, n, i in CATEGORIES]
    for code, name, ccaa, items in prov_pages:
        fn = slug(name) + ".html"
        desc = "Agenda de planes de ocio en %s (%s): %d planes próximos entre conciertos, teatro, exposiciones, deporte, ferias y fiestas." % (name, ccaa, len(items))
        body = _PAGE % dict(
            title="Planes en %s" % name, desc=html.escape(desc), canonical="%s/p/%s" % (SITE_URL, fn),
            rss="../feeds/provincia-%s.xml" % code, params="prov=%s" % code, count=len(items),
            cards="".join(_card(e) for e in items[:60]),
            more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?prov=%s\">Ver todos en la app</a>.</p>" % (len(items), code)) if len(items) > 60 else "",
            links=" · ".join(["<a href=\"../t/%s.html\">%s</a>" % (k, html.escape(n)) for k, n, _ in CATEGORIES] + prov_links))
        with open(os.path.join(prov_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
        pages.append("p/" + fn)
    for key, name, icon in CATEGORIES:
        items = upcoming([e for e in events if e["category"] == key])
        fn = key + ".html"
        desc = "%s en toda España: %d planes próximos por provincia, con fechas, entradas y calendario." % (name, len(items))
        body = _PAGE % dict(
            title="%s %s" % (icon, name), desc=html.escape(desc), canonical="%s/t/%s" % (SITE_URL, fn),
            rss="../feeds/tipo-%s.xml" % key, params="cat=%s" % key, count=len(items),
            cards="".join(_card(e) for e in items[:60]),
            more=("<p class=\"hint\">Se muestran 60 de %d. <a href=\"../?cat=%s\">Ver todos en la app</a>.</p>" % (len(items), key)) if len(items) > 60 else "",
            links=" · ".join(type_links + prov_links))
        with open(os.path.join(type_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(body)
        pages.append("t/" + fn)
    prov_slugs = {code: slug(name) for code, name, _ in PROVINCIAS}
    event_pages = static.write_event_pages(site_dir, events, prov_slugs)
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">")
        fh.write("<url><loc>%s/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>" % SITE_URL)
        for p in pages:
            fh.write("<url><loc>%s/%s</loc><changefreq>daily</changefreq></url>" % (SITE_URL, p))
        for p in event_pages:
            fh.write("<url><loc>%s/%s</loc></url>" % (SITE_URL, p))
        fh.write("</urlset>\n")
    with open(os.path.join(site_dir, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write("User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n" % SITE_URL)
    return pages + event_pages
