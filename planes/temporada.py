"""Páginas de temporada de Navidad con la fecha y la hora de cada ciudad: encendido de luces, cabalgatas de Reyes
y Nochevieja. Es lo que más se busca esos días («a qué hora encienden las luces en Pamplona», «cabalgata de Reyes
Madrid horario») y Planika ya tiene esos planes de las agendas oficiales; aquí se juntan por día y hora.

La URL no lleva año, para que gane fuerza de un año a otro. Fuera de temporada, o con pocos planes publicados, la
página se queda como noindex y no se enlaza.
"""
import re

from .util import is_permanent, norm

_XMAS = re.compile(r"\b(navidad|navidenos?|navidenas?|nadal|nadalencs?|gabon|gabonetako|christmas|xmas)")
_LUCES = re.compile(r"\b(encendido|alumbrado|iluminacion|enllumenat|encesa|argiztapen\w*|piztea)\b")
_CABALGATA = re.compile(r"\b(cabalgatas?|cavalcadas?|kabalkada)\b")
_REYES = re.compile(r"\b(reyes|reis|erregeen|erregeak|errege magoak)\b")
_NOCHEVIEJA = re.compile(
    r"\b(nochevieja|fin de ano|cap d.any|urtezahar|campanadas|san silvestre|sant silvestre|ano nuevo|any nou|urte berri)")

# clave: (archivo, título corto, desde (MM-DD), hasta (MM-DD), mínimo de planes)
PAGES = {
    "luces": ("encendido-luces-navidad.html", "Encendido de luces de Navidad", "11-01", "12-15", 5),
    "cabalgatas": ("cabalgatas-reyes.html", "Cabalgatas de Reyes", "11-15", "01-06", 5),
    "nochevieja": ("nochevieja.html", "Nochevieja y Año Nuevo", "11-15", "01-01", 5),
}
ORDER = ("luces", "cabalgatas", "nochevieja")


def _days(e):
    return e.get("sessions") or [e["start"], e["end"]]


def matches(key, e):
    """¿Es `e` un plan de la página `key`?"""
    if is_permanent(e):
        return False
    text = norm(e.get("title_es") or e["title"])
    if key == "luces":
        # El encendido es en noviembre o diciembre y con tema navideño (no «iluminación» de cualquier cosa)
        return (bool(_LUCES.search(text)) and (e["category"] == "navidad" or bool(_XMAS.search(text)))
                and e["start"][5:7] in ("11", "12"))
    if key == "cabalgatas":
        # De Reyes: lo dice el título o es del 2 al 6 de enero (no la de Papá Noel de diciembre)
        if not _CABALGATA.search(text):
            return False
        return bool(_REYES.search(text)) or any("01-02" <= d[5:] <= "01-06" for d in _days(e))
    if key == "nochevieja":
        # Del 26 de diciembre al 1 de enero (no un ciclo de conciertos «Fin de año musical» de octubre)
        return bool(_NOCHEVIEJA.search(text)) and any(d[5:] >= "12-26" or d[5:] <= "01-01" for d in _days(e))
    return False


def in_season(key, t0):
    _, _, a, b, _ = PAGES[key]
    md = t0[5:]
    return a <= md <= b if a <= b else (md >= a or md <= b)


def season_label_year(key, t0):
    """Año del título: «Encendido de luces 2026», «Cabalgatas de Reyes 2027», «Nochevieja 2026»."""
    y, m = int(t0[:4]), int(t0[5:7])
    if key == "cabalgatas":
        return y + 1 if m >= 11 else y
    return y - 1 if m == 1 else y


def items(key, events, t0):
    """Planes de la página que aún no han terminado (en temporada o no)."""
    return [e for e in events if e["end"] >= t0 and matches(key, e)]


def active(events, t0):
    """{clave: planes} de las páginas que hoy se publican indexables y se enlazan."""
    out = {}
    for key in ORDER:
        if not in_season(key, t0):
            continue
        its = items(key, events, t0)
        if len(its) >= PAGES[key][4]:
            out[key] = its
    return out
