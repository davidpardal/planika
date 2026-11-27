# -*- coding: utf-8 -*-
"""Pruebas de los conectores nuevos con respuestas recortadas de las fuentes reales."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import src_barcelona, src_deporte_pro, src_jimmyjazz, src_sportsdb, src_diba, src_esmadrid, src_municipios, src_murcia, src_vitoria, src_zaragoza  # noqa: E402


class TestBarcelonaTimetable(unittest.TestCase):
    ROW = '<td class="timetable-day" rowspan=1><div>%s</div></td><td class="timetable-hour" rowspan=1><div>%s</div></td>'

    def test_free_and_schedule(self):
        raw = ('<table class="timetable-table"><tr class="timetable-header"><th>Dies</th></tr><tr>' + self.ROW % ("Dissabte", "de 18.00&nbsp;h a 21.00&nbsp;h")
               + '<td class="timetable-price" rowspan=2><div>Entrada Gratuïta</div></td><td class="timetable-description" rowspan=2>'
               '<div><p style="margin:0">Aforament limitat</p></div></td></tr><tr>' + self.ROW % ("Diumenge", "d'11.00&nbsp;h a 14.00&nbsp;h") + '</tr></table>')
        text, tm, free, price = src_barcelona.timetable(raw)
        self.assertEqual(text, "Horario: Dissabte de 18.00 h a 21.00 h · Diumenge d'11.00 h a 14.00 h. Precio: Entrada Gratuïta. Aforament limitat.")
        self.assertEqual((tm, free, price), ("", True, "Gratuït"))  # dos horas de inicio distintas: sin hora única

    def test_single_time_and_prices(self):
        raw = '<tr>' + self.ROW % ("diumenge", "a les 10:30 h") + '<td class="timetable-price"><div>General: 12 €<br>Reduïda: 8 €</div></td></tr>'
        self.assertEqual(src_barcelona.timetable(raw)[1:], ("10:30", False, "De 8 a 12 €"))
        several = '<tr>' + self.ROW % ("Dimecres", "a les 16.00 h, <br>a les 18.15 h i <br>a les 19.00 h") + '</tr>'
        self.assertEqual(src_barcelona.timetable(several)[1], "")
        self.assertEqual(src_barcelona.timetable(""), ("", "", None, ""))


class TestZaragoza(unittest.TestCase):
    ROW = {
        "id": 316340, "title": "JUEGA E IMAGINA 2026: HAI, LA PESCADORA DE SUEÑOS", "description": "<p>Espect&aacute;culo de magia</p>",
        "startDate": "2026-12-05T00:00:00", "endDate": "2026-12-05T00:00:00", "type": "Espectáculos",
        "alt": "https://www.zaragoza.es/sede/servicio/cultura/evento/316340",
        "image": "//www.zaragoza.es/cont/paginas/actividades/imagen/x.png",
        "category": [{"id": 1, "title": "Teatro"}], "population": [{"id": 1, "title": "Infantil"}],
        "price": [{"fareGroup": "General", "hasCurrencyValue": 4.0, "hasCurrency": "EUR"}],
        "subEvent": [{"location": {"title": "Centro Cívico La Almozara", "streetAddress": "Avda. Puerta Sancho, 30",
                                   "addressLocality": "Zaragoza",
                                   "geometry": {"type": "Point", "coordinates": [-0.9011286, 41.6618627]}},
                      "openingHours": [{"dayOfWeek": "Sábado", "startTime": "18:00", "endTime": "19:00"}]}],
    }

    def test_event(self):
        ev = src_zaragoza.parse([self.ROW])[0]
        self.assertEqual((ev["start"], ev["time"], ev["province"], ev["city"]), ("2026-12-05", "18:00", "Zaragoza", "Zaragoza"))
        self.assertEqual(ev["venue"], "Centro Cívico La Almozara")
        self.assertEqual((ev["lat"], ev["lon"]), (41.66186, -0.90113))
        self.assertEqual((ev["price"], ev["free"]), ("4 €", False))
        self.assertTrue(ev["image"].startswith("https://www.zaragoza.es/"))
        self.assertEqual(ev["category"], "infantil")

    def test_free_and_long_courses(self):
        free = dict(self.ROW, id=2, price=[{"fareGroup": "Gratuita", "hasCurrencyValue": 0}], population=[])
        course = dict(self.ROW, id=3, type="Cursos y talleres", startDate="2026-10-01T00:00:00", endDate="2027-06-15T00:00:00")
        workshop = dict(self.ROW, id=4, type="Cursos y talleres")
        typo = dict(self.ROW, id=6, type="Cursos y talleres", startDate="202-10-07T00:00:00")
        club = dict(self.ROW, id=7, type="Otros", startDate="2026-09-01T00:00:00", endDate="2027-06-30T00:00:00")
        evs = src_zaragoza.parse([free, course, workshop, "basura", {"id": 5}, typo, club])
        self.assertEqual(len(evs), 2)
        self.assertEqual((evs[0]["price"], evs[0]["free"], evs[0]["category"]), ("Gratis", True, "escena"))

    def test_missing_pieces(self):
        ev = src_zaragoza.parse([{"id": 9, "title": "Sin lugar", "startDate": "2026-12-01T00:00:00"}])[0]
        self.assertEqual((ev["city"], ev["venue"], ev["lat"], ev["time"]), ("Zaragoza", "", None, ""))


class TestMunicipios(unittest.TestCase):
    ROW = {
        "id": 63512, "global_id": "merida.es?id=63512", "url": "https://merida.es/agenda/gala-turuta-oro-2026/",
        "title": "Gala XXIV Premios &#8216;Turuta de Oro&#8217;", "description": "<p>El sábado 14 de noviembre</p>",
        "image": {"url": "https://merida.es/wp-content/uploads/2026/10/gala.jpg"}, "all_day": False,
        "start_date": "2026-11-14 12:00:00", "end_date": "2026-11-14 12:00:00", "cost": "30&euro;",
        "categories": [{"name": "Festejos"}], "venue": {"venue": "Teatro Mar&iacute;a Luisa", "address": "Calle Camilo José Cela", "city": "Mérida"},
    }

    def test_event(self):
        ev = src_municipios.parse("Ayuntamiento de Mérida", [self.ROW], "Mérida", "06")[0]
        self.assertEqual(ev["title"], "Gala XXIV Premios ‘Turuta de Oro’")
        self.assertEqual((ev["source"], ev["province"], ev["city"], ev["time"]), ("Ayuntamiento de Mérida", "Badajoz", "Mérida", "12:00"))
        self.assertEqual((ev["venue"], ev["price"]), ("Teatro María Luisa", "30€"))
        self.assertEqual(ev["image"], "https://merida.es/wp-content/uploads/2026/10/gala.jpg")

    def test_empty_venue_and_image(self):
        # La API devuelve [] en venue y false en image cuando no hay datos
        row = dict(self.ROW, venue=[], image=False, all_day=True, categories=[])
        ev = src_municipios.parse("Ayuntamiento de Teruel", [row], "Teruel", "44")[0]
        self.assertEqual((ev["city"], ev["province"], ev["venue"], ev["image"], ev["time"]), ("Teruel", "Teruel", "", "", ""))

    def test_sites_are_well_formed(self):
        names = [s[0] for s in src_municipios.SITES]
        self.assertEqual(len(names), len(set(names)))
        for _, root, _, code in src_municipios.SITES:
            self.assertTrue(root.startswith("https://") and not root.endswith("/"))
            self.assertRegex(code, r"^\d\d$")


class TestEsMadrid(unittest.TestCase):
    XML = """<?xml version="1.0" encoding="UTF-8"?><serviceList>
<service fechaActualizacion="2026-10-30" id="109846"><basicData><language>es</language><name><![CDATA[Los Fabulosos Cadillacs]]></name>
<title><![CDATA[Los Fabulosos Cadillacs]]></title><body><![CDATA[<p><strong>La m&iacute;tica banda</strong> act&uacute;a en Las Ventas.</p>]]></body>
<web>https://www.esmadrid.com/agenda/fabulosos-cadillacs-live-ventas</web><idrt/><nombrert/></basicData>
<geoData><address>de Alcalá , 237</address><zipcode>28028</zipcode><latitude>40.432242700000</latitude><longitude>-3.663377300000</longitude></geoData>
<multimedia><media type="image"><description/><url>https://estaticos.esmadrid.com/cadillacs.jpg</url></media></multimedia>
<extradata><item name="idTipo">6</item><item name="Tipo">Eventos</item><categorias><categoria><item name="idCategoria">6449</item>
<item name="Categoria">Música</item><subcategorias><subcategoria><item name="SubCategoria">Latina</item></subcategoria></subcategorias></categoria></categorias>
<item name="Servicios de pago"><![CDATA[<p>Desde 55 €</p><p>No se permite la entrada a menores</p>]]></item><item name="Horario"><![CDATA[<p>Apertura: 19:00 h</p><p>Inicio: 20:30 h</p>]]></item>
<fechas><rango><inicio>29/11/2026</inicio><dias>7</dias><fin>29/11/2026</fin></rango></fechas></extradata></service>
<service id="2"><basicData><title><![CDATA[Juegos de jard&iacute;n]]></title><body/><web/><nombrert>Real Jardín Botánico</nombrert></basicData><geoData/>
<extradata><categorias><categoria><item name="Categoria">Exposiciones</item></categoria></categorias><item name="Horario"><![CDATA[<p>10:00 - 19:30 h</p>]]></item>
<fechas><rango><inicio>16/09/2026</inicio><fin>10/01/2027</fin></rango><rango><inicio>01/02/2027</inicio><fin>15/02/2027</fin></rango></fechas></extradata></service>
<service id="3"><basicData><title>Sin fechas</title></basicData><extradata/></service></serviceList>"""

    def test_parse(self):
        evs = src_esmadrid.parse(self.XML.encode("utf-8"))
        self.assertEqual(len(evs), 2)
        a, b = evs
        self.assertEqual((a["title"], a["start"], a["time"], a["category"], a["subtype"]), ("Los Fabulosos Cadillacs", "2026-11-29", "20:30", "musica", "Latina"))
        self.assertEqual((a["price"], a["free"], a["province"], a["address"]), ("Desde 55 €", False, "Madrid", "Calle de Alcalá , 237"))
        self.assertEqual((a["lat"], a["lon"]), (40.43224, -3.66338))
        self.assertEqual((b["title"], b["start"], b["end"], b["time"], b["category"], b["venue"]),
                         ("Juegos de jardín", "2026-09-16", "2027-02-15", "", "expos", "Real Jardín Botánico"))


class TestDiba(unittest.TestCase):
    def test_parse(self):
        el = {"acte_id": "agendaturisme463102253", "titol": "Pessebre Vivent Parlat de Viladecans", "data_inici": "2026-12-18 00:00:00",
              "data_fi": "2026-12-20 23:59:59", "descripcio": "L’Associació del Pessebre Vivent", "imatge": [],
              "acte_url": "https://www.barcelonaesmoltmes.cat/-/pessebre-vivent-parlat-de-viladecans",
              "grup_adreca": {"adreca_nom": "Jardins de Magdalena Modolell", "adreca": "Carrer del Sol, 2", "municipi_nom": "Viladecans",
                              "localitzacio": "41.4515200,2.0193027"}, "rel_municipis": {}, "preu": ""}
        park = {"acte_id": "parcs1", "titol": "Marina - Dia de les abelles", "data_inici": "2027-04-18 10:30:00", "data_fi": "2027-04-18 23:59:59",
                "imatge": ["https://parcs.diba.cat/a.jpg"], "grup_adreca": {"adreca_nom": "", "municipi_nom": "", "localitzacio": ""},
                "rel_municipis": {"municipi_nom": "Badalona", "centre_municipal": "41.4500690,2.2475168"}, "preu": []}
        a = src_diba.parse([el], None, "Turisme")[0]
        self.assertEqual((a["start"], a["end"], a["time"], a["city"], a["province"]), ("2026-12-18", "2026-12-20", "", "Viladecans", "Barcelona"))
        self.assertEqual((a["lat"], a["lon"]), (41.45152, 2.0193))
        tour = dict(el, acte_id="t2", titol="AudaTours Audioguía", data_inici="2024-05-11 00:00:00", data_fi="2027-12-20 00:00:00")
        messy = dict(el, acte_id="t3", grup_adreca=dict(el["grup_adreca"], municipi_nom="08221 TERRASSA"))
        self.assertEqual([x["city"] for x in src_diba.parse([tour, messy])], ["Terrassa"])
        b = src_diba.parse([park, {"rel_municipis": []}], "naturaleza", "Parcs naturals")[0]
        self.assertEqual((b["category"], b["city"], b["time"], b["image"], b["lat"]), ("naturaleza", "Badalona", "10:30", "https://parcs.diba.cat/a.jpg", 41.45007))


class TestMurcia(unittest.TestCase):
    RSS = """<rss version="0.91"><channel><title>Eventos|Ayuntamiento de Murcia</title>
<item> <title>&#39;Homenaje a una desconocida&#39;</title> <link>http://eventos.murcia.es/event_detail/161269.html</link>
<pubDate>Fri, 20 Nov 2026 20:00:00 +0100</pubDate> <description> <![CDATA[<p>Auditorio y Centro de Artes Escénicas &#39;Sebastián Gálvez Arce&#39;, Calle Antonia Maymon, Beniaján, España</p><p>En diciembre de 2015 dimos con un puesto.</p>]]></description></item>
<item><title>Sin fecha</title><link>http://eventos.murcia.es/x</link><pubDate></pubDate><description>x</description></item></channel></rss>"""

    def test_parse(self):
        evs = src_murcia.parse(self.RSS)
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual((ev["title"], ev["start"], ev["time"]), ("'Homenaje a una desconocida'", "2026-11-20", "20:00"))
        self.assertEqual((ev["venue"], ev["address"], ev["city"], ev["province"]),
                         ("Auditorio y Centro de Artes Escénicas 'Sebastián Gálvez Arce'", "Calle Antonia Maymon", "Beniaján", "Murcia"))
        self.assertEqual(ev["url"], "https://eventos.murcia.es/event_detail/161269.html")
        self.assertEqual(ev["description"], "En diciembre de 2015 dimos con un puesto.")


if __name__ == "__main__":
    unittest.main()


class TestVitoria(unittest.TestCase):
    @staticmethod
    def item(guid, title, pub):
        return ("<item><title>%s</title><link>https://v.es/?uid=%s</link><pubDate>%s</pubDate>"
                "<guid>https://v.es/?uid=%s</guid></item>" % (title, guid, pub, guid))

    def test_groups_days_into_range(self):
        from planes.util import iso, today
        from datetime import timedelta
        d = lambda n: (today() + timedelta(days=n)).strftime("%a, %d %b %Y 10:00:00 GMT")
        xml = "<rss>" + self.item("a", "Exposici&oacute;n: Arana", d(1)) + self.item("a", "Exposici&oacute;n: Arana", d(3)) \
            + self.item("b", "Concierto de c&aacute;mara", d(2)) + "</rss>"
        evs = {e["title"]: e for e in src_vitoria.parse(xml)}
        self.assertEqual(len(evs), 2)
        arana = evs["Exposición: Arana"]
        self.assertEqual((arana["start"], arana["end"], arana["time"]), (iso(today() + timedelta(days=1)), iso(today() + timedelta(days=3)), ""))
        conc = evs["Concierto de cámara"]
        self.assertEqual((conc["time"], conc["province"], conc["city"]), ("11:00", "Álava", "Vitoria-Gasteiz"))

    def test_drops_past_and_permanent(self):
        xml = "<rss>" + self.item("x", "Pasado", "Mon, 05 Jan 2026 10:00:00 GMT") \
            + self.item("y", "Aula", "Mon, 05 Jan 2026 10:00:00 GMT") + self.item("y", "Aula", "Fri, 05 Jan 2029 10:00:00 GMT") + "</rss>"
        self.assertEqual(src_vitoria.parse(xml), [])


class TestDeportePro(unittest.TestCase):
    def test_laliga(self):
        data = {"matches": [
            {"round": "Matchday 14", "date": "2026-11-22", "time": "21:00", "team1": "Real Madrid CF", "team2": "FC Barcelona"},
            {"round": "Matchday 3", "date": "2026-11-22", "team1": "Deportivo Alavés", "team2": "Getafe CF"},
            {"round": "Matchday 1", "date": "2026-08-15", "team1": "Getafe CF", "team2": "Sevilla FC"},
            {"round": "Matchday 2", "date": "2026-11-23", "team1": "Equipo Desconocido", "team2": "Sevilla FC", "score": {}},
            {"round": "Matchday 5", "date": "2026-11-24", "team1": "Sevilla FC", "team2": "Valencia CF", "score": {"ft": [1, 1]}},
        ]}
        evs = src_deporte_pro.parse_laliga(data, "2026-11-17")
        self.assertEqual(len(evs), 2)
        ev = evs[0]
        self.assertEqual((ev["title"], ev["start"], ev["time"], ev["province"], ev["category"]),
                         ("Real Madrid CF - FC Barcelona", "2026-11-22", "21:00", "Madrid", "deporte"))
        self.assertEqual((evs[1]["province"], evs[1]["time"]), ("Álava", ""))

    def test_laliga_official_fixes(self):
        data = {"matches": [
            {"round": "Matchday 13", "date": "2026-11-22", "team1": "Athletic Club", "team2": "RCD Espanyol de Barcelona"},
            {"round": "Matchday 13", "date": "2026-11-22", "team1": "Real Madrid CF", "team2": "RC Celta de Vigo"},
            {"round": "Matchday 23", "date": "2027-02-07", "team1": "Real Sociedad de Fútbol", "team2": "Real Madrid CF"},
        ]}
        fixes = {"Real Madrid CF|RC Celta de Vigo": {"date": "2026-11-21", "time": "21:00"},
                 "Real Sociedad de Fútbol|Real Madrid CF": {"date": "2026-12-02", "time": "19:00"},
                 "Athletic Club|RCD Espanyol de Barcelona": {"date": "2026-11-20", "time": "21:00"}}
        evs = {e["title"]: e for e in src_deporte_pro.parse_laliga(data, "2026-11-21", fixes=fixes)}
        self.assertNotIn("Athletic Club - RCD Espanyol de Barcelona", evs)  # ya jugado según el día oficial
        rm = evs["Real Madrid CF - RC Celta de Vigo"]
        self.assertEqual((rm["start"], rm["time"]), ("2026-11-21", "21:00"))
        rs = evs["Real Sociedad de Fútbol - Real Madrid CF"]  # adelantado por la Supercopa
        self.assertEqual((rs["start"], rs["time"]), ("2026-12-02", "19:00"))
        plain = src_deporte_pro.parse_laliga(data, "2026-11-21")
        self.assertEqual({e["id"] for e in plain if "Celta" in e["title"]}, {rm["id"]})  # el id no cambia

    def test_laliga_fixes_file(self):
        fixes = src_deporte_pro.load_fixes()
        names = set(src_deporte_pro.LALIGA_CLUBS)
        for key, fix in fixes.items():
            home, away = key.split("|")
            self.assertIn(home, names, key)
            self.assertIn(away, names, key)
            self.assertRegex(fix["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertRegex(fix.get("time", ""), r"^(\d{2}:\d{2})?$")
            self.assertTrue(fix.get("refs"), key)

    def test_euroleague(self):
        item = ("<item><gameday>7</gameday><arenaname>BUESA ARENA</arenaname><date>%s</date><startime>20:30</startime>"
                "<gamecode>E2026_70</gamecode><hometeam>KOSNER BASKONIA</hometeam><homecode>%s</homecode>"
                "<awayteam>PARIS</awayteam><awaycode>PRS</awaycode><played>%s</played></item>")
        xml = "<schedule>" + item % ("Nov 20, 2026", "BAS", "false") + item % ("Nov 20, 2026", "PRS", "false") \
            + item % ("Oct 01, 2026", "BAS", "true") + "</schedule>"
        teams = '<clubs><club code="BAS"><name>Kosner Baskonia Vitoria-Gasteiz</name></club><club code="PRS"><name>Paris Basketball</name></club></clubs>'
        evs = src_deporte_pro.parse_euro(xml, teams, "E", "2026-11-17")
        self.assertEqual(len(evs), 1)
        self.assertEqual((evs[0]["title"], evs[0]["time"], evs[0]["venue"], evs[0]["province"], evs[0]["subtype"]),
                         ("Kosner Baskonia Vitoria-Gasteiz - Paris Basketball", "20:30", "Buesa Arena", "Álava", "Euroliga"))


class TestSportsDbTime(unittest.TestCase):
    def test_utc_to_madrid(self):
        self.assertEqual(src_sportsdb.to_madrid("2026-11-22", "11:30:00"), ("2026-11-22", "12:30"))  # invierno: UTC+1
        self.assertEqual(src_sportsdb.to_madrid("2026-07-01", "18:00:00"), ("2026-07-01", "20:00"))  # verano: UTC+2
        self.assertEqual(src_sportsdb.to_madrid("2026-11-21", "23:30:00"), ("2026-11-22", "00:30"))  # cambia de día
        self.assertEqual(src_sportsdb.to_madrid("2026-11-21", "00:00:00"), ("2026-11-21", ""))  # sin hora
        self.assertEqual(src_sportsdb.to_madrid("2026-11-21", ""), ("2026-11-21", ""))


class TestSportsDbCache(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._http, self._sleep = src_sportsdb.http_json, src_sportsdb.time.sleep
        src_sportsdb.time.sleep = lambda *_: None

    def tearDown(self):
        src_sportsdb.http_json, src_sportsdb.time.sleep = self._http, self._sleep

    def test_budget_and_cache(self):
        def fake(url, params=None, **kw):
            self.calls.append(params["d"])
            return {"events": [{"idEvent": params["d"], "dateEvent": params["d"]}]}
        src_sportsdb.http_json = fake
        store, budget = {}, [3, False]
        out = src_sportsdb._daily("4408", "ACB", store, budget, lambda *_: None)
        self.assertEqual((len(self.calls), budget[0]), (3, 0))      # gasta solo el presupuesto
        self.assertEqual(len(out), 3)                                # y devuelve lo descargado
        self.calls.clear()
        again = src_sportsdb._daily("4408", "ACB", store, [3, False], lambda *_: None)
        self.assertTrue(set(self.calls).isdisjoint({e["idEvent"] for e in out}))  # lo ya guardado no se vuelve a pedir
        self.assertGreaterEqual(len(again), 3)

    def test_429_stops(self):
        def boom(*a, **k):
            raise RuntimeError("429")
        src_sportsdb.http_json = boom
        budget = [8, False]
        src_sportsdb._daily("4408", "ACB", {}, budget, lambda *_: None)
        self.assertTrue(budget[1])
        self.assertEqual(budget[0], 7)  # una sola petición fallida y no se insiste


class TestTribe(unittest.TestCase):
    """Agendas turísticas con The Events Calendar (Visit Palma, Visit Elche)."""

    def test_parse(self):
        from planes import src_tribe
        from planes.util import iso, today
        from datetime import timedelta
        d = iso(today() + timedelta(days=3))
        items = [
            {"id": 1, "title": "El Grinch &#8211; Musical", "start_date": d + " 18:00:00", "end_date": d + " 19:30:00",
             "url": "https://visitpalma.com/es/evento/grinch/", "cost": "Gratis", "categories": [{"name": "Infantil"}],
             "venue": {"venue": "Trui Teatre", "city": "Palma", "address": "Camí de Son Rapinya"}, "description": "<p>Musical familiar</p>"},
            {"id": 2, "title": "NAVIDAD 2026 &#8211; PALMA", "start_date": d + " 00:00:00", "end_date": iso(today() + timedelta(days=40)) + " 23:59:59",
             "all_day": True, "venue": [], "categories": [{"name": "Fiestas y tradiciones"}]},
        ]
        evs = {e["title"]: e for e in src_tribe.parse("Visit Palma", "https://visitpalma.com", "Palma", "Illes Balears", items)}
        g = evs["El Grinch – Musical"]
        self.assertEqual((g["time"], g["venue"], g["province"], g["source"]), ("18:00", "Trui Teatre", "Illes Balears", "Visit Palma"))
        self.assertTrue(g["free"])
        n = evs["NAVIDAD 2026 – PALMA"]
        self.assertEqual((n["time"], n["city"], n["url"]), ("", "Palma", "https://visitpalma.com"))
        self.assertGreater(n["end"], n["start"])

    def test_registered(self):
        import fetch_events
        self.assertIn("tribe", fetch_events.SOURCES)
        self.assertIn("jimmyjazz", fetch_events.SOURCES)
        self.assertNotIn("lorca", fetch_events.SOURCES)


class TestVitoriaRetry(unittest.TestCase):
    def test_retries_then_parses(self):
        from unittest import mock
        calls = []

        def flaky(*a, **k):
            calls.append(1)
            if len(calls) < 3:
                raise TimeoutError("sin respuesta")
            return "<rss></rss>"
        with mock.patch.object(src_vitoria, "http_text", flaky), mock.patch.object(src_vitoria.time, "sleep", lambda s: None):
            self.assertEqual(src_vitoria.fetch(lambda m: None), [])
        self.assertEqual(len(calls), 3)

    def test_gives_up(self):
        from unittest import mock

        def down(*a, **k):
            raise TimeoutError("caída")
        with mock.patch.object(src_vitoria, "http_text", down), mock.patch.object(src_vitoria.time, "sleep", lambda s: None):
            with self.assertRaises(TimeoutError):
                src_vitoria.fetch(lambda m: None)


def _jj_post(i, link, title, excerpt, content="", cats=(1336, 30)):
    """Entrada de la API de WordPress de Jimmy Jazz, recortada (título, extracto con la fecha, contenido Divi)."""
    return {"id": i, "link": link, "title": {"rendered": title}, "excerpt": {"rendered": "<p>%s</p>" % excerpt},
            "content": {"rendered": content}, "categories": list(cats)}


class TestGaliciaIds(unittest.TestCase):
    def test_same_id_from_calendar_and_rss(self):
        from planes import src_galicia
        ics = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:abc-123@cultura.gal\nSUMMARY:Sistema Lupo\nDTSTART:20261128T110000\n"
               "DTEND:20261128T120000\nLOCATION:Biblioteca - A Coruña - A Coruña\nURL:https://www.cultura.gal/gl/sistema-lupo\n"
               "END:VEVENT\nEND:VCALENDAR\n")
        rss = ("<rss><channel><item><title>Sistema Lupo</title><link>https://www.cultura.gal/gl/evento/1/2/3</link>"
               "<pubDate>Sat, 28 Nov 2026 11:00:00 +0100</pubDate><description><![CDATA[<div class=\"info\">x<br>Biblioteca - A Coruña - A Coruña</div>]]>"
               "</description></item></channel></rss>")
        from unittest import mock
        with mock.patch.object(src_galicia, "http_text", side_effect=[ics]):
            a = src_galicia.fetch(lambda *x: None)
        with mock.patch.object(src_galicia, "http_text", side_effect=[OSError(), OSError(), rss]):
            b = src_galicia.fetch(lambda *x: None)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)
        self.assertEqual(a[0]["id"], b[0]["id"])


class TestJimmyJazz(unittest.TestCase):
    from datetime import date
    T0 = date(2026, 11, 20)

    def parse(self, *posts):
        return src_jimmyjazz.parse(list(posts), self.T0)

    def test_concert_with_support_act_doors_prices_and_tickets(self):
        e, = self.parse(_jj_post(
            1, "https://jimmyjazzgasteiz.com/raimundo/", "Raimundo el Canastero", "<h4>+ Broken Brothers Brass Band</h4> Viernes 20 Noviembre",
            '[et_pb_image src=»https://jimmyjazzgasteiz.com/wp-content/uploads/2026/05/R.jpg»][/et_pb_image]<p>Viernes 20 noviembre '
            'Puertas – 20:30 Anticipada: 15 € Taquilla: 18 €</p>[et_pb_button button_url=»https://l.eus/JJG-ReC-2026&#8243;]'))
        self.assertEqual((e["title"], e["start"], e["time"]), ("Raimundo el Canastero + Broken Brothers Brass Band", "2026-11-20", "20:30"))
        self.assertEqual((e["venue"], e["city"], e["province_code"]), ("Sala Jimmy Jazz", "Vitoria-Gasteiz", "01"))
        self.assertEqual(e["price"], "Anticipada 15 €, taquilla 18 €")
        self.assertEqual(e["tickets_url"], "https://l.eus/JJG-ReC-2026")
        self.assertTrue(e["image"].endswith("/R.jpg"))
        self.assertEqual(e["category"], "musica")

    def test_year_comes_from_the_weekday_and_impossible_dates_are_dropped(self):
        evs = self.parse(_jj_post(2, "https://jimmyjazzgasteiz.com/a/", "Tanxugueiras", "Sábado 6 Febrero"),
                         _jj_post(3, "https://jimmyjazzgasteiz.com/b/", "Fecha imposible", "Lunes 20 Noviembre"))
        self.assertEqual([(e["title"], e["start"]) for e in evs], [("Tanxugueiras", "2027-02-06")])

    def test_club_night_keeps_the_announced_day_without_a_misleading_hour(self):
        e, = self.parse(_jj_post(4, "https://jimmyjazzgasteiz.com/apetak/", "Apetak", "&gt; I-F &gt; I-REAL Sábado 21 Noviembre",
                                 "<p>Puertas – 1:00 Anticipada: 12 € Taquilla: 15 €</p> https://soundcloud.com/x", cats=(1336, 5)))
        self.assertEqual((e["title"], e["start"], e["time"], e["subtype"]), ("Apetak: I-F, I-REAL", "2026-11-21", "", "Sesión DJ"))
        self.assertIn("Noche del sábado 21 al domingo 22, puertas a la 1:00", e["description"])
        self.assertEqual(e["tickets_url"], "")  # un enlace de SoundCloud no es la venta de entradas

    def test_kubik_free_entry_and_date_range(self):
        kubik, free, rng = self.parse(
            _jj_post(5, "https://kubikvitoria.com/beste-bat/", "Beste Bat (Kubik)", "– KOMANDO KOMBATE – BULKADA Viernes 20 Noviembre"),
            _jj_post(6, "https://jimmyjazzgasteiz.com/bernaola/", "Bernaola Zikloa", "STONE Domingo 29 Noviembre", "<p>Puertas – 19:30 Entrada libre</p>"),
            _jj_post(7, "https://jimmyjazzgasteiz.com/gazte/", "Gazte Talent", "8 – 9 Diciembre", "<p>Puertas – 18:30</p>"))
        self.assertEqual((kubik["title"], kubik["venue"]), ("Beste Bat: KOMANDO KOMBATE, BULKADA", "Sala Kubik"))
        self.assertTrue(free["free"])
        self.assertEqual((rng["start"], rng["end"]), ("2026-12-08", "2026-12-09"))

    def test_concert_hall_categories_ignore_band_biographies(self):
        band, comic = self.parse(
            _jj_post(8, "https://jimmyjazzgasteiz.com/p/", "Peiremans+", "Jueves 17 Diciembre", "<p>Con Haritz Beristain Txiki. Actuación – 21:00</p>"),
            _jj_post(9, "https://jimmyjazzgasteiz.com/i/", "Ignatius Farray", "Domingo 22 Noviembre", "<p>Ignatius Farray es un cómico de Tenerife</p>"))
        self.assertEqual((band["category"], comic["category"]), ("musica", "escena"))


class TestSameVenueDedupe(unittest.TestCase):
    def ev(self, source, title, **kw):
        from planes import util
        base = dict(province_code="01", city="Vitoria-Gasteiz", venue="Sala Jimmy Jazz")
        base.update(kw)
        return util.event(source, title, title, "2026-11-28", **base)

    def test_same_plan_from_two_sources_is_merged_and_completed(self):
        import fetch_events
        a = self.ev("Open Data Euskadi", "BENGO + TATTA (Jimmy Jazz Gasteiz)", lat=42.85, lon=-2.67, image="https://x/i.jpg")
        b = self.ev("Salas Jimmy Jazz y Kubik", "Bengo & Tatta", time="20:30", tickets_url="https://l.eus/x", price="Anticipada 15 €")
        dj = self.ev("Salas Jimmy Jazz y Kubik", "Dario Nuñez: PINTILLO, RESTECH")
        out, n = fetch_events.dedupe_venue([a, b, dj])
        self.assertEqual(n, 1)
        self.assertEqual(len(out), 2)
        merged = next(e for e in out if "tatta" in e["title"].lower())
        self.assertEqual((merged["time"], merged["tickets_url"], merged["lat"]), ("20:30", "https://l.eus/x", 42.85))

    def test_similar_plans_from_one_source_are_kept(self):
        import fetch_events
        x = self.ev("Ajuntament", "Taller de costura: iniciació", venue="Centre Cívic")
        y = self.ev("Ajuntament", "Taller de costura: avançat", venue="Centre Cívic")
        self.assertEqual(fetch_events.dedupe_venue([x, y])[1], 0)

    def test_coordinates_from_another_plan_in_the_same_venue(self):
        import fetch_events
        a = self.ev("Open Data Euskadi", "Saurom", lat=42.85, lon=-2.67)
        b = self.ev("Salas Jimmy Jazz y Kubik", "Apetak: QUELZA")
        self.assertEqual(fetch_events.fill_venue_coords([a, b]), 1)
        self.assertEqual((b["lat"], b["lon"]), (42.85, -2.67))



class TestAgendaCulturalAndalucia(unittest.TestCase):
    """Listado público de la Agenda Cultural de Andalucía (tarjetas recortadas del marcado real)."""

    @staticmethod
    def card(slug, title, dates, place, when, img="/aaiicc/agendaculturaldeandalucia/sites/default/files/x.jpg.webp?itok=1"):
        days = "".join('<div><div class="text-4xl font-light">%s</div><div><div class="text-sm">%s</div><div class="text-xs">%s</div></div></div>'
                       % d if isinstance(d, tuple) else '<div class="mx-2"> al </div>' for d in dates)
        return ('<div class="flex flex-col"><article role="article" class="flex flex-col flex-1"><div><div class="relative">'
                '<a href="/aaiicc/agendaculturaldeandalucia/evento/%s"><div><picture><source srcset="x 1x"/>'
                '<img src="%s" alt="%s" /></picture></div></a><div class="pt-6"><div class="flex">%s</div></div></div>'
                '<div><div><a href="/aaiicc/agendaculturaldeandalucia/evento/%s">\n  %s\n  </a></div>'
                '<div><div><i class="icon"></i></div><div><a href="/aaiicc/agendaculturaldeandalucia/espacios/x" hreflang="es">%s</a></div></div>'
                '<div><div><i></i></div><div><div><p>%s</p></div></div></div></div></div></article></div>'
                % (slug, img, title, days, slug, title, place, when))

    def page(self):
        c = self.card
        return (
            '<select data-drupal-selector="edit-topic" name="topic"><option value="All">- Cualquiera -</option>'
            '<option value="1429">Espectáculos</option><option value="1430">Exposiciones</option></select>'
            '<select name="province"><option value="All">- Cualquiera -</option><option value="1440">Córdoba</option>'
            '<option value="1445">Sevilla</option></select><header><div class="headline">771 Actividades</div></header>'
            + c("el-guiton-onofre-2", "el guitón onofre", [("27", "Noviembre", "2026")],
                "Teatro Municipal Calixto Sánchez - Mairena del Alcor (Sevilla)", "A las 21:00")
            + c("mujer-en-cinta-4", "Mujer en cinta de correr sobre fondo negro", [("27", "Noviembre", "2026")],
                "Teatro Central - Sevilla", "27/11/2026 - 20:30")
            + c("vitrales", "Exposición &#039;Vitrales y Suturas&#039; en el Palacio de Viana",
                [("01", "Noviembre", "2026"), None, ("29", "Noviembre", "2026")], "Palacio de Viana - Córdoba", "De 10:00 a 19:00")
            + c("love-love-love-2", "love, love, love", [("26", "Mayo", "2027")],
                "Espacio por determinar - Línea de la Concepción (La)", "Sin determinar")
            + c("nina-pastori", "Actuación de Niña Pastori en la Plaza de San Francisco", [("27", "Noviembre", "2026")],
                "Sevilla. Plaza de San Francisco - Sevilla", "Sin determinar")
            + c("concierto-julio", "Concierto de la Orquesta Ciudad de Granada", [("28", "Noviembre", "2026")],
                "Palacio de Congresos y Exposiciones - Granada", "20:00 horas"))

    def test_cards(self):
        from planes import src_aaiicc as a
        page = self.page()
        self.assertEqual(a.total(page), 771)
        self.assertEqual(a.topics(page), [("1429", "Espectáculos"), ("1430", "Exposiciones")])
        self.assertEqual(a.options(page, "province"), [("1440", "Córdoba"), ("1445", "Sevilla")])
        cards = {c["slug"]: c for c in a.parse_cards(page)}
        self.assertEqual(len(cards), 6)
        g = cards["el-guiton-onofre-2"]
        self.assertEqual((g["title"], g["start"], g["end"], g["venue"], g["city"], g["province"]),
                         ("el guitón onofre", "2026-11-27", "2026-11-27", "Teatro Municipal Calixto Sánchez", "Mairena del Alcor", "Sevilla"))
        self.assertEqual(g["url"], "https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia/evento/el-guiton-onofre-2")
        self.assertTrue(g["image"].startswith("https://www.juntadeandalucia.es/aaiicc/"))
        v = cards["vitrales"]
        self.assertEqual((v["title"], v["start"], v["end"], v["city"], v["province"]),
                         ("Exposición 'Vitrales y Suturas' en el Palacio de Viana", "2026-11-01", "2026-11-29", "Córdoba", "Córdoba"))
        lo = cards["love-love-love-2"]
        self.assertEqual((lo["venue"], lo["city"], lo["province"], lo["when"]), ("", "La Línea de la Concepción", "", ""))
        n = cards["nina-pastori"]
        self.assertEqual((n["venue"], n["city"], n["province"]), ("Plaza de San Francisco", "Sevilla", "Sevilla"))

    def test_events(self):
        from planes import src_aaiicc as a
        cards = {c["slug"]: c for c in a.parse_cards(self.page())}
        g = a.to_event(cards["el-guiton-onofre-2"], "Espectáculos")
        self.assertEqual((g["category"], g["time"], g["province"], g["source"]), ("escena", "21:00", "Sevilla", a.NAME))
        m = a.to_event(cards["mujer-en-cinta-4"], "Espectáculos")
        self.assertEqual((m["time"], m["city"], m["province"]), ("20:30", "Sevilla", "Sevilla"))
        j = a.to_event(cards["concierto-julio"], "Espectáculos")
        self.assertEqual((j["category"], j["time"], j["province"]), ("musica", "20:00", "Granada"))
        v = a.to_event(cards["vitrales"], "Exposiciones")
        self.assertEqual((v["category"], v["time"]), ("expos", ""))  # el horario de apertura no es la hora de un evento
        lo = a.to_event(cards["love-love-love-2"], "Agenda infantil y juvenil", "Cádiz")
        self.assertEqual((lo["category"], lo["province"], lo["city"], lo["time"]), ("infantil", "Cádiz", "La Línea de la Concepción", ""))
        # la provincia del filtro manda cuando la tarjeta no nombra el municipio
        sin = dict(cards["nina-pastori"], city="", province="")
        self.assertEqual(a.to_event(sin, "Espectáculos", "Sevilla")["province"], "Sevilla")

    def test_fetch_combines_filters(self):
        from unittest import mock
        from planes import src_aaiicc as a
        page = self.page().replace("771 Actividades", "6 Actividades")
        calls = []

        def fake(url, params=None, **kw):
            calls.append(dict(params or {}))
            return page
        logs = []
        with mock.patch.object(a, "http_text", fake), mock.patch.object(a, "PAUSE", 0):
            evs = a.fetch(logs.append)
        self.assertEqual(len(evs), 6)  # cada plan una sola vez aunque salga en todas las combinaciones
        self.assertEqual(len(calls), 1 + 2 * 2)  # listado general + 2 temáticas × 2 provincias, una página cada una
        # manda la temática prioritaria (Exposiciones antes que Espectáculos) y su provincia
        self.assertEqual({(e["subtype"], e["province"]) for e in evs}, {("Exposiciones", "Córdoba")})
        self.assertIn("6 eventos de 6 en el listado", logs[0])

    def test_skip(self):
        from planes import src_aaiicc as a
        base = {"title": "Visita guiada al Monasterio", "start": "2026-11-27", "end": "2026-11-27"}
        self.assertFalse(a.skip(base))
        self.assertTrue(a.skip(dict(base, title="Visitas escolares en el Archivo de Indias")))
        self.assertTrue(a.skip(dict(base, title="Taller escolar de flamenco en Sevilla")))
        self.assertTrue(a.skip(dict(base, start="2024-08-01", end="2028-01-01")))  # oferta de varios años
        self.assertFalse(a.skip(dict(base, start="2026-10-01", end="2027-03-31")))  # exposición de temporada

    def test_registered(self):
        import fetch_events
        self.assertIn("aaiicc", fetch_events.SOURCES)
