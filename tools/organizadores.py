#!/usr/bin/env python3
"""Propone en data/organizadores.json los eventos nuevos enviados desde «Publica tu evento».

Lee los envíos pendientes de Supabase (función event_submissions_pending, con la clave pública: devuelve los datos del
evento, nunca el correo del organizador) y añade los que todavía no están ni en data/organizadores.json ni en
data/organizadores_descartados.json. El workflow organizadores.yml lo sube a la rama organizadores-nuevos y abre (o
actualiza) un pull request: fusionarlo es aprobar y publicar. Para descartar un envío, su id va a
data/organizadores_descartados.json.

python3 tools/organizadores.py [--resumen /tmp/resumen.md]   # escribe el resumen del PR; sale con 0 si no hay nada nuevo
"""
import argparse
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from planes.util import PROVINCIAS, iso, today  # noqa: E402

API = "https://rqjrrdtdscvcimwzrwxj.supabase.co/rest/v1/rpc/"
KEY = "sb_publishable_1gASlwY1wubC872dD5SJMw_4txaahRF"  # clave pública de la web
DATA = os.path.join(ROOT, "data", "organizadores.json")
DESCARTADOS = os.path.join(ROOT, "data", "organizadores_descartados.json")
PLANES = {"gratis": "Publicar gratis", "destacado": "Destacado (5 €)", "destacado_instagram": "Destacado + Instagram (12 €)",
          "bono": "Bono de 5 destacados (20 €)"}
PROV = {c: n for c, n, _ in PROVINCIAS}


def pending():
    req = urllib.request.Request(API + "event_submissions_pending", data=b"{}", method="POST",
                                 headers={"apikey": KEY, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def entry(row, checked=None):
    """Un envío -> entrada de data/organizadores.json (mismo formato que data/destacados.json)."""
    d = row.get("data") or {}
    url = d.get("url") or d.get("tickets_url") or ""
    lugar = d.get("kind") == "lugar"  # local abierto todo el año (escape room, parque de bolas…): sin fechas
    out = {
        "id": "org-" + str(row["sub_id"])[:8],
        "kind": "lugar" if lugar else "",
        "title": d.get("title") or "",
        "start": "" if lugar else d.get("start") or "",
        "end": "" if lugar else d.get("end") or d.get("start") or "",
        "time": "" if lugar else d.get("time") or "",
        "horario": d.get("horario") or "",
        "city": d.get("city") or "",
        "province": PROV.get(d.get("province_code") or "", ""),
        "venue": d.get("venue") or "",
        "address": d.get("address") or "",
        "description": d.get("description") or "",
        "category": d.get("category") or "otros",
        "price": d.get("price") or "",
        "free": bool(d.get("free")),
        "url": url,
        "tickets_url": d.get("tickets_url") or "",
        "image": d.get("image") or "",
        "organizer": d.get("organizer") or "",
        "plan": row.get("plan") or "gratis",
        "destacado": False,  # se activa a mano cuando el destacado está pagado (o es de lanzamiento)
        "refs": [url] if url else [],
        "sent": row.get("sent") or "",
        "checked": checked or iso(today()),
    }
    keep = ("id", "title", "url", "province", "checked") + (() if lugar else ("start",))
    return {k: v for k, v in out.items() if v not in ("", None) or k in keep}


def load(path, key):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    return data.get(key, []) if isinstance(data, dict) else data


def summary(new):
    lines = ["Eventos y locales enviados desde «Publica tu evento» pendientes de aprobar. **Fusionar este PR los publica** en la "
             "siguiente actualización. Para descartar uno, quítalo del fichero o dime su id.", "",
             "| id | Evento | Fecha | Lugar | Opción |", "|---|---|---|---|---|"]
    for e in new:
        if e.get("kind") == "lugar":
            when = "Todo el año" + ((" (" + e["horario"].replace("|", "/") + ")") if e.get("horario") else "")
        else:
            when = e["start"] + (("–" + e["end"]) if e.get("end") and e["end"] != e["start"] else "") + ((" " + e["time"]) if e.get("time") else "")
        where = ", ".join(x for x in (e.get("venue"), e.get("city"), e.get("province")) if x)
        lines.append("| `%s` | [%s](%s) | %s | %s | %s |" % (e["id"], e["title"].replace("|", "/"), e.get("url", ""), when,
                                                         where.replace("|", "/"), PLANES.get(e.get("plan"), e.get("plan"))))
    paid = [e for e in new if e.get("plan") != "gratis"]
    if paid:
        lines += ["", "⭐ %d quieren destacado: se publican sin destacar hasta que el destacado esté pagado (o sea de "
                  "lanzamiento); entonces se pone `\"destacado\": true`." % len(paid)]
    lines += ["", "Los correos de contacto están en Supabase (tabla `event_submissions`), nunca en el repositorio."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resumen", default="")
    args = ap.parse_args()
    current = load(DATA, "events")
    known = {e.get("id") for e in current} | set(load(DESCARTADOS, "ids"))
    rows = pending()
    new = [entry(r) for r in rows]
    new = [e for e in new if e["id"] not in known and (e.get("kind") == "lugar" or e["start"] >= iso(today()))]
    print("Envíos en Supabase: %d · nuevos para revisar: %d" % (len(rows), len(new)))
    if not new:
        return 0
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump({"about": "Eventos enviados por sus organizadores desde planikaapp.com/promociona-tu-evento.html y aprobados "
                            "al fusionar el PR diario. Ver planes/src_organizadores.py.",
                   "events": current + new}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    if args.resumen:
        with open(args.resumen, "w", encoding="utf-8") as fh:
            fh.write(summary(new) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
