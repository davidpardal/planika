# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest
import xml.dom.minidom
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from planes import boletin  # noqa: E402


def ev(i, start, cat="musica", city="Bilbao", pc="48", prov="Bizkaia", **kw):
    return dict({"id": "%014x" % i, "title": "Plan %d <b>" % i, "start": start, "end": kw.pop("end", start), "time": "20:00",
                 "category": cat, "city": city, "province_code": pc, "province": prov, "venue": "Sala %d" % i,
                 "description": "x" * 130, "image": "https://img/%d.jpg" % i, "source": "Fuente", "free": False}, **kw)


class TestBoletin(unittest.TestCase):
    def setUp(self):
        self.evs = [ev(1, "2026-11-20"), ev(2, "2026-11-21", cat="escena", city="Madrid", pc="28", prov="Madrid"),
                    ev(3, "2026-11-22", cat="infantil", free=True), ev(4, "2026-11-25"),           # miércoles: fuera
                    ev(5, "2026-10-01", end="2027-01-31", cat="expos"),                            # expo larga: fuera
                    ev(6, "2026-11-21", cat="fiestas", free=True, city="Getxo")]

    def test_weekend_and_selection(self):
        self.assertEqual(boletin.weekend(date(2026, 11, 19))[:2], (date(2026, 11, 20), date(2026, 11, 22)))
        self.assertEqual(boletin.weekend(date(2026, 11, 21))[2], date(2026, 11, 21))  # en sábado, desde hoy
        ed = boletin.select(self.evs, date(2026, 11, 19))
        self.assertEqual(ed["total"], 4)
        ids = [e["id"] for e in ed["top"] + ed["free"] + ed["kids"]]
        self.assertEqual(len(ids), len(set(ids)))  # ningún plan dos veces
        self.assertNotIn("%014x" % 4, ids)
        self.assertLessEqual(sum(1 for e in ed["top"] if e["province_code"] == "48"), 2)  # variedad de provincias

    def test_write_archive_feed(self):
        with tempfile.TemporaryDirectory() as site:
            boletin.write(site, self.evs, date(2026, 11, 17), config={})       # martes: sin archivo
            self.assertFalse(os.path.exists(os.path.join(site, "boletin", "2026-11-20.html")))
            boletin.write(site, self.evs, date(2026, 11, 19), config={"form_url": "https://alta.example/f", "unsubscribe_tag": "{{ unsubscribe }}"})
            out = os.path.join(site, "boletin")
            self.assertTrue(os.path.exists(os.path.join(out, "2026-11-20.html")))
            with open(os.path.join(out, "email.html"), encoding="utf-8") as fh:
                mail = fh.read()
            self.assertIn("Plan 1 &lt;b&gt;", mail)               # títulos escapados
            self.assertIn("{{ unsubscribe }}", mail)              # baja del servicio de envío
            self.assertIn("utm_source=boletin", mail)
            with open(os.path.join(out, "index.html"), encoding="utf-8") as fh:
                page = fh.read()
            self.assertIn("https://alta.example/f", page)
            self.assertIn('content="index,follow"', page)         # con formulario, la página de alta se indexa
            self.assertNotIn("{{ unsubscribe }}", page)
            with open(os.path.join(out, "email.json"), encoding="utf-8") as fh:
                meta = json.load(fh)
            self.assertEqual(meta["edicion"], "2026-11-20")
            self.assertTrue(meta["asunto"].startswith("Planes del finde 20–22 nov"))
            doc = xml.dom.minidom.parse(os.path.join(site, "feeds", "boletin.xml"))
            self.assertEqual(len(doc.getElementsByTagName("item")), 1)

    def test_brevo_draft_by_default(self):
        import boletin_brevo

        class Resp:
            def __init__(self, code, data=None):
                self.status_code, self._data, self.text = code, data or {}, ""

            def json(self):
                return self._data

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, url, **kw):
                self.calls.append(url)
                return Resp(201, {"id": 7})

        self.assertEqual(boletin_brevo.main(env={}, session=Session()), 0)  # sin clave, nada
        with tempfile.TemporaryDirectory() as site:
            boletin.write(site, self.evs, date(2026, 11, 19), config={})
            old, root = boletin_brevo.ROOT, None
            try:
                # ROOT apunta a una copia con site/boletin
                root = tempfile.mkdtemp()
                os.makedirs(os.path.join(root, "site"))
                os.rename(os.path.join(site, "boletin"), os.path.join(root, "site", "boletin"))
                boletin_brevo.ROOT = root
                env = {"BREVO_API_KEY": "k", "BREVO_LIST_ID": "3", "BREVO_SENDER_EMAIL": "hola@planikaapp.com"}
                s = Session()
                self.assertEqual(boletin_brevo.main(env=env, session=s, t0=date(2026, 11, 19)), 0)
                self.assertEqual(len(s.calls), 1)                                   # borrador: no se envía
                s = Session()
                self.assertEqual(boletin_brevo.main(env=dict(env, BOLETIN_ENVIO="auto"), session=s, t0=date(2026, 11, 19)), 0)
                self.assertTrue(s.calls[1].endswith("/emailCampaigns/7/sendNow"))
                # Una edición vieja no se envía nunca
                self.assertEqual(boletin_brevo.main(env=env, session=Session(), t0=date(2026, 11, 26)), 1)
            finally:
                boletin_brevo.ROOT = old
                import shutil
                if root:
                    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
