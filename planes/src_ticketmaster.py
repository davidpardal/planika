# -*- coding: utf-8 -*-
"""Ticketmaster Discovery API (requiere TICKETMASTER_API_KEY)."""
import os
import time
from datetime import timedelta

from .classify import classify
from .util import event, http_json, today

NAME = "Ticketmaster"
URL = "https://app.ticketmaster.com/discovery/v2/events.json"
HOME = "https://www.ticketmaster.es/"
SEGMENTS = ["Music", "Sports", "Arts & Theatre", "Film", "Miscellaneous"]
PAGE_SIZE = 200
MAX_PAGES = 5  # la API limita a 1000 resultados por consulta (size * page < 1000)


def fetch(log, days=180):
    key = os.environ.get("TICKETMASTER_API_KEY", "").strip()
    if not key:
        log("%s: omitido (define TICKETMASTER_API_KEY en .env para activarlo)" % NAME)
        return []
    out = {}
    start = today()
    horizon = start + timedelta(days=days)
    # Se trocea por segmento y por ventanas de 30 días para sortear el tope de 1000 resultados.
    win = start
    while win < horizon:
        win_end = min(win + timedelta(days=30), horizon)
        for seg in SEGMENTS:
            for page in range(MAX_PAGES):
                params = {
                    "apikey": key, "countryCode": "ES", "locale": "es-es", "size": PAGE_SIZE, "page": page,
                    "segmentName": seg, "sort": "date,asc",
                    "startDateTime": win.strftime("%Y-%m-%dT00:00:00Z"),
                    "endDateTime": win_end.strftime("%Y-%m-%dT23:59:59Z"),
                }
                try:
                    data = http_json(URL, params=params, retries=2)
                except Exception as exc:  # noqa: BLE001
                    log("%s: error %s (%s, p%d)" % (NAME, exc.__class__.__name__, seg, page))
                    break
                time.sleep(0.25)  # límite de 5 peticiones/segundo
                items = (data.get("_embedded") or {}).get("events") or []
                for it in items:
                    ev = _convert(it)
                    if ev:
                        out[ev["id"]] = ev
                pg = data.get("page") or {}
                if page + 1 >= int(pg.get("totalPages") or 0):
                    break
        win = win_end + timedelta(days=1)
    log("%s: %d eventos" % (NAME, len(out)))
    return list(out.values())


def _convert(it):
    venues = (it.get("_embedded") or {}).get("venues") or [{}]
    v = venues[0]
    dates = (it.get("dates") or {}).get("start") or {}
    cls = (it.get("classifications") or [{}])[0]
    seg = (cls.get("segment") or {}).get("name") or ""
    genre = (cls.get("genre") or {}).get("name") or ""
    sub = (cls.get("subGenre") or {}).get("name") or ""
    imgs = sorted(it.get("images") or [], key=lambda i: -(i.get("width") or 0))
    img = next((i.get("url") for i in imgs if (i.get("ratio") == "16_9" and (i.get("width") or 0) <= 1024)), None) or (imgs[0].get("url") if imgs else "")
    prices = it.get("priceRanges") or []
    price = ""
    if prices:
        p = prices[0]
        lo, hi = p.get("min"), p.get("max")
        if lo is not None and hi is not None and lo != hi:
            price = "%g - %g %s" % (lo, hi, p.get("currency", "EUR"))
        elif lo is not None:
            price = "%g %s" % (lo, p.get("currency", "EUR"))
    loc = v.get("location") or {}
    city = (v.get("city") or {}).get("name") or ""
    state = (v.get("state") or {}).get("name") or ""
    if "test" in (it.get("name") or "").lower() and it.get("test"):
        return None
    return event(
        NAME, it.get("id"), it.get("name"), dates.get("localDate"), time=(dates.get("localTime") or "")[:5],
        description=it.get("info") or it.get("pleaseNote") or "", subtype=(genre if genre and genre != "Undefined" else seg),
        category=classify([seg, genre, sub], it.get("name")),
        province=state, city=city, venue=v.get("name"), address=(v.get("address") or {}).get("line1"),
        lat=loc.get("latitude"), lon=loc.get("longitude"), price=price,
        url=it.get("url"), tickets_url=it.get("url"), image=img,
    )
