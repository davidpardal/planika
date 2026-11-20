# -*- coding: utf-8 -*-
"""Grandes citas con fecha comprobada a mano (data/destacados.json).

Sirve para huecos que las agendas abiertas todavía no cubren: el encendido de
luces de una capital, una feria tradicional o un mercado de Navidad que solo
aparece en la web del ayuntamiento o en prensa. Cada entrada lleva la página
que verá el usuario ('url'), las fuentes con que se comprobó ('refs') y el día
de la comprobación ('checked'). No se inventa nada: si falta la hora, se deja
vacía.

Como data/curated.json, el fichero se vuelve a mezclar en cada ejecución (y con
--rebuild), así que nada se pierde al regenerar data/events.json. Las entradas
cuya fecha de fin ya ha pasado se descartan solas.
"""
import json
import os
import re

from .classify import CATEGORY_KEYS
from .util import event, iso, today

NAME = "Selección Planika"
HOME = "https://planikaapp.com/fuentes.html"
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "destacados.json")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def load(path=None):
    """Lee el fichero. Lanza si el JSON no se puede leer: el generador conserva
    entonces la mezcla anterior, como con cualquier fuente caída."""
    with open(path or PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    items = data.get("events") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("data/destacados.json: 'events' no es una lista")
    return items


def problems(raw):
    """Motivos por los que una entrada no es publicable (lista vacía = correcta)."""
    out = []
    if not isinstance(raw, dict):
        return ["no es un objeto"]
    for key in ("id", "title", "start", "url", "province", "checked"):
        if not str(raw.get(key) or "").strip():
            out.append("falta %s" % key)
    for key in ("start", "end", "checked"):
        if raw.get(key) and not _DATE.match(str(raw[key])):
            out.append("%s no es AAAA-MM-DD" % key)
    if raw.get("time") and not _TIME.match(str(raw["time"])):
        out.append("time no es HH:MM")
    if raw.get("end") and raw.get("start") and str(raw["end"]) < str(raw["start"]):
        out.append("end anterior a start")
    refs = raw.get("refs")
    if not isinstance(refs, list) or not any(str(r).startswith("https://") for r in refs):
        out.append("sin refs https")
    if raw.get("category") and raw["category"] not in CATEGORY_KEYS:
        out.append("categoría desconocida")
    return out


def fetch(log):
    out, seen, skipped = [], set(), 0
    now = iso(today())
    for raw in load():
        bad = problems(raw)
        if bad or raw["id"] in seen:
            skipped += 1
            if bad:
                log("  %s: omitido %s (%s)" % (NAME, (raw or {}).get("id") if isinstance(raw, dict) else "?", ", ".join(bad)))
            continue
        seen.add(raw["id"])
        if (raw.get("end") or raw["start"]) < now:
            continue  # ya ha pasado
        kw = dict(
            end=raw.get("end") or raw["start"],
            time=raw.get("time") or "",
            description=raw.get("description") or "",
            category=raw.get("category") or "otros",
            subtype=raw.get("subtype") or "",
            province=raw.get("province"),
            city=raw.get("city"),
            venue=raw.get("venue") or "",
            address=raw.get("address") or "",
            lat=raw.get("lat"),
            lon=raw.get("lon"),
            url=raw["url"],
            tickets_url=raw.get("tickets_url") or "",
            audience=raw.get("audience") or "",
        )
        if raw.get("price"):
            kw["price"] = raw["price"]
        if raw.get("free") is not None:
            kw["free"] = bool(raw["free"])
        ev = event(NAME, raw["id"], raw["title"], raw["start"], **kw)
        if not ev or not ev.get("province_code"):
            skipped += 1
            continue
        out.append(ev)
    log("%s: %d citas comprobadas%s" % (NAME, len(out), (" (%d omitidas)" % skipped) if skipped else ""))
    return out


def replace_events(events, log=None):
    """Quita la mezcla anterior de esta fuente y añade la versión de hoy."""
    fresh = fetch(log or (lambda msg: None))
    return [e for e in events if e.get("source") != NAME] + fresh
