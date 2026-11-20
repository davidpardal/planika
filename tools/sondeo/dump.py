import requests, re, html, json
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
B = "https://jimmyjazzgasteiz.com"
def get(u):
    r = requests.get(u, headers=H, timeout=40)
    print("\n###", u, r.status_code, len(r.content), r.headers.get("x-wp-total")); return r
def strip(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", t, flags=re.S)))).strip()
cats = get(B + "/wp-json/wp/v2/categories?per_page=100&_fields=id,name,slug,count").json()
print(cats)
ids = [c["id"] for c in cats if c["slug"] in ("agenda", "agenda-conciertos-vitoria-gasteiz", "agenda-djs-vitoria-gasteiz", "kubik")]
r = get(B + "/wp-json/wp/v2/posts?per_page=5&categories=%s" % ",".join(map(str, ids)))
posts = r.json()
for p in posts[:3]:
    print("\n---", p["id"], p["date"], p["modified"], p["link"], p["categories"], p.get("tags"), p.get("lang"))
    print("title:", p["title"]["rendered"])
    print("keys:", sorted(p.keys()))
    print("meta:", json.dumps(p.get("meta"))[:600])
    print("acf:", json.dumps(p.get("acf"))[:600])
    print("excerpt:", strip(p["excerpt"]["rendered"])[:300])
    c = p["content"]["rendered"]
    print("content:", strip(c)[:1200])
    print("links:", re.findall(r'href="([^"]+)"', c)[:8])
r = get(posts[0]["link"])
t = r.text
i = t.find(posts[0]["title"]["rendered"][:15])
print("page around title:", strip(t[max(0, i-3000):i+3000])[:2500])
print("ld:", re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', t, re.S)[:2])
r = get(B + "/aviso-legal/")
m = re.search(r"<main.*?</main>|<article.*?</article>", r.text, re.S)
print(strip(m.group(0) if m else r.text)[:3500])
# portada: estructura de la lista de agenda
r = get(B + "/")
t = r.text
i = t.find("Raimundo")
print("home html around first item:", t[max(0, i-1500):i+1200])
