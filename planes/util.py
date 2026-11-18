# -*- coding: utf-8 -*-
"""Utilidades comunes: HTTP, fechas, limpieza de texto y provincias."""
import hashlib
import html
import json
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UA = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"

# ---------------------------------------------------------------- HTTP

_session = requests.Session()
# Accept-Encoding: identity -> algunos portales (datos.madrid.es) se cuelgan al comprimir respuestas grandes
_session.headers.update({"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Accept-Encoding": "identity"})


def http_get(url, params=None, headers=None, retries=3, timeout=(15, 90)):
    """GET con reintentos. Devuelve el objeto Response o lanza la última excepción."""
    last = None
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 429:  # límite de peticiones: esperar y reintentar
                last = requests.HTTPError("429 Too Many Requests para %s" % url, response=r)
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last if last is not None else RuntimeError("sin respuesta de %s" % url)


def http_json(url, params=None, headers=None, **kw):
    r = http_get(url, params=params, headers=headers, **kw)
    try:
        return r.json()
    except ValueError:
        # Algunos portales devuelven JSON con BOM o content-type raro
        return json.loads(r.content.decode("utf-8-sig", errors="replace"))


def http_text(url, params=None, headers=None, encoding=None, **kw):
    r = http_get(url, params=params, headers=headers, **kw)
    if encoding:
        r.encoding = encoding
    elif not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text

# ---------------------------------------------------------------- Texto

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(s, limit=None):
    if not s:
        return ""
    s = html.unescape(_TAG_RE.sub(" ", str(s)))
    s = s.replace("\ufffd", "")
    s = _WS_RE.sub(" ", s).strip()
    if limit and len(s) > limit:
        cut = s[:limit]
        ends = [m.end() for m in re.finditer(r"[.!?»\"”)](?=\s)", cut)]
        if ends and ends[-1] >= limit * 0.5:
            s = cut[:ends[-1]].strip()          # termina en una frase completa, sin puntos suspensivos
        else:
            s = s[: limit - 1].rsplit(" ", 1)[0] + "…"
    return s


def norm(s):
    """Minúsculas, sin acentos ni signos; para comparar nombres."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("ñ", "n")
    s = re.sub(r"[^a-z0-9/ ]+", " ", s)
    return _WS_RE.sub(" ", s).strip()


def clean_url(u):
    if not u:
        return ""
    u = str(u).strip()
    if not u:
        return ""
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u.lstrip("/")
    return u

# ---------------------------------------------------------------- Fechas

_DATE_PATTERNS = (
    ("%Y-%m-%d", re.compile(r"^(\d{4}-\d{2}-\d{2})")),
    ("%d/%m/%Y", re.compile(r"^(\d{1,2}/\d{1,2}/\d{4})")),
    ("%Y/%m/%d", re.compile(r"^(\d{4}/\d{2}/\d{2})")),
)


def parse_date(s):
    """Devuelve 'YYYY-MM-DD' o None a partir de formatos habituales."""
    if not s:
        return None
    if isinstance(s, (date, datetime)):
        return s.strftime("%Y-%m-%d")
    s = str(s).strip()
    for fmt, rx in _DATE_PATTERNS:
        m = rx.match(s)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt).strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None


_TIME_RE = re.compile(r"(\d{1,2})[:.h](\d{2})")
_TIME_H_RE = re.compile(r"\b(\d{1,2})\s*h\b")


def parse_time(s):
    """Extrae la primera hora 'HH:MM' de un texto libre ('a les 18 h', '19.30 h')."""
    if not s:
        return ""
    s = str(s)
    m = _TIME_RE.search(s)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mi < 60:
            return "%02d:%02d" % (h, mi)
    m = _TIME_H_RE.search(s)
    if m and 0 <= int(m.group(1)) < 24:
        return "%02d:00" % int(m.group(1))
    return ""


def today():
    return date.today()


def iso(d):
    return d.strftime("%Y-%m-%d")

# ---------------------------------------------------------------- Provincias

# código INE, nombre, comunidad autónoma
PROVINCIAS = [
    ("01", "Álava", "País Vasco"), ("02", "Albacete", "Castilla-La Mancha"),
    ("03", "Alicante", "Comunitat Valenciana"), ("04", "Almería", "Andalucía"),
    ("05", "Ávila", "Castilla y León"), ("06", "Badajoz", "Extremadura"),
    ("07", "Illes Balears", "Illes Balears"), ("08", "Barcelona", "Cataluña"),
    ("09", "Burgos", "Castilla y León"), ("10", "Cáceres", "Extremadura"),
    ("11", "Cádiz", "Andalucía"), ("12", "Castellón", "Comunitat Valenciana"),
    ("13", "Ciudad Real", "Castilla-La Mancha"), ("14", "Córdoba", "Andalucía"),
    ("15", "A Coruña", "Galicia"), ("16", "Cuenca", "Castilla-La Mancha"),
    ("17", "Girona", "Cataluña"), ("18", "Granada", "Andalucía"),
    ("19", "Guadalajara", "Castilla-La Mancha"), ("20", "Gipuzkoa", "País Vasco"),
    ("21", "Huelva", "Andalucía"), ("22", "Huesca", "Aragón"),
    ("23", "Jaén", "Andalucía"), ("24", "León", "Castilla y León"),
    ("25", "Lleida", "Cataluña"), ("26", "La Rioja", "La Rioja"),
    ("27", "Lugo", "Galicia"), ("28", "Madrid", "Comunidad de Madrid"),
    ("29", "Málaga", "Andalucía"), ("30", "Murcia", "Región de Murcia"),
    ("31", "Navarra", "Navarra"), ("32", "Ourense", "Galicia"),
    ("33", "Asturias", "Asturias"), ("34", "Palencia", "Castilla y León"),
    ("35", "Las Palmas", "Canarias"), ("36", "Pontevedra", "Galicia"),
    ("37", "Salamanca", "Castilla y León"), ("38", "Santa Cruz de Tenerife", "Canarias"),
    ("39", "Cantabria", "Cantabria"), ("40", "Segovia", "Castilla y León"),
    ("41", "Sevilla", "Andalucía"), ("42", "Soria", "Castilla y León"),
    ("43", "Tarragona", "Cataluña"), ("44", "Teruel", "Aragón"),
    ("45", "Toledo", "Castilla-La Mancha"), ("46", "Valencia", "Comunitat Valenciana"),
    ("47", "Valladolid", "Castilla y León"), ("48", "Bizkaia", "País Vasco"),
    ("49", "Zamora", "Castilla y León"), ("50", "Zaragoza", "Aragón"),
    ("51", "Ceuta", "Ceuta"), ("52", "Melilla", "Melilla"),
]
PROV_BY_CODE = {c: {"code": c, "name": n, "ccaa": a} for c, n, a in PROVINCIAS}

_ALIASES = {
    "alava": "01", "araba": "01", "araba alava": "01", "alava araba": "01", "vitoria": "01",
    "guipuzcoa": "20", "gipuzkoa": "20", "vizcaya": "48", "bizkaia": "48",
    "valencia": "46", "valencia valencia": "46", "castellon": "12", "castello": "12",
    "castellon de la plana": "12", "castello de la plana": "12", "alicante": "03", "alacant": "03",
    "alicante alacant": "03", "gerona": "17", "girona": "17", "lerida": "25", "lleida": "25",
    "orense": "32", "ourense": "32", "la coruna": "15", "a coruna": "15", "coruna": "15",
    "baleares": "07", "illes balears": "07", "islas baleares": "07", "mallorca": "07",
    "menorca": "07", "ibiza": "07", "eivissa": "07", "formentera": "07",
    "las palmas": "35", "palmas": "35", "gran canaria": "35", "lanzarote": "35", "fuerteventura": "35",
    "santa cruz de tenerife": "38", "tenerife": "38", "la palma": "38", "la gomera": "38", "el hierro": "38",
    "nafarroa": "31", "navarra": "31", "comunidad foral de navarra": "31",
    "asturias": "33", "principado de asturias": "33", "cantabria": "39", "murcia": "30",
    "region de murcia": "30", "la rioja": "26", "rioja": "26", "madrid": "28", "comunidad de madrid": "28",
    "ceuta": "51", "melilla": "52",
}
for _c, _n, _a in PROVINCIAS:
    _ALIASES.setdefault(norm(_n), _c)


def province_code_from_name(name):
    """Código de provincia a partir de un nombre (acepta alias y variantes cooficiales)."""
    if not name:
        return None
    n = norm(name)
    if n in _ALIASES:
        return _ALIASES[n]
    for part in re.split(r"[/,()-]| de ", str(name)):
        p = norm(part)
        if p in _ALIASES:
            return _ALIASES[p]
    return None


_MUNI_INDEX = None


def _load_municipios():
    global _MUNI_INDEX
    if _MUNI_INDEX is not None:
        return _MUNI_INDEX
    idx = {}
    path = os.path.join(DATA_DIR, "municipios.json")
    try:
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
    except OSError:
        rows = []
    for row in rows:
        code = row["id"][:2]
        name = row["nm"]
        variants = set()
        for piece in name.split("/"):
            piece = piece.strip()
            variants.add(piece)
            # "Palmas de Gran Canaria, Las" -> "Las Palmas de Gran Canaria"
            if "," in piece:
                base, art = piece.rsplit(",", 1)
                variants.add("%s %s" % (art.strip(), base.strip()))
                variants.add(base.strip())
        for v in variants:
            key = norm(v)
            if key and key not in idx:  # el primero gana (capitales suelen ir primero por provincia)
                idx[key] = code
    # Capitales y grandes ciudades: forzar para evitar homónimos
    idx.update({
        "madrid": "28", "barcelona": "08", "valencia": "46", "sevilla": "41", "zaragoza": "50",
        "malaga": "29", "murcia": "30", "palma": "07", "palma de mallorca": "07",
        "las palmas de gran canaria": "35", "bilbao": "48", "alicante": "03", "cordoba": "14",
        "valladolid": "47", "vigo": "36", "gijon": "33", "oviedo": "33", "santander": "39",
        "pamplona": "31", "iruna": "31", "donostia": "20", "san sebastian": "20",
        "vitoria gasteiz": "01", "vitoria": "01", "logrono": "26", "toledo": "45", "burgos": "09",
        "salamanca": "37", "granada": "18", "cadiz": "11", "jerez de la frontera": "11",
        "almeria": "04", "huelva": "21", "jaen": "23", "santa cruz de tenerife": "38",
        "a coruna": "15", "la coruna": "15", "santiago de compostela": "15", "lugo": "27",
        "ourense": "32", "pontevedra": "36", "badajoz": "06", "caceres": "10", "merida": "06",
        "albacete": "02", "ciudad real": "13", "cuenca": "16", "guadalajara": "19", "huesca": "22",
        "teruel": "44", "leon": "24", "palencia": "34", "segovia": "40", "soria": "42",
        "zamora": "49", "avila": "05", "girona": "17", "lleida": "25", "tarragona": "43",
        "castellon de la plana": "12", "castello de la plana": "12", "elche": "03", "elx": "03",
        "cartagena": "30", "lorca": "30", "marbella": "29", "benidorm": "03", "ibiza": "07",
        "eivissa": "07", "mahon": "07", "mao": "07", "ceuta": "51", "melilla": "52",
    })
    _MUNI_INDEX = idx
    return idx


def province_code_from_city(city):
    if not city:
        return None
    idx = _load_municipios()
    n = norm(city)
    if n in idx:
        return idx[n]
    # "Donostia / San Sebastián", "Castelló de la Plana (Castellón)"
    for part in re.split(r"[/(),]", str(city)):
        p = norm(part)
        if p in idx:
            return idx[p]
    return None


def resolve_province(province=None, city=None, code=None):
    """Devuelve (code, name, ccaa) o (None, None, None)."""
    c = None
    if code:
        c = str(code).zfill(2)
        if c not in PROV_BY_CODE:
            c = None
    if not c and province:
        c = province_code_from_name(province)
    if not c and city:
        c = province_code_from_city(city)
    if not c and province:
        c = province_code_from_city(province)
    if not c:
        return None, None, None
    p = PROV_BY_CODE[c]
    return c, p["name"], p["ccaa"]

# ---------------------------------------------------------------- Eventos


# Las visitas sin fecha única (museos, monumentos, salas) llevan este subtype.
# La web las muestra como "Visita permanente" y no las trata como un evento de un día.
PERMANENT_SUBTYPE = "Permanente"


def is_permanent(ev):
    return bool(ev) and ev.get("subtype") == PERMANENT_SUBTYPE


def make_id(source, *parts):
    raw = source + "|" + "|".join(str(p or "") for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]


def event(source, source_id, title, start, **kw):
    """Construye un evento normalizado. Devuelve None si falta lo mínimo."""
    title = strip_html(title, 200)
    start = parse_date(start)
    if not title or not start:
        return None
    end = parse_date(kw.get("end")) or start
    if end < start:
        end = start
    max_end = iso(today() + timedelta(days=400))
    if end > max_end:  # fechas de fin erróneas (p. ej. 2924) o "permanentes"
        end = max_end
    t = kw.get("time") or ""
    if t == "00:00":
        t = ""
    code, pname, ccaa = resolve_province(kw.get("province"), kw.get("city"), kw.get("province_code"))
    ev = {
        "id": make_id(source, source_id or title + start),
        "title": title,
        "description": strip_html(kw.get("description"), 220),
        "category": kw.get("category") or "otros",
        "subtype": strip_html(kw.get("subtype"), 60),
        "start": start,
        "end": end,
        "time": t,
        "province": pname or "",
        "province_code": code or "",
        "ccaa": ccaa or "",
        "city": strip_html(kw.get("city"), 80),
        "venue": strip_html(kw.get("venue"), 120),
        "address": strip_html(kw.get("address"), 160),
        "lat": kw.get("lat"),
        "lon": kw.get("lon"),
        "price": strip_html(kw.get("price"), 80),
        "free": kw.get("free"),
        "url": clean_url(kw.get("url")),
        "tickets_url": clean_url(kw.get("tickets_url")),
        "image": clean_url(kw.get("image")),
        "source": source,
        "audience": strip_html(kw.get("audience"), 60),
    }
    for k in ("lat", "lon"):
        try:
            ev[k] = round(float(ev[k]), 5) if ev[k] not in (None, "") else None
        except (TypeError, ValueError):
            ev[k] = None
    if ev["free"] is None:
        p = norm(ev["price"])
        if p:
            ev["free"] = bool(re.search(r"\b(gratis|gratuit|libre|free|doan|dohain)", p)) or p in ("0", "0 eur", "0 euros")
    return ev


# ---------------------------------------------------------------- iCalendar

def parse_ics(text):
    """Parser mínimo de VEVENT: devuelve una lista de dicts con las propiedades (sin parámetros)."""
    lines = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            key, val = line.split(":", 1)
            key = key.split(";", 1)[0].upper()
            val = val.replace("\\n", "\n").replace("\\,", ",").replace("\;", ";")
            cur.setdefault(key, val)
    return events
