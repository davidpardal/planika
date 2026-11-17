# -*- coding: utf-8 -*-
"""Visitas permanentes: museos, monumentos, espacios naturales y salas.

No salen de una agenda con fecha. Están escritos a mano en data/curated.json
(nombre, municipio, provincia, tipo, descripción, URL oficial y, si se conoce,
coordenadas). Cada ejecución del generador los vuelve a mezclar, así que no
desaparecen cuando se regenera data/events.json.

No tienen un día concreto: la ficha usa el subtype "Permanente", empieza hoy y
acaba dentro del tope que ya aplica el normalizador (400 días). Al día siguiente
se reescriben con una ventana nueva, así que no caducan ni se cuelan como si
hubieran terminado. La web los pinta como "Visita permanente", los deja fuera
del calendario diario y los ordena detrás de los planes con fecha.
"""
import json
import os
from datetime import timedelta

from .classify import CATEGORY_KEYS
from .util import PERMANENT_SUBTYPE, event, iso, today

NAME = "Visitas permanentes"
HOME = "https://planikaapp.com/"
CURATED_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "curated.json")


def load_places(path=None):
    """Lee el fichero curado. Lanza si el JSON no se puede leer: el generador
    conserva entonces la mezcla anterior (como con cualquier otra fuente caída)."""
    path = path or CURATED_PATH
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        places = data.get("places") or []
    elif isinstance(data, list):
        places = data
    else:
        raise ValueError("data/curated.json no contiene una lista de lugares")
    if not isinstance(places, list):
        raise ValueError("data/curated.json: 'places' no es una lista")
    return places


def fetch(log):
    places = load_places()
    start = iso(today())
    # Mismo tope que util.event: una ventana larga, reescrita cada día.
    end = iso(today() + timedelta(days=400))
    out = []
    seen = set()
    skipped = 0
    for raw in places:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        pid = str(raw.get("id") or "").strip()
        if not pid or pid in seen:
            skipped += 1
            continue
        seen.add(pid)
        category = raw.get("category") or "otros"
        if category not in CATEGORY_KEYS:
            category = "otros"
        kw = dict(
            end=end,
            description=raw.get("description") or "",
            category=category,
            subtype=PERMANENT_SUBTYPE,
            province=raw.get("province"),
            city=raw.get("city"),
            venue=raw.get("venue") or "",
            address=raw.get("address") or "",
            lat=raw.get("lat"),
            lon=raw.get("lon"),
            url=raw.get("url") or "",
            audience=raw.get("audience") or "",
        )
        if raw.get("price"):
            kw["price"] = raw["price"]
        if "free" in raw and raw["free"] is not None:
            kw["free"] = bool(raw["free"])
        ev = event(NAME, pid, raw.get("title"), start, **kw)
        if not ev or not ev.get("province_code") or not ev.get("url"):
            skipped += 1
            continue
        out.append(ev)
    log("%s: %d visitas permanentes%s" % (NAME, len(out), (" (%d filas omitidas)" % skipped) if skipped else ""))
    return out


def replace_events(events, log=None):
    """Quita la mezcla anterior de esta fuente y añade la versión de hoy."""
    fresh = fetch(log or (lambda msg: None))
    base = [e for e in events if e.get("source") != NAME]
    return base + fresh
