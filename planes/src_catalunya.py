# -*- coding: utf-8 -*-
"""Generalitat de Catalunya: agenda cultural (Socrata)."""
from .classify import classify
from .util import event, http_json, iso, parse_time, today

NAME = "Agenda cultural de Catalunya"
URL = "https://analisi.transparenciacatalunya.cat/resource/rhpv-yr4f.json"
HOME = "https://agenda.cultura.gencat.cat/"
_PROV = {"barcelona": "08", "girona": "17", "lleida": "25", "tarragona": "43"}
_IMG_BASE = "https://agenda.cultura.gencat.cat"


def fetch(log):
    out = []
    offset = 0
    limit = 1000
    where = "data_fi >= '%sT00:00:00.000'" % iso(today())
    while True:
        rows = http_json(URL, params={"$limit": limit, "$offset": offset, "$where": where, "$order": "codi"})
        if not rows:
            break
        for r in rows:
            loc = (r.get("comarca_i_municipi") or "").replace("agenda:ubicacions/", "")
            parts = [p for p in loc.split("/") if p]
            prov = _PROV.get(parts[0]) if parts else None
            city = parts[-1].replace("-", " ").title() if len(parts) >= 3 else ""
            cats = [c.replace("agenda:categories/", "") for c in (r.get("tags_categor_es") or "").split(",") if c]
            ambits = [c.replace("agenda:ambits/", "") for c in (r.get("tags_mbits") or "").split(",") if c]
            img = r.get("imgapp") or r.get("imatges") or ""
            img = img.split(",")[0].strip()
            if img and img.startswith("/"):
                img = _IMG_BASE + img
            gratis = (r.get("gratuita") or "").strip().lower() == "si" or (r.get("gratuita") or "").strip().lower() == "sí"
            links = (r.get("enlla_os") or "").split(",")
            url = next((l.strip() for l in links if l.strip().startswith("http")), "") or \
                ("%s/activitats/%s" % (HOME.rstrip("/"), r.get("codi")) if r.get("codi") else HOME)
            ev = event(
                NAME, r.get("codi"), r.get("denominaci"), (r.get("data_inici") or "")[:10],
                end=(r.get("data_fi") or "")[:10], time=parse_time(r.get("horari")),
                description=r.get("descripcio") or r.get("subt_tol"), subtype=", ".join(cats)[:60],
                category=classify(cats + ambits, r.get("denominaci"), r.get("descripcio")),
                province_code=prov, city=city, venue=r.get("espai"), address=r.get("adre_a"),
                lat=r.get("latitud"), lon=r.get("longitud"),
                price=r.get("entrades") or ("Gratuïta" if gratis else ""), free=gratis or None,
                url=url, tickets_url=r.get("linkbotoentrades"), image=img,
            )
            if ev:
                out.append(ev)
        if len(rows) < limit:
            break
        offset += limit
    log("%s: %d eventos" % (NAME, len(out)))
    return out
