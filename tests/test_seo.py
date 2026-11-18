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


class TestEventPage(unittest.TestCase):
    def test_title_has_date_and_place(self):
        e = util.event("Agenda", "1", "Concierto de la Orquesta Sinfónica de Euskadi con obras de Ravel y Debussy",
                       "2026-11-21", city="Bilbao", province_code="48")
        t = static.seo_title(e, "2026-11-18", "Bilbao")
        self.assertTrue(t.endswith("· 21 nov · Bilbao"), t)
        self.assertLessEqual(len(t), 60)
        exp = util.event("Agenda", "2", "Expo", "2026-10-01", end="2027-01-15", city="Bilbao", province_code="48")
        self.assertEqual(static.seo_title(exp, "2026-11-18", "Bilbao"), "Expo · hasta el 15 ene · Bilbao")

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
            self.assertIn("<title>Qué hacer en Bizkaia: planes y eventos · Planika</title>", prov)
            self.assertIn('href="../c/bilbao.html"', prov)
            self.assertIn('href="../p/bizkaia-pagina-2.html"', prov)
            self.assertIn("Hay 131 planes con fecha en Bizkaia", prov)  # texto con datos reales de la página
            self.assertIn("Conciertos en España", read(tmp, "t", "musica.html"))
            ld = json.loads(prov.split('<script type="application/ld+json">')[1].split("</script>")[0])
            self.assertEqual([g["@type"] for g in ld["@graph"]], ["ItemList", "BreadcrumbList"])
            ficha = read(tmp, "e", static.event_file(evs[0]))
            self.assertIn('href="../c/bilbao.html"', ficha)  # miga de pan a la ciudad
            self.assertIn('<span class="upd">Agenda actualizada el 18 nov 2026. </span>', ficha)

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
