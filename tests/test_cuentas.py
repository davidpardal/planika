"""Cuentas opcionales (Supabase): comprobaciones estáticas de seguridad y de coherencia entre app.js e index.html."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


class CuentasTest(unittest.TestCase):
    def test_only_publishable_key_in_site(self):
        for dp, _, files in os.walk(os.path.join(ROOT, "site")):
            if os.sep + "data" in dp:
                continue
            for f in files:
                if f.endswith((".js", ".html")):
                    txt = read(dp, f)
                    self.assertNotIn("sb_secret_", txt, f)
                    self.assertNotIn("service_role", txt, f)
        app = read("site", "app.js")
        self.assertRegex(app, r"var SB_KEY = 'sb_publishable_[A-Za-z0-9_]+';")
        self.assertIn("var ACCOUNTS_PUBLIC = ", app)

    def test_ids_used_by_app_exist(self):
        app, index = read("site", "app.js"), read("site", "index.html")
        missing = sorted(i for i in set(re.findall(r"\$\('([A-Za-z0-9_-]+)'\)", app)) if 'id="%s"' % i not in index)
        self.assertEqual(missing, [], "ids que app.js busca y no están en index.html")

    def test_link_return_asks_when_not_requested_here(self):
        app = read("site", "app.js")
        self.assertIn("accShow('confirm')", app)
        self.assertIn("K_ASK", app)

    def test_privacy_mentions_accounts(self):
        from planes import legal
        page = legal.privacy_page()
        self.assertIn('id="cuentas"', page)
        self.assertIn("Borrar mi cuenta", page)
        for key in ("planika_sesion", "planika_fav_ops", "planika_lugar", "planika_pide"):
            self.assertIn(key, page)

    def test_keepalive_ping(self):
        wf = read(".github", "workflows", "update.yml")
        self.assertIn("/rest/v1/rpc/ping", wf)
        self.assertNotIn("sb_secret_", wf)


if __name__ == "__main__":
    unittest.main()
