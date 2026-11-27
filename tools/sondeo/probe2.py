"""Sondeo de fuentes candidatas: estado, tipo y un resumen de lo que devuelve cada URL.

Líneas que empiezan por "J " se piden con Accept: application/json (Plone REST, JSON:API).
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

UA = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"
LINES = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]


def one(line):
    accept = "application/json" if line.startswith("J ") else "*/*"
    url = line[2:] if line.startswith("J ") else line
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": accept}, timeout=20)
    except Exception as e:  # noqa: BLE001
        return "[ERR] %s\n    %s: %s\n" % (url, type(e).__name__, str(e)[:140])
    ct = r.headers.get("content-type", "")[:40]
    body = r.text
    extra = ""
    try:
        d = r.json()
        if isinstance(d, dict) and isinstance(d.get("events"), list):
            ev = d["events"]
            extra = "TRIBE total=%s pages=%s | %s" % (d.get("total"), d.get("total_pages"),
                    " · ".join("%s %s" % (str(e.get("start_date"))[:10], re.sub("<[^>]+>", "", str(e.get("title")))[:50]) for e in ev[:3]))
        elif isinstance(d, dict) and "result" in d and isinstance(d["result"], dict) and "results" in d["result"]:
            extra = "CKAN %d: %s" % (d["result"].get("count", 0), " | ".join(p.get("name", "") for p in d["result"]["results"][:15]))
        elif isinstance(d, dict) and "items" in d:
            extra = "PLONE items_total=%s | %s" % (d.get("items_total"), " · ".join(str(i.get("title"))[:50] for i in d["items"][:4]))
        elif isinstance(d, dict) and "data" in d:
            extra = "JSONAPI/DATA %s" % (str(d["data"])[:250])
        else:
            extra = "JSON " + json.dumps(d)[:250]
    except Exception:  # noqa: BLE001
        n_item = body.count("<item")
        n_vev = body.count("BEGIN:VEVENT")
        n_entry = body.count("<entry")
        title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        gen = re.search(r'<meta name="generator" content="([^"]+)"', body, re.I)
        feeds = re.findall(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*href="([^"]+)"', body, re.I)
        ld = body.count('"@type":"Event"') + body.count('"@type": "Event"')
        tribe = "wp-json/tribe" in body or "tribe-events" in body
        extra = "items=%d vevent=%d entries=%d ldEvents=%d tribe=%s gen=%s title=%s feeds=%s" % (
            n_item, n_vev, n_entry, ld, tribe, gen.group(1)[:30] if gen else "-",
            (title.group(1).strip()[:60] if title else "-"), feeds[:3])
    return "[%s] %s len=%d %s\n    %s\n" % (r.status_code, ct, len(r.content), url, extra)


with ThreadPoolExecutor(12) as ex:
    for out in ex.map(one, LINES):
        print(out, flush=True)
