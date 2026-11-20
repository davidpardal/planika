import requests, json, re, html
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
B = "https://lagenterula.com"
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=60)
        print("\n###", u, r.status_code, r.headers.get("content-type"), len(r.content), r.headers.get("x-wp-total"), r.headers.get("x-wp-totalpages"))
        return r
    except Exception as e:
        print("\n###", u, "ERR", str(e)[:120])
def strip(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
for p in ("/aviso-legal/", "/pagina-ejemplo/"):
    r = get(B + p)
    if r is not None and r.ok:
        m = re.search(r'<div class="entry-content[^"]*"[^>]*>(.*?)</div>\s*</div>', r.text, re.S) or re.search(r"<main.*?</main>", r.text, re.S)
        print(strip(m.group(0) if m else r.text)[:4000])
r = get(B + "/wp-json/")
d = r.json()
for route, v in d.get("routes", {}).items():
    if "mec" in route or "event" in route: print("ROUTE", route, [m for e in v.get("endpoints", []) for m in e.get("methods", [])])
for p in ("/wp-json/wp/v2/mec-events?per_page=2", "/wp-json/mec/v1.0/events?limit=2", "/wp-json/mec/v1/events?limit=2", "/wp-json/mec/v1.0/events"):
    r = get(B + p)
    if r is not None: print(r.text[:2500])
r = get(B + "/events/feed/")
if r is not None:
    t = r.text
    print("items:", t.count("<item>"))
    it = t.split("<item>")[1].split("</item>")[0]
    print(re.sub(r"<content:encoded>.*?</content:encoded>", "<content:encoded>…</content:encoded>", it, flags=re.S)[:3000])
    print("mec tags:", sorted(set(re.findall(r"<(mec:[a-zA-Z]+)", t))))
r = get(B + "/events/feed/?paged=2")
if r is not None: print("page2 items:", r.text.count("<item>"))
r = get(B + "/sitemap_index.xml")
if r is not None: print(r.text[:1500])
r = get(B + "/events/tartalo-4/")
if r is not None:
    t = r.text
    for k in ("mec-single-event-date", "mec-single-event-time", "mec-single-event-location", "mec-event-cost", "mec-single-event-category", "mec-events-meta-group", "mec-booking", "mec-event-more-info"):
        i = t.find(k); print("--", k, i, strip(t[i:i+700])[:350] if i > 0 else "")
    print("ld+json:", [x[:2000] for x in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', t, re.S)][:3])
