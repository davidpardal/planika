# -*- coding: utf-8 -*-
"""Ayuntamiento de Zaragoza: agenda de actividades de la ciudad (API de datos abiertos)."""
import time
from datetime import datetime

from .classify import classify
from .util import event, http_json, parse_date

NAME = "Ayuntamiento de Zaragoza"
URL = "https://www.zaragoza.es/sede/servicio/actividades/evento/list.json"
HOME = "https://www.zaragoza.es/sede/portal/cultura/agenda/"
PAGE = 100
MAX_PAGES = 60
FIELDS = ("id,title,description,startDate,endDate,subEvent,category,price,image,type,alt,geometry,"
          "population,minAge,maxAge")


def _price(prices):
    if not isinstance(prices, list) or not prices:
        return "", None
    vals = []
    for p in prices:
        if not isinstance(p, dict):
            continue
        try:
            vals.append((float(p.get("hasCurrencyValue") or 0), str(p.get("fareGroup") or "").strip()))
        except (TypeError, ValueError):
            continue
    if not vals:
        return "", None
    if all(v == 0 for v, _ in vals):
        return "Gratis", True
    paid = sorted(v for v, _ in vals if v > 0)
    txt = ("%g €" % paid[0]) if paid[0] == paid[-1] else ("De %g a %g €" % (paid[0], paid[-1]))
    return txt.replace(".", ","), False


def parse(rows):
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        start, end = parse_date(r.get("startDate")), parse_date(r.get("endDate"))
        kind = str(r.get("type") or "")
        if start and end and "curso" in kind.lower():
            # Cursos de larga duración con inscripción: no son un plan para un día
            try:
                if (datetime.strptime(end, "%Y-%m-%d") - datetime.strptime(start, "%Y-%m-%d")).days > 14:
                    continue
            except ValueError:  # la fuente trae alguna fecha mal tecleada ("202-10-07")
                continue
        subs = [s for s in (r.get("subEvent") or []) if isinstance(s, dict)]
        loc = (subs[0].get("location") if subs else None) or {}
        hours = (subs[0].get("openingHours") if subs else None) or []
        tm = str(hours[0].get("startTime") or "")[:5] if hours and isinstance(hours[0], dict) else ""
        coords = ((loc.get("geometry") or {}).get("coordinates") or (r.get("geometry") or {}).get("coordinates") or [None, None])
        lon, lat = (list(coords) + [None, None])[:2]
        try:
            if lat is not None and not (39 < float(lat) < 44):  # coordenadas UTM en vez de WGS84
                lat = lon = None
        except (TypeError, ValueError):
            lat = lon = None
        cats = [c.get("title") for c in (r.get("category") or []) if isinstance(c, dict)]
        price, free = _price(r.get("price"))
        img = str(r.get("image") or "")
        if img.startswith("//"):
            img = "https:" + img
        aud = ", ".join(p.get("title", "") for p in (r.get("population") or []) if isinstance(p, dict))
        ev = event(
            NAME, r.get("id"), r.get("title"), start, end=end, time=tm, description=r.get("description"),
            subtype=(cats[0] if cats else kind), category=classify(cats + [kind], r.get("title"), r.get("description"), aud),
            province_code="50", city=loc.get("addressLocality") or "Zaragoza", venue=loc.get("title"),
            address=loc.get("streetAddress"), lat=lat, lon=lon, price=price, free=free,
            url=r.get("alt") or "https://www.zaragoza.es/sede/servicio/cultura/evento/%s" % r.get("id"),
            image=img, audience=aud,
        )
        if ev:
            out.append(ev)
    return out


def fetch(log):
    rows, total = [], None
    for page in range(MAX_PAGES):
        data = http_json(URL, params={"rows": PAGE, "start": page * PAGE, "srsname": "wgs84", "fl": FIELDS},
                         timeout=(20, 120))
        batch = data.get("result") or []
        rows.extend(batch)
        total = data.get("totalCount") or len(rows)
        if not batch or len(rows) >= total:
            break
        time.sleep(0.4)  # el servidor corta las peticiones muy seguidas
    out = parse(rows)
    log("%s: %d eventos (de %d actividades en vigor)" % (NAME, len(out), len(rows)))
    return out
