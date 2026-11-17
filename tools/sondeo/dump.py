import requests, json, re, time
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)", "Accept": "*/*"}
def get(u, **kw):
    try: return requests.get(u, headers=H, timeout=40, **kw)
    except Exception as e:
        print("  ERR", str(e)[:100]); return None
def text(v):
    if isinstance(v, list): v = v[0] if v else ""
    if isinstance(v, dict): v = v.get("_value") or v.get("value") or ""
    return str(v)
BAD = re.compile(r"alcald|concejal|cargos|responsables|lehendakari|2030|presidente|consejer|pleno|transparen|licitaci|convenio|subvenci|contrat|ods\b|sdg", re.I)
seen = set()
for q in ("actividades", "eventos", "calendario", "fiestas", "programacion", "espectaculos", "cartelera", "conciertos", "festivales", "teatro", "museos exposiciones", "ocio"):
    for page in (0,):
        r = get("https://datos.gob.es/apidata/catalog/dataset/title/%s?_pageSize=40&_page=%d&_sort=-modified" % (requests.utils.quote(q), page))
        time.sleep(4)
        if r is None: continue
        try: items = r.json()["result"]["items"]
        except Exception: print("##", q, "no json", r.status_code); continue
        print("\n## %s -> %d" % (q, len(items)))
        for it in items:
            t = text(it.get("title"))
            if BAD.search(t) or t in seen: continue
            seen.add(t)
            dist = it.get("distribution") or []
            if isinstance(dist, dict): dist = [dist]
            fm = []
            for d in dist:
                f = d.get("format"); f = text(f.get("value") if isinstance(f, dict) else f).split("/")[-1].lower()
                if f not in fm: fm.append(f)
            print("  *", t[:75], "|", (it.get("modified") or "")[:12], "|", ",".join(fm)[:50], "|", text(it.get("publisher"))[-9:])
def ckan(base, q):
    r = get("%s/api/3/action/package_search?q=%s&rows=12" % (base, q))
    if r is None: return
    try: d = r.json()["result"]
    except Exception: print("  no json", base, r.status_code); return
    print("\n== CKAN", base, q, d["count"])
    for p in d["results"]:
        print("  *", p.get("title", "")[:70], "|", (p.get("metadata_modified") or "")[:10], "|", [x.get("format") for x in p.get("resources", [])][:4])
for b in ("https://dadesobertes.gva.es", "https://catalogo-datos.asturias.es", "https://datos.gijon.es", "https://opendata.palma.cat"):
    for q in ("agenda", "eventos"):
        ckan(b, q)
