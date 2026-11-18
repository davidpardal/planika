# -*- coding: utf-8 -*-
"""SEO técnico: criterio de calidad de las fichas, sitemaps con lastmod real y robots.txt.

- Las fichas con muy poca información (sin descripción, sin lugar, sin hora…) se publican igual para quien llega
  desde la app, pero con noindex,follow y fuera del sitemap: así Google dedica el rastreo a las páginas útiles.
- El lastmod de cada URL solo cambia cuando cambia su contenido. Se guarda entre ejecuciones en
  data/sitemap_state.json (huella del contenido y fecha del último cambio).
- sitemap.xml es un índice: un sitemap para las páginas de la web y otro (o varios) para las fichas,
  para poder ver por separado en Search Console qué se indexa de cada tipo.
"""
import hashlib
import json
import os
import re
from xml.sax.saxutils import escape as _xml

from .util import iso, today

MIN_SCORE = 2          # puntuación mínima para que una ficha sea indexable
SITEMAP_MAX = 45000    # por debajo del límite de 50.000 URL por archivo
_UPD = re.compile(r'<span class="upd">.*?</span>', re.S)


def quality_score(e):
    """Cuánta información útil tiene la ficha de un plan (0-6), solo con datos que vienen de la fuente."""
    d = len((e.get("description") or "").strip())
    s = 2 if d >= 120 else (1 if d >= 40 else 0)
    if e.get("venue") or e.get("address"):
        s += 1
    if e.get("time"):
        s += 1
    if re.match(r"^https?://", e.get("image") or "", re.I):
        s += 1
    if e.get("tickets_url") or e.get("price") or e.get("free"):
        s += 1
    return s


def is_indexable(e):
    return quality_score(e) >= MIN_SCORE


def digest(text):
    """Huella del contenido de una página; ignora los sellos de "actualizado el…" (<span class="upd">)."""
    return hashlib.sha1(_UPD.sub("", text).encode("utf-8")).hexdigest()[:12]


def load_state(path):
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _urlset(site_url, urls):
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path, lastmod in urls:
        out.append("<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>" % (site_url, _xml(path), lastmod))
    out.append("</urlset>\n")
    return "\n".join(out)


def write_sitemaps(site_dir, entries, site_url, state_path=None, day=None):
    """Escribe sitemap.xml (índice) y sitemap-<grupo>.xml.

    entries: lista de (ruta relativa, grupo, huella). La portada es la ruta "".
    Devuelve [(archivo, número de URL)]."""
    day = day or iso(today())
    old = load_state(state_path)
    state, groups = {}, {}
    for path, group, h in entries:
        if path in state:
            continue  # sin duplicados
        prev = old.get(path) or {}
        lastmod = prev.get("d") if prev.get("h") == h and prev.get("d") else day
        state[path] = {"h": h, "d": lastmod}
        groups.setdefault(group, []).append((path, lastmod))
    for fn in os.listdir(site_dir):
        if re.match(r"^sitemap-[a-z0-9-]+\.xml$", fn):
            os.remove(os.path.join(site_dir, fn))
    written, index = [], []
    for group, urls in groups.items():
        parts = [urls[i:i + SITEMAP_MAX] for i in range(0, len(urls), SITEMAP_MAX)]
        for n, chunk in enumerate(parts, 1):
            fn = "sitemap-%s.xml" % group if len(parts) == 1 else "sitemap-%s-%d.xml" % (group, n)
            with open(os.path.join(site_dir, fn), "w", encoding="utf-8") as fh:
                fh.write(_urlset(site_url, chunk))
            written.append((fn, len(chunk)))
            index.append((fn, max(lm for _, lm in chunk)))
    with open(os.path.join(site_dir, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for fn, lastmod in index:
            fh.write("<sitemap><loc>%s/%s</loc><lastmod>%s</lastmod></sitemap>\n" % (site_url, fn, lastmod))
        fh.write("</sitemapindex>\n")
    if state_path:
        os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
        # Una URL por línea: el commit diario del workflow solo cambia las líneas de las páginas que cambian.
        with open(state_path, "w", encoding="utf-8") as fh:
            fh.write("{\n" + ",\n".join(json.dumps(k, ensure_ascii=False) + ":" + json.dumps(v, separators=(",", ":"), sort_keys=True)
                                         for k, v in sorted(state.items())) + "\n}\n")
    return written


def robots_txt(site_url):
    return ("User-agent: *\n"
            "Allow: /\n"
            "# La app guarda búsqueda y filtros en parámetros (?e=, ?prov=, ?cat=, ?q=…) sobre la misma página,\n"
            "# que ya tiene canonical a la portada: son navegación facetada y no hace falta rastrearlos.\n"
            "Disallow: /?\n"
            "\n"
            "Sitemap: %s/sitemap.xml\n" % site_url)
