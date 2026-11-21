# -*- coding: utf-8 -*-
"""Partidos repetidos entre fuentes.

El mismo partido llega a veces por dos agendas con nombres de club distintos y hasta con otra fecha:
«CB Murcia - Basket Zaragoza» (TheSportsDB) y «UCAM Murcia CB - Casademont Zaragoza» (Ayuntamiento de Murcia),
o «Real Madrid CF - RC Celta de Vigo» el sábado a las 21:00 (calendario oficial) y «Real Madrid - RC Celta de
Vigo (LALIGA EA SPORTS)» el domingo, sin hora (agenda turística, que da el fin de semana de la jornada).

Se consideran el mismo partido si: son de fuentes distintas, de la misma provincia, del mismo deporte y
categoría (masculina o femenina), a 3 días o menos, y cada equipo de uno «contiene» al del otro una vez
quitadas las siglas y palabras comunes (CF, Club, CB...) y el patrocinador sobrante (Murcia ⊂ UCAM Murcia).
Se queda el que tiene hora (fecha confirmada) y, si no, el de la fuente de calendario oficial; del otro se
toman la sala, la ubicación, la imagen y lo que le falte.
"""
import re
from datetime import date

from .util import norm

MAX_DAYS = 3
# Fuentes de calendario, de más a menos fiable para la fecha y la hora
SOURCE_RANK = ["Deporte profesional (LaLiga, Euroliga, EuroCup)", "TheSportsDB (ligas españolas)"]
_FILL = ("venue", "address", "lat", "lon", "image", "description", "tickets_url", "price", "time")
_SPLIT = re.compile(r"\s+(?:-|–|—|vs\.?|v\.?|contra)\s+", re.I)
_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_STOP = set("""club cf fc cd ud sd sad rc rcd ca cb bc ce cdb ad sc ac cp de del la el l les los las y
    futbol balompie basket baloncesto basquet bàsquet""".split())
_WOMEN = {"femenino", "femenina", "fem", "women", "woman", "cff", "femeni", "femenı", "w"}
_ALIAS = {"r": "real", "at": "atletico", "atl": "atletico", "ath": "athletic"}
_SPORTS = (
    ("basket", ("acb", "liga endesa", "euroliga", "euroleague", "eurocup", "baloncesto", "basket", "basquet", "nba",
                "liga femenina de baloncesto", " cb ", " bc ", "copa del rey de baloncesto")),
    ("balonmano", ("balonmano", "asobal", "handbol", "handball")),
    ("voley", ("voleibol", "voley", "volley", "superliga")),
    ("hockey", ("hockey", "hoquei")),
    ("futbol", ("laliga", "la liga", "futbol", "hypermotion", "liga f", "primera federacion", "segunda federacion",
                "champions", "europa league", "conference league", "copa del rey")),
)


def sport(e):
    text = " %s %s " % (norm(e.get("title")), norm(e.get("subtype")))
    for name, words in _SPORTS:
        if any(w in text for w in words):
            return name
    return ""


def teams(title):
    """(local, visitante) como conjuntos de palabras, más si es categoría femenina; None si no es un partido."""
    parts = _SPLIT.split(_PAREN.sub(" ", title or ""))
    if len(parts) != 2:
        return None
    women = False
    sides = []
    for p in parts:
        words = [_ALIAS.get(w, w) for w in norm(p).split()]
        women = women or any(w in _WOMEN for w in words)
        core = frozenset(w for w in words if w not in _STOP and w not in _WOMEN and not w.isdigit() and len(w) > 1)
        if not core:
            return None
        sides.append(core)
    if "liga f" in norm(title) or "femenina" in norm(title):
        women = True
    return sides[0], sides[1], women


def _same_side(a, b):
    return a <= b or b <= a


def _rank(e):
    try:
        src = SOURCE_RANK.index(e.get("source"))
    except ValueError:
        src = len(SOURCE_RANK)
    rich = sum(1 for k in _FILL if e.get(k))
    return (0 if e.get("time") else 1, src, -rich)


def _days(a, b):
    try:
        return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)
    except ValueError:
        return 99


def dedupe_matches(events):
    """Une el mismo partido publicado por dos fuentes. Devuelve (planes, número unido)."""
    cand = []
    for i, e in enumerate(events):
        if e.get("category") != "deporte":
            continue
        t = teams(e.get("title"))
        if t:
            cand.append((i, e, t, sport(e)))
    by_prov = {}
    for c in cand:
        by_prov.setdefault(c[1].get("province_code"), []).append(c)
    drop = set()
    for group in by_prov.values():
        group.sort(key=lambda c: c[1]["start"])
        for x in range(len(group)):
            i, a, ta, sa = group[x]
            if i in drop:
                continue
            best = None
            for y in range(x + 1, len(group)):
                j, b, tb, sb = group[y]
                gap = _days(a["start"], b["start"])
                if gap > MAX_DAYS:
                    break
                if j in drop or a.get("source") == b.get("source") or ta[2] != tb[2]:
                    continue
                # Mismo deporte; si una fuente no lo dice, solo el mismo día
                if sa != sb and (sa and sb or gap):
                    continue
                if not (_same_side(ta[0], tb[0]) and _same_side(ta[1], tb[1])):
                    continue
                # Si hay varias opciones, la del mismo día
                if best is None or gap < best[0]:
                    best = (gap, j)
            if best is None:
                continue
            j = best[1]
            keep, lose = (i, j) if _rank(events[i]) <= _rank(events[j]) else (j, i)
            for k in _FILL:
                if not events[keep].get(k) and events[lose].get(k):
                    if k == "time" and events[keep]["start"] != events[lose]["start"]:
                        continue  # una hora de otro día no vale
                    events[keep][k] = events[lose][k]
            drop.add(lose)
    return [e for i, e in enumerate(events) if i not in drop], len(drop)
