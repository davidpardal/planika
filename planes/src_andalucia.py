# -*- coding: utf-8 -*-
"""Junta de Andalucía: agenda de eventos organizados por la Junta."""
from .classify import classify
from .util import event, http_json

NAME = "Junta de Andalucía"
URL = "https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json"
HOME = "https://www.juntadeandalucia.es/organismos/agenda.html"
_BASE = "https://www.juntadeandalucia.es"


def fetch(log):
    data = http_json(URL)
    out = []
    for r in data:
        dates = (r.get("date_registration") or [{}])[0]
        start = dates.get("start_date_registration")
        end = dates.get("end_date_registration")
        prov = ((r.get("province") or [{}])[0] or {}).get("province")
        coords = ((r.get("coordinates") or [{}])[0] or {})
        img = ""
        imgs = r.get("image") or []
        if imgs:
            th = (imgs[0].get("thumbnail") or [{}])[0]
            img = th.get("image_url") or ""
            if img.startswith("/"):
                img = _BASE + img
        themes = r.get("themes") or []
        if isinstance(themes, list):
            themes = [next((v for v in t.values() if isinstance(v, str)), "") if isinstance(t, dict) else str(t) for t in themes]
        more = r.get("more_info") or ""
        if isinstance(more, list):
            more = (more[0] or {}).get("url", "") if more and isinstance(more[0], dict) else (more[0] if more else "")
        ev = event(
            NAME, r.get("id"), r.get("title"), start, end=end,
            time=_time(r.get("schedule")), description=r.get("description"),
            subtype=", ".join(str(t) for t in themes if t)[:60] or (r.get("matter") or ""),
            category=classify(list(themes) + [r.get("matter") or ""], r.get("title"), r.get("description")),
            province=prov, city=r.get("location"), address=r.get("address"),
            lat=coords.get("latitude"), lon=coords.get("longitude"), price=r.get("cost"),
            url=str(more).strip() or HOME, image=img,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out


def _time(s):
    from .util import parse_time
    return parse_time(s)
