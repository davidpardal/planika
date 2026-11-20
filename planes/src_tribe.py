# -*- coding: utf-8 -*-
"""Agendas turísticas oficiales hechas con WordPress + The Events Calendar.

Ese complemento publica una API JSON pública (/wp-json/tribe/events/v1/events) con fecha, hora,
lugar, precio, categorías e imagen. Sirve para ciudades que no tienen agenda en datos abiertos.
Cada web cuenta como una fuente distinta (SOURCE_NAMES), así que si una falla se conservan sus
planes de la última descarga buena sin tocar los de la otra.
"""
import html
import re

from .classify import classify
from .util import event, http_json, iso, strip_html, today

# nombre visible, web, ciudad y provincia por defecto
SITES = [
    ("Visit Palma", "https://visitpalma.com", "Palma", "Illes Balears"),
    ("Visit Elche", "https://www.visitelche.com", "Elche", "Alicante"),
]
NAME = "Agendas turísticas (Palma, Elche)"
HOME = SITES[0][1]
SOURCE_NAMES = [s[0] for s in SITES]
API = "%s/wp-json/tribe/events/v1/events"
MAX_PAGES = 20
_FREE = re.compile(r"^\s*(gratis|gratuito|gratuita|free|entrada libre|0\s*€?|0[,.]00\s*€?)\s*$", re.I)


def _text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _city(found, default):
    """La ciudad de la web manda salvo que el lugar diga otra; «Elx-Elche» se queda en «Elche»."""
    if not found or default.lower() in found.lower():
        return default
    return found


def parse(name, base, city, province, items):
    out = []
    for e in items:
        title = _text(e.get("title"))
        start = (e.get("start_date") or "")[:10]
        end = (e.get("end_date") or "")[:10]
        hhmm = (e.get("start_date") or "")[11:16]
        all_day = e.get("all_day") or hhmm in ("", "00:00")
        venue = e.get("venue") if isinstance(e.get("venue"), dict) else {}
        cats = [c.get("name") for c in e.get("categories") or [] if isinstance(c, dict) and c.get("name")]
        desc = strip_html(e.get("description") or e.get("excerpt") or "", 400)
        cost = _text(e.get("cost"))
        img = e.get("image") if isinstance(e.get("image"), dict) else {}
        kw = dict(
            end=end, time="" if all_day else hhmm, description=desc, subtype=", ".join(cats)[:60],
            category=classify(cats, title, desc), province=province,
            city=_city(_text(venue.get("city")), city), venue=_text(venue.get("venue")), address=_text(venue.get("address")),
            lat=venue.get("geo_lat"), lon=venue.get("geo_lng"), url=e.get("url") or base, image=img.get("url") or "",
        )
        if cost:
            kw["price"] = cost
            if _FREE.match(cost):
                kw["free"] = True
        ev = event(name, e.get("id"), title, start, **kw)
        if ev:
            out.append(ev)
    return out


def fetch_site(name, base, city, province):
    items, page = [], 1
    while page <= MAX_PAGES:
        data = http_json(API % base, params={"per_page": 50, "page": page, "start_date": iso(today())})
        items.extend(data.get("events") or [])
        if page >= int(data.get("total_pages") or 1):
            break
        page += 1
    return parse(name, base, city, province, items)


def fetch(log):
    out = []
    for name, base, city, province in SITES:
        try:
            evs = fetch_site(name, base, city, province)
        except Exception as exc:  # noqa: BLE001 - una web caída no tumba la otra
            log("%s: ERROR %s" % (name, exc.__class__.__name__))
            continue
        log("%s: %d eventos" % (name, len(evs)))
        out.extend(evs)
    return out
