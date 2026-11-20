# -*- coding: utf-8 -*-
"""Salas Jimmy Jazz y Kubik (Vitoria-Gasteiz): conciertos y sesiones de club desde su propia web.

Las dos salas son de la misma empresa y publican su agenda en el mismo WordPress como entradas de la
categoría «Agenda» (API pública /wp-json/wp/v2/posts). La fecha va en el extracto sin año
(«Viernes 20 Noviembre»): el año es el próximo en que ese día cae en ese día de la semana; si no
cuadra con ninguno, el plan se descarta en vez de adivinar. Puertas, hora de actuación, precios y
enlace de entradas salen del texto del post. Los conciertos suelen estar también en Open Data Euskadi
con otro título: fetch_events.dedupe_venue los une (misma sala, mismo día, casi las mismas palabras).

Las sesiones de club abren a la 1:00 de la madrugada: se dejan en el día que anuncia la sala, sin hora
(«las 01:00 del viernes» se leería como la noche del jueves), y la descripción dice «noche del viernes 20
al sábado 21, puertas a la 1:00».
"""
import html
import re
from datetime import date, timedelta

from .classify import classify
from .util import event, http_json, iso, norm, today

NAME = "Salas Jimmy Jazz y Kubik"
HOME = "https://jimmyjazzgasteiz.com/"
API = "https://jimmyjazzgasteiz.com/wp-json/wp/v2/posts"
CAT_AGENDA, CAT_CONCIERTOS, CAT_DJS = 1336, 30, 5  # categorías en castellano (las «-eu» repiten en euskera)
VENUES = {  # nombre como lo publica Open Data Euskadi, para unir los duplicados
    "jimmy": ("Sala Jimmy Jazz", "Coronación de la Virgen Blanca 4"),
    "kubik": ("Sala Kubik", "Bakea Kalea 5"),
}
_DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]
_DATE = re.compile(r"(?:\b(%s)\s+)?\b(\d{1,2})(?:\s+(\d{1,2}))?\s+(?:de\s+)?(%s)\b" % ("|".join(_DIAS), "|".join(_MESES)))
_SKIP_URL = re.compile(r"soundcloud|youtu|maps\.app|goo\.gl/maps|instagram|facebook|twitter|tiktok|spotify|"
                       r"/wp-content/|vitoria-gasteiz\.org|jimmyjazzgasteiz\.com/(?!web)|kubikvitoria\.com", re.I)


def _text(s):
    s = re.sub(r"\[/?et_pb[^\]]*\]", " ", s or "")  # atajos del maquetador Divi
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _when(excerpt, t0):
    """(inicio, fin) del último «[día de la semana] D[–D2] mes» del extracto, o None si no cuadra."""
    found = list(_DATE.finditer(norm(excerpt)))
    if not found:
        return None
    m = found[-1]
    wd = _DIAS.index(m.group(1)) if m.group(1) else None
    d1, d2, month = int(m.group(2)), int(m.group(3) or 0), _MESES.index(m.group(4)) + 1
    for y in (t0.year, t0.year + 1):
        try:
            start = date(y, month, d1)
        except ValueError:
            continue
        if start < t0 - timedelta(days=1) or (wd is not None and start.weekday() != wd):
            continue
        end = start
        if d2 > d1:
            try:
                end = date(y, month, d2)
            except ValueError:
                pass
        return start, end
    return None


def _time(text):
    """Hora de actuación (o, si no la hay, de puertas): (etiqueta, hora, minuto) o None."""
    for label, rx in (("Actuación", "actuaci[oó]n"), ("Puertas", "puertas")):
        m = re.search(rx + r"\s*[–>:-]?\s*(\d{1,2})[:.](\d{2})", text, re.I)
        if m and int(m.group(1)) <= 24 and int(m.group(2)) < 60:
            return label, int(m.group(1)) % 24, int(m.group(2))
    return None


def _at(h, mi):
    return "a medianoche" if (h, mi) == (0, 0) else "a la%s %d:%02d" % ("" if h == 1 else "s", h, mi)


def _dia(d):
    return _DIAS[d.weekday()].replace("miercoles", "miércoles").replace("sabado", "sábado")


def _price(text):
    if re.search(r"entrada libre|entrada gratuita|\bgratis\b|doan", text, re.I):
        return "Entrada libre", True
    parts = []
    for label, rx in (("early bird", r"early\s*bird"), ("anticipada", r"anticipada"), ("taquilla", r"taquilla"), ("VIP", r"\bvip")):
        m = re.search(rx + r"\s*:?\s*(\d+(?:[,.]\d{1,2})?)\s*€", text, re.I)
        if m:
            parts.append("%s %s €" % (label, m.group(1)))
    if not parts:
        return "", None
    s = ", ".join(parts)
    return s[0].upper() + s[1:], None


def _tickets(raw):
    for u in re.findall(r"https?://[^\s\"'«»″\]\[]+", html.unescape(raw or "")):
        u = re.sub(r"(&#8243;|&#8221;|″|»|\"|')+$", "", html.unescape(u))
        if not _SKIP_URL.search(u):
            return u
    return ""


def _image(raw):
    m = re.search(r"src=[\"»″]+(https://[^\"«»″\s]+?\.(?:jpe?g|png|webp))", html.unescape(raw or ""), re.I)
    return m.group(1) if m else ""


def _title(title, sub):
    """«Raimundo el Canastero» + «+ Broken Brothers Brass Band» → «Raimundo el Canastero + Broken Brothers Brass Band»;
    «Apetak» + «> I-F > I-REAL» → «Apetak: I-F, I-REAL»."""
    base = re.sub(r"\s*\((?:kubik)\)\s*$", "", title.strip(" >–-"), flags=re.I).strip()
    sub = sub.strip()
    if not sub:
        return base
    if sub.startswith("+"):
        return "%s %s" % (base, sub)
    if sub[0] in ">–-":
        parts = [p.strip() for p in re.split(r"(?:^|\s)[>–-]\s+", sub) if p.strip()]
        return "%s: %s" % (base, ", ".join(parts)) if base else ", ".join(parts)
    if sub[0].islower():
        return "%s %s" % (base, sub)
    return "%s: %s" % (base, sub)


def parse(posts, t0=None):
    t0 = t0 or today()
    out, seen = [], set()
    for p in posts:
        title = html.unescape(re.sub(r"<[^>]+>", "", (p.get("title") or {}).get("rendered") or "")).strip()
        excerpt = _text((p.get("excerpt") or {}).get("rendered"))
        raw = (p.get("content") or {}).get("rendered") or ""
        text = _text(raw)
        when = _when(excerpt, t0)
        if not title or not when:
            continue
        start, end = when
        # Lo que va antes de la fecha en el extracto es el subtítulo (teloneros, cartel de DJ…)
        dm = re.search(r"(?:(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\s+)?\d{1,2}"
                       r"(?:\s*[–-]\s*\d{1,2})?\s+(?:de\s+)?\w+\s*$", excerpt, re.I)
        sub = excerpt[:dm.start()].strip() if dm else ""
        link = p.get("link") or HOME
        kubik = "kubikvitoria.com" in link or re.search(r"\(kubik\)", title, re.I)
        venue, address = VENUES["kubik" if kubik else "jimmy"]
        cats = p.get("categories") or []
        dj = CAT_DJS in cats and CAT_CONCIERTOS not in cats
        name = _title(title, sub)
        key = (norm(name), iso(start))
        if key in seen:
            continue
        seen.add(key)
        t = _time(text)
        late = bool(t and t[1] < 6)
        hhmm = "%02d:%02d" % t[1:] if t and not late else ""
        if late:
            nxt = start + timedelta(days=1)
            when_txt = "Noche del %s %d al %s %d, puertas %s." % (_dia(start), start.day, _dia(nxt), nxt.day, _at(*t[1:]))
        else:
            when_txt = "%s %s." % (t[0], _at(*t[1:])) if t else ""
        price, free = _price(text)
        category = "musica" if dj else classify([], name, text[:300])
        if category == "otros":
            category = "musica"
        kind = "Sesión de club" if dj else {"musica": "Concierto", "escena": "Espectáculo"}.get(category, "Plan")
        desc = " ".join(x for x in ("%s en %s." % (kind, venue.replace("Sala ", "la sala ")), when_txt,
                                    "Entrada libre." if free else (price + "." if price else "")) if x)
        out.append(event(NAME, p.get("id") or link, name, iso(start), end=iso(end), time=hhmm,
                         city="Vitoria-Gasteiz", province="Álava", venue=venue, address=address, description=desc,
                         category=category, subtype="Sesión DJ" if dj else "", price=price, free=free, url=link,
                         tickets_url=_tickets(raw), image=_image(raw)))
    return [e for e in out if e]


def fetch(log):
    posts, page = [], 1
    while page <= 5:
        batch = http_json(API, params={"categories": CAT_AGENDA, "per_page": 100, "page": page,
                                       "_fields": "id,link,title,excerpt,content,categories"})
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    out = parse(posts)
    log("%s: %d planes de %d entradas de agenda" % (NAME, len(out), len(posts)))
    return out
