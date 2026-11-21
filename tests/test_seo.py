# -*- coding: utf-8 -*-
"""Pruebas del SEO técnico: indexabilidad de fichas, sitemaps con lastmod real, robots.txt, canónicas,
datos estructurados, enlazado interno (sin enlaces rotos, todo a pocos clics) y arquitectura de páginas."""
import json
import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from planes import classify, publish, seo, static, util  # noqa: E402
import indexnow  # noqa: E402
import seo_check  # noqa: E402

NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
SITE = "https://planikaapp.com"


def rich(i, **kw):
    """Plan con información suficiente para ser indexable."""
    base = dict(province_code="48", city="Bilbao", venue="Sala %d" % (i % 7), time="20:00", category="musica",
                description="Concierto de presentación del nuevo disco, con banda completa y artistas invitados en una noche especial.",
                url="https://organizador.example/%d" % i)
    base.update(kw)
    return util.event("Agenda", "r%d" % i, "Concierto número %d" % i, util.iso(util.today()), **base)


def thin(i, **kw):
    """Plan con solo título y fecha (como muchos de la agenda de Barcelona)."""
    base = dict(province_code="48", city="Getxo", category="charlas", url="https://agenda.example/")
    base.update(kw)
    return util.event("Agenda", "t%d" % i, "Taller %d" % i, util.iso(util.today()), **base)


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as fh:
        return fh.read()


def sitemap_locs(site_dir):
    idx = ET.fromstring(read(site_dir, "sitemap.xml"))
    assert idx.tag == NS + "sitemapindex"
    locs = []
    for loc in idx.iter(NS + "loc"):
        child = ET.fromstring(read(site_dir, loc.text.rsplit("/", 1)[1]))
        locs += [(u.findtext(NS + "loc"), u.findtext(NS + "lastmod")) for u in child.iter(NS + "url")]
    return locs


def build(tmp, events):
    """Sitio mínimo: portada con enlaces a las páginas de intención y a las provincias con planes, más lo generado."""
    publish.write_feeds(os.path.join(tmp, "feeds"), events)
    pages = publish.write_pages(tmp, events, [], "2026-11-18T04:30", state_path=os.path.join(tmp, "state.json"))
    provs = sorted({e["province_code"] for e in events})
    links = "".join('<a href="p/%s.html">p</a>' % publish.slug(n) for c, n, _ in util.PROVINCIAS if c in provs)
    links += '<a href="planes-hoy.html">h</a><a href="planes-este-fin-de-semana.html">f</a><a href="planes-gratis.html">g</a>'
    links += "".join('<a href="t/%s.html">t</a>' % k for k, _, _ in classify.CATEGORIES)
    with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as fh:
        fh.write('<html><head><link rel="canonical" href="%s/"></head><body>%s</body></html>' % (SITE, links))
    for fn in ("styles.css", "icon.svg"):
        open(os.path.join(tmp, fn), "w").close()
    return pages


class TestQualityGate(unittest.TestCase):
    def test_score(self):
        self.assertGreaterEqual(seo.quality_score(rich(1)), seo.MIN_SCORE)
        self.assertLess(seo.quality_score(thin(1)), seo.MIN_SCORE)
        self.assertTrue(seo.is_indexable(thin(2, venue="Biblioteca", time="18:00")))  # lugar y hora: suficiente

    def test_thin_pages_are_noindex_and_out_of_sitemap(self):
        evs = [rich(1), thin(1)]
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, evs)
            r, t = static.event_file(evs[0]), static.event_file(evs[1])
            self.assertIn('content="index,follow', read(tmp, "e", r))
            self.assertIn('content="noindex,follow"', read(tmp, "e", t))
            locs = [u for u, _ in sitemap_locs(tmp)]
            self.assertIn("%s/e/%s" % (SITE, r), locs)
            self.assertNotIn("%s/e/%s" % (SITE, t), locs)


class TestSitemaps(unittest.TestCase):
    def test_lastmod_only_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = os.path.join(tmp, "state.json")
            seo.write_sitemaps(tmp, [("", "paginas", "a"), ("p/x.html", "paginas", "b"), ("e/y.html", "fichas", "c")],
                               SITE, state, day="2026-11-10")
            seo.write_sitemaps(tmp, [("", "paginas", "a2"), ("p/x.html", "paginas", "b"), ("e/y.html", "fichas", "c"),
                                     ("e/y.html", "fichas", "c")], SITE, state, day="2026-11-18")
            lm = dict(sitemap_locs(tmp))
            self.assertEqual(lm[SITE + "/"], "2026-11-18")           # cambió
            self.assertEqual(lm[SITE + "/p/x.html"], "2026-11-10")   # igual: conserva la fecha
            self.assertEqual(lm[SITE + "/e/y.html"], "2026-11-10")
            self.assertEqual(len(sitemap_locs(tmp)), 3)               # sin duplicados
            self.assertEqual(sorted(f for f in os.listdir(tmp) if f.startswith("sitemap")),
                             ["sitemap-fichas.xml", "sitemap-paginas.xml", "sitemap.xml"])

    def test_digest_ignores_update_stamp(self):
        a = '<p>Hola <span class="upd">Actualizado el 1 nov 2026</span></p>'
        b = '<p>Hola <span class="upd">Actualizado el 2 nov 2026</span></p>'
        self.assertEqual(seo.digest(a), seo.digest(b))
        self.assertNotEqual(seo.digest(a), seo.digest("<p>Adiós</p>"))

    def test_robots(self):
        txt = seo.robots_txt(SITE)
        self.assertIn("Disallow: /?\n", txt)
        self.assertIn("Sitemap: %s/sitemap.xml" % SITE, txt)
        self.assertNotRegex(txt, r"(?m)^Disallow: /\s*$")
        self.assertNotIn(".css", txt)
        self.assertNotIn(".js", txt)


class TestStructuredData(unittest.TestCase):
    def test_permanent_visit_is_not_an_event(self):
        perm = util.event("Visitas permanentes", "alhambra", "La Alhambra", "2026-11-15", end="2027-12-20",
                          subtype="Permanente", province="Granada", city="Granada", lat=37.17, lon=-3.59,
                          url="https://www.alhambra-patronato.es/visitar", description="Palacio nazarí.")
        ld = static.event_jsonld(perm, SITE + "/e/x.html", "2026-11-18")
        self.assertEqual(ld["@type"], "TouristAttraction")
        self.assertNotIn("startDate", ld)
        self.assertEqual(ld["address"]["addressLocality"], "Granada")
        self.assertIn("geo", ld)

    def test_offer_has_no_invented_availability(self):
        e = rich(3, price="15 €", tickets_url="https://entradas.example/3")
        ld = static.event_jsonld(e, SITE + "/e/x.html", util.iso(util.today()))
        self.assertEqual(ld["offers"]["price"], "15")
        self.assertNotIn("availability", ld["offers"])
        self.assertNotIn("offers", static.event_jsonld(rich(4), SITE + "/e/y.html"))  # sin precio ni entradas: sin oferta
        mixed = static.event_jsonld(rich(5, price="De 0 a 18 €", tickets_url="https://entradas.example/5"), SITE + "/e/z.html")
        self.assertEqual(mixed["offers"]["price"], "18")  # no se marca como gratis lo que es de pago


class TestEventPage(unittest.TestCase):
    def test_title_has_date_and_place(self):
        e = util.event("Agenda", "1", "Concierto de la Orquesta Sinfónica de Euskadi con obras de Ravel y Debussy",
                       "2026-11-21", city="Bilbao", province_code="48")
        t = static.seo_title(e, "2026-11-18", "Bilbao")
        self.assertTrue(t.endswith("· 21 nov · Bilbao"), t)
        self.assertLessEqual(len(t), static.TITLE_MAX)
        self.assertTrue(t.startswith("Concierto de la Orquesta Sinfónica de"), t)  # el nombre, casi entero
        exp = util.event("Agenda", "2", "Expo", "2026-10-01", end="2027-01-15", city="Bilbao", province_code="48")
        self.assertEqual(static.seo_title(exp, "2026-11-18", "Bilbao"), "Expo · hasta el 15 ene · Bilbao")

    def test_long_name_keeps_priority_over_place(self):
        e = util.event("Agenda", "3", "Taller per a la gent gran: Humanitats", "2026-11-10", end="2026-12-21",
                       city="Barcelona", province_code="08")
        t = static.seo_title(e, "2026-11-18", "Carrer de Sicília 321")
        self.assertTrue(t.startswith("Taller per a la gent gran: Humanitats · hasta el 21 dic · "), t)

    def test_names_that_differ_at_the_end_get_full_titles(self):
        """Cursos que solo se distinguen por el final («…iniciació», «…avançat»): títulos distintos sin recurrir a la sala."""
        evs = [rich(i, venue="Centre Cívic", city="Barcelona", province_code="08") for i in (20, 21)]
        evs[0]["title"] = "Taller Costura amb màquina de cosir per a gent gran del barri: iniciació"
        evs[1]["title"] = "Taller Costura amb màquina de cosir per a gent gran del barri: avançat"
        with tempfile.TemporaryDirectory() as tmp:
            static.write_event_pages(tmp, evs, {"08": "barcelona"})
            titles = sorted(re.search("<title>(.*?)</title>", read(tmp, "e", f)).group(1) for f in os.listdir(os.path.join(tmp, "e")))
        self.assertEqual(len(set(titles)), 2, titles)
        self.assertTrue(any("avançat" in t for t in titles), titles)

    def test_same_title_same_day_uses_venue(self):
        evs = [rich(i, venue="Centro cívico %s" % n) for i, n in ((10, "Norte"), (11, "Sur"))]
        for e in evs:
            e["title"] = "Taller de yoga"
        with tempfile.TemporaryDirectory() as tmp:
            static.write_event_pages(tmp, evs, {"48": "bizkaia"})
            titles = sorted(re.search("<title>(.*?)</title>", read(tmp, "e", f)).group(1) for f in os.listdir(os.path.join(tmp, "e")))
        self.assertEqual(len(set(titles)), 2, titles)
        self.assertIn("Centro cívico Norte", titles[0])


class TestArchitecture(unittest.TestCase):
    def test_full_site_passes_seo_check(self):
        # 130 planes en Bilbao (ciudad con página propia y listado paginado), gratis, finde y uno pobre.
        evs = [rich(i, free=(i % 3 == 0)) for i in range(130)] + [thin(1), rich(500, province_code="50", city="Zaragoza")]
        with tempfile.TemporaryDirectory() as tmp:
            pages = build(tmp, evs)
            for p in ("c/bilbao.html", "p/bizkaia.html", "p/bizkaia-pagina-2.html", "p/bizkaia-gratis.html",
                      "planes-hoy.html", "planes-este-fin-de-semana.html", "planes-gratis.html", "t/musica.html"):
                self.assertIn(p, pages)
            errors, stats = seo_check.check(tmp, SITE)
            self.assertEqual(errors, [])
            self.assertLessEqual(stats["depth_max"], 3)
            prov = read(tmp, "p", "bizkaia.html")
            mes = "%s %d" % (publish._MESES[util.today().month - 1], util.today().year)
            self.assertIn("<title>Qué hacer en Bizkaia: planes y eventos (%s) · Planika</title>" % mes, prov)
            self.assertIn('href="../c/bilbao.html"', prov)
            self.assertIn('href="../p/bizkaia-pagina-2.html"', prov)
            self.assertIn("Hay 131 planes con fecha en Bizkaia", prov)  # texto con datos reales de la página
            self.assertIn("Conciertos en España", read(tmp, "t", "musica.html"))
            ld = json.loads(prov.split('<script type="application/ld+json">')[1].split("</script>")[0])
            self.assertEqual([g["@type"] for g in ld["@graph"]], ["ItemList", "BreadcrumbList"])
            ficha = read(tmp, "e", static.event_file(evs[0]))
            self.assertIn('href="../c/bilbao.html"', ficha)  # miga de pan a la ciudad
            self.assertIn('<span class="upd">Agenda actualizada el 18 nov 2026. </span>', ficha)

    def test_city_intent_pages(self):
        """Las ciudades con página propia tienen también finde, gratis y tipo de plan, enlazadas desde
        la provincia, el tipo de plan y las páginas nacionales («qué hacer en Bilbao este fin de semana»)."""
        fri, _ = publish.weekend_window(util.today())
        day = util.iso(fri)
        evs = [dict(rich(i, free=(i % 2 == 0)), start=day, end=day) for i in range(45)]
        evs += [rich(100 + i, category="otros") for i in range(6)]
        with tempfile.TemporaryDirectory() as tmp:
            pages = build(tmp, evs)
            for p in ("c/bilbao.html", "c/bilbao-fin-de-semana.html", "c/bilbao-gratis.html", "c/bilbao-musica.html"):
                self.assertIn(p, pages)
            self.assertNotIn("c/bilbao-otros.html", pages)
            self.assertIn('href="../c/bilbao-fin-de-semana.html"', read(tmp, "p", "bizkaia-fin-de-semana.html"))
            self.assertIn('href="c/bilbao-fin-de-semana.html"', read(tmp, "planes-este-fin-de-semana.html"))
            self.assertIn('href="../c/bilbao-musica.html"', read(tmp, "t", "musica.html"))
            self.assertIn('href="../c/bilbao-musica.html"', read(tmp, "p", "bizkaia-musica.html"))
            city = read(tmp, "c", "bilbao.html")
            self.assertIn('href="bilbao-gratis.html"', city)
            finde = read(tmp, "c", "bilbao-fin-de-semana.html")
            self.assertIn("<title>Qué hacer este fin de semana en Bilbao (", finde)
            self.assertIn('href="../c/bilbao.html"', finde)  # miga de pan: Inicio › Bizkaia › Bilbao › finde
            errors, _ = seo_check.check(tmp, SITE)
            self.assertEqual(errors, [])

    def test_indexnow_sends_only_changed_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, [rich(1), rich(2)])
            self.assertIsNone(indexnow.find_key(tmp))
            key = "0123456789abcdef0123456789abcdef"
            with open(os.path.join(tmp, key + ".txt"), "w") as fh:
                fh.write(key)
            self.assertEqual(indexnow.find_key(tmp), key)
            today = util.iso(util.today())
            urls = indexnow.changed_urls(tmp, today)
            self.assertIn(SITE + "/p/bizkaia.html", urls)
            self.assertEqual(len(urls), len(set(urls)))
            self.assertEqual(indexnow.changed_urls(tmp, "2999-01-01"), [])  # nada cambiado después: nada que enviar

    def test_today_page_switches_to_next_day_at_seven(self):
        """«Hoy» lleva ya preparada la versión de mañana, que el navegador activa a las 07:00 de Madrid."""
        from datetime import timedelta
        t0 = util.today()
        t1 = util.iso(t0 + timedelta(days=1))
        evs = [rich(1), dict(rich(2), id="m2", start=t1, end=t1, title="Concierto de mañana")]
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, evs)
            page = read(tmp, "planes-hoy.html")
            self.assertEqual(page.count('id="next-day"'), 1)
            self.assertIn('data-at="%sT07:00"' % t1, page)
            tpl = page.split('<template id="next-day"')[1].split("</template>")[0]
            self.assertIn("from=%s&amp;to=%s" % (t1, t1), tpl)  # el botón de la app pasa a mañana
            self.assertIn("Concierto de mañana", tpl)
            visible = page.split('<template id="next-day"')[0]
            self.assertNotIn("Concierto de mañana", visible.split('<main class="wrap">')[1])
            self.assertIn("hourCycle:'h23'", page)
            errors, _ = seo_check.check(tmp, SITE)
            self.assertEqual(errors, [])

    def test_analytics_only_through_consent(self):
        """Ninguna página carga Google Analytics por su cuenta: solo consent.js, y solo si se acepta.
        Todas llevan en el pie el enlace para cambiar la decisión."""
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, [rich(1), rich(2, free=True)])
            from planes import legal
            legal.write_legal_pages(tmp)
            pages = [os.path.join(dp, f) for dp, _, fs in os.walk(tmp) for f in fs
                     if f.endswith(".html") and os.path.join(dp, f) != os.path.join(tmp, "index.html")]  # la portada de prueba es un esqueleto
            self.assertGreater(len(pages), 5)
            for p in pages:
                page = read(p)
                self.assertNotIn("googletagmanager", page, p)
                self.assertIn('src="/consent.js"', page, p)
                self.assertIn("data-privacy-settings", page, p)
        js = read(ROOT, "site", "consent.js")
        self.assertIn('if (v === "accepted") loadGA();', js)  # sin decisión guardada: se muestra el panel, no se carga GA
        self.assertIn('data-choice="rejected"', js)
        index = read(ROOT, "site", "index.html")
        self.assertNotIn("googletagmanager", index)
        self.assertIn("data-privacy-settings", index)

    def test_stale_hub_pages_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "p"))
            open(os.path.join(tmp, "p", "teruel-musica.html"), "w").close()
            build(tmp, [rich(1)])
            self.assertFalse(os.path.exists(os.path.join(tmp, "p", "teruel-musica.html")))

    def test_seo_check_detects_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, [rich(1)])
            with open(os.path.join(tmp, "p", "bizkaia.html"), "a", encoding="utf-8") as fh:
                fh.write('<a href="no-existe.html">x</a>')
            errors, _ = seo_check.check(tmp, SITE)
            self.assertTrue(any("enlace roto" in e for e in errors), errors)


class _Day:
    """Fija la fecha de «hoy» en todos los módulos que la usan (las pruebas corren cualquier día del año)."""
    def __init__(self, iso_day):
        from datetime import date
        self.d = date.fromisoformat(iso_day)

    def __enter__(self):
        from unittest import mock
        self.ps = [mock.patch.object(m, "today", return_value=self.d) for m in (publish, static, seo, util)]
        for p in self.ps:
            p.start()
        return self

    def __exit__(self, *a):
        for p in self.ps:
            p.stop()


class TestPuente(unittest.TestCase):
    def test_puente_dates(self):
        cases = {2025: ("2025-12-06", "2025-12-08"), 2026: ("2026-12-05", "2026-12-08"), 2027: ("2027-12-04", "2027-12-08"),
                 2028: ("2028-12-06", "2028-12-10"), 2029: ("2029-12-06", "2029-12-09"), 2030: ("2030-12-06", "2030-12-08")}
        for y, (a, b) in cases.items():
            pa, pb = publish.puente_diciembre(y)
            self.assertEqual((util.iso(pa), util.iso(pb)), (a, b), y)
        self.assertEqual(publish.puente_rango(*publish.puente_diciembre(2026)), "del sábado 5 al martes 8 de diciembre")
        self.assertTrue(publish.puente_estado("2026-11-20")[3])
        self.assertTrue(publish.puente_estado("2026-12-08")[3])
        self.assertEqual(publish.puente_estado("2026-12-09")[:1] + (publish.puente_estado("2026-12-09")[3],), (2026, False))
        self.assertEqual(publish.puente_estado("2027-03-01")[0], 2026)  # fuera de temporada: el último puente
        self.assertFalse(publish.puente_estado("2027-09-30")[3])

    def _evs(self):
        evs = [dict(rich(i, free=(i % 4 == 0)), start="2026-12-%02d" % (5 + i % 4), end="2026-12-%02d" % (5 + i % 4)) for i in range(30)]
        evs += [dict(rich(100 + i, province_code="28", city="Madrid"), start="2026-12-06", end="2026-12-06") for i in range(6)]
        evs += [dict(rich(200 + i, category="navidad"), title="Mercado de Navidad %d" % i, start="2026-12-05", end="2026-12-08") for i in range(3)]
        evs += [rich(300, province_code="50", city="Zaragoza")]  # fuera del puente
        return evs

    def test_puente_page_in_season(self):
        with _Day("2026-11-20"), tempfile.TemporaryDirectory() as tmp:
            pages = build(tmp, self._evs())
            self.assertIn("puente-diciembre.html", pages)
            page = read(tmp, "puente-diciembre.html")
            self.assertIn("<title>Puente de diciembre 2026: qué hacer del 5 al 8 de diciembre · Planika</title>", page)
            self.assertIn('content="index,follow', page)
            self.assertIn("Hay 39 planes con fecha del sábado 5 al martes 8 de diciembre", page)
            self.assertIn('<section id="navidad">', page)
            self.assertIn('<section id="bizkaia">', page)
            self.assertIn('<section id="madrid">', page)
            self.assertIn("Sábado 5</a> (", page)
            self.assertNotIn("Zaragoza", page.split("Planes del puente por provincia")[1].split("Otras páginas")[0])
            self.assertIn('href="puente-diciembre.html"', read(tmp, "planes-gratis.html"))  # enlazada desde los hubs
            self.assertIn("puente-diciembre.html", read(tmp, "sitemap-paginas.xml"))
            self.assertEqual(seo_check.check(tmp, SITE)[0], [])

    def test_puente_page_out_of_season_is_noindex(self):
        with _Day("2026-12-09"), tempfile.TemporaryDirectory() as tmp:
            evs = [dict(rich(i), start="2026-12-10", end="2026-12-10") for i in range(25)]
            pages = build(tmp, evs)
            self.assertNotIn("puente-diciembre.html", pages)
            page = read(tmp, "puente-diciembre.html")  # la dirección sigue existiendo: no da 404
            self.assertIn('content="noindex,follow"', page)
            self.assertIn("El puente de diciembre de 2026 ya pasó", page)
            self.assertNotIn("puente-diciembre.html", read(tmp, "sitemap-paginas.xml"))
            self.assertNotIn('href="puente-diciembre.html"', read(tmp, "planes-gratis.html"))
            self.assertEqual(seo_check.check(tmp, SITE)[0], [])


class TestGoneFichas(unittest.TestCase):
    def _build(self, tmp, evs):
        return publish.write_pages(tmp, evs, [], "2026-11-18T04:30", state_path=os.path.join(tmp, "state.json"),
                                   fichas_path=os.path.join(tmp, "fichas.json"))

    def test_gone_fichas_stay_with_notice_for_60_days(self):
        a = dict(rich(1), start="2026-11-20", end="2026-11-20")
        b = dict(rich(2), start="2026-11-20", end="2026-11-20", title="Concierto que ya pasó")
        c = dict(rich(3), start="2026-11-28", end="2026-11-28", title="Concierto que se cancela")
        d = dict(rich(4), start="2026-11-29", end="2026-11-29", title="Concierto con nombre viejo")
        e = dict(rich(5), start="2026-11-30", end="2026-11-30", title="Concierto que cambia de id")
        others = [dict(rich(10 + i), start="2026-11-25", end="2026-11-25") for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            with _Day("2026-11-20"):
                self._build(tmp, [a, b, c, d, e] + others)
            fb, fc, fd = (static.event_file(x) for x in (b, c, d))
            d2 = dict(d, title="Concierto con nombre nuevo")
            e2 = dict(e, id="otroid5")
            with _Day("2026-11-21"):
                pages = self._build(tmp, [d2, e2] + others)  # a y b ya pasaron, c desaparece, d cambia de título, e de id
                self.assertIn('url=%s"' % static.event_file(e2), read(tmp, "e", static.event_file(e)))
                past = read(tmp, "e", fb)
                self.assertIn('content="noindex,follow"', past)
                self.assertIn("<title>Concierto que ya pasó (ya pasó) · Planika</title>", past)
                self.assertIn("Planes parecidos próximos", past)
                self.assertIn(static.event_file(others[0]), past)       # enlaza planes próximos de la misma ciudad
                self.assertIn('href="../p/bizkaia.html"', past)
                self.assertIn("ya no aparece en la agenda", read(tmp, "e", fc))
                moved = read(tmp, "e", fd)
                self.assertIn('http-equiv="refresh"', moved)
                self.assertIn('<link rel="canonical" href="%s/e/%s">' % (SITE, static.event_file(d2)), moved)
                self.assertNotIn("e/" + fb, pages)                       # no cuenta como página indexable
                self.assertNotIn(fb, read(tmp, "sitemap-fichas.xml"))
                state = json.loads(read(tmp, "fichas.json"))
                self.assertEqual(state[fb]["g"], "2026-11-21")
                self.assertNotIn("g", state[static.event_file(d2)])
            with _Day("2027-01-20"):  # 60 días después de desaparecer: se mantiene
                self._build(tmp, others)
                self.assertTrue(os.path.exists(os.path.join(tmp, "e", fb)))
            with _Day("2027-01-21"):  # al día 61, la dirección deja de existir
                self._build(tmp, others)
                self.assertFalse(os.path.exists(os.path.join(tmp, "e", fb)))
                self.assertNotIn(fb, json.loads(read(tmp, "fichas.json")))

    def test_same_name_same_day_is_not_redirected(self):
        a1 = dict(rich(1), title="Taller de pilates", start="2026-11-25", end="2026-11-25")
        a2 = dict(rich(2), title="Taller de pilates", start="2026-11-25", end="2026-11-25")
        a3 = dict(rich(3), title="Taller de pilates", start="2026-11-25", end="2026-11-25")
        with tempfile.TemporaryDirectory() as tmp:
            with _Day("2026-11-20"):
                self._build(tmp, [a1, a2])
            with _Day("2026-11-21"):
                self._build(tmp, [a2, a3])  # a1 desaparece; a3 es otro taller con el mismo nombre
                page = read(tmp, "e", static.event_file(a1))
                self.assertNotIn('http-equiv="refresh"', page)
                self.assertIn("ya no aparece en la agenda", page)

    def test_bad_state_names_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "fichas.json"), "w") as fh:
                json.dump({"../../index.html": {"id": "x", "t": "x", "s": "2026-01-01", "e": "2026-01-01", "k": "musica", "pc": "48"}}, fh)
            self._build(tmp, [rich(1)])
            self.assertFalse(os.path.exists(os.path.join(tmp, "index.html")))


class TestSeason(unittest.TestCase):
    def test_xmas_sections(self):
        mk = lambda i, t, d, **kw: util.event("Agenda", "x%d" % i, t, d, province_code="28", city="Madrid", **kw)
        evs = [mk(1, "Mercado de Navidad de la Plaza Mayor", "2026-11-26", end="2026-12-31"),
               mk(2, "Mercat de Nadal de Tordera", "2026-11-28"), mk(3, "Christmas Market del puerto", "2026-12-05"),
               mk(4, "Gran concierto de Fin de Año", "2026-12-28"), mk(5, "Concierto de Año Nuevo", "2027-01-01"),
               mk(6, "Pre campanadas", "2026-12-30"), mk(7, "Programa Fin de Año Musical", "2026-11-21"),  # fuera de fechas
               mk(8, "Belén Rueda presenta su libro", "2026-12-02"),                                     # no es un belén
               mk(9, "Taller de iluminación escénica", "2026-12-02")]                                   # no son luces de Navidad
        secs = {k: [e["title"] for e in it] for k, _, it in publish.xmas_sections(evs, "2026-11-18")}
        self.assertEqual(len(secs["mercados"]), 3)
        self.assertEqual(sorted(secs["nochevieja"]), ["Concierto de Año Nuevo", "Gran concierto de Fin de Año", "Pre campanadas"])
        self.assertNotIn("belenes", secs)
        self.assertNotIn("luces", secs)
        self.assertEqual(publish.season_year("2027-01-03"), 2026)
        evs.append(mk(10, "Encendido navideño", "2026-11-21", category="navidad"))
        with tempfile.TemporaryDirectory() as tmp:
            build(tmp, evs)
            nav = read(tmp, "t", "navidad.html")
            self.assertIn('<section id="mercados">', nav)
            self.assertIn("Planes de Navidad 2026 en España", nav)
            self.assertEqual(seo_check.check(tmp, SITE)[0], [])


class TestAssets(unittest.TestCase):
    def test_prerender_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as fh:
                fh.write('<h2 class="count" id="count" aria-live="polite"></h2>\n<section id="list" class="list" aria-live="polite"></section>')
            evs = static.default_order([rich(i) for i in range(30)])
            self.assertTrue(publish.prerender_index(tmp, evs))
            page = read(tmp, "index.html")
            self.assertEqual(page.count("<article class=\"card pop"), 24)
            self.assertIn('href="e/%s"' % static.event_file(evs[0]), page)
            self.assertIn('aria-live="polite">30 planes</h2>', page)
            self.assertFalse(publish.prerender_index(tmp, evs))  # sin cambios: no reescribe
            self.assertEqual(page.count('<section id="list"'), 1)

    def test_stamp_index_versions_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "data", "d"))
            for name, body in (("styles.css", "a{}"), ("app.js", "1"), ("data/core.js", "2"), ("data/d/0.js", "3")):
                with open(os.path.join(tmp, name), "w") as fh:
                    fh.write(body)
            with open(os.path.join(tmp, "index.html"), "w") as fh:
                fh.write('<link rel="stylesheet" href="styles.css"><script defer src="data/core.js"></script>'
                         '<script defer src="data/d/0.js?v=old"></script><script defer src="app.js"></script><img src="hero.jpg">')
            self.assertTrue(static.stamp_index(tmp))
            page = read(tmp, "index.html")
            self.assertRegex(page, r'href="styles\.css\?v=[0-9a-f]{10}"')
            self.assertRegex(page, r'src="app\.js\?v=[0-9a-f]{10}"')
            self.assertNotIn("v=old", page)
            self.assertIn('src="hero.jpg"', page)
            self.assertFalse(static.stamp_index(tmp))  # sin cambios: no reescribe
            with open(os.path.join(tmp, "app.js"), "w") as fh:
                fh.write("2")
            self.assertTrue(static.stamp_index(tmp))  # app.js cambia: cambia su versión


class TestDataQuality(unittest.TestCase):
    def test_mojibake(self):
        self.assertEqual(util.strip_html("Visitas a la exposiciÃģn de MÃšsica en MÃĄlaga"),
                         "Visitas a la exposición de Música en Málaga")
        self.assertEqual(util.strip_html("Programa de Competencias (EdiciÃ³n 2) · MuÃ±oz"), "Programa de Competencias (Edición 2) · Muñoz")
        self.assertEqual(util.strip_html("SÃO PAULO"), "SÃO PAULO")  # texto legítimo: no se toca

    def test_classification_fixes(self):
        c = classify.classify
        self.assertEqual(c(["FiestasNavidadesReyes"], "Cine homenaje a Tim Burton"), "cine")
        self.assertEqual(c(["FiestasNavidadesReyes"], "Encendido del árbol de la Navidad"), "navidad")
        self.assertEqual(c(["FiestasNavidadesReyes"], "Gran verbena"), "fiestas")
        self.assertEqual(c([], "Taller 'Ioga en família'"), "infantil")
        self.assertEqual(c([], "Activitat per a infants 'Explota els globus!'"), "infantil")
        self.assertEqual(c([], "Pessebre vivent de Tona"), "navidad")
        self.assertEqual(c([], "II Congreso de cuidados"), "charlas")
        self.assertNotEqual(c([], "El castell de Rubió"), "fiestas")
        self.assertNotEqual(c([], "Holy, Donna Ferrato", "Una muestra sobre la cultura popular"), "fiestas")
        self.assertEqual(c([], "Castells a la plaça"), "fiestas")


if __name__ == "__main__":
    unittest.main()
