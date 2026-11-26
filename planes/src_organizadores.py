# -*- coding: utf-8 -*-
"""Eventos que envían los propios organizadores desde «Publica tu evento» (data/organizadores.json).

El flujo: el formulario de la web guarda el envío en Supabase; cada día tools/organizadores.py propone los nuevos
en un pull request (rama organizadores-nuevos) y quedan publicados cuando David lo fusiona. Este módulo solo lee
el fichero ya aprobado, como data/destacados.json: se vuelve a mezclar en cada ejecución y lo que ya ha pasado se
descarta solo.

Locales abiertos todo el año ("kind": "lugar": escape rooms, boleras, parques de bolas…): no tienen fecha. Se publican
como las visitas permanentes de data/curated.json (empiezan hoy y se reescriben cada día) con «Todo el año».

Destacados: una entrada con "destacado": true (y opcionalmente "destacado_hasta": "AAAA-MM-DD") sale arriba en las
listas de su provincia y su categoría con la etiqueta «Destacado» hasta esa fecha (o hasta el día del evento). Un local
no tiene día del evento: necesita destacado_hasta (30 días desde que se activa).
"""
import json
import os
import re

from datetime import timedelta

from . import src_destacados
from .classify import CATEGORY_KEYS
from .util import PERMANENT_SUBTYPE, event, iso, today

NAME = "Organizadores"
HOME = "https://planikaapp.com/promociona-tu-evento.html"
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "organizadores.json")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load(path=None):
    """Lee el fichero; si no existe todavía, no hay eventos. Lanza si el JSON está roto (se conserva la mezcla anterior)."""
    try:
        with open(path or PATH, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    items = data.get("events") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("data/organizadores.json: 'events' no es una lista")
    return items


def problems(raw):
    """Mismas comprobaciones que la Selección Planika; la página del propio organizador hace de referencia."""
    if not isinstance(raw, dict):
        return ["no es un objeto"]
    refs = raw.get("refs") or [raw.get("url") or ""]
    if raw.get("kind") == "lugar":
        out = ["falta %s" % k for k in ("id", "title", "url", "province", "checked", "address", "category")
               if not str(raw.get(k) or "").strip()]
        if not any(str(r).startswith("https://") for r in refs):
            out.append("sin refs https")
        if raw.get("category") and raw["category"] not in CATEGORY_KEYS:
            out.append("categoría desconocida")
        if raw.get("destacado") and not raw.get("destacado_hasta"):
            out.append("un local destacado necesita destacado_hasta")
    else:
        out = src_destacados.problems(dict(raw, refs=refs))
    if raw.get("destacado_hasta") and not _DATE.match(str(raw["destacado_hasta"])):
        out.append("destacado_hasta no es AAAA-MM-DD")
    return out


def is_featured(raw, now=None):
    """¿Sale destacado hoy? Hasta destacado_hasta o, si no se dice, hasta el último día del evento."""
    if not raw.get("destacado"):
        return False
    now = now or iso(today())
    until = raw.get("destacado_hasta") or raw.get("end") or raw.get("start")
    return bool(until) and now <= until


def fetch(log):
    out, seen, skipped = [], set(), 0
    now = iso(today())
    for raw in load():
        bad = problems(raw)
        if bad or raw["id"] in seen:
            skipped += 1
            if bad:
                log("  %s: omitido %s (%s)" % (NAME, raw.get("id") if isinstance(raw, dict) else "?", ", ".join(bad)))
            continue
        seen.add(raw["id"])
        lugar = raw.get("kind") == "lugar"
        if not lugar and (raw.get("end") or raw["start"]) < now:
            continue
        desc = raw.get("description") or ""
        if raw.get("horario"):
            desc = (desc.rstrip() + "\n\nHorario: " + raw["horario"].strip()).strip()
        kw = dict(end=raw.get("end") or raw.get("start"), time=raw.get("time") or "", description=desc,
                  category=raw.get("category") or "otros", province=raw.get("province"), city=raw.get("city"),
                  venue=raw.get("venue") or "", address=raw.get("address") or "", url=raw["url"],
                  tickets_url=raw.get("tickets_url") or "", image=raw.get("image") or "", price=raw.get("price") or "")
        if lugar:  # como las visitas permanentes: empieza hoy y se reescribe cada día
            kw.update(end=iso(today() + timedelta(days=400)), time="", subtype=PERMANENT_SUBTYPE)
        if raw.get("free") is not None:
            kw["free"] = bool(raw["free"])
        ev = event(NAME, raw["id"], raw["title"], now if lugar else raw["start"], **kw)
        if not ev or not ev.get("province_code"):
            skipped += 1
            continue
        if is_featured(raw, now):
            ev["featured"] = True
        out.append(ev)
    n_feat = sum(1 for e in out if e.get("featured"))
    log("%s: %d planes enviados por organizadores%s%s" % (NAME, len(out), (", %d destacados" % n_feat) if n_feat else "",
                                                          (" (%d omitidos)" % skipped) if skipped else ""))
    return out


def replace_events(events, log=None):
    """Quita la mezcla anterior de esta fuente y añade la versión de hoy."""
    fresh = fetch(log or (lambda msg: None))
    return [e for e in events if e.get("source") != NAME] + fresh
