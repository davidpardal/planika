# -*- coding: utf-8 -*-
"""Pruebas mínimas de las piezas que más se rompen: fechas, provincias, clasificación, iCal y sesiones."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import classify, publish, static, util  # noqa: E402


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
        self.assertLess(ev["end"], "2028-01-01")
        self.assertEqual(ev["ccaa"], "Comunidad de Madrid")
        self.assertIsNone(util.event("Test", "2", "", "2026-11-21"))

    def test_parse_ics(self):
        ics = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Hola\r\n mundo\r\nDTSTART;TZID=Europe/Madrid:20261118T200000\r\nEND:VEVENT\r\nEND:VCALENDAR"
        evs = util.parse_ics(ics)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["SUMMARY"], "Holamundo")
        self.assertEqual(evs[0]["DTSTART"], "20261118T200000")


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
        self.assertEqual(page.count("</script>"), 1)  # solo el cierre del bloque JSON-LD
        self.assertIn("Teatro &lt;Real&gt;", page)
        ld = json.loads(page.split('<script type="application/ld+json">')[1].split("</script>")[0])
        self.assertIn("</script>", ld["description"])

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
            rows = json.loads(core.split("window.PLANES_CORE=")[1].rstrip(";\n"))["events"]
            self.assertEqual(rows[1][0], evs[1]["id"])
            self.assertEqual(rows[1][13], 2)  # con entradas, no gratis
            with open(os.path.join(tmp, "d", "0.js"), encoding="utf-8") as fh:
                det = fh.read()
            self.assertTrue(det.startswith('PLANIKA_D("2026-11-14T04:15",0,'))
            self.assertIn("entradas.example", det)
            self.assertNotIn("entradas.example", core)


if __name__ == "__main__":
    unittest.main()
