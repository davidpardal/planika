"""Burdeos (Francia), del 5 al 8 de diciembre: la fuente no anuncia fechas que no constan y el resto de la web
trata bien un lugar fuera de España (país en los datos estructurados, sin tocar coordenadas, fuera del boletín)."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import boletin, salas, src_burdeos as bx, static, util  # noqa: E402

STATUS_OK = '{"id": 1, "label": {"fr": "Programmé"}}'
ONSITE = '{"id": 1, "label": {"fr": "Sur place"}}'


def row(uid, title, first, last, daterange="", **kw):
    r = {"uid": uid, "originagenda_uid": "999", "title_fr": title, "description_fr": "Descripción", "firstdate_begin": first,
         "lastdate_begin": last, "lastdate_end": last, "daterange_fr": daterange, "status": STATUS_OK,
         "attendancemode": ONSITE, "location_name": "Auditorium de Bordeaux", "location_city": "Bordeaux",
         "location_address": "9-13 cours Georges Clemenceau 33000 Bordeaux", "location_countrycode": "FR",
         "location_coordinates": {"lon": -0.5785, "lat": 44.8422}, "conditions_fr": "", "keywords_fr": None, "links": None}
    r.update(kw)
    return r


class SourceTest(unittest.TestCase):
    def one(self, r):
        evs = bx.to_events([r])
        return evs

    def test_concert_hour_in_paris_time(self):
        (e,) = self.one(row("1", "Lang Lang", "2026-12-05T19:00:00+00:00", "2026-12-05T19:00:00+00:00", "Samedi 5 décembre, 20h00",
                            keywords_fr=["Piano"], links='[{"link": "https://www.opera-bordeaux.com/piano-lang-lang-85401"}]'))
        self.assertEqual((e["start"], e["end"], e["time"]), ("2026-12-05", "2026-12-05", "20:00"))
        self.assertEqual((e["city"], e["province_code"], e["province"], e["ccaa"]), ("Burdeos", "FR33", "Gironda", "Francia"))
        self.assertEqual(e["category"], "musica")
        self.assertEqual(e["url"], "https://www.opera-bordeaux.com/piano-lang-lang-85401")
        self.assertEqual((e["lat"], e["lon"]), (44.8422, -0.5785))

    def test_url_falls_back_to_openagenda(self):
        (e,) = self.one(row("73946251", "La Flûte Enchantée", "2026-12-05T19:00:00+00:00", "2026-12-05T19:00:00+00:00",
                            links='[{"link": "mailto:x@y.fr"}]'))
        self.assertEqual(e["url"], "https://openagenda.com/agendas/999/events/73946251")

    def test_short_multi_day_kept_whole(self):
        (e,) = self.one(row("2", "Les portes ouvertes de Pessac-Léognan", "2026-12-05T08:00:00+00:00",
                            "2026-12-06T08:00:00+00:00", "5 et 6 décembre", location_city="Pessac"))
        self.assertEqual((e["start"], e["end"], e["city"]), ("2026-12-05", "2026-12-06", "Pessac"))

    def test_continuous_exhibition_keeps_its_period(self):
        (e,) = self.one(row("3", "Exposition \"Pollen\" au CAPC", "2026-01-06T09:00:00+00:00", "2027-06-20T09:00:00+00:00",
                            "6 janvier 2026 - 20 juin 2027"))
        self.assertEqual((e["start"], e["end"], e["time"], e["category"]), ("2026-01-06", "2027-06-20", "", "expos"))

    def test_recurring_without_known_session_in_window_is_skipped(self):
        self.assertEqual(self.one(row("4", "Atelier Dessin au fusain", "2026-09-02T12:30:00+00:00", "2026-12-30T12:30:00+00:00",
                                      "2 septembre - 30 décembre, les mercredis")), [])
        # Visita sobre una exposición: tiene sesiones sueltas aunque las palabras clave digan «exposition»
        self.assertEqual(self.one(row("5", "Visite ludique - La céramique de A à Z", "2026-05-10T12:00:00+00:00",
                                      "2027-02-25T12:00:00+00:00", "10 mai 2026 - 25 février 2027", keywords_fr=["exposition"])), [])

    def test_last_session_in_window_only_that_day(self):
        (e,) = self.one(row("6", "Idées à lire", "2026-09-12T09:00:00+00:00", "2026-12-05T10:00:00+00:00",
                            "12 septembre et 5 décembre"))
        self.assertEqual((e["start"], e["end"], e["time"]), ("2026-12-05", "2026-12-05", "11:00"))

    def test_outside_window_skipped(self):
        self.assertEqual(self.one(row("7", "Concert", "2026-12-12T19:00:00+00:00", "2026-12-12T19:00:00+00:00")), [])

    def test_not_leisure_cancelled_online(self):
        self.assertEqual(self.one(row("8", "Financer mon projet d'entreprise", "2026-12-08T08:30:00+00:00", "2026-12-08T08:30:00+00:00")), [])
        self.assertEqual(self.one(row("9", "Concert", "2026-12-05T19:00:00+00:00", "2026-12-05T19:00:00+00:00",
                                      status='{"id": 6, "label": {"fr": "Annulé"}}')), [])
        self.assertEqual(self.one(row("10", "Conférence", "2026-12-05T19:00:00+00:00", "2026-12-05T19:00:00+00:00",
                                      attendancemode='{"id": 2, "label": {"fr": "En ligne"}}')), [])

    def test_price_label_and_free(self):
        self.assertEqual(bx.price_fr("85 € / 65 € tarif réduit RSA / 42 € carte jeune"), ("85 €", False))
        self.assertEqual(bx.price_fr("Entrée libre et gratuite"), ("Entrée libre et gratuite", True))
        self.assertEqual(bx.price_fr("5 € par enfant. Gratuit avec la Carte Jeune"), ("5 € par enfant", False))
        self.assertFalse(bx.price_fr("Tarif libre à partir de 2€")[1])

    def test_window_is_december_5_to_8(self):
        self.assertEqual(bx.WINDOW, (date(2026, 12, 5), date(2026, 12, 8)))


class OutsideSpainTest(unittest.TestCase):
    def ev(self):
        return util.event(bx.NAME, "x", "Lang Lang", "2026-12-05", time="20:00", category="musica", province_code="FR33",
                          city="Burdeos", venue="Auditorium de Bordeaux", lat=44.8422, lon=-0.5785)

    def test_country(self):
        self.assertEqual((util.country("48"), util.country("FR33"), util.country("")), ("ES", "FR", "ES"))

    def test_coordinates_outside_spain_are_kept(self):
        e = self.ev()
        salas.fix_coords([e])
        self.assertEqual((e["lat"], e["lon"]), (44.8422, -0.5785))
        self.assertEqual(salas.imprecise([dict(e, lat=None, lon=None)]), [])

    def test_structured_data_country(self):
        ld = static.event_jsonld(self.ev(), "https://planikaapp.com/e/x.html", t0="2026-12-01")
        self.assertEqual(ld["location"]["address"]["addressCountry"], "FR")

    def test_not_in_spanish_newsletter(self):
        es = util.event("Prueba", "y", "Concierto en Bilbao", "2026-12-05", category="musica", province_code="48", city="Bilbao")
        ed = boletin.select([self.ev(), es], date(2026, 12, 3))
        self.assertEqual(ed["total"], 1)


if __name__ == "__main__":
    unittest.main()
