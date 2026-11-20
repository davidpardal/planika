import sys, os
sys.path.insert(0, os.getcwd())
import fetch_events as F
from planes import src_euskadi, src_jimmyjazz
log = print
jj = src_jimmyjazz.fetch(log)
eu = [e for e in src_euskadi.fetch(log) if e["province_code"] == "01"]
print("JJ", len(jj), "Euskadi Álava", len(eu))
for e in jj:
    print("  JJ", e["start"], e["time"] or "--:--", e["category"], "|", e["title"][:70], "|", e["venue"], "|", e["price"][:40], "|", e["tickets_url"][:50])
allev = F.dedupe(eu + jj)
before = list(allev)
ids_before = {id(e) for e in allev}
out, n = F.dedupe_venue(allev)
print("unidos:", n)
kept_jj = [e for e in out if e["source"] == src_jimmyjazz.NAME]
print("JJ que quedan (no estaban en Euskadi):", len(kept_jj))
gone = [e for e in before if all(e is not x for x in out)]
for e in gone:
    print("  quitado:", e["source"][:12], e["start"], e["title"][:70])
# posibles duplicados que no se han unido: misma sala y día con fuentes distintas
from collections import defaultdict
g = defaultdict(list)
for e in out:
    if e["venue"] in ("Sala Jimmy Jazz", "Sala Kubik"): g[(e["start"], e["venue"])].append(e)
for k, v in sorted(g.items()):
    if len({e["source"] for e in v}) > 1:
        print("  misma sala y día, sin unir:", k, [ (e["source"][:8], e["title"][:50]) for e in v])
print("situados por sala:", F.fill_venue_coords(out))
