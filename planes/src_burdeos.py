# -*- coding: utf-8 -*-
"""Burdeos (Francia): agenda de Bordeaux Métropole (OpenAgenda) del 5 al 8 de diciembre de 2026.

Fuente temporal y acotada a esas fechas (puente de diciembre). Datos abiertos de Bordeaux Métropole, conjunto
«Agenda Bordeaux Métropole» (met_agenda), que reúne los agendas OpenAgenda de las 28 comunas de la metrópoli.

La fuente da la primera y la última sesión de cada plan, no las intermedias. Para no anunciar fechas que no
constan:
- planes de hasta 4 días: se publican tal cual (del primer al último día);
- exposiciones continuas: se publican con su periodo completo («hasta el …»);
- el resto (talleres, cursos o espectáculos que se repiten «certains mercredis», etc.) solo si su primera o su
  última sesión cae entre el 5 y el 8 de diciembre, y solo ese día.
Las horas vienen en UTC y se pasan a la hora de París.
"""
import json
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .classify import classify
from .util import event, http_json, norm, strip_html

NAME = "Agenda de Bordeaux Métropole (OpenAgenda)"
API = "https://opendata.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/met_agenda/exports/json"
HOME = "https://opendata.bordeaux-metropole.fr/explore/dataset/met_agenda/"
WINDOW = (date(2026, 12, 5), date(2026, 12, 8))
PROVINCE_CODE = "FR33"  # Gironda (Francia)
PARIS = ZoneInfo("Europe/Paris")
CITY_ES = {"bordeaux": "Burdeos"}

_RECURRING = re.compile(r"\b(certains|chaque|tous les|toutes les|les (lundis|mardis|mercredis|jeudis|vendredis|samedis|dimanches))\b| et \d")
_EXPO = re.compile(r"\b(expo|exposition|exposicion|exhibition)\b")
# Trámites y avisos municipales que la agenda mezcla con el ocio
_NOT_LEISURE = re.compile(r"\b(conseil (municipal|de metropole|communautaire)|appel a (projets|candidatures)|recherche d.emploi|"
                          r"insalubre|permanence|reunion publique|enquete publique|don du sang|collecte de|entreprise|"
                          r"entrepreneur|emploi|broyage|dechets verts|devenez benevole)\b")
# Visitas, talleres o cursos sobre una exposición: tienen sesiones sueltas, no están abiertos todos los días
_NOT_CONTINUOUS = re.compile(r"^(visite|visites|atelier|ateliers|cours|stage|conference|rencontre|lecture|projection)\b")
# Tipos de plan en francés (el clasificador general está pensado para castellano, catalán y euskera)
_FR_RULES = [
    ("infantil", r"\b(enfants?|famille|familles|familial|jeune public|bebes?|tout.petits|marionnettes?|conte|contes|kids)\b"),
    ("navidad", r"\b(noel|marche de noel|fetes de fin d.annee|pere noel|calendrier de l.avent|sapin)\b"),
    ("cine", r"\b(cinema|cine|film|films|projection|court.metrage|documentaire)\b"),
    ("deporte", r"\b(sport|sportif|match|rugby|football|basket|handball|course a pied|marathon|trail|natation|patinage|petanque)\b"),
    ("escena", r"\b(theatre|danse|spectacle|opera|cirque|humour|one man show|comedie|ballet|improvisation|cabaret|magie)\b"),
    ("musica", r"\b(concert|concerts|musique|jazz|piano|orchestre|chorale|recital|chanson|chansons|dj|symphoni|rock|electro|rap|lyrique)\b"),
    ("expos", r"\b(expo|exposition|musee|galerie|vernissage|photographie|peinture|sculpture|oeuvres?)\b"),
    ("gastro", r"\b(marche|degustation|vins?|gastronom|brocante|salon|foire|vide.grenier|oenolog|portes ouvertes)\b"),
    ("fiestas", r"\b(fete|festival|carnaval|bal|guinguette)\b"),
    ("naturaleza", r"\b(visite|visites|balade|randonnee|promenade|nature|jardin|parc|velo|patrimoine)\b"),
    ("charlas", r"\b(conference|atelier|ateliers|rencontre|lecture|lecteurs|litteraire|livres?|bd|bibliotheque|mediatheque|"
                r"debat|cours|formation|dictee|club|numerique|jeux|jeu|scrabble|echecs|puzzles?)\b"),
]
_FR_COMPILED = [(k, re.compile(rx)) for k, rx in _FR_RULES]


def _local(s):
    """'2026-12-05T19:00:00+00:00' -> datetime en hora de París."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(PARIS)
    except ValueError:
        return None


def _id(field):
    """Los campos status y attendancemode llegan como JSON {"id": n, "label": {...}}."""
    if isinstance(field, dict):
        return field.get("id")
    try:
        return json.loads(field).get("id")
    except (TypeError, ValueError, AttributeError):
        return None


def _keywords(r):
    kw = r.get("keywords_fr")
    if isinstance(kw, str):
        try:
            kw = json.loads(kw)
        except ValueError:
            kw = [kw]
    return [str(k) for k in (kw or [])]


def _links(r):
    links = r.get("links")
    if isinstance(links, str):
        try:
            links = json.loads(links)
        except ValueError:
            links = []
    out = []
    for item in links or []:
        u = item.get("link") if isinstance(item, dict) else item
        if isinstance(u, str) and re.match(r"^https?://", u):
            out.append(u)
    return out


def category_fr(title, keywords, description, age_max=None):
    if age_max not in (None, "") and str(age_max).isdigit() and 0 < int(age_max) <= 12:
        return "infantil"
    text = norm(" ".join([title] + keywords))
    for key, rx in _FR_COMPILED:
        if rx.search(text):
            return key
    text2 = norm(description)[:300]
    for key, rx in _FR_COMPILED:
        if rx.search(text2):
            return key
    return classify(keywords, title, description)


def _in_window(d):
    return WINDOW[0] <= d <= WINDOW[1]


def plan_dates(r):
    """[(inicio, fin, hora)] que se pueden anunciar sin inventar fechas (ver la cabecera del módulo)."""
    first, last = _local(r.get("firstdate_begin")), _local(r.get("lastdate_begin") or r.get("lastdate_end"))
    if not first or not last:
        return []
    d0, d1 = first.date(), max(last.date(), first.date())
    hour = first.strftime("%H:%M")
    if d1 < WINDOW[0] or d0 > WINDOW[1]:
        return []
    dr = norm(r.get("daterange_fr") or "")
    recurring = bool(_RECURRING.search(dr))
    if (d1 - d0).days <= 3:
        return [(d0, d1, hour)]
    title = norm(r.get("title_fr") or "")
    expo = _EXPO.search(title) or (_EXPO.search(norm(" ".join(_keywords(r)))) and not _NOT_CONTINUOUS.search(title))
    if expo and not recurring:
        return [(d0, d1, "")]
    out = []
    if _in_window(d0):
        out.append((d0, d0, hour))
    if _in_window(d1) and d1 != d0:
        out.append((d1, d1, last.strftime("%H:%M")))
    return out


def to_events(rows):
    out = []
    for r in rows:
        title = strip_html(r.get("title_fr"), 200)
        if not title or _NOT_LEISURE.search(norm(title)):
            continue
        if _id(r.get("status")) in (4, 6) or _id(r.get("attendancemode")) == 2:  # aplazado, anulado, solo en línea
            continue
        if (r.get("location_countrycode") or "FR") != "FR":
            continue
        dates = plan_dates(r)
        if not dates:
            continue
        kws = _keywords(r)
        desc = r.get("description_fr") or r.get("longdescription_fr") or ""
        city = r.get("location_city") or "Bordeaux"
        city = CITY_ES.get(norm(city), city)
        geo = r.get("location_coordinates") or {}
        links = _links(r)
        url = links[0] if links else "https://openagenda.com/agendas/%s/events/%s" % (r.get("originagenda_uid"), r.get("uid"))
        fam = re.search(r"\b(famille|familles|familial|jeune public|enfants?)\b", norm(" ".join(kws + [title])))
        for d0, d1, hour in dates:
            ev = event(
                NAME, "%s|%s" % (r.get("uid"), d0.isoformat() if len(dates) > 1 else ""), title, d0.isoformat(),
                end=d1.isoformat(), time=hour, description=desc,
                category=category_fr(title, kws, strip_html(desc), r.get("age_max")),
                province_code=PROVINCE_CODE, city=city, venue=r.get("location_name"), address=r.get("location_address"),
                lat=geo.get("lat"), lon=geo.get("lon"), price=r.get("conditions_fr"), url=url,
                audience="Familias" if fam else "",
            )
            if ev:
                out.append(ev)
    return out


def fetch(log):
    a, b = WINDOW[0] - timedelta(days=1), WINDOW[1] + timedelta(days=1)  # margen por el paso de UTC a París
    where = "firstdate_begin <= '%sT23:59:59' and lastdate_end >= '%s'" % (b.isoformat(), a.isoformat())
    rows = http_json(API, params={"where": where, "lang": "fr"})
    out = to_events(rows if isinstance(rows, list) else [])
    log("%s: %d planes entre el %s y el %s (de %d en la agenda)" % (NAME, len(out), WINDOW[0], WINDOW[1], len(rows or [])))
    return out
