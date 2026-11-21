# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import salas  # noqa: E402

BILBAO = (43.25696, -2.92344)


def ev(venue, lat=BILBAO[0], lon=BILBAO[1], source="Open Data Euskadi", city="Bilbao", pc="48"):
    return {"title": "x", "venue": venue, "city": city, "province_code": pc, "lat": lat, "lon": lon, "source": source}


class TestSalas(unittest.TestCase):
    def test_imprecise(self):
        evs = [ev("Teatro Arriaga"),                                    # agenda que da el municipio
               ev("Sala BBK", 43.26, -2.93, source="Otra"),             # coordenadas propias: se respetan
               ev("Bilborock", None, None, source="Otra"),              # sin coordenadas
               ev("", source="Otra"),                                   # sin sala: nada que buscar
               ev("Online")]                                            # no es una sala
        self.assertEqual(salas.imprecise(evs), [0, 2])

    def test_shared_point_is_centroid(self):
        # 5 salas distintas en el mismo punto exacto de una localidad: es el centro del municipio
        evs = [ev("Sala %s" % n, 42.0, -1.0, source="Otra", city="Tudela", pc="31") for n in "ABCDE"]
        self.assertEqual(len(salas.imprecise(evs)), 5)
        # 4 salas en un mismo punto pueden ser un mismo edificio (centro cívico con biblioteca...): se respetan
        self.assertEqual(salas.imprecise(evs[:4]), [])

    def test_queries(self):
        self.assertEqual(salas.queries("Biblioteca de Bilbao (Ibaialde)"), ["Biblioteca de Bilbao", "Biblioteca Ibaialde"])
        self.assertEqual(salas.queries("Teatro Barakaldo - Barakaldo Antzokia"),
                         ["Teatro Barakaldo - Barakaldo Antzokia", "Teatro Barakaldo", "Barakaldo Antzokia"])
        self.assertEqual(salas.queries("Kursaal"), ["Kursaal"])

    def test_pick_rejects_town_and_far(self):
        town = {"category": "place", "type": "city", "lat": "43.2569", "lon": "-2.9234"}
        far = {"category": "amenity", "type": "theatre", "lat": "43.40", "lon": "-2.70"}   # ~23 km
        near = {"category": "amenity", "type": "theatre", "lat": "43.2600", "lon": "-2.9250", "osm_type": "way", "osm_id": 7}
        self.assertIsNone(salas.pick([town, far], BILBAO))
        hit = salas.pick([town, far, near], BILBAO)
        self.assertEqual((hit["lat"], hit["lon"], hit["osm"]), (43.26, -2.925, "way/7"))

    def test_geocode_apply_and_cache(self):
        evs = [ev("Teatro Arriaga"), ev("Teatro Arriaga"), ev("Sala Inexistente"), ev("Sala BBK", 43.26, -2.93, source="Otra")]
        calls = []

        def search(q, ref):
            calls.append(q)
            return [{"category": "amenity", "type": "theatre", "lat": "43.2581", "lon": "-2.9244"}] if "Arriaga" in q else []

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "salas.json")
            found, missed, left = salas.geocode(evs, lambda m: None, cache={}, search=search, sleep=lambda s: None,
                                                today=date(2026, 11, 21), path=path)
            self.assertEqual((found, missed, left), (1, 1, 0))
            cache = salas.load(path)
            self.assertTrue(cache["48|bilbao|teatro arriaga"]["ok"])
            self.assertFalse(cache["48|bilbao|sala inexistente"]["ok"])
            self.assertEqual(salas.apply(evs, cache), 2)
            self.assertEqual((evs[0]["lat"], evs[0]["lon"]), (43.2581, -2.9244))
            self.assertEqual((evs[2]["lat"], evs[3]["lat"]), (BILBAO[0], 43.26))  # sin resultado y precisa: igual
            # Al día siguiente no se vuelve a preguntar (ni lo encontrado ni lo no encontrado reciente)
            n = len(calls)
            self.assertEqual(salas.pending([ev("Teatro Arriaga"), ev("Sala Inexistente")], cache, date(2026, 11, 22)), [])
            # Lo no encontrado se reintenta pasado RETRY_DAYS
            self.assertEqual(len(salas.pending([ev("Sala Inexistente")], cache, date(2027, 2, 1))), 1)
            self.assertEqual(len(calls), n)

    def test_geocode_stops_on_block(self):
        def search(q, ref):
            raise RuntimeError("Nominatim ha respondido 429")
        logs = []
        with tempfile.TemporaryDirectory() as tmp:
            found, missed, left = salas.geocode([ev("Teatro Arriaga")], logs.append, cache={}, search=search,
                                                sleep=lambda s: None, path=os.path.join(tmp, "s.json"))
        self.assertEqual((found, missed, left), (0, 0, 1))
        self.assertIn("interrumpida", logs[0])


if __name__ == "__main__":
    unittest.main()
