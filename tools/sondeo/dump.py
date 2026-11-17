import requests, json, re, time
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)", "Accept": "*/*"}
WANT = {"L01360577": "Vigo", "A05003638": "Canarias", "L01380380": "Santa Cruz Tenerife", "A07002862": "CyL",
        "L02000001": "Alava", "A16003011": "Euskadi", "L02000048": "Bizkaia", "A08002880": "CLM", "L01300161": "Cartagena"}

def get(u, **kw):
    try:
        return requests.get(u, headers=H, timeout=45, **kw)
    except Exception as e:
        print("  ERR", str(e)[:120]); return None

def text(v):
    if isinstance(v, list): v = v[0] if v else ""
    if isinstance(v, dict): v = v.get("_value") or v.get("value") or ""
    return str(v)

cands = []
for t in ("agenda cultural", "agenda"):
    for page in (0, 1):
        r = get("https://datos.gob.es/apidata/catalog/dataset/title/%s?_pageSize=50&_page=%d&_sort=-modified" % (requests.utils.quote(t), page))
        time.sleep(2)
        if r is None: continue
        try: items = r.json()["result"]["items"]
        except Exception: print("no json", t, page, r.status_code); continue
        for it in items:
            pub = text(it.get("publisher"))[-9:]
            if pub in WANT and (pub, text(it.get("title"))) not in [(c[0], c[1]) for c in cands]:
                dist = it.get("distribution") or []
                if isinstance(dist, dict): dist = [dist]
                cands.append((pub, text(it.get("title")), (it.get("modified") or "")[:10], dist))
print("candidatos", len(cands))
seen = set()
for pub, title, mod, dist in cands:
    if "2015" in title or "2016" in title or "2017" in title or "2018" in title or "2019" in title or "2020" in title or "2021" in title or "2022" in title or "2023" in title or "2024" in title: continue
    print("\n###", WANT[pub], "|", title[:70], "|", mod)
    n = 0
    for d in dist:
        url = text(d.get("accessURL")) or text(d.get("downloadURL"))
        fmt = d.get("format"); fmt = text(fmt.get("value") if isinstance(fmt, dict) else fmt)
        print("  dist", fmt[-30:], url[:150])
        if url in seen or not url.startswith("http"): continue
        low = (fmt + url).lower()
        if not any(k in low for k in ("json", "csv", "xml", "rss")): continue
        if n >= 2: continue
        seen.add(url); n += 1
        r = get(url)
        time.sleep(1.5)
        if r is None: continue
        body = re.sub(r"\s+", " ", r.text)[:450]
        print("    ->", r.status_code, r.headers.get("content-type", "")[:35], len(r.content), "bytes |", body)
        yrs = re.findall(r"2026-1[12]-\d\d|2026-0[1-9]-\d\d|2027-\d\d-\d\d|\d\d/\d\d/2026|\d\d/\d\d/2027", r.text)
        print("    fechas 2026-27:", len(yrs), yrs[:4])

print("\n== andalucia.org/eventos: endpoints")
r = get("https://www.andalucia.org/eventos/")
if r is not None:
    t = r.text
    for m in sorted(set(re.findall(r'["\'](/[A-Za-z0-9_\-/\.]*(?:api|ajax|json|search|events?)[A-Za-z0-9_\-/\.\?=&]*)["\']', t)))[:25]: print("  path", m[:140])
    for m in re.findall(r'(?:endpoint|apiUrl|ajaxUrl|restUrl|url)\s*[:=]\s*["\']([^"\']{8,160})["\']', t)[:15]: print("  cfg", m)
