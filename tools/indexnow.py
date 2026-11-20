#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Avisa por IndexNow (Bing, y con él Copilot y ChatGPT Search; también Yandex, Seznam, Naver…) de las
páginas nuevas o cambiadas, para que se rastreen el mismo día en vez de esperar a que lean el sitemap.

    python3 tools/indexnow.py site [--days 1] [--dry-run]

Lee los sitemaps ya generados y envía las URL cuyo lastmod es de hoy o de los últimos `--days` días (hora de
Madrid). El lastmod solo cambia cuando cambia la página (data/sitemap_state.json), así que no se reenvían
páginas iguales. La clave es el archivo site/<clave>.txt, que contiene la propia clave: no es un secreto,
IndexNow la publica a propósito para comprobar que el aviso viene del dueño del dominio.

Google no usa IndexNow: para Google está el sitemap dado de alta en Search Console.
No falla nunca la publicación: si IndexNow no responde, lo dice en el log y sale con 0.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH = 10000  # máximo de URL por envío según el protocolo


def madrid_today():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Madrid")).date()
    except Exception:
        return date.today()


def find_key(site_dir):
    """La clave es el nombre de site/<32 caracteres hex>.txt cuyo contenido es esa misma clave."""
    for fn in sorted(os.listdir(site_dir)):
        m = re.match(r"^([0-9a-f]{32})\.txt$", fn)
        if m:
            with open(os.path.join(site_dir, fn), encoding="utf-8") as fh:
                if fh.read().strip() == m.group(1):
                    return m.group(1)
    return None


def changed_urls(site_dir, since):
    """URL de los sitemaps (índice y trozos) con lastmod >= since (AAAA-MM-DD), sin repetir."""
    def parse(fn):
        try:
            return ET.parse(os.path.join(site_dir, fn)).getroot()
        except (OSError, ET.ParseError):
            return None
    top = parse("sitemap.xml")
    if top is None:
        return []
    files = ["sitemap.xml"]
    if top.tag == NS + "sitemapindex":
        files = [urlsplit(loc.text.strip()).path.lstrip("/") for loc in top.iter(NS + "loc")]
    out, seen = [], set()
    for fn in files:
        node = top if fn == "sitemap.xml" else parse(fn)
        if node is None:
            continue
        for url in node.iter(NS + "url"):
            loc = (url.findtext(NS + "loc") or "").strip()
            lastmod = (url.findtext(NS + "lastmod") or "")[:10]
            if loc and lastmod >= since and loc not in seen:
                seen.add(loc)
                out.append(loc)
    return out


def submit(urls, key, host, log=print):
    """Envía en tandas de 10.000. Devuelve el número de URL aceptadas (respuesta 200 o 202)."""
    ok = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        body = json.dumps({"host": host, "key": key, "keyLocation": "https://%s/%s.txt" % (host, key),
                           "urlList": chunk}).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                log("IndexNow: %d URL enviadas, respuesta %d" % (len(chunk), r.status))
                ok += len(chunk) if r.status in (200, 202) else 0
        except urllib.error.HTTPError as ex:
            log("IndexNow: respuesta %d (%s) para %d URL" % (ex.code, ex.reason, len(chunk)))
        except Exception as ex:  # red caída, DNS…: no es motivo para fallar la publicación
            log("IndexNow: no se pudo enviar (%s)" % ex)
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("site", nargs="?", default="site")
    ap.add_argument("--days", type=int, default=1, help="también las cambiadas en los N días anteriores (1: hoy y ayer)")
    ap.add_argument("--site-url", default=os.environ.get("PLANIKA_SITE_URL", "https://planikaapp.com"))
    ap.add_argument("--dry-run", action="store_true", help="solo listar lo que se enviaría")
    args = ap.parse_args(argv)
    key = find_key(args.site)
    if not key:
        print("IndexNow: no hay archivo de clave en %s; no se envía nada" % args.site)
        return 0
    since = (madrid_today() - timedelta(days=args.days)).isoformat()
    urls = changed_urls(args.site, since)
    host = urlsplit(args.site_url).netloc
    urls = [u for u in urls if urlsplit(u).netloc == host]
    print("IndexNow: %d URL nuevas o cambiadas desde el %s" % (len(urls), since))
    if args.dry_run or not urls:
        for u in urls[:20]:
            print("  ", u)
        return 0
    submit(urls, key, host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
