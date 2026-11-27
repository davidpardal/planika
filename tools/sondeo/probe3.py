"""Sondeo detallado. Prefijos: "J " -> JSON (imprime 3000 caracteres); "D " -> HTML (enlaces y pistas)."""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

UA = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"
LINES = [l.rstrip("\n") for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
PAT = re.compile(r"agenda|event|evento|esdeveniment|activitat|actividad|ical|\.ics|rss|feed|json|api", re.I)


def one(line):
    mode, url = line[:1], line[2:]
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "application/json" if mode == "J" else "*/*"}, timeout=25)
    except Exception as e:  # noqa: BLE001
        return "### [ERR] %s %s: %s\n" % (url, type(e).__name__, str(e)[:140])
    head = "### [%s] %s len=%d %s\n" % (r.status_code, r.headers.get("content-type", "")[:40], len(r.content), url)
    body = r.text
    if mode == "J":
        try:
            return head + json.dumps(r.json(), ensure_ascii=False)[:3500] + "\n"
        except Exception:  # noqa: BLE001
            return head + body[:800] + "\n"
    hrefs = []
    for h in re.findall(r'(?:href|src|action|data-[a-z-]+)="([^"]+)"', body):
        if PAT.search(h) and h not in hrefs:
            hrefs.append(h)
    ld = re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', body, re.S)
    apis = sorted(set(re.findall(r'["\'](/[a-zA-Z0-9_/\-]*(?:api|json|ajax|views/ajax)[a-zA-Z0-9_/\-.?=&]*)["\']', body)))[:20]
    dates = re.findall(r"\b\d{1,2}/\d{1,2}/20\d\d\b|\b20\d\d-\d\d-\d\d\b", body)
    out = [head, "  enlaces(%d): %s" % (len(hrefs), " | ".join(hrefs[:45])),
           "  apis: %s" % apis, "  fechas: %d ej=%s" % (len(dates), dates[:6])]
    for b in ld[:3]:
        out.append("  ld: " + re.sub(r"\s+", " ", b)[:600])
    return "\n".join(out) + "\n"


with ThreadPoolExecutor(10) as ex:
    for o in ex.map(one, LINES):
        print(o, flush=True)
