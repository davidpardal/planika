# -*- coding: utf-8 -*-
"""Ayuntamiento de Murcia: próximos eventos de eventos.murcia.es (RSS)."""
import html
import re
from email.utils import parsedate_to_datetime

from .classify import classify
from .util import event, http_text, strip_html

NAME = "Ayuntamiento de Murcia"
URLS = ("https://eventos.murcia.es/rss/category/0/next.rss", "https://eventos.murcia.es/rss/next.rss")
HOME = "https://eventos.murcia.es/"


def parse(text):
    out = []
    for item in re.findall(r"<item>(.*?)</item>", text, re.S):
        def tag(name):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), item, re.S)
            return re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)).strip() if m else ""
        title, link, raw = html.unescape(tag("title")), tag("link"), tag("description")
        try:
            dt = parsedate_to_datetime(tag("pubDate"))
        except (TypeError, ValueError):
            continue
        # El primer párrafo es el lugar: "Recinto, calle, pedanía, España"
        m = re.match(r"\s*<p>(.*?)</p>(.*)", raw, re.S)
        place, body = (strip_html(m.group(1)), m.group(2)) if m else ("", raw)
        parts = [p.strip() for p in place.split(",") if p.strip() and p.strip() != "España"]
        ev = event(
            NAME, link or title, title, dt.strftime("%Y-%m-%d"), time=dt.strftime("%H:%M"), description=body,
            category=classify([], title, strip_html(body, 300)), province_code="30",
            city=parts[-1] if len(parts) > 1 else "Murcia", venue=parts[0] if parts else "",
            address=", ".join(parts[1:-1]), url=link.replace("http://", "https://") or HOME,
        )
        if ev:
            out.append(ev)
    return out


def fetch(log):
    last = None
    for url in URLS:
        try:
            out = parse(http_text(url, encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        if out:
            log("%s: %d eventos" % (NAME, len(out)))
            return out
    if last:
        raise last
    log("%s: 0 eventos" % NAME)
    return []
