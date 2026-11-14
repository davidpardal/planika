# -*- coding: utf-8 -*-
"""Ayuntamiento de Madrid: actividades culturales y de ocio de los próximos 100 días."""
from .classify import classify
from .util import event, http_json

NAME = "Ayuntamiento de Madrid"
URL = "https://datos.madrid.es/egob/catalogo/206974-0-agenda-eventos-culturales-100.json"
HOME = "https://datos.madrid.es/portal/site/egob/menuitem.c05c1f754a33a9fbe4b2e4b284f1a5a0/?vgnextoid=6c0b6d01df986410VgnVCM2000000c205a0aRCRD"


def fetch(log):
    data = http_json(URL)
    out = []
    for g in data.get("@graph", []):
        rtype = (g.get("@type") or "").rsplit("/", 1)[-1]
        addr = g.get("address") or {}
        area = addr.get("area") or {}
        loc = g.get("location") or {}
        ev = event(
            NAME, g.get("id"), g.get("title"), (g.get("dtstart") or "")[:10],
            end=(g.get("dtend") or "")[:10], time=g.get("time") or "",
            description=g.get("description"), subtype=rtype,
            category=classify([rtype], g.get("title"), g.get("description"), g.get("audience")),
            province_code="28", city=(area.get("locality") or "Madrid").title(),
            venue=g.get("event-location"), address=area.get("street-address"),
            lat=loc.get("latitude"), lon=loc.get("longitude"),
            price=g.get("price"), free=(g.get("free") == 1), url=g.get("link"),
            audience=g.get("audience"),
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
