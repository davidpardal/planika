# -*- coding: utf-8 -*-
"""Xunta de Galicia: Axenda de Cultura de Galicia (calendario iCalendar)."""
import re

import html as _html

from .classify import classify
from .util import event, http_text, parse_date, parse_ics, strip_html

NAME = "Axenda de Cultura de Galicia"
# El portal cultura.gal sirve los mismos feeds que abertos.xunta.gal y responde desde más redes (GitHub incluida)
URL = "https://www.cultura.gal/gl/ical"
URL_ALT = ("https://abertos.xunta.gal/catalogo/cultura-ocio-deporte/-/dataset/0045/axenda-cultura-galicia/"
           "102/acceso-aos-datos.calendario")
HOME = "https://www.cultura.gal/gl/axenda"
RSS = "https://www.cultura.gal/gl/rssaxenda"
BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def fetch(log):
    text = None
    for url in (URL, URL_ALT):
        try:
            text = http_text(url, encoding="utf-8", headers=BROWSER, timeout=(30, 120), retries=2)
            break
        except Exception as exc:  # noqa: BLE001
            log("%s: calendario no disponible en %s (%s)" % (NAME, url.split("/")[2], exc.__class__.__name__))
    if text is None:
        return _fetch_rss(log)
    out = []
    for v in parse_ics(text):
        loc = v.get("LOCATION") or ""
        # "Biblioteca Pública de Lugo - Lugo   - Lugo"  ->  lugar, concello, provincia
        parts = [p.strip() for p in loc.split(" - ") if p.strip()]
        venue = parts[0] if parts else ""
        city = parts[1] if len(parts) > 1 else ""
        prov = parts[-1] if len(parts) > 2 else ""
        desc = v.get("DESCRIPTION") or ""
        m = re.search(r"(Espect[aá]culo|Exposici[oó]n|Concerto|Cine|Obradoiro|Conferencia|Festival|Teatro|Danza|M[uú]sica|Literatura|Infantil)[^\n]*", desc)
        subtype = m.group(0).strip()[:60] if m else ""
        start = (v.get("DTSTART") or "")[:8]
        start = "%s-%s-%s" % (start[:4], start[4:6], start[6:8]) if len(start) == 8 else ""
        end = (v.get("DTEND") or "")[:8]
        end = "%s-%s-%s" % (end[:4], end[4:6], end[6:8]) if len(end) == 8 else start
        t = (v.get("DTSTART") or "")
        tm = "%s:%s" % (t[9:11], t[11:13]) if "T" in t and len(t) >= 13 else ""
        ev = event(
            NAME, v.get("UID"), v.get("SUMMARY"), start, end=end, time=tm, description=desc.split("http")[0],
            subtype=subtype, category=classify([subtype], v.get("SUMMARY"), desc),
            province=prov, city=city, venue=venue, url=v.get("URL") or HOME,
        )
        if ev:
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out


def _fetch_rss(log):
    """Alternativa con el RSS: la fecha va en pubDate y el lugar en la primera línea de la descripción."""
    from email.utils import parsedate_to_datetime
    text = http_text(RSS, encoding="utf-8", headers=BROWSER, timeout=(30, 120), retries=4)
    out = []
    for item in re.findall(r"<item>(.*?)</item>", text, re.S):
        def tag(name):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), item, re.S)
            return _html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip() if m else ""
        title, link, raw = tag("title"), tag("link"), tag("description")
        try:
            dt = parsedate_to_datetime(tag("pubDate"))
        except (TypeError, ValueError):
            continue
        start = dt.strftime("%Y-%m-%d")
        tm = dt.strftime("%H:%M") if dt.strftime("%H:%M") != "00:00" else ""
        img = re.search(r'src="([^"]+)"', raw)
        info = re.search(r'class="info">(.*?)</div>', raw, re.S)
        lines = [strip_html(x) for x in re.split(r"<br\s*/?>", info.group(1))] if info else []
        lines = [x for x in lines if x]
        loc = lines[1] if len(lines) > 1 else ""
        parts = [x.strip() for x in loc.split(" - ") if x.strip()]
        desc = strip_html(info.group(1), 300) if info else strip_html(raw, 300)
        ev = event(NAME, link or title, title, start, time=tm, description=desc, category=classify([], title, desc),
                   venue=parts[0] if parts else "", city=parts[1] if len(parts) > 1 else "",
                   province=parts[-1] if len(parts) > 2 else _prov_from_text(loc), url=link or HOME,
                   image=img.group(1) if img else "")
        if ev:
            out.append(ev)
    log("%s: %d eventos (RSS)" % (NAME, len(out)))
    return out


def _prov_from_text(text):
    for p in ("A Coruña", "Lugo", "Ourense", "Pontevedra"):
        if p.lower() in (text or "").lower():
            return p
    return ""
