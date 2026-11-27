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

    sev = [e for e in fut if e["province"] == "Sevilla" and e["start"] <= "2026-12-14"]
    print("   Sevilla hasta el 14 dic:", len(sev))
    for e in sorted(sev, key=lambda e: (e["start"], e["time"]))[:45]:
        print("    %s %s→%s %5s | %-55s | %s · %s" % (e["category"][:6], e["start"], e["end"], e["time"], e["title"][:55], e["venue"][:30], e["city"]))
    print("   sin ciudad:", [(e["title"][:40], e["venue"][:25], e["province"]) for e in fut if not e["city"]][:25])
    print("   fuera de Andalucía:", [(e["title"][:40], e["city"], e["province"]) for e in fut if e["ccaa"] != "Andalucía"][:25])
# 1795761218
