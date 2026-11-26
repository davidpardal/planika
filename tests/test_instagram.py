"""Carruseles de Instagram: qué planes entran, temas (finde, gratis, con niños, puente), textos, diapositivas y reels."""
import json
import os
import sys
import tempfile
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

    def test_themes_free_kids_and_bridge(self):
        evs = [ev(i) for i in range(12)]
        evs += [ev(100 + i, free=True, price="", cat=["musica", "escena", "fiestas"][i % 3]) for i in range(9)]
        evs += [ev(200 + i, cat="infantil") for i in range(8)]
        evs += [ev(300 + i, day=["2026-12-05", "2026-12-06", "2026-12-07", "2026-12-08"][i % 4]) for i in range(14)]
        eds = instagram.editions(evs, THU)
        by = {e["slug"]: e for e in eds}
        self.assertEqual(sorted(by), ["bilbao", "bilbao-con-ninos", "bilbao-gratis", "bilbao-puente"])
        self.assertEqual([e["kind"] for e in eds], ["finde", "gratis", "ninos", "puente"])
        g = by["bilbao-gratis"]
        self.assertEqual(g["title"], "Gratis este finde en Bilbao")
        self.assertTrue(all(e.get("free") for e in g["plans"]))
        self.assertIn("🆓 Gratis este finde en Bilbao (27–29 nov): 5 planes elegidos de los 9 gratis que hay", instagram.caption(g))
        self.assertIn("#PlanesGratis", instagram.caption(g))
        sl = instagram.slides(g)
        self.assertIn("Gratis este finde en", sl[0])
        self.assertIn("planes gratis</span>", sl[-1])
        self.assertTrue(all(e["category"] == "infantil" for e in by["bilbao-con-ninos"]["plans"]))
        p = by["bilbao-puente"]
        self.assertEqual(instagram.date_range(p), "5–8 dic")
        self.assertEqual(p["total"], 14)
        self.assertIn("Puente de diciembre en", instagram.slides(p)[0])
        self.assertIn("en el puente en", instagram.slides(p)[-1])
        self.assertIn("#PuenteDeDiciembre", instagram.caption(p))
        self.assertNotIn("puente", [e["kind"] for e in instagram.editions(evs, date(2026, 11, 1))])  # aún lejos del puente

    def test_index_with_reels(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import instagram as tool
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            for f in ("nuevo.mp4", "nuevo.jpg", "viejo.mp4"):
                open(os.path.join(src, f), "wb").close()
            with open(os.path.join(src, "reels.json"), "w", encoding="utf-8") as fh:
                json.dump({"reels": [
                    {"file": "viejo.mp4", "title": "Finde pasado", "kind": "viral", "made": "2026-11-20", "until": "2026-11-22"},
                    {"file": "nuevo.mp4", "poster": "nuevo.jpg", "title": "Publica tu evento", "caption": "Texto del post #Planika",
                     "kind": "explicacion", "made": "2026-11-26"},
                    {"file": "no-existe.mp4", "title": "Falta", "made": "2026-11-26"}]}, fh)
            reels = tool.load_reels(src, out, now="2026-11-26")
            self.assertEqual([r["file"] for r in reels], ["reels/nuevo.mp4"])  # caducado y sin vídeo, fuera
            self.assertTrue(os.path.exists(os.path.join(out, "reels", "nuevo.jpg")))
        evs = [ev(i) for i in range(12)]
        ed = instagram.editions(evs, THU)[0]
        page = instagram.index_page([ed], {ed["slug"]: ["bilbao/bilbao-1.jpg"]}, "26/11/2026", reels)
        self.assertIn('<video controls playsinline preload="none" poster="reels/nuevo.jpg" src="reels/nuevo.mp4">', page)
        self.assertIn("Guardar el vídeo", page)
        self.assertIn('href="#reels" data-kind="reels">🎬 Reels (1)', page)
        self.assertIn('data-city="bilbao" data-kind="finde"', page)   # para el filtro por ciudad
        self.assertIn('id="cityNote"', page)
        self.assertIn("Explicación de la web", page)
        self.assertIn('<option value="bilbao">Bilbao</option>', page)


if __name__ == "__main__":
    unittest.main()
