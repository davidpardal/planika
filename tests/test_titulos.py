# -*- coding: utf-8 -*-
"""Títulos para mostrar (util.clean_title) y hora de «Actualizado»."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import publish, static, util  # noqa: E402

c = util.clean_title


class TestCleanTitle(unittest.TestCase):
    def test_ticket_listings_lose_prefix_date_and_venue(self):
        self.assertEqual(c("Entradas Malú (28 de noviembre - Baluarte, Pamplona)"), "Malú")
        self.assertEqual(c("Entradas Carlos Ares - fin de gira (26 y 27 de noviembre - Bilbao)"), "Carlos Ares - fin de gira")
        self.assertEqual(c("Entradas La Oreja de Van Gogh con Amaia Montero (Bilbao - 5 diciembre)"),
                         "La Oreja de Van Gogh con Amaia Montero")
        self.assertEqual(c("Entradas Peiremans+: gira de conciertos (noviembre-diciembre)"), "Peiremans+: gira de conciertos")
        self.assertEqual(c("Entradas Neal Sugarman (Dabadaba)", "Dabadaba", "Bilbao"), "Neal Sugarman")
        self.assertEqual(c("Entradas Sho-Hai (Jimmy Jazz Gasteiz)", "Jimmy Jazz", "Vitoria-Gasteiz"), "Sho-Hai")
        self.assertEqual(c('Entradas "Vaquero" (28 de noviembre - San Sebastián)'), "Vaquero")
        self.assertEqual(c("Entradas U.D.O.: \"Triple Anniversary Tour\" (Sala Totem)", "Totem", "Basauri"),
                         'U.D.O.: "Triple Anniversary Tour"')
        self.assertEqual(c("Negufest 2027: Entradas concierto Pignoise (22 de enero - Bilbao)"), "Negufest 2027: Concierto Pignoise")
        self.assertEqual(c("(suspendido) Entradas Peiremans+ (27 de noviembre - Elgeta)"), "(suspendido) Peiremans+")
        self.assertEqual(c("Entradas +dMANÁ (Tributo a Maná) (15 de mayo de 2027, Vitoria-Gasteiz)"), "+dMANÁ (Tributo a Maná)")

    def test_meaningful_parentheses_stay(self):
        for t in ("Museo San Telmo (exposición permanente y visitas guiadas)", "Monólogo (+18)", "MOMAD 2027 (Edición febrero)",
                  "Taller (iniciació)", "Liga F: Athletic - Real Madrid (Liga F Moeve)"):
            self.assertEqual(c(t, "Museo San Telmo", "Donostia / San Sebastián"), t)
        self.assertEqual(c("«Visiones de Ultramar» (Programa inaugural Museo de Bellas Artes de Bilbao)",
                           "Museo de Bellas Artes de Bilbao", "Bilbao"),
                         "«Visiones de Ultramar» (Programa inaugural Museo de Bellas Artes de Bilbao)")

    def test_all_caps(self):
        self.assertEqual(c("HEAD HOLES + THE HOT DOGS"), "Head Holes + The Hot Dogs")
        self.assertEqual(c("CONCIERTO DE NAVIDAD EN EL ARRIAGA"), "Concierto de Navidad en el Arriaga")
        self.assertEqual(c("I GALA DEL DÍA INTERNACIONAL DEL VOLUNTARIADO"), "I Gala del Día Internacional del Voluntariado")
        self.assertEqual(c("TRISTESA I ALEGRIA EN LA VIDA DE LES GIRAFES"), "Tristesa i Alegria en la Vida de les Girafes")
        self.assertEqual(c("VIII FESTIVAL CAIXABANK D'ORQUESTRES"), "VIII Festival Caixabank d'Orquestres")
        self.assertEqual(c("RPG-7 + KALERIZO + DISKONFORMES"), "RPG-7 + Kalerizo + Diskonformes")
        self.assertEqual(c("CAPERUCITA (O PARA QUIÉN ES ESTE PASTEL)"), "Caperucita (o para Quién Es Este Pastel)")
        # Una sola palabra en mayúsculas suele ser el nombre artístico: se queda
        self.assertEqual(c("LEVITANTS"), "LEVITANTS")
        self.assertEqual(c("Concierto LUCHO RK"), "Concierto LUCHO RK")

    def test_quotes_and_stylized_names(self):
        self.assertEqual(c('"El carnaval animal"'), "El carnaval animal")
        self.assertEqual(c("«Los virus, héroes y villanos»"), "Los virus, héroes y villanos")
        self.assertEqual(c('"iZuloa"'), "iZuloa")  # no se cambia la grafía del nombre
        self.assertEqual(c('Mocedades: "Gira 60 Aniversario"'), 'Mocedades: "Gira 60 Aniversario"')

    def test_display_title_prefers_translation(self):
        e = util.event("Agenda", "1", "LE ROI DES MAGICIENS", "2026-12-06", city="Burdeos", province_code="FR33")
        self.assertEqual(util.display_title(e), "Le Roi des Magiciens")
        e["title_es"] = "El rey de los magos"
        self.assertEqual(util.display_title(e), "El rey de los magos")

    def test_page_url_and_data_row_keep_raw_title(self):
        """La URL de la ficha sale del título original: limpiar el título no rompe lo ya indexado."""
        e = util.event("Open Data Euskadi", "2", "Entradas Hazas (27 de noviembre - Bilbao)", "2026-11-27", city="Bilbao",
                       province_code="48")
        self.assertTrue(static.event_file(e).startswith("entradas-hazas-27-de-noviembre-bilbao-"))
        self.assertEqual(static._shown_title(e), "Hazas")
        e2 = util.event("Agenda", "3", "Concierto", "2026-11-27", city="Bilbao", province_code="48")
        self.assertEqual(static._shown_title(e2), "")  # sin cambios: no se repite en core.js


class TestClip(unittest.TestCase):
    def test_no_dangling_words_or_parentheses(self):
        self.assertEqual(static.clip("Concierto de la Orquesta Sinfónica de Euskadi", 39), "Concierto de la Orquesta Sinfónica…")
        self.assertEqual(static.clip("Museo San Telmo (exposición permanente y visitas)", 30), "Museo San Telmo…")
        self.assertEqual(static.clip("Vitoria-Gasteiz", 30), "Vitoria-Gasteiz")


class TestUpdated(unittest.TestCase):
    def test_stamp_format(self):
        self.assertRegex(util.stamp(), r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")

    def test_sources_page_text(self):
        self.assertEqual(publish._upd_text("2026-11-24T06:50", hour=True), "24 nov 2026 a las 6:50")
        self.assertEqual(publish._upd_text("2026-11-24T06:50"), "24 nov 2026")
        page = publish._sources_page([{"name": "X", "home": "https://x.example", "count": 3}], "2026-11-24T16:05")
        self.assertIn("Actualizado el 24 nov 2026 a las 16:05", page)
        self.assertNotIn("2026-11-24", page)


class TestTransient(unittest.TestCase):
    def test_which_errors_get_a_second_attempt(self):
        import requests
        import fetch_events
        self.assertTrue(fetch_events.transient(requests.ConnectionError("RemoteDisconnected")))
        self.assertTrue(fetch_events.transient(requests.Timeout()))
        r = requests.Response()
        r.status_code = 503
        self.assertTrue(fetch_events.transient(requests.HTTPError(response=r)))
        r404 = requests.Response()
        r404.status_code = 404
        self.assertFalse(fetch_events.transient(requests.HTTPError(response=r404)))
        self.assertFalse(fetch_events.transient(ValueError("JSON roto")))


if __name__ == "__main__":
    unittest.main()
