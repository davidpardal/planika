import requests, json, re, time
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)", "Accept": "application/json, text/plain, */*"}

def get(u, n=500, **kw):
    try:
        r = requests.get(u, headers=H, timeout=40, **kw)
        return r
    except Exception as e:
        print("  ERR", str(e)[:150]); return None

def head(u, n=400):
    r = get(u)
    if r is None: return None
    t = re.sub(r"\s+", " ", r.text)[:n]
    print("  ->", r.status_code, r.headers.get("content-type", "")[:40], len(r.content), "bytes |", t)
    return r

def ckan(base, q="agenda", rows=15):
    print("\n== CKAN", base, q)
    r = get("%s/api/3/action/package_search?q=%s&rows=%d" % (base, q, rows))
    if r is None: return
    try:
        d = r.json()["result"]
    except Exception:
        print("  no JSON", r.status_code, re.sub(r"\s+", " ", r.text)[:200]); return
    print("  count", d["count"])
    for p in d["results"]:
        res = [(x.get("format"), x.get("url")) for x in p.get("resources", [])][:3]
        print("  *", p.get("title", "")[:70], "|", (p.get("metadata_modified") or "")[:10], "|", res)

# 1) CKAN de varios portales
for base in ("https://opendata.vlci.valencia.es", "https://datosabiertos.navarra.es", "https://opendata.aragon.es",
             "https://datos.comunidad.madrid", "https://datosabiertos.sevilla.org"):
    ckan(base, "agenda")
    ckan(base, "eventos")

# 2) Opendatasoft Valencia
print("\n== ODS Valencia")
head("https://valencia.opendatasoft.com/api/explore/v2.1/catalog/datasets?q=agenda&limit=10")

# 3) datos.gob.es: catálogo nacional por título
for t in ("agenda", "eventos", "agenda cultural"):
    print("\n== datos.gob.es title", t)
    r = get("https://datos.gob.es/apidata/catalog/dataset/title/%s?_pageSize=40&_page=0&_sort=-modified" % requests.utils.quote(t))
    if r is None: continue
    try:
        items = r.json()["result"]["items"]
        print("  items", len(items))
        for it in items:
            title = it.get("title")
            if isinstance(title, list): title = (title[0] or {}).get("_value", "")
            dist = it.get("distribution") or []
            if isinstance(dist, dict): dist = [dist]
            fm = [((d.get("format") or {}).get("value") if isinstance(d.get("format"), dict) else d.get("format")) for d in dist][:3]
            print("  *", str(title)[:70], "|", (it.get("modified") or "")[:10], "|", fm, "|", (it.get("publisher") or "")[-40:])
    except Exception as e:
        print("  parse", e, re.sub(r"\s+", " ", r.text)[:200])

# 4) Bilbao
print("\n== Bilbao")
head("https://www.bilbao.eus/cs/Satellite?c=Page&cid=1272990237857&pageid=1272990237857&idioma=es&pagename=Bilbaonet/Page/BIO_ListadoEventosAppInfoBilbao&todos=si", 600)
head("https://www.bilbao.eus/cs/Satellite?c=Page&pageid=3000094681&idioma=es&pagename=Bilbaonet/Page/OD_obtenerAgendaMunicipal&formato=XML", 600)

# 5) Andalucía y Sevilla
print("\n== Andalucia")
head("https://www.andalucia.org/eventos/", 300)
head("https://datos.juntadeandalucia.es/api/v0/", 300)
head("https://www.sevilla.org/servicios/datos-abiertos", 200)
print("\n== Zaragoza / Euskadi turismo")
head("https://opendata.euskadi.eus/contenidos/ds_eventos/eventos_turisticos/opendata/agenda.xml", 300)
head("https://www.zaragoza.es/sede/servicio/cultura/evento.json?rows=2", 400)
