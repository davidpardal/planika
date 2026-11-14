# -*- coding: utf-8 -*-
"""TheSportsDB (clave pública de pruebas): partidos de LaLiga, LaLiga 2, ACB, Copa del Rey y Supercopa."""
import json
import os
import time

from .util import DATA_DIR, event, http_json, iso, today

NAME = "TheSportsDB (ligas españolas)"
HOME = "https://www.thesportsdb.com/"
KEY = os.environ.get("THESPORTSDB_KEY", "123")
BASE = "https://www.thesportsdb.com/api/v1/json/%s/" % KEY
LEAGUES = {
    "4335": ("LaLiga", "Fútbol"), "4400": ("LaLiga Hypermotion", "Fútbol"), "4408": ("Liga Endesa ACB", "Baloncesto"),
    "4483": ("Copa del Rey", "Fútbol"), "4511": ("Supercopa de España", "Fútbol"),
}
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
        for endpoint, params in (("eventsnextleague.php", {"id": lid}),):
            try:
                d = http_json(BASE + endpoint, params=params, retries=3)
                events.extend(d.get("events") or [])
            except Exception as exc:  # noqa: BLE001
                log("%s: %s %s (%s)" % (NAME, endpoint, lname, exc.__class__.__name__))
            time.sleep(2.2)
        for e in events:
            date = e.get("dateEvent") or ""
            if not date or date < iso(today()) or e.get("strPostponed") == "yes":
                continue
            if e.get("intHomeScore") not in (None, ""):
                continue  # ya disputado
            city = _team_city(e.get("idHomeTeam"), cache)
            title = "%s - %s" % (e.get("strHomeTeam"), e.get("strAwayTeam"))
            ev = event(
                NAME, e.get("idEvent"), title, date, time=(e.get("strTime") or "")[:5] if (e.get("strTime") or "") != "00:00:00" else "",
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
