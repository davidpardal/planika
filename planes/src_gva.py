# -*- coding: utf-8 -*-
"""Generalitat Valenciana: agenda del Institut Valencià de Cultura (IVC)."""
from .classify import classify
from .util import event, http_json, parse_time

NAME = "Institut Valencià de Cultura"
URL = ("https://dadesobertes.gva.es/dataset/25cc4d21-e1dd-4d05-b057-dbcc44d4338c/resource/"
       "15084e00-c416-4b4d-b229-7a06f4bf07b0/download/lista-de-actividades-culturales-programadas-por-el-ivc.json")
HOME = "https://ivc.gva.es/"


def fetch(log):
    data = http_json(URL)
    rows = data.get("data", data) if isinstance(data, dict) else data
    # El JSON viene como una lista plana de diccionarios de una sola clave; se reagrupa por evento.
    events = []
    cur = None
    for kv in rows:
        if isinstance(kv, dict) and len(kv) == 1:
            (k, v), = kv.items()
            if k == "titulo_evento":
                cur = {}
                events.append(cur)
            if cur is not None:
                cur[k] = v
        elif isinstance(kv, dict):
            events.append(kv)
    out = []
    for i, r in enumerate(events):
        title = (r.get("titulo_evento") or "").strip()
        if title.upper().startswith("(CANCELADO") or title.upper().startswith("(CANCEL·LAT"):
            continue
        rtype = (r.get("tipo_evento") or "").strip()
        ev = event(
            NAME, "%s|%s|%s" % (title, r.get("fecha_inicio"), r.get("lugar_evento")), title, r.get("fecha_inicio"),
            end=r.get("fecha_fin"), time=parse_time(r.get("hora")), subtype=rtype,
            category=classify([rtype], title),
            province=(r.get("provincia") or "").strip(), city=(r.get("municipio") or "").strip(),
            venue=r.get("lugar_evento"), address=r.get("direccion"), lat=r.get("latitud"), lon=r.get("longitud"),
            price=(r.get("precio") or "").strip(), url=(r.get("web") or "").strip() or HOME,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
