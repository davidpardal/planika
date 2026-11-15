# -*- coding: utf-8 -*-
"""Agendas de ayuntamientos y diputaciones que publican sus eventos con la API pública de
«The Events Calendar» (WordPress): /wp-json/tribe/events/v1/events.

Para añadir un municipio basta una línea en SITES; comprobar antes que
https://<web>/wp-json/tribe/events/v1/events devuelve {"events": [...]}.
"""
import html

from .classify import classify
from .util import event, http_json, iso, today

NAME = "Agendas municipales"
HOME = "https://github.com/davidpardal/planika#fuentes"
# (nombre que se muestra como fuente, web, ciudad por defecto, código de provincia)
SITES = [
    ("Ayuntamiento de Mérida", "https://merida.es", "Mérida", "06"),
    ("Ayuntamiento de Teruel", "https://www.teruel.es", "Teruel", "44"),
    ("Ayuntamiento de Ejea de los Caballeros", "https://www.ejea.es", "Ejea de los Caballeros", "50"),
    ("Ayuntamiento de Siero", "https://www.ayto-siero.es", "Siero", "33"),
    ("Ayuntamiento de Puertollano", "https://www.puertollano.es", "Puertollano", "13"),
    ("Diputación de Albacete", "https://web.dipualba.es", "", "02"),
    ("Ayuntamiento de Elche", "https://www.elche.es", "Elche", "03"),
    ("Ayuntamiento de Orihuela", "https://www.orihuela.es", "Orihuela", "03"),
    ("Teatro Chapí de Villena", "https://www.teatrochapi.com", "Villena", "03"),
    ("Ajuntament de Torrent", "https://www.torrent.es", "Torrent", "46"),
]
SOURCE_NAMES = [s[0] for s in SITES]
PER_PAGE = 50
MAX_PAGES = 8


def parse(label, rows, city, code, home=""):
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        venue = r.get("venue") if isinstance(r.get("venue"), dict) else {}
        image = r.get("image") if isinstance(r.get("image"), dict) else {}
        cats = [html.unescape(str(c.get("name") or "")) for c in (r.get("categories") or []) if isinstance(c, dict)]
        start = str(r.get("start_date") or "")
        tm = "" if r.get("all_day") else start[11:16]
        title = html.unescape(str(r.get("title") or ""))
        cost = html.unescape(str(r.get("cost") or ""))
        ev = event(
            label, r.get("global_id") or r.get("id"), title, start[:10], end=str(r.get("end_date") or "")[:10], time=tm,
            description=r.get("description") or r.get("excerpt"), subtype=cats[0] if cats else "",
            category=classify(cats, title, r.get("description")),
            province_code=code, city=html.unescape(str(venue.get("city") or "")) or city,
            venue=html.unescape(str(venue.get("venue") or "")), address=venue.get("address"),
            lat=venue.get("geo_lat"), lon=venue.get("geo_lng"), price=cost,
            url=r.get("url") or home, tickets_url=r.get("website") or "", image=image.get("url") or "",
        )
        if ev:
            out.append(ev)
    return out


def fetch_site(label, root, city, code):
    rows = []
    for page in range(1, MAX_PAGES + 1):
        data = http_json(root + "/wp-json/tribe/events/v1/events",
                         params={"per_page": PER_PAGE, "page": page, "start_date": iso(today())}, retries=2, timeout=(15, 60))
        rows.extend(data.get("events") or [])
        if page >= int(data.get("total_pages") or 1):
            break
    return parse(label, rows, city, code, root)


def fetch(log):
    out, failed = [], []
    for label, root, city, code in SITES:
        try:
            evs = fetch_site(label, root, city, code)
        except Exception as exc:  # noqa: BLE001 - una web caída no debe tumbar las demás
            failed.append(label)
            log("%s: %s no disponible (%s)" % (NAME, label, exc.__class__.__name__))
            continue
        out.extend(evs)
    if failed and not out:
        raise RuntimeError("ninguna de las %d webs ha respondido" % len(SITES))
    log("%s: %d eventos de %d webs%s" % (NAME, len(out), len(SITES) - len(failed),
                                        (" (sin respuesta: %s)" % ", ".join(failed)) if failed else ""))
    return out
