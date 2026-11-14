# -*- coding: utf-8 -*-
"""Gobierno Vasco (Kulturklik / Open Data Euskadi): eventos culturales próximos."""
from .classify import classify
from .util import event, http_json

NAME = "Open Data Euskadi"
URL = "https://api.euskadi.eus/culture/events/v1.0/events/upcoming"
HOME = "https://www.kulturklik.euskadi.eus/"
_PROV = {"1": "01", "01": "01", "20": "20", "48": "48", "31": "31"}  # la API incluye Navarra e Iparralde (Francia)


def fetch(log, max_pages=400):
    out = []
    page = 1
    total_pages = 1
    while page <= total_pages and page <= max_pages:
        data = http_json(URL, params={"_page": page, "_elements": 50})
        total_pages = int(data.get("totalPages") or 1)
        for it in data.get("items", []):
            title = it.get("nameEs") or it.get("nameEu")
            rtype = it.get("typeEs") or ""
            ev = event(
                NAME, it.get("id"), title, (it.get("startDate") or "")[:10],
                end=(it.get("endDate") or "")[:10],
                time=_time(it.get("openingHoursEs") or it.get("openingHoursEu")),
                description=it.get("descriptionEs") or it.get("descriptionEu"), subtype=rtype,
                category=classify([rtype], title, it.get("descriptionEs")),
                province_code=_PROV.get(str(it.get("provinceNoraCode") or "")),
                city=it.get("municipalityEs") or it.get("municipalityEu"),
                venue=it.get("establishmentEs") or it.get("establishmentEu"),
                lat=it.get("municipalityLatitude"), lon=it.get("municipalityLongitude"),
                price=it.get("priceEs") or it.get("priceEu"),
                url=it.get("sourceUrlEs") or it.get("urlEventEs") or it.get("sourceUrlEu"),
                tickets_url=it.get("purchaseUrlEs") or it.get("purchaseUrlEu"),
                image=(it.get("images") or [{}])[0].get("imageUrl"),
            )
            if ev:
                out.append(ev)
        page += 1
    log("%s: %d eventos (%d páginas)" % (NAME, len(out), page - 1))
    return out


def _time(s):
    from .util import parse_time
    return parse_time(s)
