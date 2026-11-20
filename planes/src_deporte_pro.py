# -*- coding: utf-8 -*-
"""Deporte profesional con fuentes abiertas, solo partidos de equipos españoles en casa.

- LaLiga: openfootball/football.json (dominio público). No trae estadio ni, a veces, hora.
- Euroliga y EuroCup: API pública de euroleague.net (calendario y equipos), con pabellón y hora.
"""
import html
import json
import os
import re
from datetime import datetime, timedelta

from .util import event, http_json, http_text, iso, today

NAME = "Deporte profesional (LaLiga, Euroliga, EuroCup)"
# Fechas y horas oficiales comprobadas a mano: openfootball pone cada jornada en su domingo y sin hora.
FIXES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "horarios_partidos.json")
HOME = "https://www.laliga.com/"
LALIGA_URL = "https://raw.githubusercontent.com/openfootball/football.json/master/%s/es.1.json"
EURO_URL = "https://api-live.euroleague.net/v1/%s?seasonCode=%s%d"
EURO_COMPS = {"E": ("Euroliga", "https://www.euroleaguebasketball.net/euroleague/"),
              "U": ("EuroCup", "https://www.euroleaguebasketball.net/eurocup/")}

# club -> (ciudad, código de provincia)
LALIGA_CLUBS = {
    "Athletic Club": ("Bilbao", "48"), "CA Osasuna": ("Pamplona", "31"), "Club Atlético de Madrid": ("Madrid", "28"),
    "Deportivo Alavés": ("Vitoria-Gasteiz", "01"), "Elche CF": ("Elche", "03"), "FC Barcelona": ("Barcelona", "08"),
    "Getafe CF": ("Getafe", "28"), "Levante UD": ("Valencia", "46"), "Málaga CF": ("Málaga", "29"),
    "RC Celta de Vigo": ("Vigo", "36"), "RC Deportivo La Coruña": ("A Coruña", "15"),
    "RCD Espanyol de Barcelona": ("Cornellà de Llobregat", "08"), "Rayo Vallecano de Madrid": ("Madrid", "28"),
    "Real Betis Balompié": ("Sevilla", "41"), "Real Madrid CF": ("Madrid", "28"),
    "Real Racing Club de Santander": ("Santander", "39"), "Real Sociedad de Fútbol": ("San Sebastián", "20"),
    "Sevilla FC": ("Sevilla", "41"), "Valencia CF": ("Valencia", "46"), "Villarreal CF": ("Villarreal", "12"),
    "Real Oviedo": ("Oviedo", "33"), "RCD Mallorca": ("Palma", "07"), "Girona FC": ("Girona", "17"),
    "UD Las Palmas": ("Las Palmas de Gran Canaria", "35"), "Real Valladolid CF": ("Valladolid", "47"),
    "CD Leganés": ("Leganés", "28"), "Cádiz CF": ("Cádiz", "11"), "Granada CF": ("Granada", "18"),
    "UD Almería": ("Almería", "04"), "Real Zaragoza": ("Zaragoza", "50"), "Real Sporting de Gijón": ("Gijón", "33"),
}
EURO_CLUBS = {  # código de club de euroleague.net -> (ciudad, provincia)
    "BAS": ("Vitoria-Gasteiz", "01"), "BAR": ("Barcelona", "08"), "MAD": ("Madrid", "28"), "PAM": ("Valencia", "46"),
    "MAN": ("Manresa", "08"), "TNF": ("San Cristóbal de La Laguna", "38"), "BGS": ("Burgos", "09"),  # añadir aquí otros clubes españoles
}


def load_fixes(path=FIXES_PATH):
    """{"local|visitante": {"date", "time"}} de LaLiga, de data/horarios_partidos.json ({} si no está)."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("laliga") or {}
    except (OSError, ValueError):
        return {}


def parse_laliga(data, t0=None, season="2026/27", fixes=None):
    t0 = t0 or iso(today())
    fixes = fixes or {}
    out = []
    for m in data.get("matches") or []:
        home, away = m.get("team1"), m.get("team2")
        nominal = m.get("date") or ""
        fix = fixes.get("%s|%s" % (home, away)) or {}
        date = fix.get("date") or nominal  # día oficial si LaLiga ya lo fijó
        if date < t0 or (m.get("score") or {}).get("ft"):
            continue
        city, prov = LALIGA_CLUBS.get(home, ("", ""))
        if not city:
            continue
        rnd = re.sub(r"\D", "", m.get("round") or "")
        ev = event(  # el id sigue la fecha de openfootball: la ficha no cambia de dirección al fijarse el día
            NAME, "laliga-%s-%s-%s" % (nominal, home, away), "%s - %s" % (home, away), date,
            time=fix.get("time") or m.get("time") or "",
            description="LaLiga%s. Fútbol profesional en %s." % (", jornada " + rnd if rnd else "", city),
            subtype="LaLiga", category="deporte", city=city, province_code=prov, url=HOME,
        )
        if ev:
            out.append(ev)
    return out


def parse_euro(schedule_xml, teams_xml, comp, t0=None):
    t0 = t0 or iso(today())
    league, url = EURO_COMPS[comp]
    names = {code: html.unescape(re.sub(r"\s+", " ", n)) for code, n in
             re.findall(r'<club code="(\w+)".*?<name>(.*?)</name>', teams_xml, re.S)}
    out = []
    for item in re.findall(r"<item>(.*?)</item>", schedule_xml, re.S):
        def tag(name):
            m = re.search(r"<%s>(.*?)</%s>" % (name, name), item, re.S)
            return html.unescape(m.group(1).strip()) if m else ""
        home = tag("homecode")
        if home not in EURO_CLUBS or tag("played") == "true":
            continue
        try:
            date = datetime.strptime(tag("date"), "%b %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            continue
        if date < t0:
            continue
        city, prov = EURO_CLUBS[home]
        arena = tag("arenaname").title()
        ev = event(
            NAME, "%s-%s" % (comp, tag("gamecode")), "%s - %s" % (names.get(home, tag("hometeam").title()),
                                                                  names.get(tag("awaycode"), tag("awayteam").title())),
            date, time=tag("startime"),
            description="%s, jornada %s. Baloncesto en %s." % (league, tag("gameday") or "-", arena or city),
            subtype=league, category="deporte", city=city, province_code=prov, venue=arena, url=url,
        )
        if ev:
            out.append(ev)
    return out


def fetch(log, days=180):
    out, t0 = {}, iso(today())
    horizon = iso(today() + timedelta(days=days))
    y = today().year if today().month >= 7 else today().year - 1
    for season in ("%d-%02d" % (y, (y + 1) % 100),):
        try:
            fixes = load_fixes()
            for ev in parse_laliga(http_json(LALIGA_URL % season, retries=2), t0, fixes=fixes):
                out[ev["id"]] = ev
        except Exception as exc:  # noqa: BLE001
            log("%s: LaLiga %s (%s)" % (NAME, season, exc.__class__.__name__))
    for comp in EURO_COMPS:
        try:
            sched = http_text(EURO_URL % ("schedules", comp, y), encoding="utf-8")
            teams = http_text(EURO_URL % ("teams", comp, y), encoding="utf-8")
            for ev in parse_euro(sched, teams, comp, t0):
                out[ev["id"]] = ev
        except Exception as exc:  # noqa: BLE001
            log("%s: %s (%s)" % (NAME, EURO_COMPS[comp][0], exc.__class__.__name__))
    res = [e for e in out.values() if e["start"] <= horizon]
    log("%s: %d partidos" % (NAME, len(res)))
    return res
