# -*- coding: utf-8 -*-
"""Idiomas de la interfaz (site/i18n.js): que no falte ninguna traducción de lo que usa la web."""
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from planes import publish, static  # noqa: E402


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as fh:
        return fh.read()


I18N = read("site", "i18n.js")
K = json.loads(re.search(r"/\*DICT\*/\s*var K = (.*?);\s*/\*END\*/", I18N, re.S).group(1))
H = json.loads(re.search(r"/\*HTML\*/\s*var H = (.*?);\s*/\*END\*/", I18N, re.S).group(1))
APP = read("site", "app.js")
INDEX = read("site", "index.html")


def app_keys():
    keys = set(re.findall(r"tr\(\s*'((?:[^'\\]|\\.)*)'", APP))
    for a, b in re.findall(r"tr\([^()']*?\?\s*'((?:[^'\\]|\\.)*)'\s*:\s*'((?:[^'\\]|\\.)*)'", APP):
        keys |= {a, b}
    return keys


class TestDictionary(unittest.TestCase):
    def test_every_entry_has_four_languages_and_same_holes(self):
        for es, tr in K.items():
            self.assertEqual(len(tr), 4, es)  # euskera, catalán, gallego, inglés
            holes = sorted(re.findall(r"\{\w+\}", es))
            for x in tr:
                self.assertTrue(x, es)
                self.assertEqual(sorted(re.findall(r"\{\w+\}", x)), holes, (es, x))
        for k, v in H.items():
            self.assertEqual(len(v), 4, k)

    def test_app_strings_are_translated(self):
        missing = sorted(app_keys() - set(K))
        self.assertEqual(missing, [], "Textos de app.js sin traducir en i18n.js")

    def test_category_names_are_translated(self):
        names = set(static.CAT_NAME.values()) | set(publish.CAT_INTENT.values()) | set(publish.SUB_LABEL.values())
        self.assertEqual(sorted(n for n in names if n not in K), [])
        for n in publish.CAT_INTENT.values():  # enlaces «Conciertos en Bizkaia» de las páginas generadas
            self.assertIn(n + " en {x}", K)

    def test_html_blocks_exist(self):
        for key in re.findall(r'data-i18n-html="([^"]+)"', INDEX):
            self.assertIn(key, H)

    def test_menu_and_filters_are_translated(self):
        for s in ("Mis favoritos", "Crear tu plan", "¿Buscas un plan?", "Búsqueda avanzada", "Borrar filtros", "Idioma"):
            self.assertIn(s, K)


class TestPages(unittest.TestCase):
    def test_generated_pages_load_i18n(self):
        self.assertIn('src="/i18n.js"', static.BEACON)

    def test_home_loads_i18n_before_app(self):
        self.assertLess(INDEX.index('src="i18n.js'), INDEX.index('src="app.js'))
        self.assertIn('class="lang-sel"', INDEX)

    def test_search_engines_stay_in_spanish(self):
        # La URL es la misma en todos los idiomas: los buscadores tienen que ver siempre el español
        self.assertRegex(I18N, r"BOT\.test\(navigator\.userAgent")
        self.assertIn("crawl", I18N)


if __name__ == "__main__":
    unittest.main()
