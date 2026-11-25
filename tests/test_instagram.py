"""Carruseles de Instagram del finde: qué planes entran, textos y diapositivas."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import instagram, util  # noqa: E402

THU = date(2026, 11, 26)


def ev(i, city="Bilbao", day="2026-11-28", cat="musica", **kw):
    base = dict(province_code="48" if city == "Bilbao" else "01", city=city, venue="Sala %d" % (i % 5), time="20:00", category=cat,
                description="Concierto de presentación del nuevo disco, con banda completa y artistas invitados en una noche especial.",
                url="https://organizador.example/%d" % i, price="12 €")
    title = kw.pop("title", "Concierto número %d" % i)
    base.update(kw)
    return util.event("Agenda", "ig%d" % i, title, day, **base)


class TestInstagram(unittest.TestCase):
    def test_editions(self):
        cats = ["musica", "escena", "cine", "infantil", "charlas", "otros"]
        evs = [ev(i, cat=cats[i % len(cats)]) for i in range(30)]
        evs += [ev(100, title="Concierto suspendido"), ev(101, title="Gran gala (AGOTADAS)"), ev(102, title="Concierto agotado", price="Agotado")]
        evs += [ev(200 + i, city="Vitoria-Gasteiz") for i in range(20)]
        evs += [ev(300 + i, city="Getxo") for i in range(5)]           # pocas: sin carrusel
        evs += [ev(400, day="2026-12-05")]                              # el finde siguiente
        eds = instagram.editions(evs, THU)
        self.assertEqual([e["city"] for e in eds], ["Bilbao", "Vitoria-Gasteiz"])  # Bilbao primero, Getxo no
        bil = eds[0]
        self.assertEqual(len(bil["plans"]), 5)
        titles = [util.display_title(e) for e in bil["plans"]]
        self.assertFalse(any("suspendido" in t.lower() or "agotad" in t.lower() for t in titles))
        self.assertNotIn("charlas", [e["category"] for e in bil["plans"]])  # hay planes de ocio de sobra
        self.assertEqual(len({e["category"] for e in bil["plans"]}), 4)    # variedad: un tipo de cada antes de repetir
        self.assertEqual(bil["total"], 30)
        self.assertEqual(instagram.date_range(bil), "27–29 nov")

    def test_price(self):
        self.assertEqual(instagram.price(dict(free=True)), "Gratis")
        self.assertEqual(instagram.price(dict(price="Preu: 20€")), "20 €")
        self.assertEqual(instagram.price(dict(price="General: 25 €")), "25 €")
        self.assertEqual(instagram.price(dict(price="Consultar página oficial")), "")
        self.assertEqual(instagram.price(dict(price="")), "")

    def test_caption_and_slides(self):
        evs = [ev(i, cat=["musica", "escena", "cine", "infantil", "fiestas"][i % 5], free=(i == 0)) for i in range(20)]
        ed = instagram.editions(evs, THU)[0]
        cap = instagram.caption(ed)
        self.assertIn("Este finde en Bilbao (27–29 nov): 5 planes elegidos de los 20 que hay", cap)
        self.assertIn("sábado 28 · 20:00", cap)
        self.assertIn("#Bilbao #PlanesBilbao #QueHacerEnBilbao", cap)
        sl = instagram.slides(ed)
        self.assertEqual(len(sl), 7)  # portada, 5 planes y cierre
        self.assertIn("Este finde en", sl[0])
        self.assertIn("1/5 · Bilbao", sl[1])
        self.assertIn("Sábado 28 · 20:00", sl[1])
        self.assertIn("Hay <span", sl[-1])
        self.assertNotIn("<img", "".join(sl))  # sin fotos de los organizadores
        page = instagram.index_page([ed], {ed["slug"]: ["bilbao/bilbao-%d.jpg" % k for k in range(1, 8)]}, "26/11/2026")
        self.assertIn('content="noindex,nofollow"', page)
        self.assertIn("Guardar las 7 imágenes", page)
        self.assertEqual(instagram.short_city("Donostia / San Sebastián"), "Donostia")
        self.assertEqual(instagram.slugify("Donostia / San Sebastián"), "donostia-san-sebastian")


if __name__ == "__main__":
    unittest.main()
