"""Diagnóstico: por qué Nominatim no encuentra algunas salas (variantes de consulta)."""
import json, time, requests
UA = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"
S = requests.Session(); S.headers.update({"User-Agent": UA})
CASES = [
 ("Teatro María Luisa", "Mérida", (38.9161, -6.3437)),
 ("Centro Cívico Aldabe", "Vitoria-Gasteiz", (42.84672, -2.67164)),
 ("Biblioteca Foral de Bizkaia", "Bilbao", (43.25696, -2.92344)),
 ("Sala Rekalde", "Bilbao", (43.25696, -2.92344)),
 ("Kutxa Fundazioa Kubo", "Donostia / San Sebastián", (43.32073, -1.98445)),
 ("Kursaal", "Donostia / San Sebastián", (43.32073, -1.98445)),
 ("Fábrica Museo La Encartada", "Balmaseda", (43.1937, -3.1934)),
 ("Lekuona Fabrika", "Errenteria", (43.31275, -1.89963)),
 ("Ciudadela", "Pamplona / Iruña", (42.81764, -1.64854)),
 ("Palacio Real de la Almudaina", "Palma de Mallorca", (39.5696, 2.6502)),
 ("Casa de Cultura de Legazpi", "Legazpi", (43.05436, -2.33364)),
 ("Altxerri Jazz Club", "Donostia / San Sebastián", (43.32073, -1.98445)),
 ("Azkena", "Bilbao", (43.25696, -2.92344)),
 ("Centro Municipal de Castaños", "Bilbao", (43.25696, -2.92344)),
]
def get(params):
    time.sleep(1.1)
    r = S.get("https://nominatim.openstreetmap.org/search", params=dict(params, format="jsonv2", limit=4, countrycodes="es"), timeout=30)
    if r.status_code != 200:
        return "HTTP %d %s" % (r.status_code, r.text[:200])
    return [(x.get("name"), "%s=%s" % (x.get("category"), x.get("type")), round(float(x["lat"]), 4), round(float(x["lon"]), 4), round(x.get("importance") or 0, 3)) for x in r.json()]
for venue, city, (lat, lon) in CASES:
    vb = "%.5f,%.5f,%.5f,%.5f" % (lon - 0.12, lat + 0.09, lon + 0.12, lat - 0.09)
    print("\n##", venue, "|", city)
    print(" A bounded   :", get({"q": venue, "viewbox": vb, "bounded": 1}))
    print(" B q+ciudad  :", get({"q": "%s, %s" % (venue, city.split(" / ")[0])}))
    print(" C estructur.:", get({"amenity": venue, "city": city.split(" / ")[0]}))
