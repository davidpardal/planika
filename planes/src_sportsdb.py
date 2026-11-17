# -*- coding: utf-8 -*-
"""TheSportsDB (clave pública de pruebas): partidos de LaLiga 2, ACB, Copa del Rey y Supercopa (LaLiga y Euroliga vienen de src_deporte_pro)."""
import json
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .util import DATA_DIR, event, http_json, iso, today

NAME = "TheSportsDB (ligas españolas)"
HOME = "https://www.thesportsdb.com/"
KEY = os.environ.get("THESPORTSDB_KEY", "123")
BASE = "https://www.thesportsdb.com/api/v1/json/%s/" % KEY
LEAGUES = {
    "4400": ("LaLiga Hypermotion", "Fútbol"), "4408": ("Liga Endesa ACB", "Baloncesto"),
    "4483": ("Copa del Rey", "Fútbol"), "4511": ("Supercopa de España", "Fútbol"),
    "4534": ("Liga ASOBAL", "Balonmano"), "5486": ("Liga Femenina de Baloncesto", "Baloncesto"),
}
# La clave gratuita solo devuelve 1 partido con "próximos de la liga", pero "eventsday" da hasta 5 por día:
# en estas ligas se pregunta día a día durante DAILY_DAYS días.
DAILY = {"4408", "4534", "5486"}
DAILY_DAYS = 14
PLAY_WEEKDAYS = {4, 5, 6, 0}  # viernes a lunes: ahí se juegan casi todas las jornadas (la API gratuita limita las peticiones)
MADRID = ZoneInfo("Europe/Madrid")


def to_madrid(date, tm):
    """TheSportsDB da la hora en UTC. Devuelve (fecha, hora) en hora de Madrid; sin hora, (fecha, '')."""
    if not date or not tm or tm.startswith("00:00"):
        return date, ""
    try:
        dt = datetime.strptime("%s %s" % (date, tm[:5]), "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(MADRID)
    except ValueError:
        return date, ""
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")


def _daily(lid, lname, log):
    out = []
    for n in range(DAILY_DAYS):
        if (today() + timedelta(days=n)).weekday() not in PLAY_WEEKDAYS:
            continue
        day = iso(today() + timedelta(days=n))
        for attempt in (0, 1):
            try:
                out.extend(http_json(BASE + "eventsday.php", params={"d": day, "l": lid}, retries=1).get("events") or [])
                break
            except Exception as exc:  # noqa: BLE001  (429: se espera y se reintenta una vez)
                if attempt:
                    log("%s: %s %s (%s); se corta la consulta diaria" % (NAME, lname, day, exc.__class__.__name__))
                    return out
                time.sleep(45)
        time.sleep(4)
    return out
_CACHE = os.path.join(DATA_DIR, "teams_cache.json")


def _load_cache():
    try:
        with open(_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _team_city(team_id, cache):
    if not team_id:
        return ""
    if team_id in cache:
        return cache[team_id]
    try:
        d = http_json(BASE + "lookupteam.php", params={"id": team_id}, retries=3)
        t = (d.get("teams") or [{}])[0]
        city = t.get("strStadiumLocation") or t.get("strLocation") or ""
        city = city.split(",")[0].strip()
    except Exception:  # noqa: BLE001
        city = ""
    cache[team_id] = city
    time.sleep(2.2)  # la clave gratuita admite pocas peticiones por minuto
    return city


def fetch(log, days=180):
    cache = _load_cache()
    out = {}
    for lid, (lname, sport) in LEAGUES.items():
        events = []
        if lid in DAILY:
            events = _daily(lid, lname, log)
        else:
            try:
                events.extend(http_json(BASE + "eventsnextleague.php", params={"id": lid}, retries=3).get("events") or [])
            except Exception as exc:  # noqa: BLE001
                log("%s: eventsnextleague %s (%s)" % (NAME, lname, exc.__class__.__name__))
            time.sleep(2.2)
        for e in events:
            date, hhmm = to_madrid(e.get("dateEvent") or "", e.get("strTime") or "")
            if not date or date < iso(today()) or e.get("strPostponed") == "yes":
                continue
            if e.get("intHomeScore") not in (None, ""):
                continue  # ya disputado
            city = _team_city(e.get("idHomeTeam"), cache)
            title = "%s - %s" % (e.get("strHomeTeam"), e.get("strAwayTeam"))
            ev = event(
                NAME, e.get("idEvent"), title, date, time=hhmm,
                description="%s, jornada %s. %s en %s." % (lname, e.get("intRound") or "-", sport, e.get("strVenue") or city),
                subtype=lname, category="deporte", city=city, venue=e.get("strVenue"),
                url=HOME + "event/" + str(e.get("idEvent")), image=e.get("strThumb") or e.get("strPoster"),
            )
            if ev:
                out[ev["id"]] = ev
    try:
        with open(_CACHE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    except OSError:
        pass
    log("%s: %d partidos" % (NAME, len(out)))
    return list(out.values())


def _season():
    y = today().year
    return "%d-%d" % ((y, y + 1) if today().month >= 7 else (y - 1, y))
