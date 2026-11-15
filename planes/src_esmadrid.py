# -*- coding: utf-8 -*-
"""Madrid Destino: agenda turística de la ciudad de Madrid (esmadrid.com), con conciertos y grandes eventos."""
import re
import xml.etree.ElementTree as ET

from .classify import classify
from .util import event, http_get, parse_date, parse_time, strip_html

NAME = "esMADRID (agenda turística de Madrid)"
URL = "https://www.esmadrid.com/opendata/agenda_v1_es.xml"
HOME = "https://www.esmadrid.com/agenda-madrid"
CATS = {"musica": "musica", "teatro y danza": "escena", "exposiciones": "expos", "deporte": "deporte",
        "ferias": "gastro", "ninos": "infantil"}


def _txt(node, path):
    el = node.find(path) if node is not None else None
    return (el.text or "").strip() if el is not None else ""


def parse(xml_bytes):
    from .util import norm
    root = ET.fromstring(xml_bytes)
    out = []
    for s in root.iter("service"):
        basic, geo, extra = s.find("basicData"), s.find("geoData"), s.find("extradata")
        if basic is None or extra is None:
            continue
        starts, ends = [], []
        for rango in extra.iter("rango"):
            a, b = parse_date(_txt(rango, "inicio")), parse_date(_txt(rango, "fin"))
            if a:
                starts.append(a)
                ends.append(b or a)
        if not starts:
            continue
        start, end = min(starts), max(ends)
        items = {i.get("name"): (i.text or "") for i in extra.findall("item")}
        cats = [(i.text or "").strip() for i in extra.iter("item") if i.get("name") == "Categoria"]
        subs = [(i.text or "").strip() for i in extra.iter("item") if i.get("name") == "SubCategoria" and (i.text or "").strip() != "Otros"]
        title = _txt(basic, "title") or _txt(basic, "name")
        body = _txt(basic, "body")
        horario = strip_html(items.get("Horario"))
        m = re.search(r"Inicio:\s*([^.]*?\d{1,2}[:.]\d{2})", horario)
        tm = parse_time(m.group(1) if m else horario) if start == end else ""
        cat = next((CATS[norm(c)] for c in cats if norm(c) in CATS), None) or classify(cats + subs, title, body)
        ev = event(
            NAME, s.get("id"), title, start, end=end, time=tm, description=body, subtype=(subs or cats or [""])[0],
            category=cat, province_code="28", city="Madrid", venue=_txt(basic, "nombrert"),
            address=("Calle " + _txt(geo, "address")) if _txt(geo, "address")[:3].lower() in ("de ", "del") else _txt(geo, "address"),
            lat=_txt(geo, "latitude") or None, lon=_txt(geo, "longitude") or None,
            price=strip_html(items.get("Servicios de pago"), 80), url=_txt(basic, "web") or HOME,
            image=_txt(s, "multimedia/media/url"),
        )
        if ev:
            out.append(ev)
    return out


def fetch(log):
    out = parse(http_get(URL, timeout=(20, 180)).content)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
