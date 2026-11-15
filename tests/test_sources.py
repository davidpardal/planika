# -*- coding: utf-8 -*-
"""Pruebas de los conectores nuevos con respuestas recortadas de las fuentes reales."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import src_diba, src_esmadrid, src_municipios, src_murcia, src_zaragoza  # noqa: E402


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
        evs = src_zaragoza.parse([free, course, workshop, "basura", {"id": 5}])
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
<item name="Servicios de pago"><![CDATA[<p>Desde 55 €</p>]]></item><item name="Horario"><![CDATA[<p>Apertura: 19:00 h</p><p>Inicio: 20:30 h</p>]]></item>
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
