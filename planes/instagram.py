# -*- coding: utf-8 -*-
"""Carruseles de Instagram del fin de semana, uno por ciudad: «Este finde en Bilbao».

Cada día se preparan con la agenda del día (como el boletín): portada, 5 planes elegidos (uno por diapositiva) y
cierre, en 1080×1350 (el formato vertical de Instagram), más el texto del post con hashtags. tools/instagram.py
los dibuja y los deja en site/ig/ (noindex, fuera del sitemap y de git) para guardarlos desde el móvil.

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
MIN_PLANS = 15    # ciudades con al menos estos planes el finde
MAX_CITIES = 8
# Primero las ciudades del público de Planika; después, las demás por número de planes
CITY_ORDER = ["bilbao", "vitoria-gasteiz", "donostia-san-sebastian", "pamplona-iruna", "madrid", "barcelona",
              "zaragoza", "valencia", "sevilla", "malaga"]
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


def editions(events, t0):
    """[{city, province, code, slug, total, free, plans, fri, sun, first}] del finde en curso o el próximo."""
    fri, sun, first = boletin.weekend(t0)
    a, b = iso(first), iso(sun)
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
    keys = [k for k in groups if len(groups[k]) >= MIN_PLANS]
    rank = {c: i for i, c in enumerate(CITY_ORDER)}
    keys.sort(key=lambda k: (rank.get(slugify(names[k][0]), 99), -len(groups[k])))
    out = []
    for k in keys[:MAX_CITIES]:
        items = groups[k]
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
        out.append({"city": names[k][0], "province": names[k][1], "code": k[0], "slug": slugify(names[k][0]),
                    "total": len(items), "free": sum(1 for e in items if e.get("free")), "plans": picked,
                    "fri": fri, "sun": sun, "first": first})
    return out


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
    lines = ["🗓 Este finde en %s (%s): %d planes elegidos de los %d que hay 👇" % (
        ed["city"], date_range(ed), len(ed["plans"]), ed["total"]), ""]
    nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    for i, e in enumerate(ed["plans"]):
        extra = [where(e)] + (["gratis"] if e.get("free") else [])
        lines.append("%s %s — %s · %s" % (nums[i], display_title(e), when(e, ed).lower(), " · ".join(x for x in extra if x)))
    lines += ["", "Todos los planes del finde, con horarios y mapa: planikaapp.com",
              "📌 Guárdalo y compártelo con quien se venga.", ""]
    tags = []
    for part in ed["city"].split(" / "):
        h = _hashtag(part)
        if h:
            tags += ["#%s" % h, "#Planes%s" % h, "#QueHacerEn%s" % h]
    tags += ["#PlanesFinde", "#Planika"]
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
    out = [_page(
        _top(ed, date_range(ed)) +
        '<div style="position:absolute;left:64px;right:64px;top:300px">'
        '<div class="sticker" style="font-size:64px">Este finde en</div>'
        '<div style="font-size:%dpx;font-weight:900;line-height:1;letter-spacing:-.03em;margin:46px 0 0;overflow-wrap:anywhere">%s</div>'
        '<div style="font-size:52px;font-weight:800;margin-top:46px;line-height:1.25">%d planes elegidos%s</div>'
        '<div style="font-size:38px;font-weight:600;margin-top:18px;color:#4a4263">de los %d que hay en la agenda%s</div>'
        '<ul style="list-style:none;margin-top:54px;display:flex;flex-direction:column;gap:18px">%s</ul></div>'
        '<div class="foot"><span class="url">planikaapp.com</span><span>Desliza →</span></div>'
        % (big, html.escape(name), n, (" · %d gratis" % free_n) if free_n else "", ed["total"],
           (" (%d gratis)" % ed["free"]) if ed["free"] else "",
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
        '<div style="font-size:64px;font-weight:900;line-height:1.15">Hay <span class="sticker" style="font-size:72px;background:%s">%d planes</span></div>'
        '<div style="font-size:64px;font-weight:900;line-height:1.15;margin-top:30px">este finde en %s</div>'
        '<div style="font-size:46px;font-weight:700;margin-top:60px;line-height:1.35">Todos, con horarios y mapa, en<br>'
        '<span style="background:%s;color:#fff;border-radius:999px;padding:6px 26px;display:inline-block;margin-top:16px;font-weight:900">planikaapp.com</span></div>'
        '<div style="font-size:42px;font-weight:800;margin-top:70px">📌 Guárdalo y compártelo<br>con quien se venga</div></div>'
        '<div class="foot"><span>@planikaapp</span><span>%s</span></div>'
        % (TEAL, ed["total"], html.escape(name), INK, LOGO % (80, 80))))
    return out


# ---------------------------------------------------------------- página para guardarlos desde el móvil

def index_page(eds, files, updated):
    """files: {slug: [rutas relativas de las imágenes]}."""
    blocks = []
    for ed in eds:
        imgs = files.get(ed["slug"]) or []
        if not imgs:
            continue
        cap = caption(ed)
        blocks.append(
            '<section class="ed" data-slug="%(slug)s"><h2>Este finde en %(city)s <small>%(n)d imágenes</small></h2>'
            '<div class="strip">%(imgs)s</div>'
            '<p class="acts"><button type="button" class="btn primary" data-save>📲 Guardar las %(n)d imágenes</button> '
            '<button type="button" class="btn" data-copy>📋 Copiar el texto</button></p>'
            '<pre class="cap">%(cap)s</pre></section>'
            % dict(slug=html.escape(ed["slug"]), city=html.escape(ed["city"]), n=len(imgs), cap=html.escape(cap),
                   imgs="".join('<a href="%s" download><img src="%s" alt="Diapositiva %d" loading="lazy" width="270" height="338"></a>'
                                % (html.escape(f), html.escape(f), k + 1) for k, f in enumerate(imgs))))
    rng = date_range(eds[0]) if eds else ""
    return """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Carruseles de Instagram · Planika</title>
<style>
body{margin:0;font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;color:%(ink)s;background:%(page)s}
main{max-width:900px;margin:0 auto;padding:18px 16px 60px}
h1{font-size:26px;margin:6px 0 4px} h2{font-size:20px;margin:0 0 10px} h2 small{font-weight:600;color:#4a4263;font-size:14px}
.note{color:#4a4263;margin:0 0 18px}
.ed{background:#fff;border:3px solid %(ink)s;border-radius:18px;box-shadow:4px 4px 0 %(ink)s;padding:14px;margin:0 0 22px}
.strip{display:flex;gap:10px;overflow-x:auto;padding-bottom:8px;scroll-snap-type:x mandatory}
.strip img{width:200px;height:250px;border:2px solid %(ink)s;border-radius:10px;scroll-snap-align:start;display:block}
.btn{font:inherit;font-weight:800;border:2px solid %(ink)s;border-radius:999px;background:#fff;padding:10px 16px;box-shadow:3px 3px 0 %(ink)s;margin:4px 6px 4px 0}
.btn.primary{background:%(hot)s;color:#fff}
.cap{white-space:pre-wrap;font-size:14px;line-height:1.45;font-family:inherit;background:%(page)s;border:2px dashed #cfc7dc;border-radius:12px;padding:10px;margin:10px 0 0}
</style></head><body><main>
<h1>📸 Carruseles de Instagram · finde %(rng)s</h1>
<p class="note">Hechos con la agenda del %(updated)s. En el iPhone, «Guardar las imágenes» las lleva a Fotos de una vez (o mantén pulsada cada una).
Después, «Copiar el texto» para el pie del post. Esta página no está enlazada ni sale en Google.</p>
%(blocks)s
</main>
<script>
document.querySelectorAll('.ed').forEach(function (sec) {
  var imgs = Array.prototype.map.call(sec.querySelectorAll('.strip img'), function (i) { return i.getAttribute('src'); });
  sec.querySelector('[data-save]').addEventListener('click', function () {
    var b = this;
    Promise.all(imgs.map(function (u, k) {
      return fetch(u).then(function (r) { return r.blob(); }).then(function (bl) { return new File([bl], sec.dataset.slug + '-' + (k + 1) + '.jpg', { type: 'image/jpeg' }); });
    })).then(function (files) {
      if (navigator.canShare && navigator.canShare({ files: files })) return navigator.share({ files: files });
      files.forEach(function (f, k) { setTimeout(function () { var a = document.createElement('a'); a.href = imgs[k]; a.download = f.name; document.body.appendChild(a); a.click(); a.remove(); }, k * 300); });
    }).catch(function () { b.textContent = 'Mantén pulsada cada imagen para guardarla'; });
  });
  sec.querySelector('[data-copy]').addEventListener('click', function () {
    var t = sec.querySelector('.cap').textContent, b = this;
    (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { b.textContent = '✓ Texto copiado'; })
      .catch(function () { var r = document.createRange(); r.selectNodeContents(sec.querySelector('.cap')); var s = getSelection(); s.removeAllRanges(); s.addRange(r); });
  });
});
</script></body></html>
""" % dict(ink=INK, page=PAGE, hot=HOT, rng=html.escape(rng), updated=html.escape(updated), blocks="".join(blocks) or "<p>Este finde no hay ciudades con planes suficientes.</p>")
