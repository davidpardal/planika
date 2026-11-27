# -*- coding: utf-8 -*-
"""Pruebas mínimas de las piezas que más se rompen: fechas, provincias, clasificación, iCal y sesiones."""
import json
import os
import re
import sys
import tempfile
import unittest
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import classify, publish, static, util  # noqa: E402



def _all_sitemaps(site_dir):
    """sitemap.xml es un índice: devuelve el texto del índice y de todos los sitemaps que enlaza."""
    import io
    parts = []
    for fn in sorted(os.listdir(site_dir)):
        if fn.startswith("sitemap") and fn.endswith(".xml"):
            with open(os.path.join(site_dir, fn), encoding="utf-8") as fh:
                parts.append(fh.read())
    return io.StringIO("\n".join(parts))

class TestUtil(unittest.TestCase):
    def test_parse_date(self):
        self.assertEqual(util.parse_date("2026-11-21 18:00:00.0"), "2026-11-21")
        self.assertEqual(util.parse_date("21/11/2026"), "2026-11-21")
        self.assertEqual(util.parse_date("2026-11-21T20:00:00Z"), "2026-11-21")
        self.assertIsNone(util.parse_date("sin fecha"))

    def test_parse_time(self):
        self.assertEqual(util.parse_time("A les 18 h"), "18:00")
        self.assertEqual(util.parse_time(", V - 19.30 h"), "19:30")
        self.assertEqual(util.parse_time("De 09:30h a 14:30h"), "09:30")
        self.assertEqual(util.parse_time(""), "")

    def test_resolve_province(self):
        self.assertEqual(util.resolve_province(province="Castelló")[0], "12")
        self.assertEqual(util.resolve_province(province="Araba/Álava")[0], "01")
        self.assertEqual(util.resolve_province(city="Donostia / San Sebastián")[0], "20")
        self.assertEqual(util.resolve_province(city="Bilbao")[0], "48")
        self.assertEqual(util.resolve_province(province="Bilbao, Vizcaya")[0], "48")
        self.assertEqual(util.resolve_province(code="7")[2], "Illes Balears")
        self.assertEqual(util.resolve_province(city="Biarritz"), (None, None, None))

    def test_event_normalisation(self):
        ev = util.event("Test", "1", "<b>Concierto</b>", "2026-11-21", end="2924-06-30", time="00:00", price="Gratis", province="Madrid")
        self.assertEqual(ev["title"], "Concierto")
        self.assertEqual(ev["time"], "")
        self.assertTrue(ev["free"])
        self.assertLessEqual(ev["end"], util.iso(util.today() + timedelta(days=400)))  # tope de fin (antes, fecha fija que caducaba)
        self.assertEqual(ev["ccaa"], "Comunidad de Madrid")
        self.assertIsNone(util.event("Test", "2", "", "2026-11-21"))

    def test_parse_ics(self):
        ics = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Hola\r\n mundo\r\nDTSTART;TZID=Europe/Madrid:20261118T200000\r\nEND:VEVENT\r\nEND:VCALENDAR"
        evs = util.parse_ics(ics)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["SUMMARY"], "Holamundo")
        self.assertEqual(evs[0]["DTSTART"], "20261118T200000")


class TestCanonCities(unittest.TestCase):
    def _run(self, *pairs):
        evs = [{"city": c, "province_code": pc} for c, pc in pairs]
        n = util.canon_cities(evs)
        return n, [e["city"] for e in evs]

    def test_bilingual_names_join(self):
        n, out = self._run(("Donostia / San Sebastián", "20"), ("San Sebastián", "20"), ("Pamplona", "31"), ("Pamplona/Iruña", "31"))
        self.assertEqual(out, ["Donostia / San Sebastián"] * 2 + ["Pamplona / Iruña"] * 2)
        self.assertEqual(n, 3)

    def test_official_spelling(self):
        _, out = self._run(("Vilanova I La Geltru", "08"), ("L Hospitalet De Llobregat", "08"), ("Mataro", "08"), ("Palma", "07"),
                           ("Vitoria", "01"), ("Peñíscola", "12"))
        self.assertEqual(out, ["Vilanova i la Geltrú", "L'Hospitalet de Llobregat", "Mataró", "Palma de Mallorca", "Vitoria-Gasteiz", "Peñíscola"])

    def test_single_form_kept(self):
        _, out = self._run(("Alicante", "03"), ("Alicante", "03"), ("Bilbao", "48"))
        self.assertEqual(out, ["Alicante", "Alicante", "Bilbao"])
        _, out = self._run(("Alicante", "03"), ("Alacant", "03"))
        self.assertEqual(out, ["Alicante / Alacant"] * 2)

    def test_other_province_and_unknown_places(self):
        # Mismo nombre en otra provincia no se toca; lo que no es municipio solo unifica mayúsculas y tildes
        _, out = self._run(("San Sebastián", "28"), ("El Palmar", "30"), ("El palmar", "30"), ("El Palmar", "30"), ("", "30"))
        self.assertEqual(out, ["San Sebastián", "El Palmar", "El Palmar", "El Palmar", ""])


class TestClassify(unittest.TestCase):
    def test_source_types(self):
        self.assertEqual(classify.classify(["Concierto"], "Lo que sea"), "musica")
        self.assertEqual(classify.classify(["agenda:categories/teatre"], "x"), "escena")
        self.assertEqual(classify.classify(["Ferias, Exposiciones y Museos"], "x"), "expos")

    def test_keywords(self):
        self.assertEqual(classify.classify([], "Ruta de senderismo por el Montseny"), "naturaleza")
        self.assertEqual(classify.classify([], "Taller de cerámica para niños"), "infantil")
        self.assertEqual(classify.classify([], "Mercado medieval de Ávila"), "gastro")
        self.assertEqual(classify.classify([], "Athletic Club - Real Sociedad", ""), "otros")

    def test_prefixes_do_not_leak(self):
        # "vi", "cata" y "castell" como prefijo clasificaban mal «Vigil», «catedral» o «castellano»
        self.assertEqual(classify.classify([], "José Manuel Vigil presenta su libro de memorias"), "charlas")
        self.assertEqual(classify.classify([], "Club de Lectura en Castellano"), "charlas")
        self.assertEqual(classify.classify([], "Concierto en la catedral"), "musica")
        self.assertEqual(classify.classify([], "Cata de vinos de la tierra"), "gastro")
        self.assertEqual(classify.classify([], "Diada castellera amb els castells de la colla"), "fiestas")

    def test_audience_wins(self):
        self.assertEqual(classify.classify(["Concierto"], "x", audience="Niños, Familias"), "infantil")


class TestPublish(unittest.TestCase):
    def test_group_sessions(self):
        mk = lambda d, t: util.event("S", d + t, "Hamlet", d, time=t, venue="Teatro Real", province_code="28")  # noqa: E731
        evs = [mk("2026-11-21", "20:00"), mk("2026-11-22", "20:00"), mk("2026-11-23", "19:00"),
               util.event("S", "x", "Otra obra", "2026-11-21", venue="Teatro Real", province_code="28")]
        out, merged = publish.group_sessions(evs)
        self.assertEqual(merged, 2)
        ham = next(e for e in out if e["title"] == "Hamlet")
        self.assertEqual(ham["sessions"], ["2026-11-21", "2026-11-22", "2026-11-23"])
        self.assertEqual(ham["end"], "2026-11-23")
        self.assertEqual(len(out), 2)

    def test_slug(self):
        self.assertEqual(publish.slug("Santa Cruz de Tenerife"), "santa-cruz-de-tenerife")
        self.assertEqual(publish.slug("A Coruña"), "a-coruna")


class TestStatic(unittest.TestCase):
    def ev(self, **kw):
        base = dict(time="20:00", venue="Teatro Real", city="Madrid", province_code="28", price="Desde 12,50 €",
                    tickets_url="https://entradas.example/x")
        base.update(kw)
        return util.event("S", "id1", "¡Hamlet! · Versión Ñ", "2026-11-21", **base)

    def test_event_file(self):
        e = self.ev()
        self.assertEqual(static.event_file(e), "hamlet-version-n-%s.html" % e["id"])
        self.assertLessEqual(len(static.event_slug("palabra " * 40)), 60)
        self.assertEqual(static.event_file(dict(e, title="日本語")), e["id"] + ".html")

    def test_jsonld(self):
        e = self.ev()
        ld = static.event_jsonld(e, "https://x/e/a.html", "2026-11-14")
        self.assertEqual(ld["@type"], "Event" if e["category"] not in static.LD_TYPE else static.LD_TYPE[e["category"]])
        self.assertEqual(ld["startDate"], "2026-11-21T20:00:00+01:00")
        self.assertEqual(ld["location"]["address"]["addressRegion"], "Madrid")
        self.assertEqual(ld["offers"]["price"], "12.5")
        canarias = static.event_jsonld(self.ev(province_code="38", city="La Laguna"), "u", "2026-11-14")
        self.assertEqual(canarias["startDate"], "2026-11-21T20:00:00+00:00")

    def test_event_page_escapes(self):
        # Las fuentes ya se limpian en util.event; aquí se fuerza un evento "sucio" para probar la segunda barrera
        e = dict(self.ev(), url="javascript:alert(1)", venue="Teatro <Real>", description='Una obra </script> con "comillas"')
        page = static.event_page(e, t0="2026-11-14", prov_slug="madrid")
        self.assertNotIn("javascript:alert", page)
        # solo los cierres propios: el bloque JSON-LD, consent.js (GA4 solo se carga si se acepta), i18n.js (idioma
        # de la interfaz) y el registro del service worker
        self.assertEqual(page.count("</script>"), 3 + static.PWA_HEAD.count("</script>"))
        self.assertIn("Teatro &lt;Real&gt;", page)
        ld = json.loads(page.split('<script type="application/ld+json">')[1].split("</script>")[0])
        self.assertIn("</script>", ld["@graph"][0]["description"])
        crumbs = ld["@graph"][1]
        self.assertEqual(crumbs["@type"], "BreadcrumbList")
        self.assertEqual([c["name"] for c in crumbs["itemListElement"]][:2], ["Inicio", "Madrid"])
        self.assertTrue(crumbs["itemListElement"][1]["item"].endswith("/p/madrid.html"))
        self.assertEqual(crumbs["itemListElement"][-1]["item"], "https://planikaapp.com/e/" + static.event_file(e))

    def test_write_data_roundtrip(self):
        evs = [self.ev(), util.event("S", "id2", "Expo larga", "2026-01-01", end="2027-01-01", province_code="08")]
        evs = static.default_order(static.unique_ids(evs + [evs[0]]), "2026-11-14")
        self.assertEqual([e["title"] for e in evs], ["Expo larga", "¡Hamlet! · Versión Ñ"])
        payload = {"updated_at": "2026-11-14T04:15", "from": "2026-11-14", "to": "2027-05-13", "days": 180,
                   "categories": [], "provinces": [], "sources": [], "events": evs}
        with tempfile.TemporaryDirectory() as tmp:
            size, chunks = static.write_data(tmp, payload)
            self.assertEqual(chunks, 1)
            with open(os.path.join(tmp, "core.js"), encoding="utf-8") as fh:
                core = fh.read()
            data = json.loads(core.split("window.PLANES_CORE=")[1].rstrip(";\n"))
            rows = data["events"]
            # la lista de tipos sale del código aunque el payload (events.json viejo) traiga otra: los índices dependen de ella
            self.assertEqual([c["key"] for c in data["categories"]], static.CAT_KEYS)
            self.assertEqual(rows[1][0], evs[1]["id"])
            self.assertEqual(rows[1][13], 2)  # con entradas, no gratis
            with open(os.path.join(tmp, "d", "0.js"), encoding="utf-8") as fh:
                det = fh.read()
            self.assertTrue(det.startswith('PLANIKA_D("2026-11-14T04:15",0,'))
            self.assertIn("entradas.example", det)
            self.assertNotIn("entradas.example", core)


class TestPermanent(unittest.TestCase):
    def test_when_and_order(self):
        perm = util.event("Visitas permanentes", "alhambra", "La Alhambra", "2026-11-15",
                          end="2027-12-20", subtype="Permanente", province="Granada", city="Granada",
                          url="https://www.alhambra-patronato.es/visitar")
        dated = util.event("Agenda", "c", "Concierto", "2026-11-20", province="Granada", city="Granada")
        self.assertTrue(util.is_permanent(perm))
        self.assertEqual(static._when(perm, "2026-11-15"), "Visita permanente")
        ordered = static.default_order([perm, dated], "2026-11-15")
        self.assertEqual([e["title"] for e in ordered], ["Concierto", "La Alhambra"])
        # La ventana no supera el tope de fechas "permanentes" del normalizador.
        self.assertLessEqual(perm["end"], "2027-12-20")
        self.assertGreaterEqual(perm["end"], perm["start"])

    def test_feeds_and_province_page(self):
        perm = util.event("Visitas permanentes", "seo", "La Seo", "2026-11-15", end="2027-12-01",
                          subtype="Permanente", province_code="50", city="Zaragoza",
                          url="https://example.com/seo", description="Catedral.")
        dated = util.event("Agenda", "1", "Concierto en el auditorio", "2026-11-16",
                           province_code="50", city="Zaragoza")
        with tempfile.TemporaryDirectory() as tmp:
            publish.write_feeds(tmp, [dated, perm])
            with open(os.path.join(tmp, "todos.xml"), encoding="utf-8") as fh:
                todos = fh.read()
            with open(os.path.join(tmp, "provincia-50.xml"), encoding="utf-8") as fh:
                prov = fh.read()
            self.assertIn("Concierto", todos)
            self.assertNotIn("La Seo", todos)
            self.assertIn("La Seo", prov)
            self.assertIn("Visita permanente", prov)
            publish.write_pages(tmp, [perm])
            page = os.path.join(tmp, "p", "zaragoza.html")
            self.assertTrue(os.path.exists(page))
            with open(page, encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn("La Seo", html)
            self.assertIn("Visita permanente", html)
            with _all_sitemaps(tmp) as fh:
                self.assertIn("zaragoza.html", fh.read())

    def test_combo_pages_need_five_events(self):
        evs = [util.event("Agenda", str(i), "Concierto %d" % i, "2026-11-20",
                          province_code="50", city="Zaragoza", category="musica") for i in range(5)]
        evs += [util.event("Agenda", "c%d" % i, "Charla %d" % i, "2026-11-20",
                           province_code="50", city="Zaragoza", category="charlas") for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp:
            pages = publish.write_pages(tmp, evs)
            self.assertIn("p/zaragoza-musica.html", pages)
            self.assertNotIn("p/zaragoza-charlas.html", pages)
            with open(os.path.join(tmp, "p", "zaragoza.html"), encoding="utf-8") as fh:
                self.assertIn("zaragoza-musica.html", fh.read())
            with _all_sitemaps(tmp) as fh:
                self.assertIn("zaragoza-musica.html", fh.read())

    def test_promo_page_and_footer_link(self):
        ev = util.event("Agenda", "1", "Concierto", "2026-11-20",
                        province_code="50", city="Zaragoza", category="musica")
        with tempfile.TemporaryDirectory() as tmp:
            pages = publish.write_pages(tmp, [ev])
            self.assertIn("promociona-tu-evento.html", pages)
            with open(os.path.join(tmp, "promociona-tu-evento.html"), encoding="utf-8") as fh:
                promo = fh.read()
            self.assertIn("Publica tu evento gratis", promo)
            self.assertIn("FAQPage", promo)
            self.assertIn("rpc/submit_event", promo)          # formulario propio (Supabase), sin Google Forms
            self.assertNotIn("docs.google.com/forms", promo)
            for price in ("0 €", "5 €", "12 €", "20 €"):
                self.assertIn(price, promo)
            self.assertNotIn('value="FR33"', promo)           # el formulario solo admite provincias españolas
            self.assertRegex(promo, r"\d+ planes de \d+ provincias")  # cifras del día, no escritas a mano
            self.assertIn('name="kind" value="lugar"', promo)       # escape rooms, boleras, parques de bolas…
            self.assertIn("?tipo=lugar#publicar", promo)
            with open(os.path.join(tmp, "p", "zaragoza.html"), encoding="utf-8") as fh:
                self.assertIn("../promociona-tu-evento.html", fh.read())
            with _all_sitemaps(tmp) as fh:
                self.assertIn("promociona-tu-evento.html", fh.read())

    def test_sources_page(self):
        ev = util.event("Agenda", "1", "Concierto", "2026-11-20",
                        province_code="50", city="Zaragoza", category="musica")
        srcs = [{"name": "Ayuntamiento <A>", "home": "https://a.example/?x=1&y=2", "count": 1200, "error": ""},
                {"name": "Fuente B", "home": "https://b.example/", "count": 34, "error": "timeout"},
                {"name": "Fuente vacía", "home": "https://c.example/", "count": 0, "error": ""}]
        with tempfile.TemporaryDirectory() as tmp:
            pages = publish.write_pages(tmp, [ev], srcs, "2026-11-17T04:30")
            self.assertIn("fuentes.html", pages)
            with open(os.path.join(tmp, "fuentes.html"), encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("2 fuentes, 1.234 planes", page)
            self.assertIn("Ayuntamiento &lt;A&gt;", page)
            self.assertIn("x=1&amp;y=2", page)
            self.assertNotIn("con error en la última descarga", page)   # los errores no se enseñan al público
            self.assertNotIn("Fuente vacía", page)                     # fuentes con 0 planes fuera de la lista
            with _all_sitemaps(tmp) as fh:
                self.assertIn("/fuentes.html", fh.read())

    def test_legal_pages(self):
        from planes import legal
        cfg = {"nombre": "Ana <Test>", "nif": "", "domicilio": "", "email": "hola@example.com"}
        with tempfile.TemporaryDirectory() as tmp:
            pages = publish.write_pages(tmp, [], [], "")
            self.assertIn("privacidad.html", pages)
            self.assertIn("aviso-legal.html", pages)
            with _all_sitemaps(tmp) as fh:
                sm = fh.read()
            self.assertIn("/privacidad.html", sm)
            self.assertIn("/aviso-legal.html", sm)
            with open(os.path.join(tmp, "privacidad.html"), encoding="utf-8") as fh:
                base = fh.read()
            self.assertIn("planika_favs", base)
            self.assertNotIn("Titular:", base)            # sin datos de titular no se inventa ninguno
        priv, aviso = legal.privacy_page(cfg), legal.legal_page(cfg)
        self.assertIn("Ana &lt;Test&gt;", priv)
        self.assertIn("mailto:hola@example.com", aviso)
        self.assertNotIn("NIF:", aviso)

    def test_strip_html_cuts_at_sentence(self):
        txt = "Primera frase completa que ocupa bastante espacio. Segunda frase larga que ya no cabe del todo aquí"
        out = util.strip_html(txt, 70)
        self.assertEqual(out, "Primera frase completa que ocupa bastante espacio.")
        self.assertTrue(util.strip_html("palabra " * 50, 40).endswith("…"))

    def test_related_has_no_repeats_and_official_link(self):
        evs = [util.event("Agenda", str(i), "Concierto %d" % i, "2026-11-20", province_code="50",
                          city="Zaragoza", category="musica", url="https://o.example/%d" % i) for i in range(4)]
        with tempfile.TemporaryDirectory() as tmp:
            from planes import static
            static.write_event_pages(tmp, evs, {"50": "zaragoza"})
            names = os.listdir(os.path.join(tmp, "e"))
            with open(os.path.join(tmp, "e", names[0]), encoding="utf-8") as fh:
                page = fh.read()
        rel = page.split("Más planes</h2>")[1].split("</ul>")[0]
        links = re.findall(r'<li><a href="([^"]+)"', rel)
        self.assertEqual(len(links), len(set(links)))
        self.assertEqual(len(links), 3)
        self.assertIn("ver en la web oficial", page)

    def test_curated_file_merges_without_duplicates(self):
        from planes.src_curated import NAME, fetch, replace_events
        evs = fetch(lambda msg: None)
        self.assertGreaterEqual(len(evs), 160)
        ids = [e["id"] for e in evs]
        self.assertEqual(len(ids), len(set(ids)))
        from collections import Counter
        counts = Counter(e["province_code"] for e in evs)
        # Mínimos de la selección curada (provincias vacías o finas en la agenda).
        floors = {
            "02": 6, "03": 6, "04": 6, "06": 6, "07": 6, "10": 4, "11": 2, "13": 6,
            "14": 5, "16": 9, "18": 8, "19": 3, "21": 4, "22": 4, "23": 3, "26": 5,
            "27": 1, "29": 8, "33": 11, "35": 7, "38": 6, "39": 5, "41": 11, "44": 2,
            "45": 10, "50": 12, "51": 8, "52": 8,
        }
        for code, n in floors.items():
            self.assertGreaterEqual(counts[code], n, code)
        urls = {e["url"] for e in evs}
        for seed in (
            "https://iaacc.es/visita/",
            "https://www.centrobotin.org/",
            "https://www.alhambra-patronato.es/visitar",
            "https://alcazarsevilla.org/",
            "https://www.teatrodelamaestranza.es/es/",
            "https://www.museobbaa.com/",
            "https://esbaluard.org/",
            "https://www.cultura.gob.es/mgreco/inicio.html",
            "https://www.museowurth.es/",
            "https://auditorioalfredokraus.es/",
            "https://www.parqueciencias.com/",
            "https://caam.net/",
            "https://www.consorciomerida.org/",
        ):
            self.assertIn(seed, urls)
        for e in evs:
            self.assertEqual(e["source"], NAME)
            self.assertEqual(e["subtype"], "Permanente")
            self.assertTrue(e["province_code"])
            self.assertTrue(e["title"])
            self.assertTrue(e["city"])
            self.assertTrue(e["description"])
            self.assertTrue(e["url"].startswith("http"))
            self.assertGreaterEqual(e["end"], e["start"])
            self.assertLessEqual(len(e["description"]), 220)
        again = replace_events(evs + evs, lambda msg: None)
        self.assertEqual(sum(1 for e in again if e["source"] == NAME), len(evs))
        self.assertEqual([e["id"] for e in again if e["source"] == NAME], ids)


if __name__ == "__main__":
    unittest.main()


class TestLandingWindows(unittest.TestCase):
    def test_weekend_window(self):
        from datetime import date
        from planes.publish import weekend_window
        self.assertEqual(weekend_window(date(2026, 11, 17)), (date(2026, 11, 20), date(2026, 11, 22)))  # martes
        self.assertEqual(weekend_window(date(2026, 11, 21)), (date(2026, 11, 21), date(2026, 11, 22)))  # sábado: arranca hoy
        self.assertEqual(weekend_window(date(2026, 11, 20))[0], date(2026, 11, 20))  # viernes

    def test_in_window(self):
        from planes.publish import in_window
        ev = lambda s, e, **k: dict({"start": s, "end": e, "category": "musica"}, **k)
        self.assertTrue(in_window(ev("2026-11-21", "2026-11-21"), "2026-11-20", "2026-11-22"))
        self.assertFalse(in_window(ev("2026-11-25", "2026-11-25"), "2026-11-20", "2026-11-22"))
        self.assertFalse(in_window(ev("2026-11-10", "2026-11-30"), "2026-11-20", "2026-11-22"))  # exposición larga
        self.assertTrue(in_window(ev("2026-11-19", "2026-11-23"), "2026-11-20", "2026-11-22"))  # rango corto
        self.assertTrue(in_window(ev("2026-11-01", "2026-12-01", sessions=["2026-11-21"]), "2026-11-20", "2026-11-22"))


class TestNavidad(unittest.TestCase):
    def test_navidad(self):
        from planes.classify import classify
        for t in ("Mercado de Navidad", "Cabalgata de Reyes", "Olentzero eguna", "Belén viviente", "Concierto de villancicos", "Nadal a la plaça"):
            self.assertEqual(classify([], t, ""), "navidad", t)
        self.assertEqual(classify([], "Concierto de jazz", ""), "musica")


class TestXmasTheme(unittest.TestCase):
    """La etiqueta navideña: un concierto o un taller de Navidad sigue en su
    tipo, pero también sale con el filtro y en las páginas de Navidad."""

    def _ev(self, title, category="musica", desc="", subtype=""):
        return {"title": title, "description": desc, "category": category, "subtype": subtype}

    def test_is_xmas_titles(self):
        for t in ("Concierto de Navidad de la Banda Municipal", "Taller de adornos navideños", "Gabonetako kontzertua",
                  "Concert de Nadal", "Christmas Jazz Night", "Cuentacuentos de Olentzero", "Coro de villancicos",
                  "San Silvestre Lagunera 2026", "Campanadas en la plaza", "Pessebre vivent"):
            self.assertTrue(classify.is_xmas(self._ev(t)), t)

    def test_is_xmas_rejects_false_friends(self):
        for t in ("Exposición sobre Rafa Nadal", "Concierto de jazz", "Visita al belén de agua"):
            self.assertFalse(classify.is_xmas(self._ev(t)), t)
        # Las visitas permanentes no se etiquetan aunque hablen de Navidad
        self.assertFalse(classify.is_xmas(self._ev("Museo del Belén", "expos", subtype=util.PERMANENT_SUBTYPE)))
        # Ferias de Santo Tomás y Santa Llúcia: solo en diciembre (o de finales de noviembre a diciembre)
        fair = self._ev("Programa Santo Tomás 2026 en Bilbao", "fiestas")
        self.assertTrue(classify.is_xmas(dict(fair, start="2026-12-21", end="2026-12-21")))
        self.assertTrue(classify.is_xmas(dict(self._ev("Fira de Santa Llúcia a l'Avinguda de la Catedral", "fiestas"),
                                              start="2026-11-27", end="2026-12-23")))
        self.assertFalse(classify.is_xmas(dict(self._ev("Visita a la iglesia de Santo Tomás", "expos"),
                                               start="2026-03-07", end="2026-03-07")))
        # La categoría navidad siempre cuenta
        self.assertTrue(classify.is_xmas(self._ev("Feria", "navidad")))
        # En la descripción solo cuentan frases claras
        self.assertTrue(classify.is_xmas(self._ev("Feria de artesanía", "otros", "Gran mercado de Navidad en la plaza")))
        self.assertFalse(classify.is_xmas(self._ev("Horario de la biblioteca", "otros", "Cerrado en Navidad")))

    def test_in_cat_and_data_flag(self):
        e = {"category": "musica", "xmas": True}
        self.assertTrue(publish.in_cat(e, "navidad"))
        self.assertTrue(publish.in_cat(e, "musica"))
        self.assertFalse(publish.in_cat({"category": "musica", "xmas": False}, "navidad"))
        app = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "app.js"), encoding="utf-8").read()
        self.assertIn("r[13] & 4", app)  # bit 4 de flags = etiqueta navideña
        self.assertIn("state.cats.navidad && e.xm", app)


class TestDestacados(unittest.TestCase):
    def test_file_is_valid_and_merges(self):
        from planes import src_destacados as d
        items = d.load()
        self.assertGreaterEqual(len(items), 5)
        ids = [i["id"] for i in items]
        self.assertEqual(len(ids), len(set(ids)))
        for raw in items:
            self.assertEqual(d.problems(raw), [], raw.get("id"))
        evs = d.fetch(lambda msg: None)
        for e in evs:
            self.assertEqual(e["source"], d.NAME)
            self.assertTrue(e["province_code"] and e["url"], e["title"])
            self.assertGreaterEqual(e["end"], util.iso(util.today()))
        merged = d.replace_events(d.replace_events([{"source": "x", "id": "a"}]))
        self.assertEqual(sum(1 for e in merged if e["source"] == d.NAME), len(evs))

    def test_problems_catches_bad_entries(self):
        from planes import src_destacados as d
        good = {"id": "x", "title": "T", "start": "2026-12-01", "url": "https://a", "province": "Sevilla",
                "checked": "2026-11-18", "refs": ["https://a"]}
        self.assertEqual(d.problems(good), [])
        self.assertIn("sin refs https", d.problems(dict(good, refs=[])))
        self.assertIn("end anterior a start", d.problems(dict(good, end="2026-11-01")))
        self.assertIn("time no es HH:MM", d.problems(dict(good, time="18h")))
        self.assertIn("falta url", d.problems(dict(good, url="")))


class TestOrganizadores(unittest.TestCase):
    """Eventos enviados por organizadores: del envío de Supabase al fichero aprobado y a la web, con destacados."""

    def _row(self, **d):
        base = {"title": "Concierto en la sala", "start": "2099-05-10", "end": "2099-05-10", "time": "20:30", "city": "Vitoria-Gasteiz",
                "province_code": "01", "venue": "Sala Jimmy Jazz", "description": "Concierto de presentación del nuevo disco.",
                "category": "musica", "url": "https://example.org/concierto", "free": False, "price": "12 €"}
        base.update(d)
        return {"sub_id": "1234abcd-0000-0000-0000-000000000000", "sent": "2099-04-01", "plan": "destacado", "data": base}

    def test_entry_from_submission_has_no_email_and_is_not_featured_yet(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import organizadores as tool
        e = tool.entry(self._row(), checked="2099-04-02")
        self.assertEqual(e["id"], "org-1234abcd")
        self.assertEqual(e["province"], "Álava")
        self.assertFalse(e["destacado"])          # el destacado se activa a mano cuando está pagado
        self.assertNotIn("email", json.dumps(e))
        from planes import src_organizadores
        self.assertEqual(src_organizadores.problems(e), [])
        self.assertIn("Destacado (5 €)", tool.summary([e]))

    def test_featured_events_go_first_with_badge(self):
        from planes import src_organizadores
        raw = {"id": "org-1", "title": "Concierto destacado", "start": "2099-05-10", "url": "https://example.org/x",
               "province": "Álava", "city": "Vitoria-Gasteiz", "checked": "2099-04-02", "destacado": True}
        self.assertTrue(src_organizadores.is_featured(raw, "2099-05-01"))
        self.assertFalse(src_organizadores.is_featured(raw, "2099-05-11"))
        self.assertFalse(src_organizadores.is_featured(dict(raw, destacado_hasta="2099-04-30"), "2099-05-01"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "organizadores.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"events": [raw]}, fh)
            old = src_organizadores.PATH
            src_organizadores.PATH = path
            try:
                evs = src_organizadores.fetch(lambda m: None)
            finally:
                src_organizadores.PATH = old
        self.assertEqual(len(evs), 1)
        self.assertTrue(evs[0]["featured"])
        other = util.event("Agenda", "2", "Antes en el calendario", "2099-05-01", province_code="01", city="Vitoria-Gasteiz", category="musica")
        with tempfile.TemporaryDirectory() as tmp:
            publish.write_pages(tmp, [other, evs[0]])
            with open(os.path.join(tmp, "p", "alava.html"), encoding="utf-8") as fh:
                page = fh.read()
        self.assertIn("⭐ Destacado", page)
        self.assertLess(page.index("Concierto destacado"), page.index("Antes en el calendario"))


class TestLocalesDeOcio(unittest.TestCase):
    """Escape rooms, boleras, parques de bolas…: solo entran si los publica su dueño, y sin planes no se ven."""

    def _lugar(self, **kw):
        raw = {"id": "org-lugar001", "kind": "lugar", "title": "Escape room de prueba", "url": "https://example.org/escape",
               "province": "Álava", "city": "Vitoria-Gasteiz", "venue": "Escape room de prueba", "address": "Calle de prueba 1",
               "category": "ocio", "horario": "De martes a domingo, de 11:00 a 21:00",
               "description": "Sala de escape de prueba para los tests.", "checked": "2026-11-26"}
        raw.update(kw)
        return raw

    def test_categories_exist_but_only_organizers_fill_them(self):
        from planes import classify, llm
        self.assertEqual(classify.CATEGORY_KEYS[-1], "otros")   # el índice de «otros» es el último en core.js
        self.assertTrue(set(classify.ORGANIZER_ONLY) <= set(classify.CATEGORY_KEYS))
        self.assertNotIn("ocio (", llm.SYSTEM)                   # la IA no clasifica planes de las agendas aquí
        for k in classify.ORGANIZER_ONLY:                        # cada tipo nuevo: nombre de búsqueda y «¿Tienes…? Publícalo»
            self.assertIn(k, publish.CAT_INTENT)
            self.assertIn(k, publish.LOCAL_ASK)
            self.assertNotIn("%s (" % k, llm.SYSTEM)
        for types, title in ((["escape room"], "Escape room: la cárcel"), (["parque infantil"], "Parque de bolas en Navidad")):
            self.assertNotIn(classify.classify(types, title), classify.ORGANIZER_ONLY)

    def test_submission_of_a_place_becomes_an_all_year_listing(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import organizadores as tool
        from planes import src_organizadores
        row = {"sub_id": "abcd1234-0000", "sent": "2026-11-26", "plan": "gratis",
               "data": {"kind": "lugar", "title": "Escape room de prueba", "start": None, "end": None, "time": "",
                        "horario": "Mar-dom 11-21", "city": "Vitoria-Gasteiz", "province_code": "01", "venue": "Escape room de prueba",
                        "address": "Calle de prueba 1", "category": "ocio", "url": "https://example.org/escape",
                        "description": "Sala de escape de prueba para los tests."}}
        e = tool.entry(row, checked="2026-11-26")
        self.assertEqual(e["kind"], "lugar")
        self.assertNotIn("start", e)
        self.assertEqual(src_organizadores.problems(e), [])
        self.assertIn("Todo el año (Mar-dom 11-21)", tool.summary([e]))
        self.assertIn("falta address", src_organizadores.problems(dict(e, address="")))
        self.assertIn("un local destacado necesita destacado_hasta", src_organizadores.problems(dict(e, destacado=True)))

    def _fetch(self, raws):
        from planes import src_organizadores
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "organizadores.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"events": raws}, fh)
            old = src_organizadores.PATH
            src_organizadores.PATH = path
            try:
                return src_organizadores.fetch(lambda m: None)
            finally:
                src_organizadores.PATH = old

    def test_place_is_published_as_permanent_with_all_year_label(self):
        evs = self._fetch([self._lugar(), self._lugar(id="org-lugar002", destacado=True, destacado_hasta="2099-01-01")])
        self.assertEqual(len(evs), 2)
        ev = evs[0]
        self.assertTrue(util.is_permanent(ev))
        self.assertEqual(ev["start"], util.iso(util.today()))
        self.assertIn("Horario: De martes a domingo", ev["description"])
        self.assertFalse(ev.get("featured"))
        self.assertTrue(evs[1]["featured"])
        self.assertEqual(static.permanent_label(ev), "Todo el año")
        self.assertIn('"@type": "EntertainmentBusiness"', json.dumps(static.event_jsonld(ev, "https://x"), ensure_ascii=False))
        self.assertEqual(static.event_jsonld(dict(ev, category="bienestar"), "https://x")["@type"], "DaySpa")
        self.assertNotIn(">Permanente<", publish._card(ev, "", util.iso(util.today())))

    def test_empty_organizer_categories_have_no_page_nor_link(self):
        other = util.event("Agenda", "2", "Concierto", "2099-05-01", province_code="01", city="Vitoria-Gasteiz", category="musica")
        with tempfile.TemporaryDirectory() as tmp:
            publish.write_pages(tmp, [other])
            self.assertFalse(os.path.exists(os.path.join(tmp, "t", "ocio.html")))
            with open(os.path.join(tmp, "t", "musica.html"), encoding="utf-8") as fh:
                self.assertNotIn("t/ocio.html", fh.read())
        with tempfile.TemporaryDirectory() as tmp:
            publish.write_pages(tmp, [other] + self._fetch([self._lugar()]))
            with open(os.path.join(tmp, "t", "ocio.html"), encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("Escape room de prueba", page)
            self.assertIn("tipo=lugar", page)                       # «¿Tienes un escape room? Publícalo gratis»
            self.assertIn("Hay 1 local abierto todo el año de escape rooms y ocio en España.", page)
            self.assertNotIn("museos, monumentos", page)
            self.assertFalse(os.path.exists(os.path.join(tmp, "t", "parques.html")))
