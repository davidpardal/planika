"""Sondeo de fuentes para Valencia y Sevilla: estructura de cada URL candidata (no guarda nada)."""
import json
import re
import sys

import requests

H = {"User-Agent": "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"}
URLS = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]


def show_html(t):
    m = re.search(r'<meta[^>]+name="[Gg]enerator"[^>]+content="([^"]+)"', t)
    print("    generator:", m.group(1) if m else "-")
    for a in re.findall(r'<link[^>]+rel="alternate"[^>]*>', t)[:5]:
        print("    alt:", a[:200])
    for ld in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', t, re.S)[:3]:
        print("    ld+json:", re.sub(r"\s+", " ", ld)[:900])
    pages = sorted(set(re.findall(r'href="([^"]*[?&]page=\d+[^"]*)"', t)))[:6]
    if pages:
        print("    paginas:", pages)
    forms = re.findall(r'<(?:select|input)[^>]+name="([^"]+)"', t)
    if forms:
        print("    campos:", sorted(set(forms))[:25])
    ev = re.findall(r'href="([^"]*(?:evento|event|agenda|actividad)[^"]*)"', t)
    print("    enlaces evento (%d):" % len(ev), list(dict.fromkeys(ev))[:10])
    ics = sorted(set(re.findall(r'href="([^"]*(?:ics|ical|rss|feed|\.xml)[^"]*)"', t, re.I)))[:6]
    if ics:
        print("    ics/rss:", ics)
    times = re.findall(r'<time[^>]*datetime="([^"]+)"', t)
    if times:
        print("    <time>:", times[:6])
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt)
    i = len(txt) // 3
    print("    texto:", txt[i:i + 700])


for line in URLS:
    hdr = dict(H)
    u = line
    if line.startswith("JSON "):
        u = line[5:]
        hdr["Accept"] = "application/json"
    try:
        r = requests.get(u, headers=hdr, timeout=30)
    except Exception as e:  # noqa: BLE001
        print("[ERR] %s\n    %s: %s\n" % (u, type(e).__name__, str(e)[:160]))
        continue
    ct = r.headers.get("content-type", "")
    print("[%s] %s len=%d %s%s" % (r.status_code, ct[:40], len(r.content), u, ("  -> " + r.url) if r.url != u else ""))
    if r.status_code >= 400:
        print("    ", r.text[:200].replace("\n", " "), "\n")
        continue
    body = r.text
    if "json" in ct or body.lstrip()[:1] in ("[", "{"):
        try:
            d = r.json()
            if isinstance(d, dict):
                print("    claves:", list(d)[:20])
                for k in ("events", "items", "data", "results", "viewentry"):
                    if isinstance(d.get(k), list) and d[k]:
                        print("    %s: %d; total=%s/%s/%s; primero:" % (k, len(d[k]), d.get("total"), d.get("items_total"), d.get("total_pages")))
                        print("    ", json.dumps(d[k][0], ensure_ascii=False)[:1800])
                        break
                else:
                    print("    ", json.dumps(d, ensure_ascii=False)[:900])
            else:
                print("    lista de %d; primero: %s" % (len(d), json.dumps(d[0], ensure_ascii=False)[:1500] if d else "-"))
        except Exception as e:  # noqa: BLE001
            print("    json mal formado", e, body[:200])
    elif "calendar" in ct or body.startswith("BEGIN:VCALENDAR"):
        print("    VEVENT: %d" % body.count("BEGIN:VEVENT"))
        i = body.find("BEGIN:VEVENT")
        print("    ", body[i:i + 1000].replace("\r\n", " | ").replace("\n", " | "))
    elif "xml" in ct or body.lstrip().startswith("<?xml"):
        print("    items:", body.count("<item"), "entries:", body.count("<entry"))
        print("    ", re.sub(r"\s+", " ", body[:1000]))
    else:
        show_html(body)
    print()
