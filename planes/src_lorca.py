# -*- coding: utf-8 -*-
"""Ayuntamiento de Lorca (Murcia): agenda cultural."""
import csv
import io

from .classify import classify
from .util import event, http_text

NAME = "Ayuntamiento de Lorca"
URL = "http://datos.lorca.es/catalogo/agenda-cultural-lorca/agenda-cultural-lorca.csv"
HOME = "https://www.lorca.es/agenda/"


def fetch(log):
    text = http_text(URL, encoding="utf-8-sig")
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        title = r.get("titulo") or ""
        ev = event(
            NAME, r.get("id"), title, (r.get("fechainicio") or "")[:10], end=(r.get("fechafin") or "")[:10],
            category=classify([], title), province_code="30", city="Lorca",
            lat=r.get("latitud"), lon=r.get("longitud"), url=r.get("url") or HOME,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
