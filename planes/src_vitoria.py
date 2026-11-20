# -*- coding: utf-8 -*-
"""Ayuntamiento de Vitoria-Gasteiz: agenda de actividades culturales (RSS municipal).

El RSS repite cada actividad una vez por día; se agrupan por identificador en un
único evento con rango de fechas. El feed no trae lugar ni descripción.
"""
import html
import re
import time
from datetime import timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

from .classify import classify
from .util import event, http_text, iso, today

NAME = "Ayuntamiento de Vitoria-Gasteiz"
URL = "https://www.vitoria-gasteiz.org/we001/was/rssAction.do?idioma=es&accion=actividadesCuadroMando&claveTema=&claveArea=38"
HOME = "https://www.vitoria-gasteiz.org/wb021/was/we001Action.do?idioma=es&accionWe001=ficha&accion=calMunicipales&claveArea=38"
MADRID = ZoneInfo("Europe/Madrid")
MAX_DAYS = 120  # actividades permanentes (aulas, clubes) fuera


def parse(text):
    groups = {}
    for item in re.findall(r"<item>(.*?)</item>", text, re.S):
        def tag(name):
            m = re.search(r"<%s[^>]*>(.*?)</%s>" % (name, name), item, re.S)
            return re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1)).strip() if m else ""
        guid, title, link = html.unescape(tag("guid")), html.unescape(tag("title")), html.unescape(tag("link"))
        try:
            dt = parsedate_to_datetime(tag("pubDate")).astimezone(MADRID)
        except (TypeError, ValueError):
            continue
        if not guid or not title:
            continue
        g = groups.setdefault(guid, {"title": title, "link": link, "dts": []})
        g["dts"].append(dt)
    out = []
    limit = iso(today() - timedelta(days=1))
    for guid, g in groups.items():
        first, last = min(g["dts"]), max(g["dts"])
        if last.strftime("%Y-%m-%d") < limit or (last - first).days > MAX_DAYS:
            continue
        multi = first.date() != last.date()
        ev = event(
            NAME, guid, g["title"], first.strftime("%Y-%m-%d"), end=last.strftime("%Y-%m-%d"),
            time="" if multi else first.strftime("%H:%M"), category=classify([], g["title"], ""),
            province_code="01", city="Vitoria-Gasteiz", url=g["link"] or HOME,
        )
        if ev:
            out.append(ev)
    return out


def fetch(log, waits=(20, 60)):
    """El RSS solo trae las actividades del día: si la web municipal no responde a la primera, se insiste
    (con esperas largas) para no dejar Vitoria-Gasteiz sin planes hasta la siguiente actualización."""
    for i, wait in enumerate(tuple(waits) + (None,)):
        try:
            text = http_text(URL, encoding="utf-8", timeout=(30, 90))
            break
        except Exception as exc:  # noqa: BLE001
            if wait is None:
                raise
            log("%s: sin respuesta (%s), nuevo intento en %ds" % (NAME, exc.__class__.__name__, wait))
            time.sleep(wait)
    out = parse(text)
    log("%s: %d eventos" % (NAME, len(out)))
    return out
