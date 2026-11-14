#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga las agendas públicas, normaliza los eventos y genera site/data/events.js.

Uso:
    python3 fetch_events.py                 # próximos 180 días, todas las fuentes
    python3 fetch_events.py --days 90       # horizonte de 90 días
    python3 fetch_events.py --sources madrid,euskadi
"""
import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from planes.classify import CATEGORIES  # noqa: E402
from planes.util import PROVINCIAS, iso, norm, today  # noqa: E402

SOURCES = ["madrid", "euskadi", "catalunya", "cyl", "gva", "malaga", "andalucia", "lorca", "ticketmaster"]


def load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), flush=True)


def dedupe(events):
    """Une duplicados (mismo título, fecha y provincia) conservando el más completo."""
    best = {}
    for ev in events:
        key = (norm(ev["title"])[:60], ev["start"], ev["province_code"])
        score = sum(1 for k in ("tickets_url", "image", "time", "venue", "description", "price") if ev.get(k))
        cur = best.get(key)
        if cur is None or score > cur[0]:
            best[key] = (score, ev)
    return [v[1] for v in best.values()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180, help="horizonte en días (por defecto 180)")
    ap.add_argument("--sources", default=",".join(SOURCES), help="fuentes separadas por comas")
    ap.add_argument("--out", default=os.path.join(ROOT, "site", "data"), help="carpeta de salida")
    args = ap.parse_args()

    load_dotenv(os.path.join(ROOT, ".env"))
    t0 = today()
    t_max = t0 + timedelta(days=args.days)
    all_events = []
    source_meta = []

    for name in [s.strip() for s in args.sources.split(",") if s.strip()]:
        try:
            mod = importlib.import_module("planes.src_%s" % name)
        except ImportError:
            log("fuente desconocida: %s" % name)
            continue
        started = time.time()
        try:
            evs = mod.fetch(log) if name != "ticketmaster" else mod.fetch(log, days=args.days)
        except Exception as exc:  # noqa: BLE001 - una fuente caída no debe tumbar el resto
            log("%s: ERROR %s: %s" % (mod.NAME, exc.__class__.__name__, exc))
            evs = []
        kept = [e for e in evs if e["end"] >= iso(t0) and e["start"] <= iso(t_max)]
        # Sin provincia resoluble (eventos en línea, sin lugar o fuera de España) no encajan en la web
        no_prov = [e for e in kept if not e["province_code"]]
        if no_prov:
            log("  -> %d descartados sin provincia (p. ej. %s)" % (len(no_prov), ", ".join(sorted({e["city"] or "sin ciudad" for e in no_prov})[:4])))
            kept = [e for e in kept if e["province_code"]]
        all_events.extend(kept)
        source_meta.append({"key": name, "name": mod.NAME, "home": mod.HOME, "count": len(kept),
                            "seconds": round(time.time() - started, 1)})
        log("  -> %d dentro del horizonte (%.1fs)" % (len(kept), time.time() - started))

    before = len(all_events)
    all_events = dedupe(all_events)
    all_events.sort(key=lambda e: (e["start"], e["time"] or "99", e["title"]))
    log("Total: %d eventos (%d duplicados eliminados)" % (len(all_events), before - len(all_events)))

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "from": iso(t0), "to": iso(t_max), "days": args.days,
        "categories": [{"key": k, "name": n, "icon": i} for k, n, i in CATEGORIES],
        "provinces": [{"code": c, "name": n, "ccaa": a} for c, n, a in PROVINCIAS],
        "sources": source_meta,
        "events": all_events,
    }
    with open(os.path.join(args.out, "events.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(args.out, "events.js"), "w", encoding="utf-8") as fh:
        fh.write("window.PLANES_DATA = ")
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    size = os.path.getsize(os.path.join(args.out, "events.js")) / 1024 / 1024
    log("Escrito %s (%.1f MB)" % (os.path.join(args.out, "events.js"), size))

    # Resumen por provincia y categoría
    by_prov = {}
    by_cat = {}
    for e in all_events:
        by_prov[e["province"] or "(sin provincia)"] = by_prov.get(e["province"] or "(sin provincia)", 0) + 1
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1
    log("Por provincia: " + ", ".join("%s %d" % kv for kv in sorted(by_prov.items(), key=lambda x: -x[1])))
    log("Por tipo: " + ", ".join("%s %d" % kv for kv in sorted(by_cat.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
