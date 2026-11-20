import requests, json, re, html
from urllib.parse import urljoin, urlsplit
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
def get(u, show=True):
    try:
        r = requests.get(u, headers=H, timeout=40, allow_redirects=True)
        if show: print("\n###", u, "->", r.url, r.status_code, (r.headers.get("content-type") or "")[:40], len(r.content))
        return r
    except Exception as e:
        if show: print("\n###", u, "ERR", str(e)[:100])
def strip(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()
CANDS = {
 "jimmyjazz": ["https://jimmyjazzgasteiz.com/es/agenda-conciertos-y-djs/"],
 "urbanrock": ["https://www.urbanrockconcept.com/"],
 "helldorado": ["https://www.helldorado.es/", "https://helldorado.com/", "https://www.salahelldorado.com/", "https://helldorado.net/"],
 "kubik": ["https://kubikvitoria.com/", "https://www.salakubik.com/", "https://kubik.eus/"],
 "vital": ["https://www.fundacionvital.eus/agenda", "https://www.fundacionvital.eus/rss.xml"],
 "artium": ["https://www.artium.eus/es/actividades", "https://www.artium.eus/es/actividades?format=feed&type=rss"],
}
for name, urls in CANDS.items():
    print("\n================", name)
    for u in urls:
        r = get(u)
        if r is None or not r.ok: continue
        t = r.text
        base = "%s://%s" % urlsplit(r.url)[:2]
        print("title:", (re.search(r"<title>(.*?)</title>", t, re.S) or [None, ""])[1].strip()[:100])
        print("generator:", re.findall(r'<meta name="generator" content="([^"]+)"', t)[:3])
        print("plugins:", sorted(set(re.findall(r'wp-content/plugins/([a-z0-9_-]+)/', t)))[:25])
        print("ld types:", re.findall(r'"@type"\s*:\s*"([A-Za-z]*Event)"', t)[:10], "count", len(re.findall(r'"@type"\s*:\s*"[A-Za-z]*Event"', t)))
        print("feeds:", sorted(set(re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]+href="([^"]+)"', t)))[:6])
        print("ical:", sorted(set(re.findall(r'href="([^"]*(?:ical|\.ics|webcal)[^"]*)"', t)))[:4])
        links = sorted(set(l for l in re.findall(r'href="([^"#]+)"', t) if re.search(r"event|evento|concierto|agenda|programa|activid", l, re.I)))
        print("event-ish links (%d):" % len(links), links[:25])
        print("text:", strip(re.sub(r"<(script|style).*?</\1>", " ", t, flags=re.S))[:1500])
        rb = get(base + "/robots.txt", show=False)
        if rb is not None and rb.ok: print("robots:", rb.text[:400].replace("\n", " | "))
        wj = get(base + "/wp-json/", show=False)
        if wj is not None and wj.ok and "json" in (wj.headers.get("content-type") or ""):
            try:
                d = wj.json(); print("wp-json namespaces:", d.get("namespaces"))
                print("event routes:", [k for k in d.get("routes", {}) if re.search(r"event|tribe|mec|agenda|concert", k)][:15])
            except Exception as e: print("wp-json no parse", e)
        break
