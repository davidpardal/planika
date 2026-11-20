import requests, json, re
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
B = "https://lagenterula.com"
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=40)
        print("\n###", u, r.status_code, r.headers.get("content-type"), len(r.content))
        return r
    except Exception as e:
        print("\n###", u, "ERR", str(e)[:120])
r = get(B + "/robots.txt")
if r is not None: print(r.text[:1500])
r = get(B + "/wp-json/")
if r is not None and r.ok:
    try:
        d = r.json(); print("namespaces:", d.get("namespaces")); print("name:", d.get("name"), "|", d.get("description"))
    except Exception as e: print("no json", e, r.text[:300])
for path in ("/wp-json/tribe/events/v1/events?per_page=3", "/wp-json/wp/v2/types", "/wp-json/wp/v2/pages?per_page=50&_fields=link,title",
             "/events/feed/", "/feed/", "/wp-sitemap.xml", "/sitemap_index.xml"):
    r = get(B + path)
    if r is None or not r.ok:
        if r is not None: print(r.text[:300])
        continue
    print(r.text[:3500])
r = get(B + "/events/tartalo-4/")
if r is not None:
    t = r.text
    print("ld+json:", [x[:1500] for x in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', t, re.S)[:2]])
    print("legal links:", sorted(set(re.findall(r'href="([^"]*(?:legal|aviso|privacidad|cookies|condiciones|terminos)[^"]*)"', t, re.I)))[:10])
    print("plugins:", sorted(set(re.findall(r'wp-content/plugins/([a-z0-9_-]+)/', t)))[:30])
    m = re.search(r'<main.*?</main>', t, re.S); print(re.sub(r"\s+", " ", (m.group(0) if m else t))[:3000])
