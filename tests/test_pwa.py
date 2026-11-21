# -*- coding: utf-8 -*-
"""App instalable: manifiesto, iconos, service worker y cabecera de las páginas estáticas."""
import json
import os
import struct
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
sys.path.insert(0, ROOT)

from planes import static  # noqa: E402


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def read(name):
    with open(os.path.join(SITE, name), encoding="utf-8") as fh:
        return fh.read()


class TestPwa(unittest.TestCase):
    def test_manifest(self):
        m = json.loads(read("manifest.webmanifest"))
        self.assertEqual((m["scope"], m["display"]), ("/", "standalone"))
        self.assertTrue(m["start_url"].startswith("/"))
        sizes = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
        # Lo que piden Chrome (instalar) y Google Play (TWA): 192 y 512, y uno adaptable (maskable)
        self.assertTrue({("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= sizes)
        for i in m["icons"]:
            path = os.path.join(SITE, i["src"].lstrip("/"))
            self.assertTrue(os.path.exists(path), i["src"])
            if i["type"] == "image/png":
                w, h = png_size(path)
                self.assertEqual("%dx%d" % (w, h), i["sizes"])
        for s in m["screenshots"] + [{"src": x["url"].split("?")[0]} for x in m["shortcuts"]]:
            self.assertTrue(os.path.exists(os.path.join(SITE, s["src"].lstrip("/"))), s["src"])
        self.assertEqual(png_size(os.path.join(SITE, "apple-touch-icon.png")), (180, 180))

    def test_service_worker_and_offline(self):
        sw = read("sw.js")
        for f in ("/offline.html", "/icon-192.png", "/manifest.webmanifest"):
            self.assertIn("'%s'" % f, sw)
            self.assertTrue(os.path.exists(os.path.join(SITE, f.lstrip("/"))))
        self.assertIn("url.origin !== self.location.origin", sw)  # no toca mapas, analítica ni imágenes de fuera
        self.assertIn("noindex", read("offline.html"))

    def test_pages_register(self):
        self.assertIn('rel="manifest"', static.BEACON)
        self.assertIn('serviceWorker.register("/sw.js")', static.BEACON)
        index = read("index.html")
        self.assertIn('href="apple-touch-icon.png"', index)
        self.assertIn('id="installBtn"', index)
        self.assertIn("serviceWorker.register('/sw.js')", read("app.js"))


if __name__ == "__main__":
    unittest.main()
