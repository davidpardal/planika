"""Prueba de la web real (planikaapp.com) en móviles simulados: iPhone (WebKit, el motor de Safari) y Android (Chromium).

Recorre lo principal (portada, buscar, calendario, mapa, menú, Mis planes, idioma, ficha y páginas generadas) y anota
errores de JS, peticiones fallidas, cosas que se salen de la pantalla y campos que harían zoom en iPhone (letra < 16 px).
Escribe capturas/moviles/informe.json y una captura JPEG por paso.
"""
import json
import os
import time
import traceback

from playwright.sync_api import sync_playwright

SITE = os.environ.get("SITE", "https://planikaapp.com/")
OUT = os.path.join("capturas", "moviles")
DEVICES = [("iPhone 15", "webkit"), ("iPhone SE", "webkit"), ("Pixel 7", "chromium"), ("Android 360", "chromium"), ("Galaxy S9+", "chromium")]
CUSTOM = {"Android 360": ("Pixel 7", {"width": 360, "height": 780})}  # ancho de muchos Samsung Galaxy A
SKIP = ("googletagmanager", "google-analytics", "analytics.google", "doubleclick")

WIDE_JS = """() => {
  var W = window.innerWidth, out = [];
  document.querySelectorAll('body *').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (!r.width || r.right <= W + 1 || getComputedStyle(el).position === 'fixed') return;
    for (var p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      var o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return;  // dentro de una fila con scroll o recortada
    }
    out.push(el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '') + ' → ' + Math.round(r.right) + 'px');
  });
  return { docW: document.documentElement.scrollWidth, W: W, wide: out.slice(0, 12), nWide: out.length };
}"""
CLIP_JS = """() => {
  var n = 0, tot = 0, ex = '';
  document.querySelectorAll('#list .card .actions').forEach(function (a) {
    tot++;
    var box = a.getBoundingClientRect(), card = a.closest('.card').getBoundingClientRect();
    var last = a.lastElementChild ? a.lastElementChild.getBoundingClientRect() : box;
    if (a.scrollWidth > a.clientWidth + 1 || last.right > card.right - 2) { n++; if (!ex) ex = Array.from(a.children).map(function (b) { return b.textContent.trim(); }).join(' | '); }
  });
  return { clipped: n, total: tot, example: ex };
}"""
FONT_JS = """() => {
  var out = [];
  document.querySelectorAll('input, select, textarea').forEach(function (el) {
    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'hidden' || el.type === 'range') return;
    var fs = parseFloat(getComputedStyle(el).fontSize);
    if (fs < 16) out.push((el.id || el.name || el.className || el.tagName) + ' ' + fs + 'px');
  });
  return out;
}"""
SMALL_JS = """() => {
  var out = [];
  document.querySelectorAll('a, button, select, summary, [role=button]').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (!r.width || r.bottom < 0 || r.top > innerHeight) return;
    if (el.closest('footer, nav.foot, .brandfoot, p')) return;  // enlaces de texto dentro de párrafos
    if (r.height < 32 || r.width < 32) out.push((el.id || el.textContent.trim().slice(0, 24) || el.tagName) + ' ' + Math.round(r.width) + '×' + Math.round(r.height));
  });
  return out.slice(0, 15);
}"""


class Run:
    def __init__(self, page, dev):
        self.page, self.dev, self.steps, self.n = page, dev, [], 0
        self.errors, self.failed, self.bad = [], [], []
        page.on("pageerror", lambda e: self.errors.append(str(e)[:300]))
        page.on("console", lambda m: self.errors.append("console: " + m.text[:300]) if m.type == "error" and not any(s in m.text for s in SKIP) else None)
        page.on("requestfailed", lambda r: self.failed.append(r.url[:160] + " " + (r.failure or "")) if not any(s in r.url for s in SKIP) else None)
        page.on("response", lambda r: self.bad.append("%d %s" % (r.status, r.url[:160])) if r.status >= 400 and not any(s in r.url for s in SKIP) else None)

    def shot(self, name):
        slug = self.dev.lower().replace(" ", "-").replace("+", "plus")
        f = "%s_%02d_%s.jpg" % (slug, self.n, name)
        self.n += 1
        self.page.screenshot(path=os.path.join(OUT, f), type="jpeg", quality=70)
        return f

    def step(self, name, fn):
        e0, f0, b0, t0 = len(self.errors), len(self.failed), len(self.bad), time.time()
        res = {"step": name}
        try:
            res.update(fn() or {})
            res["ok"] = True
        except Exception as ex:  # noqa: BLE001
            res["ok"] = False
            res["exception"] = "".join(traceback.format_exception_only(type(ex), ex)).strip()[:400]
        try:
            res["shot"] = self.shot(name)
        except Exception:  # noqa: BLE001
            pass
        res["secs"] = round(time.time() - t0, 1)
        res["js_errors"] = self.errors[e0:]
        res["failed_requests"] = self.failed[f0:]
        res["http_errors"] = self.bad[b0:]
        self.steps.append(res)
        print(self.dev, name, "OK" if res["ok"] else "FALLO " + res.get("exception", ""), flush=True)


def wait_list(page):
    page.wait_for_function("document.querySelector('#list article[data-id]')", timeout=60000)
    page.wait_for_timeout(1200)


def layout(page):
    return {"layout": page.evaluate(WIDE_JS), "small_fonts": page.evaluate(FONT_JS)}


def run_device(p, dev, engine):
    base, vp = CUSTOM.get(dev, (dev, None))
    d = dict(p.devices[base])
    if vp:
        d["viewport"] = vp
    d.pop("default_browser_type", None)
    browser = getattr(p, engine).launch()
    ctx = browser.new_context(**d, locale="es-ES", timezone_id="Europe/Madrid")
    ctx.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in SKIP) else r.continue_())
    ctx.add_init_script("try { localStorage.setItem('planika_analytics_consent', 'rejected'); } catch (e) {}")
    page = ctx.new_page()
    R = Run(page, dev)
    info = {"device": dev, "engine": engine, "viewport": d.get("viewport"), "ua": d.get("user_agent", "")[:120]}

    def home():
        t0 = time.time()
        page.goto(SITE, wait_until="domcontentloaded", timeout=60000)
        wait_list(page)
        r = {"first_cards_secs": round(time.time() - t0, 1)}
        r.update(layout(page))
        page.evaluate("window.scrollTo(0, document.querySelector('#list').offsetTop - 80)")
        page.wait_for_timeout(400)
        r["card_actions"] = page.evaluate(CLIP_JS)
        r["small_targets"] = page.evaluate(SMALL_JS)
        page.evaluate("window.scrollTo(0, 0)")
        return r
    R.step("portada", home)

    def search():
        page.locator("#where").scroll_into_view_if_needed()
        page.locator("#where").tap()
        page.keyboard.type("Bil", delay=120)
        page.wait_for_timeout(900)
        sug = page.locator("#whereList li[data-i]").first
        n = page.locator("#whereList li[data-i]").count()
        sug.tap()
        page.wait_for_timeout(1500)
        return {"suggestions": n, "count": page.inner_text("#count"), "url": page.url}
    R.step("buscar", search)

    def cards_actions():
        page.locator("#list").scroll_into_view_if_needed()
        page.wait_for_timeout(500)
        return {"card_actions": page.evaluate(CLIP_JS)}
    R.step("tarjetas", cards_actions)

    def cal():
        b = page.locator('#view [data-view="cal"]')
        b.scroll_into_view_if_needed(); b.tap()
        page.wait_for_timeout(1200)
        day = page.locator("#calGrid .day.has:not(.out):not(.past)")
        day = day.first if day.count() else page.locator("#calGrid .day:not(.out):not(.past)").first
        day.scroll_into_view_if_needed(); day.tap()
        page.wait_for_timeout(1000)
        r = {"days_with_plans": page.locator("#calGrid .day.has").count(), "panel_visible": page.locator("#dayPanel").is_visible()}
        r.update(layout(page))
        return r
    R.step("calendario", cal)

    def mapa():
        b = page.locator('#view [data-view="map"]')
        b.scroll_into_view_if_needed(); b.tap()
        page.wait_for_timeout(5000)
        page.locator("#map").scroll_into_view_if_needed()
        page.wait_for_timeout(1500)
        return {"tiles": page.locator("#map .leaflet-tile-loaded").count(),
                "markers": page.locator("#map .leaflet-marker-icon").count()}
    R.step("mapa", mapa)

    def menu():
        page.locator("#menuBtn").tap()
        page.wait_for_timeout(600)
        vis = page.locator("#sidemenu").is_visible()
        box = page.locator("#sidemenu").bounding_box()
        r = {"open": vis, "box": box}
        R.shot("menu-abierto")
        page.locator("#menuClose").tap()
        page.wait_for_timeout(500)
        r["closed"] = not page.locator("#sidemenu").is_visible()
        return r
    R.step("menu", menu)

    def plan():
        b = page.locator('#view [data-view="list"]')
        b.scroll_into_view_if_needed(); b.tap()
        page.wait_for_timeout(800)
        add = page.locator("#list .addplan").first
        add.scroll_into_view_if_needed(); add.tap()
        page.wait_for_timeout(600)
        r = {"button": add.inner_text(), "pill": page.locator("#planPill").is_visible() and page.inner_text("#planPill")}
        page.locator("#planPill").tap()
        page.wait_for_timeout(800)
        r["dialog_open"] = page.evaluate("document.getElementById('planDlg').open")
        page.locator("#planName").fill("Prueba móvil")
        page.locator("#planNoteTime").fill("14:00")
        page.locator("#planNoteText").fill("Comer")
        page.locator("#planNoteForm button[type=submit]").tap()
        page.wait_for_timeout(500)
        r["items"] = page.locator("#planList .plan-item").count()
        r["small_fonts_in_plan"] = page.evaluate(FONT_JS)
        r["dialog_box"] = page.locator("#planDlg").bounding_box()
        R.shot("plan")
        page.locator("#planIcs").tap()
        page.wait_for_timeout(1500)
        r["calendar_buttons"] = page.locator("#planCal a[data-gcal]").count()
        page.locator("#planBack").tap()
        page.wait_for_timeout(500)
        r["plans_listed"] = page.locator("#plansList .plans-row").count()
        R.shot("mis-planes")
        page.locator("#planClose").tap()
        page.wait_for_timeout(400)
        return r
    R.step("mi-plan", plan)

    def addcal():
        b = page.locator("#list .addcal").first
        b.scroll_into_view_if_needed(); b.tap()
        page.wait_for_timeout(1500)
        r = {"menu_visible": page.locator("#menu").is_visible()}
        if r["menu_visible"]:
            r["menu_box"] = page.locator("#menu").bounding_box()
            r["options"] = page.locator("#menu a, #menu button").count()
        R.shot("calendario-tarjeta")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        return r
    R.step("anadir-al-calendario", addcal)

    def idioma():
        page.evaluate("window.scrollTo(0, 0)")
        with page.expect_navigation(timeout=60000):
            page.locator(".lang-pill .lang-sel").select_option("eu")
        wait_list(page)
        r = {"sticker": page.locator(".sticker").first.inner_text(), "html_lang": page.evaluate("document.documentElement.lang")}
        r.update(layout(page))
        page.evaluate("localStorage.setItem('planika_lang', 'es')")
        return r
    R.step("idioma", idioma)

    def ficha():
        page.goto(SITE + "?prov=48&city=Bilbao", wait_until="domcontentloaded", timeout=60000)
        wait_list(page)
        href = page.locator("#list article[data-id] h3 a").first.get_attribute("href")
        page.goto(SITE + href, wait_until="load", timeout=60000)
        page.wait_for_timeout(1500)
        r = {"url": page.url, "h1": page.locator("h1").first.inner_text()[:80], "add_plan_link": page.locator('a[href*="?add="]').count()}
        r.update(layout(page))
        return r
    R.step("ficha", ficha)

    for path in ("p/bizkaia.html", "t/musica.html", "planes-este-fin-de-semana.html", "puente-diciembre.html"):
        def gen(path=path):
            page.goto(SITE + path, wait_until="load", timeout=60000)
            page.wait_for_timeout(1500)
            r = {"title": page.title()[:90]}
            r.update(layout(page))
            return r
        R.step("pagina-" + path.split("/")[-1].replace(".html", ""), gen)

    def pwa():
        page.goto(SITE, wait_until="load", timeout=60000)
        page.wait_for_timeout(2500)
        return {"manifest": page.evaluate("!!document.querySelector('link[rel=manifest]')"),
                "sw_api": page.evaluate("'serviceWorker' in navigator"),
                "sw_controller": page.evaluate("navigator.serviceWorker ? navigator.serviceWorker.getRegistrations().then(function (r) { return r.length; }) : -1")}
    R.step("pwa", pwa)

    ctx.close(); browser.close()
    info["steps"] = R.steps
    return info


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    report = []
    with sync_playwright() as p:
        only = [x for x in os.environ.get("ONLY", "").split(",") if x]
        for dev, engine in DEVICES:
            if only and dev not in only:
                continue
            try:
                report.append(run_device(p, dev, engine))
            except Exception:  # noqa: BLE001
                report.append({"device": dev, "engine": engine, "fatal": traceback.format_exc()[-800:]})
                traceback.print_exc()
    with open(os.path.join(OUT, "informe.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
