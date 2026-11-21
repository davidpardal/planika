# -*- coding: utf-8 -*-
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planes import partidos  # noqa: E402

DP = "Deporte profesional (LaLiga, Euroliga, EuroCup)"


def m(title, start, source, time="", subtype="", pc="28", **kw):
    return dict({"title": title, "start": start, "time": time, "source": source, "subtype": subtype,
                 "province_code": pc, "category": "deporte"}, **kw)


class TestPartidos(unittest.TestCase):
    def test_teams(self):
        a = partidos.teams("Real Madrid - Club Joventut Badalona (Liga Endesa. Jornada 9)")
        self.assertEqual(a, (frozenset({"real", "madrid"}), frozenset({"joventut", "badalona"}), False))
        self.assertTrue(partidos.teams("Atlético de Madrid Femenino - RCD Espanyol (Liga F Moeve)")[2])
        self.assertIsNone(partidos.teams("Concierto de Navidad"))

    def test_sport(self):
        self.assertEqual(partidos.sport(m("Real Madrid - Leyma Coruña (Liga Endesa. Jornada 19)", "x", "e", subtype="Fútbol")), "basket")
        self.assertEqual(partidos.sport(m("UCAM Murcia CB - Casademont Zaragoza", "x", "e")), "basket")
        self.assertEqual(partidos.sport(m("Getafe CF - Elche CF", "x", "e", subtype="LaLiga")), "futbol")

    def test_same_match_other_day_and_names(self):
        off = m("Real Madrid CF - RC Celta de Vigo", "2026-11-21", DP, time="21:00", subtype="LaLiga", url="u1")
        tur = m("Real Madrid - RC Celta de Vigo (LALIGA EA SPORTS)", "2026-11-22", "esMADRID", subtype="Fútbol",
                venue="Estadio Bernabéu", lat=40.45, lon=-3.69, image="img")
        out, n = partidos.dedupe_matches([tur, off])
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["start"], "2026-11-21")          # fecha y hora del calendario oficial
        self.assertEqual(out[0]["time"], "21:00")
        self.assertEqual((out[0]["venue"], out[0]["lat"], out[0]["image"]), ("Estadio Bernabéu", 40.45, "img"))

    def test_sponsor_names(self):
        a = m("CB Murcia - Basket Zaragoza", "2026-11-21", "TheSportsDB (ligas españolas)", time="21:00", subtype="Liga Endesa ACB", pc="30")
        b = m("UCAM Murcia CB - Casademont Zaragoza", "2026-11-21", "Ayuntamiento de Murcia", time="21:00", pc="30", venue="Palacio")
        out, n = partidos.dedupe_matches([a, b])
        self.assertEqual(n, 1)
        self.assertEqual(out[0]["venue"], "Palacio")

    def test_not_merged(self):
        base = m("Real Madrid CF - Valencia CF", "2027-02-28", DP, subtype="LaLiga")
        cases = [
            m("Real Madrid - Valencia Basket (Liga Endesa. Jornada 24)", "2027-02-28", "esMADRID", subtype="Baloncesto"),  # otro deporte
            m("Real Madrid CF Femenino - Valencia CF Femenino (Liga F Moeve)", "2027-02-28", "esMADRID"),             # femenino
            m("Real Madrid - Valencia CF (LALIGA EA SPORTS)", "2027-03-05", "esMADRID", subtype="Fútbol"),            # 5 días
            m("Club Atlético de Madrid - Valencia CF", "2027-02-28", "esMADRID", subtype="Fútbol"),                   # otro local
            m("Real Madrid CF - Valencia CF", "2027-02-28", "esMADRID", subtype="LaLiga", pc="46"),                   # otra provincia
            m("Valencia CF - Real Madrid CF", "2027-02-28", "esMADRID", subtype="LaLiga"),                            # al revés
        ]
        for c in cases:
            self.assertEqual(partidos.dedupe_matches([dict(base), c])[1], 0, c["title"])
        # Dentro de una misma fuente no se une nada (dos partidos distintos)
        self.assertEqual(partidos.dedupe_matches([dict(base), dict(base, start="2027-03-01")])[1], 0)

    def test_unknown_sport_same_day_only(self):
        a = m("Bidasoa Irun - Granollers", "2026-11-21", "TheSportsDB (ligas españolas)", subtype="Liga Asobal", pc="20", time="18:00")
        b = m("Bidasoa - Granollers", "2026-11-21", "Ayuntamiento de Irun", pc="20")
        self.assertEqual(partidos.dedupe_matches([a, b])[1], 1)
        self.assertEqual(partidos.dedupe_matches([a, dict(b, start="2026-11-22")])[1], 0)


if __name__ == "__main__":
    unittest.main()
