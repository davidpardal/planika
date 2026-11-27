"""Sondeo 4: tarjetas de Visit València (calidad) y búsqueda POST en la agenda de valencia.es."""
import html
import re
from datetime import datetime

import requests

H = {"User-Agent": "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"}
S = requests.Session()
S.headers.update(H)


def clean(h):
    h = re.sub(r"<(source|img|picture)[^>]*>|</picture>", "", h)
    h = re.sub(r'\s+(class|typeof|about|loading|width|height)="[^"]*"', "", h)
    h = re.sub(r"\n\s*\n+", "\n", h)
    return re.sub(r"[ \t]+", " ", h)


print("=" * 20, "Visit Valencia: tarjetas")
r = S.get("https://www.visitvalencia.com/agenda-valencia/agenda-mensual?date=2026-12", timeout=60)
t = r.text
parts = re.split(r'(?=<div\s+data-history-node-id=)', t)[1:]
print("tarjetas:", len(parts))
for p in parts[:2]:
    print("-" * 50)
    print(clean(p)[:2200])
rows = {}
for p in parts:
    a = re.search(r'href="(/agenda-valencia/[^"]+)"', p)
    h = re.search(r'card__heading[^>]*>\s*(.*?)\s*</h3>', p, re.S)
    d = re.search(r'Del (\d\d/\d\d/\d{4}) al (\d\d/\d\d/\d{4})', p)
    cat = re.findall(r'card__(?:category|tag|label)[^>]*>\s*([^<]+)<', p)
    if a and h:
        rows[a.group(1)] = (html.unescape(h.group(1)).strip(), d.groups() if d else None, cat[:3])
print("fichas unicas:", len(rows))
largos = 0
for u, (ti, d, cat) in sorted(rows.items(), key=lambda x: (x[1][1] or ("", ""))[0][::-1]):
    dias = None
    if d:
        a, b = (datetime.strptime(x, "%d/%m/%Y") for x in d)
        dias = (b - a).days
        largos += dias > 60
    print("  %s | %s | %s dias | %s" % (ti[:70], d, dias, cat))
print("con mas de 60 dias:", largos)
for page in ("?date=2026-12&page=1", "?date=2027-01"):
    rr = S.get("https://www.visitvalencia.com/agenda-valencia/agenda-mensual" + page, timeout=60)
    print(page, rr.status_code, len(set(re.findall(r'href="(/agenda-valencia/[a-z0-9-]+)"', rr.text))))

print("=" * 20, "valencia.es: POST de busqueda")
r = S.get("https://www.valencia.es/cas/agenda-de-la-ciudad", timeout=60)
t = r.text
m = re.search(r'<form action="([^"]*cargarEventosAv[^"]*)"[^>]*>(.*?)</form>', t, re.S)
if m:
    action = html.unescape(m.group(1))
    body = m.group(2)
    names = re.findall(r'name="([^"]+)"(?:[^>]*value="([^"]*)")?', body)
    print("action:", action)
    print("campos:", names[:40])
    ns = "_CalendarAc_INSTANCE_iWBt6iPSuFjM_"
    data = {n: v for n, v in names}
    for k in list(data):
        if k.endswith("fch-inicio") or k == "fch-inicio":
            data[k] = "01/12/2026"
        if k.endswith("fch-fin") or k == "fch-fin":
            data[k] = "31/12/2026"
    data.setdefault(ns + "fch-inicio", "01/12/2026")
    data.setdefault(ns + "fch-fin", "31/12/2026")
    rr = S.post(action, data=data, timeout=60)
    print("POST", rr.status_code, len(rr.text), rr.url[:200])
    tt = rr.text
    i = tt.find("Aplicar rango")
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", tt[i:], flags=re.S)))
    print(txt[:2500])
    j = tt.find("Aplicar rango")
    k = tt.find("detalle", j)
    print(clean(tt[k - 1500:k + 2500]) if k > 0 else "sin 'detalle'")
    print("enlaces:", sorted(set(re.findall(r'href="([^"]*(?:agenda|evento|detalle)[^"]*)"', tt)))[:20])
else:
    print("sin formulario")
