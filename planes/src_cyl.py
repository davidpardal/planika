# -*- coding: utf-8 -*-
"""Junta de Castilla y León: eventos de la agenda cultural categorizados y geolocalizados."""
from .classify import classify
from .util import event, http_json

NAME = "Junta de Castilla y León"
URL = ("https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets/"
       "eventos-de-la-agenda-cultural-categorizados-y-geolocalizados/records")
HOME = "https://cultura.jcyl.es/web/es/agenda-cultural.html"


def fetch(log):
    out = []
    offset = 0
    limit = 100
    while True:
        data = http_json(URL, params={"limit": limit, "offset": offset, "order_by": "fecha_inicio"})
        rows = data.get("results", [])
        if not rows:
            break
        for r in rows:
            types = [r.get("categoria") or "", r.get("tematica") or ""]
            ev = event(
                NAME, r.get("id_evento"), r.get("titulo"), r.get("fecha_inicio"),
                end=r.get("fecha_fin"), time=(r.get("hora_inicio") or "")[:5],
                description=r.get("descripcion"), subtype=r.get("tematica") or r.get("categoria"),
                category=classify(types, r.get("titulo"), r.get("descripcion"), r.get("destinatarios")),
                province_code=str(r.get("codigo_provincia") or "").zfill(2) or None,
                province=r.get("nombre_provincia"), city=r.get("nombre_localidad"),
                venue=r.get("lugar_celebracion"), address=r.get("calle"),
                lat=r.get("latitud"), lon=r.get("longitud"), price=r.get("precio"),
                url=r.get("enlace_contenido") or HOME, image=r.get("imagen_evento_ampliada") or r.get("imagen_evento"),
                audience=r.get("destinatarios"),
            )
            if ev:
                out.append(ev)
        offset += limit
        if offset >= int(data.get("total_count") or 0) or offset >= 10000:
            break
    log("%s: %d eventos" % (NAME, len(out)))
    return out
