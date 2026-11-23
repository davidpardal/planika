#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Descarga las agendas públicas, normaliza los eventos y genera los datos de la web (site/data/).

Uso:
    python3 fetch_events.py                 # próximos 180 días, todas las fuentes
    python3 fetch_events.py --days 90       # horizonte de 90 días
    python3 fetch_events.py --sources madrid,euskadi
    python3 fetch_events.py --rebuild       # sin descargar: regenera la web desde events.json y mezcla data/curated.json y data/destacados.json
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

from planes import boletin, classify, llm, partidos, publish, salas, seo, static, util  # noqa: E402
from planes.classify import CATEGORIES  # noqa: E402
from planes.util import PROVINCIAS, iso, norm, today  # noqa: E402

SOURCES = ["madrid", "esmadrid", "barcelona", "diba", "euskadi", "catalunya", "cyl", "gva", "malaga", "andalucia",
           "galicia", "zaragoza", "cartagena", "murcia", "vitoria", "jimmyjazz", "tribe", "municipios", "tenerife_deporte", "deporte_pro", "sportsdb",
           "ticketmaster", "burdeos", "destacados", "curated"]


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


# Palabras que no distinguen un plan de otro al comparar títulos de fuentes distintas
_TITLE_STOP = set("""entradas entrada sala en de del la el los las y con a al por para gira tour concierto
    presenta presentacion fin nuevo nueva show ciclo zikloa cicle vol enero febrero marzo abril mayo junio julio agosto septiembre
    octubre noviembre diciembre""".split())
_FILL = ("lat", "lon", "image", "description", "tickets_url", "price", "time", "address", "url")


def _title_words(e):
    venue = set(norm(e.get("venue")).split()) | set(norm(e.get("city")).split())
    return {w for w in norm(e["title"]).split() if len(w) > 1 and not w.isdigit() and w not in _TITLE_STOP and w not in venue}


def _richness(e):
    return sum(1 for k in ("tickets_url", "image", "time", "venue", "description", "price", "lat") if e.get(k))


def dedupe_venue(events):
    """Une el mismo plan publicado por dos fuentes con títulos distintos (la web de la sala y la agenda de
    Euskadi: «Bengo & Tatta» y «BENGO + TATTA (Jimmy Jazz Gasteiz)»): mismo día, provincia, localidad y
    sala, y casi las mismas palabras. Solo entre fuentes distintas: dentro de una fuente, dos planes
    parecidos el mismo día en la misma sala son planes distintos (dos niveles de un mismo taller).
    Se queda el más completo y se rellenan sus huecos con el otro. Devuelve (planes, número unido)."""
    from itertools import combinations
    groups = {}
    for i, e in enumerate(events):
        v = norm(e.get("venue"))
        if v:
            groups.setdefault((e["start"], e["province_code"], norm(e.get("city")), v), []).append(i)
    drop = set()
    for idxs in groups.values():
        for a, b in combinations(idxs, 2):
            ea, eb = events[a], events[b]
            if a in drop or b in drop or ea.get("source") == eb.get("source"):
                continue
            wa, wb = _title_words(ea), _title_words(eb)
            if not wa or not wb:
                continue
            common = len(wa & wb)
            # Las palabras del título más corto están casi todas en el otro (el largo suele añadir teloneros o gira)
            if common / min(len(wa), len(wb)) >= 0.75:
                keep, lose = (a, b) if _richness(ea) >= _richness(eb) else (b, a)
                for k in _FILL:
                    if not events[keep].get(k) and events[lose].get(k):
                        events[keep][k] = events[lose][k]
                drop.add(lose)
    return [e for i, e in enumerate(events) if i not in drop], len(drop)


def fill_venue_coords(events):
    """Planes sin coordenadas en una sala que otra fuente ya sitúa en el mapa (misma provincia, localidad y
    nombre de sala): se toman de ahí. Devuelve cuántos se han completado."""
    known = {}
    for e in events:
        if e.get("lat") is not None and e.get("lon") is not None and e.get("venue"):
            known.setdefault((e["province_code"], norm(e.get("city")), norm(e["venue"])), (e["lat"], e["lon"]))
    n = 0
    for e in events:
        if e.get("lat") is None and e.get("venue"):
            c = known.get((e["province_code"], norm(e.get("city")), norm(e["venue"])))
            if c:
                e["lat"], e["lon"] = c
                n += 1
    return n


def write_site(args, site_dir, payload):
    """Todo lo que se deriva de events.json: datos troceados para la web, feeds RSS y páginas estáticas."""
    events = static.default_order(static.unique_ids(payload["events"]))
    for e in events:
        e["xmas"] = classify.is_xmas(e)
    core_size, chunks = static.write_data(args.out, dict(payload, events=events))
    old = os.path.join(args.out, "events.js")  # formato anterior (un único archivo de varios MB)
    if os.path.exists(old):
        os.remove(old)
    log("Escrito %s (%.0f KB) y %d bloques de detalles en data/d/" % (os.path.join(args.out, "core.js"), core_size / 1024, chunks))
    if not args.no_pages:
        feeds = publish.write_feeds(os.path.join(site_dir, "feeds"), events)
        pages = publish.write_pages(site_dir, events, payload.get("sources") or [], payload.get("updated_at") or "",
                                    state_path=os.path.join(ROOT, "data", "sitemap_state.json"),
                                    fichas_path=os.path.join(ROOT, "data", "fichas_publicadas.json"))
        publish.prerender_index(site_dir, events)  # primeros planes en HTML estático en la portada
        ed = boletin.write(site_dir, events, today())  # boletín «Planes del finde» (web, email y feed)
        if ed:
            log("Boletín del finde %s: %d planes, %d en la selección" % (boletin.iso(ed["fri"]), ed["total"],
                len(ed["top"]) + len(ed["free"]) + len(ed["kids"]) + sum(len(c[4]) for c in ed["cities"])))
        static.stamp_index(site_dir)  # versiones en las URL de estilos, datos y app de la portada
        indexables = sum(1 for e in events if seo.is_indexable(e))
        log("Generados %d feeds RSS y %d páginas estáticas (%d fichas indexables de %d); %d fichas de planes que ya no están, con aviso"
            % (len(feeds), len(pages), indexables, len(events), publish.LAST_RUN["gone"]))


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
        # Lo mismo con las citas con fecha comprobadas a mano (data/destacados.json).
        from planes import src_curated, src_destacados
        sources = list(payload.get("sources") or [])
        counts = {}
        for key, mod in (("destacados", src_destacados), ("curated", src_curated)):
            payload["events"] = mod.replace_events(payload.get("events") or [], log)
            counts[key] = sum(1 for e in payload["events"] if e.get("source") == mod.NAME)
            sources = [s for s in sources if s.get("key") != key]
            sources.append({"key": key, "name": mod.NAME, "home": mod.HOME, "count": counts[key],
                            "seconds": 0, "error": "", "stale_from": ""})
        n_curated = counts["curated"]
        util.canon_cities(payload["events"])
        moved = salas.apply(payload["events"])
        payload["sources"] = sources
        payload["provinces"] = [{"code": c, "name": n, "ccaa": a} for c, n, a in PROVINCIAS]  # por si se ha añadido alguna
        payload["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
        with open(EVENTS_FILE, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        write_site(args, site_dir, payload)
        log("Rebuild: %d planes, %d visitas permanentes, %d citas comprobadas, %d planes situados en su sala"
            % (len(payload["events"]), n_curated, counts["destacados"], moved))
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

    renamed = util.canon_cities(all_events)
    if renamed:
        log("Nombres de localidad unificados: %d planes" % renamed)
    before = len(all_events)
    all_events = dedupe(all_events)
    all_events, same_venue = dedupe_venue(all_events)
    all_events, same_match = partidos.dedupe_matches(all_events)
    if same_match:
        log("Mismo partido en dos fuentes: %d unidos" % same_match)
    # Salas: las agendas que dan el centro del municipio (Euskadi y Navarra) pasan al punto de la sala
    geo_budget = float(os.environ.get("PLANIKA_GEO_BUDGET") or 0)
    sala_cache = salas.load()
    if geo_budget > 0:
        found, missed, left = salas.geocode(all_events, log, cache=sala_cache, budget=geo_budget)
        log("Salas buscadas en OpenStreetMap: %d encontradas, %d sin resultado, %d pendientes" % (found, missed, left))
    moved = salas.apply(all_events, sala_cache)
    located = fill_venue_coords(all_events)
    if same_venue or located or moved:
        log("Misma sala y día en dos fuentes: %d unidos; %d planes situados en su sala; %d situados en el mapa por otra fuente"
            % (same_venue, moved, located))
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
