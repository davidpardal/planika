"""Capturas de la web real (planikaapp.com) para los reels tutoriales.

Maneja la web en un móvil simulado, hace una captura JPEG tras cada paso y escribe capturas/timeline.json
con la duración de cada captura, el texto del paso y dónde se toca. El vídeo se monta aparte.
"""
import json
import os
import traceback

from playwright.sync_api import sync_playwright

SITE = os.environ.get("SITE", "https://planikaapp.com/")
OUT = "capturas"
VW, VH = 390, 700
FRAMES = []


class Reel:
    def __init__(self, page, name):
        self.page, self.name, self.n = page, name, 0
        os.makedirs(os.path.join(OUT, name), exist_ok=True)

    def shot(self, dur, cap, tap=None):
        img = "%s/%03d.jpg" % (self.name, self.n)
        self.n += 1
        self.page.screenshot(path=os.path.join(OUT, img), type="jpeg", quality=90)
        FRAMES.append({"reel": self.name, "img": img, "dur": dur, "cap": cap, "tap": tap})

    def center(self, loc):
        b = loc.bounding_box()
        return [round(b["x"] + b["width"] / 2, 1), round(b["y"] + b["height"] / 2, 1)]

    def glide(self, y_target, secs, cap, fps=12):
        """Desplaza la página poco a poco hasta scrollY = y_target, con una captura por paso."""
        y0 = self.page.evaluate("window.scrollY")
        n = max(1, int(secs * fps))
        for i in range(1, n + 1):
            k = i / n
            k = k * k * (3 - 2 * k)
            self.page.evaluate("y => window.scrollTo(0, y)", y0 + (y_target - y0) * k)
            self.page.wait_for_timeout(30)
            self.shot(1 / fps, cap)

    def glide_in(self, sel, y_target, secs, cap, fps=12):
        """Como glide, pero dentro de un elemento con scroll propio (la ventana del plan)."""
        y0 = self.page.evaluate("s => document.querySelector(s).scrollTop", sel)
        n = max(1, int(secs * fps))
        for i in range(1, n + 1):
            k = i / n
            k = k * k * (3 - 2 * k)
            self.page.evaluate("a => { document.querySelector(a[0]).scrollTop = a[1]; }", [sel, y0 + (y_target - y0) * k])
            self.page.wait_for_timeout(30)
            self.shot(1 / fps, cap)

    def glide_in_to(self, sel, loc, at_y, secs, cap):
        b = loc.bounding_box()
        y = self.page.evaluate("s => document.querySelector(s).scrollTop", sel) + b["y"] - at_y
        self.glide_in(sel, max(0, y), secs, cap)

    def glide_to(self, loc, at_y, secs, cap):
        b = loc.bounding_box()
        y = self.page.evaluate("window.scrollY") + b["y"] - at_y
        self.glide(max(0, y), secs, cap)

    def tap(self, loc, cap, wait=700, hold=1.0, pre=0.45):
        c = self.center(loc)
        self.shot(pre, cap, tap=c)
        try:
            loc.tap(timeout=5000)
        except Exception:  # p. ej. chinchetas del mapa que Playwright no da por «estables»: toque en el punto
            self.page.touchscreen.tap(c[0], c[1])
        self.page.wait_for_timeout(wait)
        self.shot(hold, cap)


def new_page(browser, geo=None):
    ctx = browser.new_context(viewport={"width": VW, "height": VH}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              locale="es-ES", timezone_id="Europe/Madrid",
                              user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Mobile Safari/537.36",
                              geolocation=geo, permissions=(["geolocation"] if geo else []) + ["clipboard-read", "clipboard-write"])
    # Sin analítica: las capturas no deben contar como visitas.
    ctx.route("**/*", lambda r: r.abort() if any(h in r.request.url for h in ("googletagmanager", "google-analytics", "analytics.google")) else r.continue_())
    # Sin el aviso de cookies tapando la mitad de abajo (se da por rechazado, como quien ya contestó)
    ctx.add_init_script("try { localStorage.setItem('planika_analytics_consent', 'rejected'); } catch (e) {}")
    page = ctx.new_page()
    return ctx, page


def open_site(page, url=SITE):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("document.querySelector('#list article[data-id]')", timeout=60000)
    page.wait_for_timeout(2500)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)


def reel_buscar(browser):
    ctx, page = new_page(browser)
    r = Reel(page, "buscar")
    open_site(page)
    r.shot(1.8, "intro")
    where = page.locator("#where")
    r.glide_to(where, 260, 0.6, "1 · Escribe dónde")
    r.tap(where, "1 · Escribe dónde", wait=1100, hold=0.5)
    for ch in "Vit":
        page.keyboard.type(ch)
        page.wait_for_timeout(350)
        r.shot(0.6, "1 · Escribe dónde")
    sug = page.locator("#whereList li[data-i]").first
    r.tap(sug, "2 · Toca tu ciudad", wait=1300, hold=1.1)
    wk = page.locator('#quick [data-range="weekend"]')
    r.glide_to(wk, 330, 0.5, "3 · Elige cuándo")
    r.tap(wk, "3 · Elige cuándo", wait=900, hold=1.0)
    free = page.locator('#what [data-free="1"]')
    r.tap(free, "4 · ¿Solo gratis? Un toque", wait=900, hold=1.0)
    r.glide_to(page.locator("#count"), 70, 1.0, "¡Listo! Tus planes")
    r.shot(0.8, "¡Listo! Tus planes")
    r.glide(page.evaluate("window.scrollY") + 420, 1.2, "¡Listo! Tus planes")
    link = page.locator("#list article[data-id] h3 a").first
    r.tap(link, "5 · Toca uno y ves la ficha", wait=2200, hold=1.3)
    r.glide(page.evaluate("window.scrollY") + 380, 1.0, "5 · Toca uno y ves la ficha")
    r.shot(0.8, "5 · Toca uno y ves la ficha")
    ctx.close()


def reel_guardar(browser):
    ctx, page = new_page(browser)
    r = Reel(page, "guardar")
    open_site(page, SITE + "?prov=48&city=Bilbao")
    r.shot(1.6, "intro")
    cards = page.locator("#list article[data-id]")
    fav1 = cards.nth(0).locator(".fav")
    r.glide_to(fav1, 430, 1.0, "1 · Pulsa ☆ y se guarda")
    r.tap(fav1, "1 · Pulsa ☆ y se guarda", wait=500, hold=0.8)
    fav2 = cards.nth(1).locator(".fav")
    r.glide_to(fav2, 430, 0.8, "1 · Pulsa ☆ y se guarda")
    r.tap(fav2, "1 · Pulsa ☆ y se guarda", wait=500, hold=0.8)
    cal = cards.nth(1).locator(".addcal")
    cal.tap()  # la primera vez carga los detalles del plan
    page.wait_for_timeout(1800)
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    r.tap(cal, "2 · Y a tu calendario", wait=700, hold=1.6)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    adv = page.locator("#adv > summary")
    r.glide_to(adv, 250, 1.0, "3 · Tus guardados, siempre a mano")
    r.tap(adv, "3 · Tus guardados, siempre a mano", wait=700, hold=0.6)
    favs = page.locator('label.check:has(#favs)')
    r.glide_to(favs, 380, 0.6, "3 · Tus guardados, siempre a mano")
    r.tap(favs, "3 · Tus guardados, siempre a mano", wait=900, hold=0.6)
    r.glide_to(page.locator("#count"), 90, 0.8, "3 · Tus guardados, siempre a mano")
    r.shot(1.4, "3 · Tus guardados, siempre a mano")
    calv = page.locator('#view [data-view="cal"]')
    r.tap(calv, "4 · O en el calendario", wait=1200, hold=1.0)
    day = page.locator("#calGrid .day.has:not(.out)").first
    if day.count():
        r.glide_to(day, 360, 0.6, "4 · O en el calendario")
        r.tap(day, "4 · O en el calendario", wait=900, hold=0.6)
        r.glide(page.evaluate("window.scrollY") + 300, 0.9, "4 · O en el calendario")
        r.shot(1.0, "4 · O en el calendario")
    ctx.close()


def reel_cerca(browser):
    # Barcelona (plaza de Catalunya): sus planes traen coordenadas propias y el mapa sale con chinchetas reales.
    ctx, page = new_page(browser, geo={"latitude": 41.3870, "longitude": 2.1701})
    r = Reel(page, "cerca")
    open_site(page)
    r.shot(1.6, "intro")
    adv = page.locator("#adv > summary")
    r.glide_to(adv, 300, 0.8, "1 · Abre «Búsqueda avanzada»")
    r.tap(adv, "1 · Abre «Búsqueda avanzada»", wait=700, hold=0.7)
    geo = page.locator("#geoBtn")
    r.glide_to(geo, 360, 0.6, "2 · Activa «Cerca de mí»")
    r.tap(geo, "2 · Activa «Cerca de mí»", wait=1800, hold=0.9)
    rad = page.locator("#radius")
    c = r.center(rad)
    r.shot(0.45, "3 · Elige a cuántos km", tap=c)
    rad.select_option("10")
    page.wait_for_timeout(900)
    r.shot(0.9, "3 · Elige a cuántos km")
    r.glide_to(page.locator("#count"), 80, 0.9, "Ordenados por distancia")
    r.shot(0.6, "Ordenados por distancia")
    r.glide(page.evaluate("window.scrollY") + 400, 1.1, "Ordenados por distancia")
    mapb = page.locator('#view [data-view="map"]')
    r.glide_to(mapb, 200, 0.8, "4 · O míralos en el mapa")
    r.tap(mapb, "4 · O míralos en el mapa", wait=4500, hold=0.6)
    r.glide_to(page.locator("#map"), 120, 0.8, "4 · O míralos en el mapa")
    page.wait_for_timeout(1500)
    r.shot(0.8, "4 · O míralos en el mapa")
    # Los planes cercanos salen agrupados: se toca el grupo más grande hasta ver chinchetas sueltas.
    for _ in range(3):
        if page.locator("#map .leaflet-marker-icon:not(.marker-cluster)").count():
            break
        cl = page.locator("#map .marker-cluster")
        if not cl.count():
            break
        best, bn = 0, -1
        for k in range(cl.count()):
            try:
                n = int((cl.nth(k).inner_text() or "0").strip() or 0)
            except ValueError:
                n = 0
            if n > bn:
                best, bn = k, n
        r.tap(cl.nth(best), "4 · O míralos en el mapa", wait=1600, hold=0.7)
    mk = page.locator("#map .leaflet-marker-icon:not(.marker-cluster)")
    target = None
    for k in range(mk.count()):
        b = mk.nth(k).bounding_box()
        if b and 40 < b["y"] < VH - 60 and 30 < b["x"] < VW - 30:
            target = mk.nth(k)
            break
    if target is not None:
        r.tap(target, "5 · Toca uno y mira el plan", wait=900, hold=1.0)
        op = page.locator("#map .leaflet-popup [data-open]").first
        if op.count():
            r.tap(op, "5 · Toca uno y mira el plan", wait=1800, hold=1.8)
            r.glide(page.evaluate("window.scrollY"), 0.1, "5 · Toca uno y mira el plan")
    ctx.close()


def reel_dias(browser):
    """Novedad: elegir varios días sueltos en el calendario (sáb 5, mar 8 y sáb 12 de diciembre en Madrid)."""
    ctx, page = new_page(browser)
    r = Reel(page, "dias")
    open_site(page, SITE + "?prov=28&city=Madrid")
    r.shot(1.8, "intro")
    calv = page.locator('#view [data-view="cal"]')
    r.glide_to(calv, 300, 0.8, "1 · Abre el calendario")
    r.tap(calv, "1 · Abre el calendario", wait=1200, hold=0.5)
    r.glide_to(page.locator("#calendar"), 20, 0.7, "1 · Abre el calendario")
    nxt = page.locator("#nextM")
    r.tap(nxt, "1 · Abre el calendario", wait=700, hold=0.6)
    for d in ("2026-12-05", "2026-12-08", "2026-12-12"):
        r.tap(page.locator('.day[data-day="%s"]' % d), "2 · Toca los días que quieras", wait=700, hold=0.7)
    r.shot(0.9, "2 · Toca los días que quieras")
    panel = page.locator("#dayPanel")
    r.glide_to(panel, 40, 1.0, "3 · Tus planes, día a día")
    r.shot(1.3, "3 · Tus planes, día a día")
    r.glide(page.evaluate("window.scrollY") + 520, 1.6, "3 · Tus planes, día a día")
    r.shot(0.6, "3 · Tus planes, día a día")
    r.glide_to(panel, 40, 0.8, "4 · O todos en la lista")
    lst = page.locator('#dayPanel .day-actions [data-goview="list"]')
    r.tap(lst, "4 · O todos en la lista", wait=1500, hold=0.5)
    r.glide_to(page.locator("#count"), 90, 0.8, "4 · O todos en la lista")
    r.shot(1.3, "4 · O todos en la lista")
    r.glide(page.evaluate("window.scrollY") + 460, 1.4, "4 · O todos en la lista")
    r.shot(0.8, "4 · O todos en la lista")
    ctx.close()


def pick_cards(page, n=3, gap=150, limit=40):
    """Tarjetas de la lista a horas distintas (desde las 10:30 y con `gap` minutos entre una y otra)."""
    import re
    cards = page.locator("#list article[data-id]")
    picked, last = [], -999
    for k in range(min(cards.count(), limit)):
        m = re.search(r"(\d{1,2}):(\d{2})", cards.nth(k).locator(".when").inner_text())
        if not m:
            continue
        t = int(m.group(1)) * 60 + int(m.group(2))
        if t >= 630 and t - last >= gap:
            picked.append(k)
            last = t
        if len(picked) == n:
            break
    for k in range(min(cards.count(), limit)):  # si no hay bastantes horas distintas, se completa por orden
        if len(picked) >= n:
            break
        if k not in picked:
            picked.append(k)
    return sorted(picked)


def reel_miplan(browser):
    """Novedad: crear tu plan del sábado 28 de noviembre en Bilbao: añadir, nombre, nota, calendario y compartir."""
    ctx, page = new_page(browser)
    r = Reel(page, "miplan")
    open_site(page, SITE + "?prov=48&city=Bilbao&dias=2026-11-28")
    r.shot(1.8, "intro")
    cards = page.locator("#list article[data-id]")
    cap = "1 · Pulsa «＋ Mi plan»"
    for k in pick_cards(page):
        b = cards.nth(k).locator(".addplan")
        r.glide_to(b, 470, 0.7, cap)
        r.tap(b, cap, wait=600, hold=0.7)
    cap = "2 · Ábrelo y ponle nombre"
    r.tap(page.locator("#planPill"), cap, wait=900, hold=0.6)
    r.tap(page.locator("#planName"), cap, wait=300, hold=0.3)
    for chunk in ("Sába", "do en ", "Bilbao"):
        page.keyboard.type(chunk, delay=40)
        r.shot(0.35, cap)
    r.shot(0.9, cap)
    dlg = "#planDlg"
    cap = "3 · Todo ordenado por hora"
    r.glide_in_to(dlg, page.locator("#planNoteForm"), 560, 1.6, cap)
    r.shot(0.9, cap)
    cap = "4 · Añade tus notas"
    t = page.locator("#planNoteTime")
    r.tap(t, cap, wait=200, hold=0.2)
    t.fill("14:00")
    r.shot(0.4, cap)
    r.tap(page.locator("#planNoteText"), cap, wait=200, hold=0.2)
    page.keyboard.type("Comer de pintxos", delay=30)
    r.shot(0.5, cap)
    r.tap(page.locator("#planNoteForm button[type=submit]"), cap, wait=600, hold=0.3)
    r.glide_in_to(dlg, page.locator("#planList .plan-item.note"), 300, 0.8, cap)
    r.shot(1.1, cap)
    cap = "5 · A tu calendario, de una vez"
    ics = page.locator("#planIcs")
    r.glide_in_to(dlg, ics, 420, 0.8, cap)
    r.tap(ics, cap, wait=1800, hold=1.0)
    r.glide_in_to(dlg, page.locator("#planCal"), 120, 0.8, cap)
    r.shot(1.3, cap)
    cap = "6 · Y compártelo con tu gente"
    cp = page.locator("#planCopy")
    r.glide_in_to(dlg, cp, 380, 0.8, cap)
    r.tap(cp, cap, wait=500, hold=1.8)
    ctx.close()


def reel_misplanes(browser):
    """Novedad: varios planes. Ya hay uno («Sábado en Bilbao»); se crea «Puente de diciembre» y se elige a cuál va cada cosa."""
    ctx, page = new_page(browser)
    r = Reel(page, "misplanes")
    # Plan de partida con planes reales del sábado 28 en Bilbao, como si ya lo hubieras hecho
    open_site(page, SITE + "?prov=48&city=Bilbao&dias=2026-11-28")
    cards = page.locator("#list article[data-id]")
    ids = [cards.nth(k).get_attribute("data-id") for k in pick_cards(page)]
    page.evaluate("""ids => { var p = { id: 'sabado', n: 'Sábado en Bilbao', i: ids.map(function (x) { return [x, '2026-11-28']; }), o: [] };
      localStorage.setItem('planika_plans', JSON.stringify({ a: 'sabado', p: [p] })); }""", ids)
    open_site(page, SITE + "?prov=48&city=Bilbao&dias=2026-12-05,2026-12-06,2026-12-07,2026-12-08")
    r.shot(1.8, "intro")
    cap = "1 · Abre «Mis planes» en el menú"
    r.tap(page.locator("#menuBtn"), cap, wait=600, hold=0.5)
    r.tap(page.locator('#sidemenu [data-menu="plan"]'), cap, wait=800, hold=1.0)
    cap = "2 · Crea otro plan"
    r.tap(page.locator("#plansNew"), cap, wait=500, hold=0.3)
    for chunk in ("Puente ", "de dic", "iembre"):
        page.keyboard.type(chunk, delay=40)
        r.shot(0.35, cap)
    r.shot(0.8, cap)
    r.tap(page.locator("#planClose"), cap, wait=500, hold=0.4)
    cap = "3 · Elige a qué plan va cada cosa"
    for k in pick_cards(page, n=2, gap=240):
        b = cards.nth(k).locator(".addplan")
        r.glide_to(b, 470, 0.7, cap)
        r.tap(b, cap, wait=700, hold=0.9)
        r.tap(page.locator("#pickList .plans-row", has_text="Puente de diciembre"), cap, wait=700, hold=0.8)
    cap = "4 · Todos tus planes, a mano"
    r.tap(page.locator("#menuBtn"), cap, wait=600, hold=0.4)
    r.tap(page.locator('#sidemenu [data-menu="plan"]'), cap, wait=800, hold=1.8)
    cap = "5 · Cada uno, con su enlace"
    r.tap(page.locator("#plansList .plans-row", has_text="Puente de diciembre"), cap, wait=800, hold=1.0)
    cp = page.locator("#planCopy")
    r.glide_in_to("#planDlg", cp, 380, 0.9, cap)
    r.tap(cp, cap, wait=500, hold=1.8)
    ctx.close()


def reel_idiomas(browser):
    """Novedad: la web en euskera, catalán, gallego e inglés (selector de arriba a la derecha)."""
    ctx, page = new_page(browser)
    r = Reel(page, "idiomas")
    open_site(page)
    r.shot(1.8, "intro")
    pill = page.locator(".lang-pill")
    prev = "1 · Toca el idioma, arriba"
    for code, cap in (("eu", "Euskaraz"), ("ca", "En català"), ("gl", "En galego"), ("en", "In English")):
        r.shot(0.5, prev, tap=r.center(pill))
        with page.expect_navigation(timeout=60000):
            page.locator(".lang-pill .lang-sel").select_option(code)
        page.wait_for_function("document.querySelector('#list article[data-id]')", timeout=60000)
        page.wait_for_timeout(1800)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(200)
        r.shot(1.1, cap)
        r.glide_to(page.locator(".sticker").first, 90, 0.9, cap)
        r.shot(0.9, cap)
        prev = cap
    r.tap(page.locator("#menuBtn"), prev, wait=700, hold=1.6)
    ctx.close()


def main():
    import shutil
    os.makedirs(OUT, exist_ok=True)
    only = [x for x in os.environ.get("REELS", "buscar,guardar,cerca").split(",") if x]
    fns = {"buscar": reel_buscar, "guardar": reel_guardar, "cerca": reel_cerca, "dias": reel_dias,
           "miplan": reel_miplan, "misplanes": reel_misplanes, "idiomas": reel_idiomas}
    old = []
    try:  # se conservan las capturas de los reels que no se repiten
        with open(os.path.join(OUT, "timeline.json"), encoding="utf-8") as fh:
            old = [f for f in json.load(fh)["frames"] if f["reel"] not in only]
    except (OSError, ValueError, KeyError):
        pass
    for name in only:
        shutil.rmtree(os.path.join(OUT, name), ignore_errors=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name in only:
            try:
                fns[name](browser)
            except Exception:
                traceback.print_exc()
        browser.close()
    FRAMES[:0] = old
    with open(os.path.join(OUT, "timeline.json"), "w", encoding="utf-8") as fh:
        json.dump({"vw": VW, "vh": VH, "frames": FRAMES}, fh, ensure_ascii=False, indent=0)
    for name in fns:
        fr = [f for f in FRAMES if f["reel"] == name]
        print(name, len(fr), "capturas, %.1f s" % sum(f["dur"] for f in fr))


if __name__ == "__main__":
    main()
