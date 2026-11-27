"""Sondeo 3: tarjetas completas de AAIICC (normal y exposición) y cómo carga eventos valencia.es."""
import re

import requests

H = {"User-Agent": "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"}
S = requests.Session()
S.headers.update(H)
A = "https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia"


def get(u, **kw):
    r = S.get(u, timeout=40, **kw)
    print("[%s] %s len=%d %s" % (r.status_code, r.headers.get("content-type", "")[:30], len(r.content), r.url))
    return r


def clean(h):
    h = re.sub(r"<(source|img|picture)[^>]*>|</picture>", "", h)
    h = re.sub(r'\s+class="[^"]*"', "", h)
    h = re.sub(r"\n\s*\n+", "\n", h)
    return re.sub(r"[ \t]+", " ", h)


def cards(t, n=3):
    parts = t.split("<article")[1:]
    print("articles:", len(parts))
    for p in parts[:n]:
        print("-" * 60)
        print(clean(p.split("</article>")[0])[:2500])


print("=" * 20, "AAIICC listado general")
cards(get(A + "/actividades").text, 2)
print("=" * 20, "AAIICC exposiciones")
cards(get(A + "/actividades?topic=1430").text, 3)
print("=" * 20, "AAIICC Sevilla + diciembre")
r = get(A + "/actividades?province=1445&date_from=2026-12-01&date_to=2026-12-31")
m = re.search(r"(\d+)\s+Actividades", r.text)
print(m and m.group(0))
print("=" * 20, "AAIICC ficha")
r = get(A + "/evento/el-guiton-onofre-2")
t = r.text
i = t.find("<main")
body = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", t[i:], flags=re.S)
print(clean(body)[:6000])
for ld in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S):
    print("ld:", re.sub(r"\s+", " ", ld)[:1500])
for p in ("1", "77"):
    print("page", p, len(set(re.findall(r'/evento/[^"]+', get(A + "/actividades?page=" + p).text))))

print("=" * 20, "valencia.es JS del calendario")
js = get("https://www.valencia.es/o/calendar.ac/js/JS.js").text
print(js[:4000])
for m in re.finditer(r"(ajax|url|resourceURL|cargarEventos|fetch)[^\n]{0,200}", js):
    print("  >", m.group(0)[:220])
page = get("https://www.valencia.es/cas/agenda-de-la-ciudad").text
for m in re.finditer(r'<form[^>]*>', page):
    print("form:", m.group(0)[:400])
for m in re.finditer(r'(cargarEventos[^"\']{0,300})', page):
    print("cargar:", m.group(0)[:400])
i = page.find("CalendarAc_INSTANCE")
print(clean(page[i - 300:i + 3000]))
