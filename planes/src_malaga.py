# -*- coding: utf-8 -*-
"""Ayuntamiento de Málaga: agenda municipal anual (CSV)."""
import csv
import io
from datetime import date

from .classify import classify
from .util import event, http_text, parse_time

NAME = "Ayuntamiento de Málaga"
URL = "https://datosabiertos.malaga.eu/recursos/cultura/agenda/%d.csv"
HOME = "https://www.malaga.eu/agenda/"


def fetch(log):
    csv.field_size_limit(10 ** 8)
    out = []
    years = sorted({date.today().year, date.today().year + 1})
    for y in years:
        try:
            text = http_text(URL % y, retries=1)
        except Exception as exc:  # noqa: BLE001 - el CSV del año siguiente puede no existir aún
            log("%s: sin CSV para %d (%s)" % (NAME, y, exc.__class__.__name__))
            continue
        for r in csv.DictReader(io.StringIO(text)):
            cat = (r.get("CATEGORIA") or "").strip()
            if cat in ("Perfiles", "TemasWeb", "Incidencias de tráfico", "Hechos de Vida", "Actos políticos"):
                continue
            title = (r.get("NOMBRE") or "").strip()
            start = (r.get("F_INICIO") or "")[:10]
            end = (r.get("F_FIN") or "")[:10]
            ev = event(
                NAME, r.get("ID_ACTIVIDAD") or r.get("ID_EVENTO"), title, start, end=end,
                time=parse_time(r.get("HORARIO")), description=r.get("DESCRIPCION") or r.get("EVENTO"),
                subtype=(r.get("ESPECIALIDAD") or cat), category=classify([cat, r.get("ESPECIALIDAD")], title, r.get("DESCRIPCION"), r.get("DESTINATARIOS_DESCRIPCION")),
                province_code="29", city="Málaga", venue=r.get("EQP_DESCRIPCION") or r.get("OTROS_LUGARES"),
                address=r.get("EQP_NOMBRECALLE"), price=r.get("PRECIO"),
                url=(r.get("DIRECCION_WEB") or "").strip() or HOME,
                audience=r.get("DESTINATARIOS_DESCRIPCION"),
            )
            if ev:
                out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
