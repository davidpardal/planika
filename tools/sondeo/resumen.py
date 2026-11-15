import collections, json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
evs = d["events"]
print("\n### RESUMEN total", len(evs))
by = collections.defaultdict(list)
for e in evs: by[e["source"]].append(e)
for src, l in sorted(by.items()):
    n = len(l)
    pct = lambda k: "%d%%" % (100 * sum(1 for e in l if e.get(k) not in (None, "", False)) / n)
    print("\n== %s: %d | hora %s lugar %s coords %s imagen %s precio %s" % (src, n, pct("time"), pct("venue"), pct("lat"), pct("image"), pct("price")))
    print("   categorias:", dict(collections.Counter(e["category"] for e in l).most_common()))
    print("   ciudades:", dict(collections.Counter(e["city"] for e in l).most_common(8)))
    for e in l[:: max(1, n // 4)][:4]:
        print("   -", json.dumps({k: e[k] for k in ("title", "start", "end", "time", "category", "city", "venue", "price")}, ensure_ascii=False)[:300])
