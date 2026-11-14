# -*- coding: utf-8 -*-
"""Cabildo de Tenerife: agenda de eventos deportivos de la isla."""
from .classify import classify
from .util import event, http_json

NAME = "Cabildo de Tenerife (deportes)"
URL = ("https://datos.tenerife.es/ckan/dataset/6cde1436-8d6f-4cf6-b5a5-c32c8a738478/resource/"
       "de1231c0-957a-4ad0-8b7b-19d6b1bfced6/download/agenda-de-eventos-deportivos-en-tenerife.json")
HOME = "https://deportestenerife.es/"


def fetch(log):
    data = http_json(URL)
    out = []
    for r in data.get("eventos", []):
        start = (r.get("evento_fecha_inicio") or "")[:10]
        if start < "2026-01-01":
            continue  # el histórico llega hasta 2015; no merece la pena procesarlo
        ev = event(
            NAME, r.get("evento_url") or r.get("evento_nombre"), r.get("evento_nombre"), start,
            end=(r.get("evento_fecha_fin") or "")[:10], time=(r.get("evento_fecha_inicio") or "")[11:16],
            description=r.get("evento_descripcion"), subtype="Deporte",
            category="deporte" if classify([], r.get("evento_nombre")) in ("otros", "deporte", "naturaleza") else classify([], r.get("evento_nombre")),
            province_code="38", city=r.get("municipio_nombre"), venue=r.get("evento_lugar"),
            url=r.get("evento_url") or HOME,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
