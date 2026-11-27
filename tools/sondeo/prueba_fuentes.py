"""Prueba con datos reales de los conectores nuevos (rama fuentes-andalucia-valencia). No publica nada."""
import collections
import html
import importlib
import re
import sys
import time

sys.path.insert(0, ".")
from planes.util import today, iso  # noqa: E402

t0 = iso(today())
for name in sys.argv[1:]:
    mod = importlib.import_module("planes.src_" + name)
    s = time.time()
    evs = mod.fetch(print)
    print("== %s: %d eventos en %.0f s" % (mod.NAME, len(evs), time.time() - s))
    fut = [e for e in evs if e["end"] >= t0]
    print("   en curso o futuros:", len(fut))
    print("   por provincia:", collections.Counter(e["province"] or "?" for e in fut).most_common())
    print("   por categoría:", collections.Counter(e["category"] for e in fut).most_common())
    print("   sin provincia:", [(e["title"][:40], e["city"]) for e in evs if not e["province"]][:15])
    print("   con hora:", sum(1 for e in fut if e["time"]), "con lugar:", sum(1 for e in fut if e["venue"]),
          "con imagen:", sum(1 for e in fut if e["image"]))
    dic = [e for e in fut if e["start"] <= "2026-12-07"]
    print("   próximos 10 días:", len(dic))
    for e in sorted(fut, key=lambda e: (e["start"], e["time"]))[:40]:
        print("    %s %s→%s %5s | %-10s | %-55s | %s · %s · %s" % (e["category"][:6], e["start"], e["end"], e["time"], e["subtype"][:10],
                                                            e["title"][:55], e["venue"][:30], e["city"], e["province"]))
    seen = set()
    for e in fut:
        k = (e["city"], e["province"])
        if k not in seen and len(seen) < 60:
            seen.add(k)
    print("   ciudades:", sorted(seen)[:60])

# Visit València: tarjetas de un solo día y fichas
import requests  # noqa: E402
S = requests.Session()
S.headers["User-Agent"] = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"
t = S.get("https://www.visitvalencia.com/agenda-valencia/agenda-mensual?date=2026-12", timeout=60).text
parts = re.split(r'(?=<div\s+data-history-node-id=)', t)[1:]
solo = [p for p in parts if "Del " not in p[:3000]]
print("== Visit València: tarjetas", len(parts), "sin rango", len(solo))
for p in solo[:3]:
    q = re.sub(r"<(source|img|picture)[^>]*>|</picture>", "", p[:3500])
    q = re.sub(r'\s+(typeof|about|loading|width|height)="[^"]*"', "", q)
    print(re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", q))[:1800])
    print("-" * 40)
dates = collections.Counter()
for p in parts:
    d = re.search(r'card__date[^>]*>\s*([^<]+?)\s*<', p)
    dates[d.group(1)[:40] if d else "-"] += 1
print("formatos de fecha:", dates.most_common(15))
for slug in ("/agenda-valencia/concierto-de-bunbury-en-valencia", "/agenda-valencia/obra-de-teatro-gigante-en-valencia"):
    r = S.get("https://www.visitvalencia.com" + slug, timeout=60)
    print("ficha", r.status_code, slug)
    body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
    for k in ("field--name-field-event-dates", "field--name-field-place", "field--name-field-location", "field--name-field-address",
              "field--name-field-price", "field--name-field-schedule", "field--name-field-event-category", "field--name-field-link",
              "field--name-field-tickets", "field--name-field-website"):
        i = body.find(k)
        if i > 0:
            print("  ", k, "->", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body[i:i + 900])))[:300])
    print("   campos:", sorted(set(re.findall(r"field--name-([a-z0-9-]+)", body)))[:40])
    print("   time:", re.findall(r'<time[^>]*datetime="([^"]+)"', r.text)[:6])
