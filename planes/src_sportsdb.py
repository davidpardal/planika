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


_DAYS_CACHE = os.path.join(DATA_DIR, "tsdb_days.json")
BUDGET = 8          # peticiones de calendario por ejecución: la clave gratuita corta con 429 enseguida
LOOKUP_BUDGET = 4   # consultas de ciudad de equipo por ejecución (el resultado se guarda)
REFRESH_DAYS = 7    # un día ya descargado se vuelve a pedir pasados 7 días

# Ciudad por palabra clave del nombre del equipo (evita consultas): (palabra, ciudad, código de provincia)
CITY_BY_TEAM = [
    ("burgos", "Burgos", "09"), ("manresa", "Manresa", "08"), ("murcia", "Murcia", "30"), ("obradoiro", "Santiago de Compostela", "15"),
    ("bilbao", "Bilbao", "48"), ("coruña", "A Coruña", "15"), ("coruna", "A Coruña", "15"), ("lleida", "Lleida", "25"),
    ("zaragoza", "Zaragoza", "50"), ("girona", "Girona", "17"), ("real madrid", "Madrid", "28"), ("barça", "Barcelona", "08"),
    ("barcelona", "Barcelona", "08"), ("valencia", "Valencia", "46"), ("unicaja", "Málaga", "29"), ("málaga", "Málaga", "29"),
    ("malaga", "Málaga", "29"), ("breogan", "Lugo", "27"), ("breogán", "Lugo", "27"), ("joventut", "Badalona", "08"),
    ("granada", "Granada", "18"), ("gran canaria", "Las Palmas de Gran Canaria", "35"), ("dreamland", "Las Palmas de Gran Canaria", "35"),
    ("tenerife", "San Cristóbal de La Laguna", "38"), ("baskonia", "Vitoria-Gasteiz", "01"),
    ("cangas", "Cangas", "36"), ("sagunto", "Sagunto", "46"), ("nava", "Nava de la Asunción", "40"), ("sevilla", "Sevilla", "41"),
    ("granollers", "Granollers", "08"), ("ademar", "León", "24"), ("león", "León", "24"), ("guadalajara", "Guadalajara", "19"),
    ("cuenca", "Cuenca", "16"), ("ciudad real", "Ciudad Real", "13"), ("puente genil", "Puente Genil", "14"),
    ("bidasoa", "Irún", "20"), ("huesca", "Huesca", "22"), ("benidorm", "Benidorm", "03"), ("logroño", "Logroño", "26"),
    ("rioja", "Logroño", "26"),
]


def team_city(name):
    n = (name or "").lower()
    for key, city, prov in CITY_BY_TEAM:
        if key in n:
            return city, prov
    return "", ""


def _load_days():
    try:
        with open(_DAYS_CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _daily(lid, lname, store, budget, log):
    """Partidos de los próximos DAILY_DAYS días (solo viernes a lunes). Usa la caché y gasta como mucho `budget[0]` peticiones."""
    out, t0 = [], today()
    days = [iso(t0 + timedelta(days=n)) for n in range(DAILY_DAYS) if (t0 + timedelta(days=n)).weekday() in PLAY_WEEKDAYS]
    stale = lambda k: k not in store or store[k]["fetched"] < iso(t0 - timedelta(days=REFRESH_DAYS))
    for day in sorted(days, key=lambda d: store.get("%s|%s" % (lid, d), {}).get("fetched", "")):
        key = "%s|%s" % (lid, day)
        if stale(key) and budget[0] > 0 and not budget[1]:
            budget[0] -= 1
            try:
                store[key] = {"fetched": iso(t0), "events": http_json(BASE + "eventsday.php", params={"d": day, "l": lid}, retries=1).get("events") or []}
            except Exception as exc:  # noqa: BLE001
                budget[1] = True  # 429: no se insiste en esta ejecución
                log("%s: %s %s (%s); se sigue mañana con lo guardado" % (NAME, lname, day, exc.__class__.__name__))
            time.sleep(4)
        out.extend(store.get(key, {}).get("events") or [])
    for k in [k for k in store if k.split("|")[1] < iso(t0)]:
        del store[k]  # fechas pasadas
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
    store = _load_days()
    budget = [BUDGET, False]  # [peticiones restantes, cortado por 429]
    lookups = [LOOKUP_BUDGET]
    out = {}
    for lid, (lname, sport) in LEAGUES.items():
        events = []
        if lid in DAILY:
            events = _daily(lid, lname, store, budget, log)
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
            city, prov = team_city(e.get("strHomeTeam"))
            if not city and lookups[0] > 0 and e.get("idHomeTeam") not in cache:
                lookups[0] -= 1
                city = _team_city(e.get("idHomeTeam"), cache)
            elif not city:
                city = cache.get(e.get("idHomeTeam"), "")
            title = "%s - %s" % (e.get("strHomeTeam"), e.get("strAwayTeam"))
            ev = event(
                NAME, e.get("idEvent"), title, date, time=hhmm,
                description="%s, jornada %s. %s en %s." % (lname, e.get("intRound") or "-", sport, e.get("strVenue") or city),
                subtype=lname, category="deporte", city=city, province_code=prov, venue=e.get("strVenue"),
                url=HOME + "event/" + str(e.get("idEvent")), image=e.get("strThumb") or e.get("strPoster"),
            )
            if ev:
                out[ev["id"]] = ev
    for path, obj in ((_CACHE, cache), (_DAYS_CACHE, store)):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(obj, fh, ensure_ascii=False, indent=0, sort_keys=True)
        except OSError:
            pass
    log("%s: %d partidos" % (NAME, len(out)))
    return list(out.values())


def _season():
    y = today().year
    return "%d-%d" % ((y, y + 1) if today().month >= 7 else (y - 1, y))
