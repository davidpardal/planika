#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comprobación SEO de un sitio Planika ya generado (sin red).

    python3 tools/seo_check.py site [--site-url https://planikaapp.com]

Revisa: XML de los sitemaps, URLs absolutas HTTPS y sin duplicados, que cada URL del sitemap exista, sea
indexable y tenga canonical autorreferencial; robots.txt; enlaces internos rotos; JSON-LD que se pueda leer;
profundidad de clics desde la portada; títulos duplicados. Sale con código 1 si encuentra errores.
"""
import argparse
import collections
import html
import json
import os
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_A = re.compile(r'<a\s[^>]*href="([^"]+)"')


def _read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8") as fh:
        return fh.read()


def _sitemap_urls(root, site_url, errors):
    """Lee sitemap.xml (índice o lista) y devuelve [(loc, lastmod)]."""
    def parse(rel):
        try:
            return ET.fromstring(_read(root, rel).encode("utf-8"))
        except (OSError, ET.ParseError) as ex:
            errors.append("sitemap %s: no se puede leer (%s)" % (rel, ex))
            return None
    top = parse("sitemap.xml")
    if top is None:
        return []
    files = ["sitemap.xml"]
    if top.tag == NS + "sitemapindex":
        files = []
        for loc in top.iter(NS + "loc"):
            u = loc.text.strip()
            if not u.startswith(site_url + "/"):
                errors.append("índice de sitemaps: %s no está en %s" % (u, site_url))
            files.append(urlsplit(u).path.lstrip("/"))
    out = []
    for rel in files:
        node = top if rel == "sitemap.xml" else parse(rel)
        if node is None:
            continue
        for url in node.iter(NS + "url"):
            loc = (url.findtext(NS + "loc") or "").strip()
            lm = (url.findtext(NS + "lastmod") or "").strip()
            if not re.match(r"^\d{4}-\d\d-\d\d", lm):
                errors.append("sitemap: %s sin lastmod válido" % loc)
            out.append((loc, lm))
    return out


def check(root, site_url="https://planikaapp.com"):
    errors, stats = [], {}
    pages = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.endswith(".html"):
                rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
                pages[rel] = _read(root, rel)

    # ---- sitemaps
    urls = _sitemap_urls(root, site_url, errors)
    locs = [u for u, _ in urls]
    stats["sitemap_urls"] = len(locs)
    for u, n in collections.Counter(locs).items():
        if n > 1:
            errors.append("sitemap: URL repetida %s" % u)
    in_sitemap = set()
    for u in locs:
        if not u.startswith(site_url + "/"):
            errors.append("sitemap: URL que no es absoluta HTTPS del dominio: %s" % u)
            continue
        rel = urlsplit(u).path.lstrip("/") or "index.html"
        in_sitemap.add(rel)
        if rel not in pages:
            errors.append("sitemap: %s no existe en el sitio generado" % u)

    # ---- robots.txt
    try:
        robots = _read(root, "robots.txt")
        if "Sitemap: %s/sitemap.xml" % site_url not in robots:
            errors.append("robots.txt: no declara %s/sitemap.xml" % site_url)
        for line in robots.splitlines():
            if re.match(r"(?i)^disallow:\s*/\s*$", line):
                errors.append("robots.txt: bloquea todo el sitio")
            if re.match(r"(?i)^disallow:\s*/.*\.(css|js)", line):
                errors.append("robots.txt: bloquea CSS o JS (%s)" % line)
    except OSError:
        errors.append("robots.txt: no existe")

    # ---- páginas
    edges, info = {}, {}
    broken = collections.Counter()
    for rel, s in pages.items():
        can = re.search(r'<link rel="canonical" href="([^"]+)"', s)
        rob = re.search(r'<meta name="robots" content="([^"]+)"', s)
        ttl = re.search(r"<title>(.*?)</title>", s, re.S)
        noindex = bool(rob and "noindex" in rob.group(1))
        info[rel] = {"can": can.group(1) if can else None, "noindex": noindex,
                     "title": html.unescape(ttl.group(1)).strip() if ttl else ""}
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(block)
            except ValueError as ex:
                errors.append("%s: JSON-LD no válido (%s)" % (rel, ex))
        out = set()
        for h in _A.findall(s):
            h = html.unescape(h)
            if h.startswith(site_url):
                h = "/" + h[len(site_url):].lstrip("/")
            elif re.match(r"^[a-z][a-z0-9+.-]*:", h, re.I) or h.startswith(("#", "//")):
                continue  # enlaces externos, mailto:, anclas
            elif "{{" in h or "{%" in h:
                continue  # etiqueta que rellena el servicio de envío (la baja del boletín: «{{ unsubscribe }}»)
            path = h.split("#")[0].split("?")[0]
            if path.startswith("/"):
                tgt = path.lstrip("/")
            else:
                tgt = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path)) if path else rel
            if tgt in ("", "."):
                tgt = "index.html"
            elif tgt.endswith("/"):
                tgt += "index.html"
            if tgt.startswith(".."):
                broken[(rel, h)] += 1
            elif tgt not in pages and not os.path.exists(os.path.join(root, tgt)):
                broken[(rel, h)] += 1
            else:
                out.add(tgt)
        edges[rel] = out
    for (rel, h), _ in broken.items():
        errors.append("enlace roto en %s → %s" % (rel, h))
    for rel in in_sitemap:
        if rel in info:
            exp = site_url + "/" + ("" if rel == "index.html" else rel)
            if info[rel]["can"] != exp:
                errors.append("%s: canonical %s (debería ser %s)" % (rel, info[rel]["can"], exp))
            if info[rel]["noindex"]:
                errors.append("%s: está en el sitemap pero tiene noindex" % rel)
    for rel, i in info.items():
        if i["can"] and not i["can"].startswith(site_url + "/"):
            errors.append("%s: canonical fuera del dominio (%s)" % (rel, i["can"]))

    # ---- profundidad desde la portada y títulos
    depth = {"index.html": 0}
    queue = ["index.html"]
    for x in queue:
        for y in edges.get(x, ()):
            if y not in depth and y in pages:
                depth[y] = depth[x] + 1
                queue.append(y)
    unreachable = sorted(r for r in in_sitemap if r not in depth)
    if unreachable:
        errors.append("%d URLs del sitemap no se alcanzan con enlaces desde la portada (p. ej. %s)" % (len(unreachable), unreachable[0]))
    d = sorted(depth.get(r, 99) for r in in_sitemap)
    stats["depth_max"] = d[-1] if d else 0
    stats["depth_p90"] = d[int(len(d) * .9)] if d else 0
    stats["html_pages"] = len(pages)
    stats["noindex_pages"] = sum(1 for i in info.values() if i["noindex"])
    titles = collections.Counter(info[r]["title"] for r in in_sitemap if r in info)
    stats["duplicate_title_groups"] = sum(1 for t, n in titles.items() if n > 1)
    return errors, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("site", nargs="?", default="site")
    ap.add_argument("--site-url", default=os.environ.get("PLANIKA_SITE_URL") or "https://planikaapp.com")
    args = ap.parse_args()
    errors, stats = check(args.site, args.site_url.rstrip("/"))
    print("Comprobación SEO de %s" % args.site)
    for k, v in stats.items():
        print("  %s: %s" % (k, v))
    for e in errors[:200]:
        print("ERROR " + e)
    if len(errors) > 200:
        print("… y %d errores más" % (len(errors) - 200))
    print("%d errores" % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
