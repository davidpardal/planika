#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga las agendas públicas, normaliza los eventos y genera los datos de la web (site/data/).

Uso:
    python3 fetch_events.py                 # próximos 180 días, todas las fuentes
    python3 fetch_events.py --days 90       # horizonte de 90 días
    python3 fetch_events.py --sources madrid,euskadi
    python3 fetch_events.py --rebuild       # sin descargar: regenera la web desde events.json y mezcla data/curated.json
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

# El estado completo de eventos vive fuera de site/ (en data/, junto a health.json):
# es un archivo interno del pipeline y no debe publicarse en la web (pesa ~9 MB).
EVENTS_FILE = os.path.join(ROOT, "data", "events.json")

from planes import llm, publish, seo, static  # noqa: E402
from planes.classify import CATEGORIES  # noqa: E402
from planes.util import PROVINCIAS, iso, norm, today  # noqa: E402

SOURCES = ["madrid", "esmadrid", "barcelona", "diba", "euskadi", "catalunya", "cyl", "gva", "malaga", "andalucia",
           "galicia", "zaragoza", "cartagena", "lorca", "murcia", "vitoria", "municipios", "tenerife_deporte", "deporte_pro", "sportsdb",
           "ticketmaster", "curated"]


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


def load_previous(path):
    """Eventos de la ejecución anterior agrupados por fuente, para cubrir fallos puntuales."""
    out = {"by_source": {}, "date": "", "age_days": 999}
    try:
        with open(path, encoding="utf-8") as fh:
            prev = json.load(fh)
    except (OSError, ValueError):
        return out
    for e in prev.get("events", []):
        out["by_source"].setdefault(e.get("source", ""), []).append(e)
    out["date"] = (prev.get("updated_at") or "")[:10]
    try:
        out["age_days"] = (today() - datetime.strptime(out["date"], "%Y-%m-%d").date()).days
    except ValueError:
        pass
    return out


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


def write_site(args, site_dir, payload):
    """Todo lo que se deriva de events.json: datos troceados para la web, feeds RSS y páginas estáticas."""
    events = static.default_order(static.unique_ids(payload["events"]))
    core_size, chunks = static.write_data(args.out, dict(payload, events=events))
    old = os.path.join(args.out, "events.js")  # formato anterior (un único archivo de varios MB)
    if os.path.exists(old):
        os.remove(old)
    log("Escrito %s (%.0f KB) y %d bloques de detalles en data/d/" % (os.path.join(args.out, "core.js"), core_size / 1024, chunks))
    if not args.no_pages:
        feeds = publish.write_feeds(os.path.join(site_dir, "feeds"), events)
        pages = publish.write_pages(site_dir, events, payload.get("sources") or [], payload.get("updated_at") or "",
                                    state_path=os.path.join(ROOT, "data", "sitemap_state.json"))
        static.stamp_index(site_dir)  # versiones en las URL de estilos, datos y app de la portada
        indexables = sum(1 for e in events if seo.is_indexable(e))
        log("Generados %d feeds RSS y %d páginas estáticas (%d fichas indexables de %d)" % (len(feeds), len(pages), indexables, len(events)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=180, help="horizonte en días (por defecto 180)")
    ap.add_argument("--sources", default=",".join(SOURCES), help="fuentes separadas por comas")
    ap.add_argument("--out", default=os.path.join(ROOT, "site", "data"), help="carpeta de salida")
    ap.add_argument("--llm", choices=["off", "otros", "all"], default=os.environ.get("PLANIKA_LLM", "off"),
                    help="clasificar con Claude los eventos dudosos (otros) o todos; requiere ANTHROPIC_API_KEY")
    ap.add_argument("--no-pages", action="store_true", help="no generar páginas estáticas ni feeds")
    ap.add_argument("--rebuild", action="store_true",
                    help="no descargar nada: regenerar datos troceados, feeds y páginas desde events.json")
    args = ap.parse_args()
    site_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)

    if args.rebuild:
        with open(EVENTS_FILE, encoding="utf-8") as fh:
            payload = json.load(fh)
        # Regenerar también mezcla las visitas permanentes, para poder refrescar
        # la web sin volver a descargar las agendas (y sin dejarlas caducar).
        from planes.src_curated import HOME as CURATED_HOME, NAME as CURATED_NAME, replace_events
        payload["events"] = replace_events(payload.get("events") or [], log)
        sources = [s for s in payload.get("sources") or [] if s.get("key") != "curated"]
        n_curated = sum(1 for e in payload["events"] if e.get("source") == CURATED_NAME)
        sources.append({"key": "curated", "name": CURATED_NAME, "home": CURATED_HOME, "count": n_curated,
                        "seconds": 0, "error": "", "stale_from": ""})
        payload["sources"] = sources
        payload["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
        with open(EVENTS_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        write_site(args, site_dir, payload)
        log("Rebuild: %d planes, %d visitas permanentes" % (len(payload["events"]), n_curated))
        return

    load_dotenv(os.path.join(ROOT, ".env"))
    previous = load_previous(EVENTS_FILE)
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
        error = ""
        try:
            evs = mod.fetch(log) if name not in ("ticketmaster", "sportsdb") else mod.fetch(log, days=args.days)
        except Exception as exc:  # noqa: BLE001 - una fuente caída no debe tumbar el resto
            log("%s: ERROR %s: %s" % (mod.NAME, exc.__class__.__name__, exc))
            evs = []
            error = "%s: %s" % (exc.__class__.__name__, str(exc)[:120])
        kept = [e for e in evs if e["end"] >= iso(t0) and e["start"] <= iso(t_max)]
        stale = ""
        # Una fuente puede agrupar varias webs (SOURCE_NAMES): cada una se cubre por separado si falla
        for src_name in getattr(mod, "SOURCE_NAMES", None) or [mod.NAME]:
            if any(e["source"] == src_name for e in kept) or not previous["by_source"].get(src_name):
                continue
            # Ha fallado hoy: se conservan los planes de la última descarga buena (máximo 7 días)
            if previous["age_days"] <= 7:
                reused = [e for e in previous["by_source"][src_name] if e["end"] >= iso(t0)]
                kept.extend(reused)
                stale = previous["date"]
                log("  -> %s sin datos hoy; se reutilizan %d planes de la descarga del %s" % (src_name, len(reused), stale))
        # Sin provincia resoluble (eventos en línea, sin lugar o fuera de España) no encajan en la web
        no_prov = [e for e in kept if not e["province_code"]]
        if no_prov:
            log("  -> %d descartados sin provincia (p. ej. %s)" % (len(no_prov), ", ".join(sorted({e["city"] or "sin ciudad" for e in no_prov})[:4])))
            kept = [e for e in kept if e["province_code"]]
        all_events.extend(kept)
        source_meta.append({"key": name, "name": mod.NAME, "home": mod.HOME, "count": len(kept),
                            "seconds": round(time.time() - started, 1), "error": error, "stale_from": stale})
        log("  -> %d dentro del horizonte (%.1fs)" % (len(kept), time.time() - started))

    before = len(all_events)
    all_events = dedupe(all_events)
    all_events, merged = publish.group_sessions(all_events)
    all_events = static.unique_ids(all_events)
    all_events.sort(key=lambda e: (e["start"], e["time"] or "99", e["title"]))
    log("Total: %d planes (%d duplicados eliminados, %d funciones agrupadas en sesiones)" % (len(all_events), before - len(all_events) - merged, merged))
    if args.llm != "off":
        llm.enrich(all_events, log, mode=args.llm)

    os.makedirs(args.out, exist_ok=True)
    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "from": iso(t0), "to": iso(t_max), "days": args.days,
        "categories": [{"key": k, "name": n, "icon": i} for k, n, i in CATEGORIES],
        "provinces": [{"code": c, "name": n, "ccaa": a} for c, n, a in PROVINCIAS],
        "sources": source_meta,
        "alerts": [],
        "events": all_events,
    }
    with open(EVENTS_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    # Salud de las fuentes (histórico + alertas)
    alerts = publish.update_health(os.path.join(ROOT, "data", "health.json"), source_meta)
    for a in alerts:
        log("ALERTA fuente -> " + a)
        print("::warning title=Fuente con problemas::" + a, flush=True)
    write_site(args, site_dir, payload)

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
