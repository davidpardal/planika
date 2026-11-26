"""Publicar en Instagram desde /ig (tools/ig_publicar.py) con una API de Instagram simulada: nada sale a la red."""
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ig_publicar as ig  # noqa: E402


class R:
    def __init__(self, status=200, j=None):
        self.status_code, self._j = status, j if j is not None else {}

    def json(self):
        return self._j


class FakeSession:
    """Simula planikaapp.com/ig (HEAD) y graph.instagram.com (GET/POST)."""

    def __init__(self, slides=7, recent=(), statuses=("FINISHED",), refresh_ok=True, me_ok=True):
        self.slides, self.recent, self.statuses, self.refresh_ok, self.me_ok = slides, list(recent), list(statuses), refresh_ok, me_ok
        self.posts, self.n = [], 0

    def head(self, url, **kw):
        if url.endswith(".mp4"):
            return R(200 if "existe" in url else 404)
        k = int(url.rsplit("-", 1)[1].split(".")[0])
        return R(200 if k <= self.slides else 404)

    def get(self, url, params=None, **kw):
        path = url.replace(ig.API, "")
        if url == ig.REFRESH:
            return R(200, {"access_token": "nueva", "expires_in": 5183944}) if self.refresh_ok else R(400, {"error": {"message": "too new"}})
        if path == "me":
            return R(200, {"user_id": "178", "username": "planikaapp"}) if self.me_ok else R(400, {"error": {"message": "Invalid OAuth access token"}})
        if path == "178/media":
            return R(200, {"data": self.recent})
        if params and params.get("fields") == "status_code":
            st = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return R(200, {"status_code": st})
        if params and params.get("fields") == "permalink":
            return R(200, {"permalink": "https://www.instagram.com/p/ABC/"})
        return R(404, {"error": {"message": "no"}})

    def post(self, url, data=None, **kw):
        self.posts.append((url.replace(ig.API, ""), dict(data)))
        self.n += 1
        return R(200, {"id": ("m%d" % self.n) if url.endswith("media_publish") else "c%d" % self.n})


CAP = "🆓 Gratis este finde en Bilbao (27–29 nov): 5 planes elegidos 👇\n\n1️⃣ …"


class TestPublicar(unittest.TestCase):
    def api(self, s):
        return ig.Api("clave", s, sleep=lambda _: None)

    def test_carousel(self):
        s = FakeSession()
        link, user = ig.publish(self.api(s), "carrusel", "bilbao-gratis", CAP, s)
        self.assertEqual((link, user), ("https://www.instagram.com/p/ABC/", "planikaapp"))
        kids = [d for p, d in s.posts if d.get("is_carousel_item") == "true"]
        self.assertEqual(len(kids), 7)
        self.assertEqual(kids[0]["image_url"], "https://planikaapp.com/ig/bilbao-gratis/bilbao-gratis-1.jpg")
        car = [d for p, d in s.posts if d.get("media_type") == "CAROUSEL"][0]
        self.assertEqual(len(car["children"].split(",")), 7)
        self.assertEqual(car["caption"], CAP)
        self.assertEqual(s.posts[-1][0], "178/media_publish")
        self.assertTrue(all(d["access_token"] == "clave" for _, d in s.posts))

    def test_reel_waits_until_processed(self):
        s = FakeSession(statuses=["IN_PROGRESS", "IN_PROGRESS", "FINISHED"])
        ig.publish(self.api(s), "reel", "reels/reel-que-existe.mp4", "🎬 Reel de prueba", s)
        cont = s.posts[0][1]
        self.assertEqual((cont["media_type"], cont["video_url"], cont["share_to_feed"]),
                         ("REELS", "https://planikaapp.com/ig/reels/reel-que-existe.mp4", "true"))
        self.assertEqual(s.posts[-1][0], "178/media_publish")

    def test_refuses_bad_paths_duplicates_and_long_captions(self):
        s = FakeSession()
        for kind, path in (("carrusel", "../x"), ("reel", "reels/../../x.mp4"), ("reel", "reels/no-esta.mp4")):
            with self.assertRaises(ig.IgError):
                ig.publish(self.api(s), kind, path, CAP, s)
        with self.assertRaises(ig.IgError):
            ig.publish(self.api(FakeSession(slides=1)), "carrusel", "bilbao", CAP, FakeSession(slides=1))
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
        dup = FakeSession(recent=[{"caption": CAP.split("\n")[0] + "\n\notro texto", "timestamp": now}])
        with self.assertRaisesRegex(ig.IgError, "ya está publicado"):
            ig.publish(self.api(dup), "carrusel", "bilbao-gratis", CAP, dup)
        self.assertEqual([p for p, _ in dup.posts], [])  # no ha creado nada
        with self.assertRaisesRegex(ig.IgError, "2200"):
            ig.publish(self.api(s), "carrusel", "bilbao-gratis", "x" * 2300, s)

    def test_processing_error_stops(self):
        s = FakeSession(statuses=["ERROR"])
        with self.assertRaisesRegex(ig.IgError, "procesar"):
            ig.publish(self.api(s), "reel", "reels/reel-que-existe.mp4", "Reel", s)
        self.assertNotIn("178/media_publish", [p for p, _ in s.posts])

    def test_token_check(self):
        self.assertEqual(ig.check_and_refresh("clave", FakeSession()), "nueva")
        self.assertEqual(ig.check_and_refresh("clave", FakeSession(refresh_ok=False)), "")  # vale, pero hoy no se renueva
        with self.assertRaisesRegex(ig.IgError, "Invalid OAuth"):
            ig.check_and_refresh("clave", FakeSession(me_ok=False))

    def test_ig_page_has_owner_only_button(self):
        from planes import instagram
        page = instagram.index_page([], {}, "26/11/2026", [{"file": "reels/a.mp4", "title": "A", "caption": "Pie", "kind": "viral"}])
        self.assertIn('id="igKey"', page)
        self.assertIn("actions/workflows/instagram.yml/dispatches", page)
        self.assertIn("if (!ghKey()) return;", page)  # sin clave guardada, no hay botón


if __name__ == "__main__":
    unittest.main()
