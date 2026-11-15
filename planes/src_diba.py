# -*- coding: utf-8 -*-
"""Diputació de Barcelona: agendas de turismo, parques naturales y teatros municipales (datos abiertos)."""
from .classify import classify
import re
from datetime import datetime

from .util import event, http_json

NAME = "Diputació de Barcelona"
API = "https://do.diba.cat/api/dataset/%s/format/json/pag-ini/1/pag-fi/%d"
HOME = "https://www.diba.cat/web/agenda"
MAX_DAYS = 60
# (conjunto de datos, elementos a pedir, categoría por defecto, etiqueta)
DATASETS = [
    ("actesturisme_ca", 800, None, "Turisme"),
    ("actesparcs", 600, "naturaleza", "Parcs naturals"),
    ("escenari", 600, "escena", "Teatres i auditoris"),
]


def parse(elements, default_cat=None, tag=""):
    out = []
    for e in elements:
        if not isinstance(e, dict):
            continue
        addr = e.get("grup_adreca") if isinstance(e.get("grup_adreca"), dict) else {}
        muni = e.get("rel_municipis") if isinstance(e.get("rel_municipis"), dict) else {}
        lat = lon = None
        pos = str(addr.get("localitzacio") or muni.get("centre_municipal") or "")
        if "," in pos:
            lat, lon = [p.strip() for p in pos.split(",")[:2]]
        start, end = str(e.get("data_inici") or ""), str(e.get("data_fi") or "")
        tm = start[11:16] if len(start) >= 16 else ""
        img = e.get("imatge")
        img = img[0] if isinstance(img, list) and img else (img if isinstance(img, str) else "")
        try:  # productos turísticos permanentes (rutas, audioguías...): no son un plan con fecha
            if (datetime.strptime(end[:10], "%Y-%m-%d") - datetime.strptime(start[:10], "%Y-%m-%d")).days > MAX_DAYS:
                continue
        except ValueError:
            pass
        city = re.sub(r"^\d{5}\s+", "", str(addr.get("municipi_nom") or muni.get("municipi_nom") or "").strip())
        if city.isupper():
            city = city.title()
        title, desc = e.get("titol"), e.get("descripcio")
        cat = classify([], title, desc)
        if cat in ("otros", "charlas") and default_cat:
            cat = default_cat
        ev = event(
            NAME, e.get("acte_id"), title, start[:10], end=end[:10], time=tm, description=desc, subtype=tag,
            category=cat, province_code="08", city=city,
            venue=addr.get("adreca_nom"), address=addr.get("adreca"), lat=lat, lon=lon,
            price=e.get("preu") if isinstance(e.get("preu"), str) else "", url=e.get("acte_url") or e.get("url_general") or HOME,
            image=img,
        )
        if ev:
            out.append(ev)
    return out


def fetch(log):
    out, failed = [], []
    for ds, size, cat, tag in DATASETS:
        try:
            data = http_json(API % (ds, size), timeout=(20, 180), retries=2)
        except Exception as exc:  # noqa: BLE001
            failed.append(ds)
            log("%s: %s no disponible (%s)" % (NAME, ds, exc.__class__.__name__))
            continue
        out.extend(parse(data.get("elements") or [], cat, tag))
    if failed and not out:
        raise RuntimeError("ningún conjunto de datos disponible")
    log("%s: %d eventos" % (NAME, len(out)))
    return out
