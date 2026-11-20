import requests, re, html
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=40)
        print("\n###", u, "->", r.url, r.status_code, (r.headers.get("content-type") or "")[:40], len(r.content)); return r
    except Exception as e: print("\n###", u, "ERR", str(e)[:100])
def strip(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style).*?</\1>", " ", t, flags=re.S)))).strip()
r = get("https://jimmyjazzgasteiz.com/")
if r is not None:
    t = r.text
    print("generator:", re.findall(r'<meta name="generator" content="([^"]+)"', t)[:3])
    print("links:", sorted(set(l for l in re.findall(r'href="([^"#]+)"', t) if "jimmyjazz" in l))[:60])
    print("ld:", len(re.findall(r'"@type"\s*:\s*"[A-Za-z]*Event"', t)))
    print(strip(t)[:2500])
for u in ("https://jimmyjazzgasteiz.com/wp-json/", "https://jimmyjazzgasteiz.com/robots.txt"):
    r = get(u)
    if r is not None and r.ok:
        if "json" in (r.headers.get("content-type") or ""):
            d = r.json(); print(d.get("namespaces")); print([k for k in d.get("routes", {}) if re.search(r"event|tribe|mec|agenda|concert", k)][:15])
        else: print(r.text[:500])
for u in ("https://helldorado.com/", "https://helldorado.com/sitemap.xml", "https://helldorado.com/llms.txt"):
    r = get(u)
    if r is not None: print(r.text[:2500])
r = get("https://kubikvitoria.com/eventos/")
if r is not None: print(strip(r.text)[:1500])
