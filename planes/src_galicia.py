# -*- coding: utf-8 -*-
"""Xunta de Galicia: Axenda de Cultura de Galicia (calendario iCalendar)."""
import re

from .classify import classify
from .util import event, http_text, parse_ics

NAME = "Axenda de Cultura de Galicia"
URL = ("https://abertos.xunta.gal/catalogo/cultura-ocio-deporte/-/dataset/0045/axenda-cultura-galicia/"
       "102/acceso-aos-datos.calendario")
HOME = "https://www.cultura.gal/gl/axenda"


def fetch(log):
    text = http_text(URL, encoding="utf-8")
    out = []
    for v in parse_ics(text):
        loc = v.get("LOCATION") or ""
        # "Biblioteca Pública de Lugo - Lugo   - Lugo"  ->  lugar, concello, provincia
        parts = [p.strip() for p in loc.split(" - ") if p.strip()]
        venue = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
        prov = parts[-1] if len(parts) > 2 else ""
        desc = v.get("DESCRIPTION") or ""
        m = re.search(r"(Espect[aá]culo|Exposici[oó]n|Concerto|Cine|Obradoiro|Conferencia|Festival|Teatro|Danza|M[uú]sica|Literatura|Infantil)[^\n]*", desc)
        subtype = m.group(0).strip()[:60] if m else ""
        start = (v.get("DTSTART") or "")[:8]
        start = "%s-%s-%s" % (start[:4], start[4:6], start[6:8]) if len(start) == 8 else ""
        end = (v.get("DTEND") or "")[:8]
        end = "%s-%s-%s" % (end[:4], end[4:6], end[6:8]) if len(end) == 8 else start
        t = (v.get("DTSTART") or "")
        tm = "%s:%s" % (t[9:11], t[11:13]) if "T" in t and len(t) >= 13 else ""
        ev = event(
            NAME, v.get("UID"), v.get("SUMMARY"), start, end=end, time=tm, description=desc.split("http")[0],
            subtype=subtype, category=classify([subtype], v.get("SUMMARY"), desc),
            province=prov, city=city, venue=venue, url=v.get("URL") or HOME,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
