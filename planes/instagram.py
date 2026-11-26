# -*- coding: utf-8 -*-
"""Carruseles de Instagram por ciudad: «Este finde en Bilbao», «Gratis este finde en Bilbao», «Con niños este finde
en Bilbao» y, en temporada, «Puente de diciembre en Bilbao».

Cada día se preparan con la agenda del día (como el boletín): portada, 5 planes elegidos (uno por diapositiva) y
cierre, en 1080×1350 (el formato vertical de Instagram), más el texto del post con hashtags. tools/instagram.py
los dibuja y los deja en site/ig/ (noindex, fuera del sitemap y de git) para guardarlos desde el móvil, junto con
los reels de la rama «reels».

No se inventa nada: cada plan sale de la agenda, con su día, hora, lugar y precio tal como vienen. No se usan las
fotos de los organizadores (tienen derechos): las diapositivas son de texto, con los colores de Planika.
"""
import html
import re
from datetime import datetime

from . import boletin
from .classify import CATEGORIES
from .util import country, display_title, iso, norm

PER_CITY = 5      # planes por carrusel
MIN_PLANS = 7     # ciudades con al menos estos planes el finde (o el puente): 5 elegidos de 7 como poco
MAX_CITIES = 20
MIN_THEME = 6     # «gratis» y «con niños»: ciudades con al menos estos planes de ese tipo
# Primero las ciudades del público de Planika; después, las demás por número de planes
CITY_ORDER = ["bilbao", "vitoria-gasteiz", "donostia-san-sebastian", "pamplona-iruna", "madrid", "barcelona",
              "zaragoza", "valencia", "sevilla", "malaga", "santander", "logrono", "burgos", "oviedo", "gijon",
              "valladolid", "salamanca", "a-coruna", "vigo", "granada", "cordoba", "alicante", "murcia", "palma"]
# Temas de carrusel: (etiqueta de la portada, «de los N … que hay», «Hay N planes …», final del cierre, hashtags)
KINDS = {
    "finde": ("Este finde en", "que hay en la agenda", "planes", "este finde en", ["#PlanesFinde"]),
    "gratis": ("Gratis este finde en", "planes gratis que hay", "planes gratis", "este finde en", ["#PlanesGratis", "#PlanesFinde"]),
    "ninos": ("Con niños este finde en", "planes con niños que hay", "planes con niños", "este finde en",
              ["#PlanesConNiños", "#PlanesEnFamilia"]),
    "puente": ("Puente de diciembre en", "que hay en el puente", "planes", "en el puente en", ["#PuenteDeDiciembre", "#Puente"]),
}
KIND_ORDER = ["finde", "gratis", "ninos", "puente"]
KIND_TITLE = {"finde": "Este finde", "gratis": "Gratis este finde", "ninos": "Con niños este finde", "puente": "Puente de diciembre"}
_KIDS = re.compile(r"\b(nin|infan|famil|haur|nens|txiki|peques)")
# Lo que no se anuncia: suspendido, agotado o que no es un plan de finde (congresos, jornadas técnicas…)
_SKIP = re.compile(r"\b(suspendid[oa]s?|cancelad[oa]s?|aplazad[oa]s?|agotad[oa]s?|sold out|completo|congreso|seminario|asamblea|"
                   r"jornadas? tecnicas?)\b")
# Primero planes de ocio; las charlas y «otros» solo si no hay bastantes
_LOW = {"charlas", "otros"}
CAT = {k: (n, i) for k, n, i in CATEGORIES}
INK, YELLOW, PINK, TEAL, LILAC, HOT, PAGE = boletin.INK, boletin.YELLOW, boletin.PINK, boletin.TEAL, boletin.LILAC, boletin.HOT, boletin.PAGE
BG = [YELLOW, PINK, TEAL, LILAC]
_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def slugify(s):
    s = norm(s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def short_city(name):
    """«Donostia / San Sebastián» → «Donostia»: en la portada cabe mejor un nombre."""
    return name.split(" / ")[0].strip()


def is_kids(e):
    return e.get("category") in ("infantil", "parques") or bool(_KIDS.search(norm(e.get("audience") or "")))


def _groups(events, first, last):
    """{(código, ciudad): [planes de esas fechas, mejores primero]} y sus nombres."""
    a, b = iso(first), iso(last)
    pool = [e for e in events if boletin._in_weekend(e, a, b) and country(e.get("province_code")) == "ES"]
    pool.sort(key=lambda e: (-boletin.score(e), boletin._day(e, a, b), e.get("time") or "99", e["title"]))
    pool = [e for e in pool if not _SKIP.search(norm("%s %s" % (display_title(e), e.get("price") or "")))]
    groups, names = {}, {}
    for e in pool:
        k = (e["province_code"], norm(e.get("city") or ""))
        if not k[1]:
            continue
        groups.setdefault(k, []).append(e)
        names.setdefault(k, (e["city"], e.get("province") or ""))
    return groups, names


def _ranked(groups, names, minimum, limit):
    rank = {c: i for i, c in enumerate(CITY_ORDER)}
    keys = [k for k in groups if len(groups[k]) >= minimum]
    keys.sort(key=lambda k: (rank.get(slugify(names[k][0]), 99), -len(groups[k])))
    return keys[:limit]


def _puente(t0):
    """(primer día, último día) del puente de diciembre si empieza en los próximos 16 días o está en curso; si no, None."""
    from datetime import timedelta
    from .publish import puente_diciembre
    a, b = puente_diciembre(t0.year)
    return (max(a, t0), b) if a - timedelta(days=16) <= t0 <= b else None


def editions(events, t0):
    """[{kind, title, city, province, code, slug, total, free, plans, fri, sun, first}]: los carruseles del día.
    Este finde en las MAX_CITIES ciudades con más agenda; «gratis» y «con niños» donde hay MIN_THEME planes de ese
    tipo; y, las dos semanas antes del puente de diciembre, el puente en las ciudades con más planes."""
    fri, sun, first = boletin.weekend(t0)
    groups, names = _groups(events, first, sun)
    out = []
    cities = _ranked(groups, names, MIN_PLANS, MAX_CITIES)
    for kind in ("finde", "gratis", "ninos"):
        for k in cities:
            items = groups[k]
            if kind == "gratis":
                items = [e for e in items if e.get("free")]
            elif kind == "ninos":
                items = [e for e in items if is_kids(e)]
            if kind != "finde" and len(items) < MIN_THEME:
                continue
            out.append(_edition(kind, names[k], k[0], items, fri, sun, first))
    pw = _puente(t0)
    if pw:
        pg, pn = _groups(events, pw[0], pw[1])
        for k in _ranked(pg, pn, MIN_PLANS, MAX_CITIES):
            out.append(_edition("puente", pn[k], k[0], pg[k], pw[0], pw[1], pw[0]))
    return out


def _edition(kind, name, code, items, fri, sun, first):
    a, b = iso(first), iso(sun)
    picked, cats, titles = [], {}, set()
    for limit, low in ((1, False), (2, False), (9, True)):  # variedad: primero uno de cada tipo de plan
        for e in items:
            t = norm(display_title(e))
            if len(picked) >= PER_CITY or e in picked or t in titles or cats.get(e["category"], 0) >= limit:
                continue
            if e["category"] in _LOW and not low:
                continue
            picked.append(e)
            titles.add(t)
            cats[e["category"]] = cats.get(e["category"], 0) + 1
    picked.sort(key=lambda e: (boletin._day(e, a, b), e.get("time") or "99"))
    slug = slugify(name[0]) + {"finde": "", "gratis": "-gratis", "ninos": "-con-ninos", "puente": "-puente"}[kind]
    return {"kind": kind, "title": "%s %s" % (KINDS[kind][0], name[0]), "city": name[0], "province": name[1],
            "code": code, "slug": slug, "total": len(items), "free": sum(1 for e in items if e.get("free")),
            "plans": picked, "fri": fri, "sun": sun, "first": first}


def date_range(ed):
    a, b = ed["first"], ed["sun"]
    if a == b:
        return "%d %s" % (a.day, _MES[a.month - 1][:3])
    if a.month == b.month:
        return "%d–%d %s" % (a.day, b.day, _MES[a.month - 1][:3])
    return "%d %s–%d %s" % (a.day, _MES[a.month - 1][:3], b.day, _MES[b.month - 1][:3])


def when(e, ed):
    d = datetime.strptime(boletin._day(e, iso(ed["first"]), iso(ed["sun"])), "%Y-%m-%d")
    s = "%s %d" % (_DIAS[d.weekday()], d.day)
    return s + (" · " + e["time"] if e.get("time") else "")


def where(e):
    parts = [p for p in (e.get("venue"), e.get("city")) if p]
    return " · ".join(dict.fromkeys(parts))


def price(e):
    """Precio corto tal como viene («5 €», «Desde 23 €»), sin «Precio:»; si no hay cifra, nada."""
    if e.get("free"):
        return "Gratis"
    p = re.sub(r"^(precios?|preus?|prezioa|general|entradas?)\s*:\s*", "", (e.get("price") or "").strip(), flags=re.I)
    p = re.sub(r"\s*€", " €", p)
    if not re.search(r"\d", p) or "consult" in norm(p):
        return ""
    return p if len(p) <= 24 else ""


def _hashtag(s):
    s = re.sub(r"[^A-Za-z0-9]", "", norm(s).title().replace(" ", ""))
    return s


def caption(ed):
    """Texto del post: los 5 planes con día, hora y lugar, y hashtags de la ciudad."""
    kind = ed.get("kind", "finde")
    icon = {"finde": "🗓", "gratis": "🆓", "ninos": "🧒", "puente": "🎒"}[kind]
    of = {"finde": "que hay", "gratis": "gratis que hay", "ninos": "con niños que hay", "puente": "que hay"}[kind]
    lines = ["%s %s %s (%s): %d planes elegidos de los %d %s 👇" % (
        icon, KINDS[kind][0], ed["city"], date_range(ed), len(ed["plans"]), ed["total"], of), ""]
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    for i, e in enumerate(ed["plans"]):
        extra = [where(e)] + (["gratis"] if e.get("free") else [])
        lines.append("%s %s — %s · %s" % (nums[i], display_title(e), when(e, ed).lower(), " · ".join(x for x in extra if x)))
    lines += ["", "Todos los planes %s, con horarios y mapa: planikaapp.com" % ("del puente" if kind == "puente" else "del finde"),
              "📌 Guárdalo y compártelo con quien se venga.", ""]
    tags = []
    for part in ed["city"].split(" / "):
        h = _hashtag(part)
        if h:
            tags += ["#%s" % h, "#Planes%s" % h, "#QueHacerEn%s" % h]
    tags += KINDS[kind][4] + ["#Planika"]
    lines.append(" ".join(dict.fromkeys(tags)))
    return "\n".join(lines)


# ---------------------------------------------------------------- diapositivas (HTML que se dibuja a 1080×1350)

LOGO = ('<svg viewBox="1.85 0.35 64 64" width="%d" height="%d"><g transform="translate(3.7 3.7)" fill="#1a1033"><rect x="4" y="8" width="56" '
        'height="51" rx="12.5"/></g><rect x="5.5" y="9.5" width="53" height="48" rx="11" fill="#fff" stroke="#1a1033" stroke-width="3"/>'
        '<path d="M5.5 26V20.5a11 11 0 0 1 11-11h31a11 11 0 0 1 11 11V26z" fill="#ff3d81" stroke="#1a1033" stroke-width="3"/>'
        '<circle cx="20" cy="41" r="5" fill="#ffd23f" stroke="#1a1033" stroke-width="2.5"/><circle cx="32" cy="41" r="5" fill="#4fd6c8" '
        'stroke="#1a1033" stroke-width="2.5"/><circle cx="44" cy="41" r="5" fill="#a78bfa" stroke="#1a1033" stroke-width="2.5"/>'
        '<rect x="16" y="2" width="6" height="13" rx="3" fill="#1a1033"/><rect x="42" y="2" width="6" height="13" rx="3" fill="#1a1033"/></svg>')

CSS = """*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:Inter,Roboto,"Helvetica Neue",Arial,sans-serif;color:%(ink)s;background:%(page)s;
 background-image:radial-gradient(#e9e3f2 2.2px,transparent 2.2px);background-size:34px 34px;position:relative}
.top{position:absolute;left:64px;right:64px;top:56px;display:flex;align-items:center;gap:18px}
.brand{font-size:52px;font-weight:900;letter-spacing:-.02em;background:linear-gradient(90deg,#ff3d81,#ff9f1c,#2ec4b6,#7b5cff);
 -webkit-background-clip:text;background-clip:text;color:transparent}
.chip{margin-left:auto;font-size:30px;font-weight:800;background:#fff;border:4px solid %(ink)s;border-radius:999px;padding:8px 24px;box-shadow:5px 5px 0 %(ink)s}
.foot{position:absolute;left:64px;right:64px;bottom:56px;display:flex;align-items:center;justify-content:space-between;font-size:30px;font-weight:800}
.foot .url{background:%(ink)s;color:#fff;border-radius:999px;padding:12px 26px}
.sticker{display:inline-block;background:%(yellow)s;border:5px solid %(ink)s;border-radius:22px;padding:10px 30px;box-shadow:9px 9px 0 %(ink)s;
 font-weight:900;transform:rotate(-2deg)}
.card{position:absolute;left:64px;right:64px;top:190px;bottom:170px;border:6px solid %(ink)s;border-radius:44px;box-shadow:16px 16px 0 %(ink)s;
 padding:64px 60px;display:flex;flex-direction:column}
.pills{display:flex;gap:16px;flex-wrap:wrap}
.pill{font-size:34px;font-weight:800;background:#fff;border:4px solid %(ink)s;border-radius:999px;padding:8px 26px}
.pill.free{background:%(hot)s;color:#fff}
.title{font-size:%(tsize)spx;line-height:1.12;font-weight:900;letter-spacing:-.015em;margin:46px 0 auto;
 display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
.row{font-size:42px;font-weight:800;margin-top:22px;display:flex;gap:18px;align-items:flex-start}
.row.small{font-size:36px;font-weight:700}
.row span:first-child{flex:none}
"""


def _page(body, tsize=84):
    css = CSS % dict(ink=INK, page=PAGE, yellow=YELLOW, hot=HOT, tsize=tsize)
    return '<!doctype html><html lang="es"><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>' % (css, body)


def _top(ed, chip):
    return '<div class="top">%s<span class="brand">Planika</span><span class="chip">%s</span></div>' % (LOGO % (70, 70), html.escape(chip))


def _title_size(t):
    n = len(t)
    return 92 if n <= 34 else 80 if n <= 60 else 68 if n <= 90 else 58


def slides(ed):
    """[html] de la portada, una diapositiva por plan y el cierre."""
    city = ed["city"]
    name = short_city(city)
    big = 170 if len(name) <= 7 else 140 if len(name) <= 10 else 112 if len(name) <= 14 else 92
    n = len(ed["plans"])
    free_n = sum(1 for e in ed["plans"] if e.get("free"))
    kind = ed.get("kind", "finde")
    kd = KINDS[kind]
    out = [_page(
        _top(ed, date_range(ed)) +
        '<div style="position:absolute;left:64px;right:64px;top:300px">'
        '<div class="sticker" style="font-size:64px">%s</div>'
        '<div style="font-size:%dpx;font-weight:900;line-height:1;letter-spacing:-.03em;margin:46px 0 0;overflow-wrap:anywhere">%s</div>'
        '<div style="font-size:52px;font-weight:800;margin-top:46px;line-height:1.25">%d planes elegidos%s</div>'
        '<div style="font-size:38px;font-weight:600;margin-top:18px;color:#4a4263">de los %d %s%s</div>'
        '<ul style="list-style:none;margin-top:54px;display:flex;flex-direction:column;gap:18px">%s</ul></div>'
        '<div class="foot"><span class="url">planikaapp.com</span><span>Desliza →</span></div>'
        % (html.escape(kd[0]), big, html.escape(name), n, (" · %d gratis" % free_n) if free_n and kind != "gratis" else "", ed["total"],
           html.escape(kd[1]), (" (%d gratis)" % ed["free"]) if ed["free"] and kind in ("finde", "puente") else "",
           "".join('<li style="font-size:36px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">%s %s</li>'
                   % (CAT.get(e.get("category"), ("", "✨"))[1], html.escape(display_title(e))) for e in ed["plans"])))]
    for i, e in enumerate(ed["plans"]):
        cname, icon = CAT.get(e.get("category"), ("Plan", "✨"))
        t = display_title(e)
        pills = '<span class="pill">%s %s</span>' % (icon, html.escape(cname))
        p = price(e)
        if p:
            pills += '<span class="pill%s">%s</span>' % (" free" if e.get("free") else "", html.escape(p))
        body = (_top(ed, "%d/%d · %s" % (i + 1, n, name)) +
                '<div class="card" style="background:%s"><div class="pills">%s</div><div class="title">%s</div>'
                '<div class="row"><span>📅</span><span>%s</span></div>'
                '<div class="row small"><span>📍</span><span>%s</span></div></div>'
                '<div class="foot"><span>Más info en</span><span class="url">planikaapp.com</span></div>'
                % (BG[i % 4], pills, html.escape(t), html.escape(when(e, ed)), html.escape(where(e))))
        out.append(_page(body, tsize=_title_size(t)))
    out.append(_page(
        _top(ed, date_range(ed)) +
        '<div style="position:absolute;left:64px;right:64px;top:330px">'
        '<div style="font-size:64px;font-weight:900;line-height:1.15">Hay <span class="sticker" style="font-size:72px;background:%s">%d %s</span></div>'
        '<div style="font-size:64px;font-weight:900;line-height:1.15;margin-top:30px">%s %s</div>'
        '<div style="font-size:46px;font-weight:700;margin-top:60px;line-height:1.35">Todos, con horarios y mapa, en<br>'
        '<span style="background:%s;color:#fff;border-radius:999px;padding:6px 26px;display:inline-block;margin-top:16px;font-weight:900">planikaapp.com</span></div>'
        '<div style="font-size:42px;font-weight:800;margin-top:70px">📌 Guárdalo y compártelo<br>con quien se venga</div></div>'
        '<div class="foot"><span>@planikaapp</span><span>%s</span></div>'
        % (TEAL, ed["total"], html.escape(kd[2]), html.escape(kd[3]), html.escape(name).replace("-", "\u2011"), INK, LOGO % (80, 80))))
    return out


# ---------------------------------------------------------------- página para guardarlos desde el móvil

def index_page(eds, files, updated, reels=()):
    """files: {slug: [rutas relativas de las imágenes]}; reels: [{file, poster, title, caption, kind}] (rutas relativas)."""
    groups = {k: [] for k in KIND_ORDER}
    for ed in eds:
        imgs = files.get(ed["slug"]) or []
        if not imgs:
            continue
        cap = caption(ed)
        groups[ed.get("kind", "finde")].append(
            '<section class="ed" data-slug="%(slug)s" data-city="%(cslug)s" data-kind="%(kind)s"><h3>%(title)s <small>%(n)d imágenes</small></h3>'
            '<div class="strip">%(imgs)s</div>'
            '<p class="acts"><button type="button" class="btn primary" data-save>📲 Guardar las %(n)d imágenes</button> '
            '<button type="button" class="btn" data-copy>📋 Copiar el texto</button></p>'
            '<pre class="cap">%(cap)s</pre></section>'
            % dict(slug=html.escape(ed["slug"]), cslug=html.escape(slugify(ed["city"])), kind=ed.get("kind", "finde"),
                   title=html.escape(ed.get("title") or ed["city"]),
                   n=len(imgs), cap=html.escape(cap),
                   imgs="".join('<a href="%s" download><img src="%s" alt="Diapositiva %d" loading="lazy" width="270" height="338"></a>'
                                % (html.escape(f), html.escape(f), k + 1) for k, f in enumerate(imgs))))
    reel_html = "".join(
        '<section class="ed reel" data-file="%(file)s"><h3>%(title)s <small>%(kind)s</small></h3>'
        '<video controls playsinline preload="none" poster="%(poster)s" src="%(file)s"></video>'
        '<p class="acts"><button type="button" class="btn primary" data-save-video>📲 Guardar el vídeo</button> '
        '<button type="button" class="btn" data-copy>📋 Copiar el texto</button></p>'
        '<pre class="cap">%(cap)s</pre></section>'
        % dict(file=html.escape(r["file"]), poster=html.escape(r.get("poster") or ""), title=html.escape(r.get("title") or r["file"]),
               kind=html.escape({"viral": "Viral", "explicacion": "Explicación de la web"}.get(r.get("kind"), "")),
               cap=html.escape(r.get("caption") or ""))
        for r in reels)
    rng = {k: date_range(next(e for e in eds if e.get("kind", "finde") == k)) for k in KIND_ORDER
           if any(e.get("kind", "finde") == k for e in eds)}
    nav = ['<a href="#reels" data-kind="reels">🎬 Reels (%d)</a>' % len(reels)] if reels else []
    nav += ['<a href="#%s" data-kind="%s">%s (%d)</a>' % (k, k, KIND_TITLE[k], len(groups[k])) for k in KIND_ORDER if groups[k]]
    body = ('<h2 class="grp" id="reels">🎬 Reels</h2>' + reel_html) if reels else ""
    body += "".join('<h2 class="grp" id="%s">%s <small>%s</small></h2>%s' % (k, KIND_TITLE[k], html.escape(rng.get(k, "")), "".join(groups[k]))
                    for k in KIND_ORDER if groups[k])
    cities = sorted({(slugify(e["city"]), e["city"]) for e in eds}, key=lambda c: norm(c[1]))
    city_opts = "".join('<option value="%s">%s</option>' % (html.escape(c), html.escape(n)) for c, n in cities)
    return """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Instagram · Planika</title>
<style>
body{margin:0;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:%(ink)s;background:%(page)s}
main{max-width:900px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:26px;margin:6px 0 4px} h2.grp{font-size:24px;margin:28px 0 12px} h2 small,h3 small{font-weight:600;color:#4a4263;font-size:14px}
h3{font-size:19px;margin:0 0 10px}
.note{color:#4a4263;margin:0 0 12px}
.jump{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}.jump a{font-weight:800;color:%(ink)s;background:#fff;border:2px solid %(ink)s;border-radius:999px;padding:6px 12px;text-decoration:none}
.filter{margin:0 -16px 6px;padding:8px 16px;position:sticky;top:0;z-index:5;background:%(page)s;border-bottom:2px solid #e9e3f2}
.filter select{font:inherit;font-weight:700;padding:8px 10px;border:2px solid %(ink)s;border-radius:12px;background:#fff;max-width:100%%}
.filter small{display:block;color:#4a4263;font-weight:700;margin-top:4px}
.ed{background:#fff;border:3px solid %(ink)s;border-radius:18px;box-shadow:4px 4px 0 %(ink)s;padding:14px;margin:0 0 22px}
.strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;scroll-snap-type:x mandatory}
.strip img{width:200px;height:250px;border:2px solid %(ink)s;border-radius:10px;scroll-snap-align:start;display:block}
.reel video{display:block;width:100%%;max-width:300px;aspect-ratio:9/16;background:#000;border:2px solid %(ink)s;border-radius:12px}
.btn{font:inherit;font-weight:800;border:2px solid %(ink)s;border-radius:999px;background:#fff;padding:10px 16px;box-shadow:3px 3px 0 %(ink)s;margin:4px 6px 4px 0;color:%(ink)s}
.btn.primary{background:%(hot)s;color:#fff}
.cap{white-space:pre-wrap;font-size:14px;line-height:1.45;font-family:inherit;background:%(page)s;border:2px dashed #cfc7dc;border-radius:12px;padding:10px;margin:10px 0 0}
</style></head><body><main>
<h1>📸 Instagram de Planika</h1>
<p class="note">Hechos con la agenda del %(updated)s. En el iPhone, «Guardar» lleva las imágenes o el vídeo a Fotos de una vez
(o mantén pulsada cada imagen). Después, «Copiar el texto» para el pie del post. Esta página no está enlazada ni sale en Google.</p>
<nav class="jump">%(nav)s</nav>
<p class="filter"><label>Ciudad: <select id="city"><option value="">Todas</option>%(city_opts)s</select></label><small id="cityNote"></small></p>
%(body)s
</main>
<script>
function copyCap(sec, b) {
  var t = sec.querySelector('.cap').textContent;
  (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { b.textContent = '✓ Texto copiado'; })
    .catch(function () { var r = document.createRange(); r.selectNodeContents(sec.querySelector('.cap')); var s = getSelection(); s.removeAllRanges(); s.addRange(r); });
}
function shareFiles(urls, names, type, b) {
  return Promise.all(urls.map(function (u, k) {
    return fetch(u).then(function (r) { return r.blob(); }).then(function (bl) { return new File([bl], names[k], { type: type }); });
  })).then(function (files) {
    if (navigator.canShare && navigator.canShare({ files: files })) return navigator.share({ files: files });
    files.forEach(function (f, k) { setTimeout(function () { var a = document.createElement('a'); a.href = urls[k]; a.download = f.name; document.body.appendChild(a); a.click(); a.remove(); }, k * 300); });
  }).catch(function () { b.textContent = 'Mantén pulsado para guardarlo'; });
}
document.querySelectorAll('.ed').forEach(function (sec) {
  sec.querySelector('[data-copy]').addEventListener('click', function () { copyCap(sec, this); });
  var s = sec.querySelector('[data-save]');
  if (s) s.addEventListener('click', function () {
    var imgs = Array.prototype.map.call(sec.querySelectorAll('.strip img'), function (i) { return i.getAttribute('src'); });
    shareFiles(imgs, imgs.map(function (u, k) { return sec.dataset.slug + '-' + (k + 1) + '.jpg'; }), 'image/jpeg', this);
  });
  var v = sec.querySelector('[data-save-video]');
  if (v) v.addEventListener('click', function () {
    var u = sec.dataset.file; shareFiles([u], [u.split('/').pop()], 'video/mp4', this);
  });
});
// Filtro por ciudad: solo sus carruseles (los reels no son de una ciudad y se esconden mientras se filtra), sin los
// temas vacíos, y la página baja hasta ellos. Se recuerda en la dirección (#ciudad=bilbao) para volver a la misma.
function applyCity(c, scroll) {
  var sel = document.getElementById('city');
  document.querySelectorAll('.ed[data-city]').forEach(function (sec) { sec.hidden = !!c && sec.dataset.city !== c; });
  document.querySelectorAll('.ed.reel').forEach(function (sec) { sec.hidden = !!c; });
  document.querySelectorAll('h2.grp, .jump a').forEach(function (el) {
    var k = el.id || el.dataset.kind;
    el.hidden = !!c && (k === 'reels' || !document.querySelector('.ed[data-kind="' + k + '"][data-city="' + c + '"]'));
  });
  var n = c ? document.querySelectorAll('.ed[data-city="' + c + '"]').length : 0;
  document.getElementById('cityNote').textContent = c ? (n === 1 ? '1 carrusel' : n + ' carruseles') + ' de ' + sel.options[sel.selectedIndex].text : '';
  try { history.replaceState(null, '', c ? '#ciudad=' + c : location.pathname + location.search); } catch (e) {}
  if (c && scroll) {
    var first = document.querySelector('h2.grp:not([hidden])');
    if (first) window.scrollTo({ top: first.getBoundingClientRect().top + window.scrollY - document.querySelector('.filter').offsetHeight - 8, behavior: 'smooth' });
  }
}
document.getElementById('city').addEventListener('change', function () { applyCity(this.value, true); });
(function () {
  var m = /ciudad=([a-z0-9-]+)/.exec(location.hash), sel = document.getElementById('city');
  if (m && sel.querySelector('option[value="' + m[1] + '"]')) { sel.value = m[1]; applyCity(m[1], true); }
})();
</script></body></html>
""" % dict(ink=INK, page=PAGE, hot=HOT, updated=html.escape(updated), nav=" ".join(nav), city_opts=city_opts,
           body=body or "<p>Hoy no hay ciudades con planes suficientes.</p>")
