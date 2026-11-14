# -*- coding: utf-8 -*-
"""Ayuntamiento de Cartagena: agenda turística y cultural de la ciudad."""
import csv
import io

from .classify import classify
from .util import event, http_text, parse_time, strip_html

NAME = "Ayuntamiento de Cartagena"
URL = "https://www.cartagena.es/api/turismo_agenda/csv.asp"
HOME = "https://turismo.cartagena.es/agenda.asp"


def fetch(log):
    text = http_text(URL, encoding="latin-1")
    out = []
    for r in csv.DictReader(io.StringIO(text), delimiter=";"):
        title = r.get("dc:titulo") or ""
        info = r.get("webct:masinfo") or ""
        ev = event(
            NAME, r.get("dc:identificador"), title, r.get("webct:fecha_inicio"), end=r.get("webct:fecha_fin"),
            time=parse_time(strip_html(info)), description=info, category=classify([], title, info),
            province_code="30", city="Cartagena", venue=r.get("webct:donde_se_realiza"),
            price=r.get("webct:tarifas"), url=r.get("webct:url_original") or HOME, image=r.get("webct:foto"),
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
