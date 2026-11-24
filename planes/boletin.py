# -*- coding: utf-8 -*-
"""Boletín semanal «Planes del finde».

Cada día se genera la edición del próximo fin de semana (o del que está en curso) con los datos del día:
- site/boletin/index.html: la edición en la web, con el botón para apuntarse si hay formulario configurado.
- site/boletin/email.html y email.json: la misma edición lista para enviar por email (HTML con estilos en
  línea y tablas, que es lo que entienden los programas de correo) con el asunto y el texto de vista previa.
- De jueves a domingo, además, site/boletin/AAAA-MM-DD.html (fecha del viernes): la edición archivada,
  y feeds/boletin.xml con las últimas ediciones archivadas, para servicios de «RSS a email».

El envío lo hace un servicio de email (data/boletin.json y docs/boletin.md); Planika solo prepara el contenido.
No se inventa nada: cada plan sale de la agenda, con enlace a su ficha.
"""
import html
import json
import os
import re
from datetime import date, datetime, timedelta, timezone

from . import seo, static
from .classify import CATEGORIES
from .util import country, display_title, is_permanent, iso, norm

SITE_URL = static.SITE_URL
CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "boletin.json")
ARCHIVE_FROM_WEEKDAY = 3   # jueves: la edición entra en el archivo y en el feed
FEED_ITEMS = 8
_MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
CAT = {k: (n, i) for k, n, i in CATEGORIES}
_EDITION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.html$")
# Tipos de plan que encajan mejor en «qué hacer el finde» que una charla o un taller
_BOOST = {"musica": 1.0, "escena": 1.0, "fiestas": 1.0, "gastro": 0.8, "infantil": 0.5, "expos": 0.3, "deporte": 0.3,
          "naturaleza": 0.5, "cine": 0.2, "navidad": 0.8, "charlas": -0.5, "otros": -1.0}
INK, YELLOW, PINK, TEAL, LILAC, HOT, PAGE = "#1a1033", "#ffd23f", "#ff6fb5", "#4fd6c8", "#a78bfa", "#ff3d81", "#fbfaf9"
CARD_BG = [YELLOW, PINK, TEAL, LILAC]


def load_config(path=CONFIG):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def weekend(t0):
    """(viernes, domingo, primer día que cuenta): el finde en curso o el próximo; en finde, desde hoy."""
    wd = t0.weekday()
    fri = t0 - timedelta(days=wd - 4) if wd >= 4 else t0 + timedelta(days=4 - wd)
    return fri, fri + timedelta(days=2), max(fri, t0)


def short_range(a, b):
    if a.month == b.month:
        return "%d–%d %s" % (a.day, b.day, _MES[a.month - 1])
    return "%d %s–%d %s" % (a.day, _MES[a.month - 1], b.day, _MES[b.month - 1])


def _in_weekend(e, a, b):
    if is_permanent(e):
        return False
    if e.get("sessions"):
        return any(a <= d <= b for d in e["sessions"])
    if e["start"] > b or e["end"] < a:
        return False
    # Lo que dura semanas (exposiciones) no es «plan del finde» salvo que empiece ese finde
    return e["start"] >= a or (datetime.strptime(e["end"], "%Y-%m-%d") - datetime.strptime(e["start"], "%Y-%m-%d")).days <= 3


def score(e):
    s = seo.quality_score(e) + _BOOST.get(e.get("category"), 0)
    if e.get("source") == "Selección Planika":
        s += 4  # grandes citas comprobadas a mano
    if re.match(r"^https?://", e.get("image") or ""):
        s += 1
    if e.get("tickets_url"):
        s += 0.5
    return s


def _day(e, a, b):
    """Día del finde en que se puede ir (el primero)."""
    if e.get("sessions"):
        days = [d for d in e["sessions"] if a <= d <= b]
        return days[0] if days else e["start"]
    return max(e["start"], a)


def select(events, t0):
    """La edición: {fri, sun, total, top, free, kids, cities: [(nombre, provincia, código, total, planes)]}."""
    fri, sun, first = weekend(t0)
    a, b = iso(first), iso(sun)
    pool = [e for e in events if _in_weekend(e, a, b) and country(e.get("province_code")) == "ES"]  # boletín de España
    pool.sort(key=lambda e: (-score(e), _day(e, a, b), e.get("time") or "99", e["title"]))
    used = set()

    def take(items, n, per_cat=2, per_city=2, need_image=False, per_prov=2):
        out, cats, cities, provs = [], {}, {}, {}
        for e in items:
            if len(out) >= n:
                break
            if e["id"] in used or (need_image and not re.match(r"^https?://", e.get("image") or "")):
                continue
            c, ci = e.get("category"), (e["province_code"], norm(e.get("city")))
            if cats.get(c, 0) >= per_cat or cities.get(ci, 0) >= per_city or provs.get(ci[0], 0) >= per_prov:
                continue
            provs[ci[0]] = provs.get(ci[0], 0) + 1
            cats[c] = cats.get(c, 0) + 1
            cities[ci] = cities.get(ci, 0) + 1
            used.add(e["id"])
            out.append(e)
        return out

    top = take(pool, 6, need_image=True) or take(pool, 6)
    free = take([e for e in pool if e.get("free")], 4)
    kids = take([e for e in pool if e.get("category") == "infantil"], 4, per_cat=4)
    count, names = {}, {}
    for e in pool:
        k = (e["province_code"], norm(e.get("city")))
        if k[1]:
            count[k] = count.get(k, 0) + 1
            names.setdefault(k, (e["city"], e.get("province") or ""))
    cities = []
    for k in sorted(count, key=lambda k: -count[k])[:6]:
        items = take([e for e in pool if (e["province_code"], norm(e.get("city"))) == k], 3, per_cat=1, per_city=3, per_prov=3)
        if items:
            cities.append((names[k][0], names[k][1], k[0], count[k], items))
    return {"fri": fri, "sun": sun, "first": first, "total": len(pool), "top": top, "free": free, "kids": kids,
            "cities": cities}


# ---------------------------------------------------------------- email (tablas y estilos en línea)

def _link(e, campaign):
    return "%s/e/%s?utm_source=boletin&utm_medium=email&utm_campaign=%s" % (SITE_URL, static.event_file(e), campaign)


def _when(e, ed):
    d = datetime.strptime(_day(e, iso(ed["first"]), iso(ed["sun"])), "%Y-%m-%d")
    s = "%s %d" % (_DIAS[d.weekday()], d.day)
    return s + (" · " + e["time"] if e.get("time") else "")


def _where(e):
    parts = [p for p in (e.get("venue"), e.get("city")) if p]
    return " · ".join(dict.fromkeys(parts))


def _esc(s):
    return html.escape(str(s or ""), quote=True)


def _row_event(e, ed, campaign, bg, big=False):
    name, icon = CAT.get(e.get("category"), ("Plan", "✨"))
    img = ""
    if big and re.match(r"^https?://", e.get("image") or ""):
        img = ('<tr><td style="padding:0"><a href="%s"><img src="%s" width="560" alt="" style="display:block;width:100%%;'
               'max-width:560px;height:auto;border:0;border-bottom:3px solid %s;border-radius:13px 13px 0 0"></a></td></tr>'
               % (_esc(_link(e, campaign)), _esc(e["image"]), INK))
    badges = '<span style="display:inline-block;background:#fff;border:2px solid %s;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:700">%s %s</span>' % (INK, icon, _esc(name))
    if e.get("free"):
        badges += ' <span style="display:inline-block;background:%s;color:#fff;border:2px solid %s;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:700">Gratis</span>' % (HOT, INK)
    return ('<tr><td style="padding:0 0 14px"><table role="presentation" width="100%%" cellspacing="0" cellpadding="0" '
            'style="background:%s;border:3px solid %s;border-radius:16px;border-collapse:separate">%s'
            '<tr><td style="padding:12px 14px 14px;font-family:Arial,Helvetica,sans-serif;color:%s">%s'
            '<div style="font-size:%dpx;line-height:1.25;font-weight:800;margin:8px 0 6px"><a href="%s" style="color:%s;text-decoration:none">%s</a></div>'
            '<div style="font-size:14px;font-weight:700">📅 %s</div><div style="font-size:14px">📍 %s</div>'
            '</td></tr></table></td></tr>'
            % (bg, INK, img, INK, badges, 20 if big else 17, _esc(_link(e, campaign)), INK, _esc(display_title(e)),
               _esc(_when(e, ed)), _esc(_where(e))))


def _section(title, items, ed, campaign, big=False, more=None):
    if not items:
        return ""
    rows = "".join(_row_event(e, ed, campaign, CARD_BG[i % 4], big) for i, e in enumerate(items))
    head = ('<tr><td style="padding:22px 0 12px"><span style="display:inline-block;background:%s;border:3px solid %s;'
            'border-radius:12px;padding:5px 12px;font-family:Arial,Helvetica,sans-serif;font-size:19px;font-weight:800;color:%s">%s</span></td></tr>'
            % (YELLOW, INK, INK, title))
    tail = ""
    if more:
        tail = ('<tr><td style="padding:0 0 6px;font-family:Arial,Helvetica,sans-serif;font-size:15px;font-weight:700">'
                '<a href="%s" style="color:%s">%s →</a></td></tr>' % (_esc(more[0]), HOT, _esc(more[1])))
    return head + rows + tail


def subject(ed):
    star = display_title(ed["top"][0]) if ed["top"] else ""
    s = "Planes del finde %s" % short_range(ed["fri"], ed["sun"])
    return s + (": %s y más" % star if star and len(star) <= 50 else "")


def preview(ed):
    return "%s planes en toda España: lo más destacado, gratis, con niños y por ciudades." % _fmt_n(ed["total"])


def _fmt_n(n):
    return "{:,}".format(n).replace(",", ".")


def email_html(ed, site_dir=None, unsubscribe="", logo=True):
    """HTML del email. unsubscribe: enlace o etiqueta del servicio de envío para darse de baja."""
    campaign = "finde-%s" % iso(ed["fri"])
    utm = "?utm_source=boletin&utm_medium=email&utm_campaign=%s" % campaign
    city_blocks = ""
    for name, prov, code, n, items in ed["cities"]:
        more = None
        if site_dir:
            for rel in _city_pages(name, prov, code):
                if os.path.exists(os.path.join(site_dir, rel)):
                    more = ("%s/%s%s" % (SITE_URL, rel, utm), "Los %s planes del finde en %s" % (_fmt_n(n), name))
                    break
        city_blocks += _section("📍 %s" % _esc(name), items, ed, campaign, more=more)
    body = (_section("⭐ Lo más destacado", ed["top"], ed, campaign, big=True)
            + _section("🆓 Gratis", ed["free"], ed, campaign)
            + _section("🧒 Con niños", ed["kids"], ed, campaign)
            + city_blocks)
    unsub = (' · <a href="%s" style="color:%s">Darse de baja</a>' % (unsubscribe, INK)) if unsubscribe else ""
    return """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>%(subject)s</title></head>
<body style="margin:0;padding:0;background:%(page)s">
<div style="display:none;max-height:0;overflow:hidden">%(preview)s</div>
<table role="presentation" width="100%%" cellspacing="0" cellpadding="0" style="background:%(page)s"><tr><td align="center" style="padding:18px 10px">
<table role="presentation" width="600" cellspacing="0" cellpadding="0" style="width:100%%;max-width:600px">
%(logo)s<tr><td style="background:%(ink)s;border-radius:16px;padding:18px 18px 16px;font-family:Arial,Helvetica,sans-serif;color:#fff">
<div style="font-size:14px;font-weight:700;color:%(yellow)s;text-transform:uppercase;letter-spacing:1px">Boletín · Planes del finde</div>
<div style="font-size:26px;font-weight:900;line-height:1.2;margin:4px 0 6px">Qué hacer del %(range)s</div>
<div style="font-size:15px">%(total)s planes en toda España este fin de semana. Aquí tienes una selección; el resto, en la web.</div>
</td></tr>
%(body)s
<tr><td style="padding:18px 0 6px" align="center"><a href="%(site)s/planes-este-fin-de-semana.html%(utm)s" style="display:inline-block;background:%(hot)s;color:#fff;border:3px solid %(ink)s;border-radius:999px;padding:12px 22px;font-family:Arial,Helvetica,sans-serif;font-size:17px;font-weight:800;text-decoration:none">Ver los %(total)s planes del finde</a></td></tr>
<tr><td style="padding:16px 4px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:#4a4263">
Planika reúne planes de agendas públicas y oficiales. Comprueba siempre fechas, horarios y precios en la web del organizador.<br>
<a href="%(site)s/%(utm)s" style="color:%(ink)s">planikaapp.com</a> · <a href="https://www.instagram.com/planikaapp/" style="color:%(ink)s">Instagram</a> · <a href="%(site)s/privacidad.html" style="color:%(ink)s">Privacidad</a>%(unsub)s
</td></tr>
</table></td></tr></table></body></html>
""" % dict(subject=_esc(subject(ed)), preview=_esc(preview(ed)), page=PAGE, ink=INK, yellow=YELLOW, hot=HOT, site=SITE_URL,
           utm=utm, range=short_range(ed["first"], ed["sun"]), total=_fmt_n(ed["total"]), body=body, unsub=unsub,
           logo=('<tr><td style="padding:0 0 8px;font-family:Arial,Helvetica,sans-serif"><a href="%s/%s" style="color:%s;'
                 'text-decoration:none;font-size:30px;font-weight:900">📅 Planika</a></td></tr>\n' % (SITE_URL, utm, INK)) if logo else "")


def _city_pages(name, prov, code):
    """Páginas de la web con los planes del finde de esa localidad (la de la ciudad o la de su provincia)."""
    from .publish import slug
    out = ["c/%s-fin-de-semana.html" % slug(name)]
    if norm(name) == norm(prov) or norm(name) in norm(prov) or norm(prov) in norm(name):
        out.append("p/%s-fin-de-semana.html" % slug(prov))
    return out


# ---------------------------------------------------------------- web

_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s · Planika</title><meta name="description" content="%(desc)s">
<meta name="robots" content="%(robots)s">%(canonical)s
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="%(title)s"><meta property="og:description" content="%(desc)s"><meta property="og:image" content="%(site)s/og.jpg">
<meta name="theme-color" content="#ffd23f"><link rel="stylesheet" href="/styles.css"><link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Planika · Boletín «Planes del finde»" href="/feeds/boletin.xml">
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="/" style="text-decoration:none;color:inherit"><span class="brandname">Planika</span></a></div>
<h1 class="tagline">%(h1)s</h1>
<p class="lead">%(lead)s</p>
<p class="meta">%(signup)s<a class="btn" href="/planes-este-fin-de-semana.html">Todos los planes del finde</a></p></div></header>
<main class="wrap" style="max-width:680px">
%(email)s
%(archive)s
<nav class="foot" style="border:0;margin-top:30px"><p><a href="/">Inicio</a> · <a href="/planes-este-fin-de-semana.html">Planes este fin de semana</a> · <a href="/feeds/boletin.xml">RSS del boletín</a> · <a href="/privacidad.html">Privacidad y cookies</a> · <a href="/privacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="/aviso-legal.html">Aviso legal</a></p></nav>
</main></body></html>
"""


def _body_only(email):
    m = re.search(r"<body[^>]*>(.*)</body>", email, re.S)
    return m.group(1) if m else email


def web_page(ed, email, config, archive=(), is_index=True):
    form = (config or {}).get("form_url") or ""
    signup = ('<a class="btn primary" href="%s" target="_blank" rel="noopener">✉️ Recíbelo cada jueves en tu email</a> '
              % _esc(form)) if form else ""
    rng = short_range(ed["first"], ed["sun"])
    title = "Planes del finde %s: qué hacer en España" % rng if is_index else "Boletín «Planes del finde» del %s" % rng
    lead = ("Cada jueves, una selección de planes para el fin de semana en toda España: lo más destacado, gratis, "
            "con niños y por ciudades. " + ("Gratis y te das de baja cuando quieras." if form else "Muy pronto, también por email."))
    arch = ""
    if archive:
        links = " · ".join('<a href="/boletin/%s">%s</a>' % (fn, _esc(lab)) for fn, lab in archive)
        arch = '<h2 style="margin:26px 0 8px">Ediciones anteriores</h2><p>%s</p>' % links
    # La edición de la web solo se indexa si hay formulario (es la página para apuntarse); las archivadas, nunca
    robots = "index,follow" if (is_index and form) else "noindex,follow"
    canonical = '<link rel="canonical" href="%s/boletin/">' % SITE_URL if is_index else ""
    return _PAGE % dict(title=_esc(title), desc=_esc(preview(ed)), robots=robots, canonical=canonical, site=SITE_URL,
                        analytics=static.BEACON, h1=_esc("Boletín «Planes del finde»" if is_index else title), lead=_esc(lead),
                        signup=signup, email=_body_only(email), archive=arch)


# ---------------------------------------------------------------- feed RSS (para «RSS a email»)

def _rfc822(d):
    return d.strftime("%a, %d %b %Y %H:%M:%S +0000")


def feed(editions):
    items = []
    for fri, title, desc, content in editions:
        pub = datetime(fri.year, fri.month, fri.day, 6, 0, tzinfo=timezone.utc) - timedelta(days=1)  # jueves por la mañana
        link = "%s/boletin/%s.html" % (SITE_URL, iso(fri))
        items.append("<item><title>%s</title><link>%s</link><guid isPermaLink=\"true\">%s</guid><pubDate>%s</pubDate>"
                     "<description>%s</description><content:encoded><![CDATA[%s]]></content:encoded></item>"
                     % (_esc(title), link, link, _rfc822(pub), _esc(desc), content.replace("]]>", "]]&gt;")))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
            '<channel><title>Planika · Boletín «Planes del finde»</title><link>%s/boletin/</link>'
            '<description>Cada jueves, planes para el fin de semana en toda España</description><language>es-es</language>%s'
            '</channel></rss>\n' % (SITE_URL, "".join(items)))


def write(site_dir, events, t0=None, config=None):
    """Genera la edición del finde, el archivo y el feed. Devuelve la edición (dict) o None si no hay planes."""
    t0 = t0 or date.today()
    config = load_config() if config is None else config
    ed = select(events, t0)
    out = os.path.join(site_dir, "boletin")
    os.makedirs(out, exist_ok=True)
    if not ed["total"]:
        return None
    unsub = config.get("unsubscribe_tag") or ""
    mail = email_html(ed, site_dir, unsubscribe=unsub)
    web_mail = email_html(ed, site_dir, logo=False)
    with open(os.path.join(out, "email.html"), "w", encoding="utf-8") as fh:
        fh.write(mail)
    with open(os.path.join(out, "email.json"), "w", encoding="utf-8") as fh:
        json.dump({"edicion": iso(ed["fri"]), "asunto": subject(ed), "vista_previa": preview(ed), "planes": ed["total"],
                   "generado": iso(t0)}, fh, ensure_ascii=False, indent=1)
    # Archivo: de jueves a domingo se guarda (y se actualiza) la edición de ese finde
    if t0.weekday() >= ARCHIVE_FROM_WEEKDAY or t0 >= ed["fri"]:
        with open(os.path.join(out, "%s.html" % iso(ed["fri"])), "w", encoding="utf-8") as fh:
            fh.write(web_page(ed, web_mail, config, is_index=False))
    archived = sorted((fn for fn in os.listdir(out) if _EDITION_RE.match(fn)), reverse=True)
    labels = []
    editions = []
    for fn in archived[:FEED_ITEMS]:
        fri = datetime.strptime(fn[:10], "%Y-%m-%d").date()
        labels.append((fn, short_range(fri, fri + timedelta(days=2))))
        with open(os.path.join(out, fn), encoding="utf-8") as fh:
            page = fh.read()
        m = re.search(r"<main[^>]*>(.*?)(<h2 style=\"margin:26px 0 8px\">Ediciones anteriores|<nav class=\"foot\")", page, re.S)
        t = re.search(r"<title>(.*?) · Planika</title>", page)
        d = re.search(r'<meta name="description" content="([^"]*)"', page)
        editions.append((fri, html.unescape(t.group(1)) if t else fn, html.unescape(d.group(1)) if d else "",
                         m.group(1).strip() if m else ""))
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(web_page(ed, web_mail, config, archive=[x for x in labels if x[0] != "%s.html" % iso(ed["fri"])], is_index=True))
    feeds = os.path.join(site_dir, "feeds")
    os.makedirs(feeds, exist_ok=True)
    with open(os.path.join(feeds, "boletin.xml"), "w", encoding="utf-8") as fh:
        fh.write(feed(editions))
    return ed
