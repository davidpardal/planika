# -*- coding: utf-8 -*-
"""Coordenadas de las salas.

Algunas agendas no dan la ubicación de la sala sino la del municipio: la del Gobierno Vasco (Kulturklik)
sitúa los ~3.600 planes de Euskadi y Navarra en el centro de su localidad, así que en el mapa salen cientos
de planes apilados en un punto y «Cerca de mí» mide mal las distancias. Otras fuentes traen planes sin
coordenadas pero con sala.

Este módulo busca cada sala una sola vez en OpenStreetMap (Nominatim), guarda el resultado en
data/salas.json y, en cada descarga, cambia el punto del municipio por el de la sala. Respeta la política
de uso de Nominatim: una petición por segundo como máximo, agente identificado y resultados en caché
(también los no encontrados, que se reintentan pasado un tiempo). La primera carga se hace de una vez;
después, en cada ejecución diaria solo se buscan las salas nuevas, con un tope de tiempo.

Uso suelto:  python3 -m planes.salas --budget 2400   (busca las salas pendientes de data/events.json)
"""
import json
import math
import os
import re
import statistics
import time
from datetime import date, timedelta

from .util import UA, _session, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "salas.json")
URL = "https://nominatim.openstreetmap.org/search"
# Agendas que dan el centro del municipio en vez de la sala
IMPRECISE_SOURCES = {"Open Data Euskadi"}
CENTROID_MIN = 5        # 5+ salas distintas de una localidad en el mismo punto exacto -> es el centro del municipio
MAX_KM = 12             # una sala no puede estar más lejos que esto del punto de referencia de su localidad
BOX = (0.09, 0.12)      # caja de búsqueda alrededor de la referencia (grados de latitud y longitud, ~10 km)
RETRY_DAYS = 45         # una sala no encontrada se vuelve a buscar pasado este tiempo
PAUSE = 1.1             # segundos entre peticiones (política de Nominatim: máximo 1 por segundo)
# Qué tipo de lugar devuelve Nominatim: una sala de verdad puntúa más que un bar con el mismo nombre
# (el bar «Kursaal» frente al palacio Kursaal). Calles, paradas, montes o barrios no sirven.
_VENUE = {"amenity": {"theatre", "arts_centre", "cinema", "library", "community_centre", "conference_centre", "events_venue",
                      "music_venue", "nightclub", "exhibition_centre", "social_centre", "townhall", "university", "college",
                      "place_of_worship", "public_bookcase", "planetarium", "concert_hall", "auditorium", "school", "casino"},
          "tourism": {"museum", "gallery", "attraction", "theme_park", "zoo", "aquarium"},
          "leisure": {"stadium", "sports_centre", "sports_hall", "ice_rink", "bullring", "water_park", "dance"},
          "historic": {"castle", "monument", "building", "manor", "monastery", "church", "archaeological_site", "city_gate",
                       "fort", "palace", "tower", "ruins", "aqueduct", "theatre", "amphitheatre"}, "building": {"public", "civic", "yes", "church", "cathedral", "palace", "castle", "university",
                                         "college", "school", "train_station", "stadium", "sports_hall", "theatre", "cinema",
                                         "museum", "monastery", "industrial", "commercial", "hall"},
          "office": {"government"}}
_OPEN = {"leisure": {"park", "garden", "nature_reserve", "marina", "pitch"}, "place": {"square"},
         "landuse": {"cemetery", "retail", "recreation_ground"}, "man_made": {"lighthouse", "tower"},
         "tourism": {"artwork", "viewpoint"}, "historic": {"memorial"}}
_MINOR = {"amenity": {"bar", "pub", "cafe", "restaurant", "fast_food", "biergarten", "ice_cream"},
          "shop": None, "tourism": {"hotel", "hostel", "guest_house", "information"}, "craft": None}
_SCORE = ((_VENUE, 2.0), (_OPEN, 1.0), (_MINOR, 0.5))
# Palabras del nombre que dicen el tipo de sala y la clase de OpenStreetMap que le corresponde
_HINTS = (({"teatro", "antzokia", "auditorio", "auditorium", "teatre"}, {"theatre", "arts_centre", "concert_hall", "auditorium"}),
          ({"biblioteca", "liburutegia", "biblioteka", "bibliotheque", "biblioteques"}, {"library"}),
          ({"museo", "museoa", "museu", "museum"}, {"museum", "gallery"}),
          ({"cine", "cines", "zinema", "zinemak", "cinema"}, {"cinema"}),
          ({"estadio", "estadi", "arena", "pabellon", "polideportivo", "frontoia", "fronton", "kiroldegia"},
           {"stadium", "sports_centre", "sports_hall"}),
          ({"civico", "gizarte", "kultur", "cultura", "kulturgunea", "kulturetxea", "etxea"}, {"community_centre", "arts_centre", "social_centre", "library"}),
          ({"galeria", "aretoa", "erakusketa"}, {"gallery", "arts_centre", "museum"}),
          ({"iglesia", "eliza", "ermita", "parroquia", "basilica", "catedral", "santuario", "convento", "monasterio"}, {"place_of_worship"}),
          ({"escuela", "eskola", "ikastola", "colegio", "ikastetxea", "instituto", "facultad", "universidad", "campus"},
           {"school", "college", "university"}))
# Tipos que solo valen si el nombre de la sala los nombra (comparten nombre con el barrio o el santo)
_HINT_TYPES = {"library", "place_of_worship", "school", "college", "university"}
# Palabras que no distinguen una sala (para buscar solo por lo propio: «Sala Rekalde» -> «Rekalde»)
_GENERIC_WORDS = set("""teatro antzokia auditorio aretoa sala salon centro civico gizarte etxea kultur kulturgunea casa cultura
    biblioteca liburutegia municipal udal museo museoa fabrica palacio jauregia real club jazz fundazioa fundacion espacio
    gunea de del la el las los y en the plaza enparantza calle kalea parque parkea polideportivo frontoia cine cines zinema
    galeria escuela eskola ikastola iglesia eliza ermita torre dorrea foral nuevo nueva viejo vieja herri andra mari
    zentroa kz kultur aula magna grados facultad sala gela eraikina interpretacion""".split())
_PAREN = re.compile(r"\s*[\(\[]([^)\]]*)[\)\]]\s*")
# Nombres que no son una sala concreta
_GENERIC = {"", "online", "en linea", "varios", "varios espacios", "varios lugares", "diversos espacios", "por determinar",
            "consultar", "otros", "calle", "calles", "centro", "casco historico", "casco viejo", "todo el municipio",
            "lugar por determinar", "lugar a determinar", "por confirmar", "a confirmar", "diversos lugares", "varias sedes"}


def key(province_code, city, venue):
    return "%s|%s|%s" % (province_code or "", norm(city), norm(venue))


def load(path=PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh).get("salas") or {}
    except (OSError, ValueError):
        return {}


def save(cache, path=PATH):
    """Una sala por línea y ordenadas: los cambios diarios se leen bien en el historial."""
    lines = ["%s: %s" % (json.dumps(k, ensure_ascii=False), json.dumps(cache[k], ensure_ascii=False, sort_keys=True))
             for k in sorted(cache)]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write('{"_info": "Coordenadas de salas buscadas en OpenStreetMap (Nominatim, datos © colaboradores de '
                 'OpenStreetMap, ODbL). Se genera solo; ok=false: no encontrada.",\n"salas": {\n')
        fh.write(",\n".join(lines))
        fh.write("\n}}\n")


def km(a, b):
    """Distancia aproximada en km entre (lat, lon)."""
    dy = (a[0] - b[0]) * 111.2
    dx = (a[1] - b[1]) * 111.2 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def _pt(e):
    if e.get("lat") is None or e.get("lon") is None:
        return None
    try:
        return (float(e["lat"]), float(e["lon"]))
    except (TypeError, ValueError):
        return None


SPAIN = (27.4, 44.0, -18.5, 4.6)  # lat y lon mínimas y máximas (con Canarias)


def _in_spain(lat, lon):
    return SPAIN[0] < lat < SPAIN[1] and SPAIN[2] < lon < SPAIN[3]


def fix_coords(events):
    """Coordenadas imposibles de algunas agendas: latitud y longitud al revés (se giran) o en otro sistema
    (UTM, se quitan para buscar la sala). Devuelve cuántos planes se han tocado."""
    n = 0
    for e in events:
        p = _pt(e)
        if p is None or _in_spain(*p):
            continue
        if _in_spain(p[1], p[0]):
            e["lat"], e["lon"] = p[1], p[0]
        else:
            e["lat"] = e["lon"] = None
        n += 1
    return n


def usable_venue(venue):
    v = norm(venue)
    return len(v) >= 4 and v not in _GENERIC


def imprecise(events):
    """Índices de los planes con sala cuya posición no es la de la sala: sin coordenadas, de una agenda que
    da el centro del municipio, o en un punto que comparten 5+ salas distintas de la misma localidad."""
    salas_en = {}
    for e in events:
        p = _pt(e)
        if p and e.get("venue"):
            salas_en.setdefault((e["province_code"], norm(e.get("city")), round(p[0], 5), round(p[1], 5)), set()).add(norm(e["venue"]))
    out = []
    for i, e in enumerate(events):
        if not usable_venue(e.get("venue")):
            continue
        p = _pt(e)
        if (p is None or e.get("source") in IMPRECISE_SOURCES
                or len(salas_en.get((e["province_code"], norm(e.get("city")), round(p[0], 5), round(p[1], 5)), ())) >= CENTROID_MIN):
            out.append(i)
    return out


def references(events):
    """Punto de referencia de cada localidad (mediana de sus planes con coordenadas): sirve para buscar la
    sala cerca y para descartar resultados de otro sitio con el mismo nombre."""
    pts = {}
    for e in events:
        p = _pt(e)
        if p:
            pts.setdefault((e["province_code"], norm(e.get("city"))), []).append(p)
    return {k: (statistics.median(a for a, _ in v), statistics.median(b for _, b in v)) for k, v in pts.items()}


def apply(events, cache=None):
    """Pone en su sala los planes situados en el centro del municipio (o sin coordenadas) cuya sala ya está
    localizada (y corrige coordenadas imposibles). Devuelve cuántos planes se han tocado."""
    cache = load() if cache is None else cache
    n = fix_coords(events)
    for i in imprecise(events):
        e = events[i]
        hit = cache.get(key(e["province_code"], e.get("city"), e["venue"]))
        if hit and hit.get("ok"):
            if (e.get("lat"), e.get("lon")) != (hit["lat"], hit["lon"]):
                e["lat"], e["lon"] = hit["lat"], hit["lon"]
                n += 1
    return n


def pending(events, cache, today=None):
    """Salas por buscar: [(clave, ciudad, sala, referencia)], las de más planes primero."""
    today = today or date.today()
    refs = references(events)
    count, info = {}, {}
    for i in imprecise(events):
        e = events[i]
        k = key(e["province_code"], e.get("city"), e["venue"])
        hit = cache.get(k)
        if hit and (hit.get("ok") or hit.get("checked", "") > (today - timedelta(days=RETRY_DAYS)).isoformat()):
            continue
        ref = refs.get((e["province_code"], norm(e.get("city"))))
        if not ref:
            continue  # sin referencia no hay forma de comprobar que el resultado es de esa localidad
        count[k] = count.get(k, 0) + 1
        info.setdefault(k, (e.get("city"), e["venue"], ref))
    return [(k,) + info[k] for k in sorted(count, key=lambda k: (-count[k], k))]


def queries(venue):
    """Formas de buscar una sala: el nombre tal cual, sin lo que va entre paréntesis y, si el paréntesis
    dice cuál es (Biblioteca de Bilbao (Ibaialde)), la primera palabra con él."""
    v = re.sub(r"\s+", " ", venue).strip(" .,-")
    out = [_PAREN.sub(" ", v).strip()]
    m = _PAREN.search(v)
    if m and m.group(1).strip():
        inside = m.group(1).strip()
        out.append("%s %s" % (v.split()[0], inside))
    # «Teatro Barakaldo - Barakaldo Antzokia»: cada mitad por separado
    for part in re.split(r"\s+[-–|/]\s+", out[0]):
        if part != out[0] and len(norm(part)) >= 4:
            out.append(part.strip())
    seen, res = set(), []
    for q in out:
        if norm(q) and norm(q) not in seen and usable_venue(q):
            seen.add(norm(q))
            res.append(q)
    return res[:3]


def _score(r, venue_words):
    cls, typ = r.get("category") or r.get("class"), r.get("type")
    base = 0.0
    for table, pts in _SCORE:
        if cls in table and (table[cls] is None or typ in table[cls]):
            base = pts
            break
    if not base:
        return 0.0
    for words, types in _HINTS:
        if venue_words & words and typ in types:
            base += 1.0
            break
    return base + 2 * float(r.get("importance") or 0)


def plan(venue, city=""):
    """Consultas en orden: las formas del nombre y, al final, solo sus palabras propias (en OpenStreetMap la
    sala suele llamarse distinto: «Palacio Real de la Almudaina» es «Palau de l'Almudaina»)."""
    out = [(q, False) for q in queries(venue)]
    own = distinctive(venue, city)
    if own and len(own) <= 3 and " ".join(sorted(own)) not in {norm(q) for q, _ in out}:
        out.append((" ".join(w for w in norm(_PAREN.sub(" ", venue)).split() if w in own), True))
    return out[:4]


def pick(results, ref, venue="", strict=False, city=""):
    """El mejor resultado: un lugar concreto (no una calle, una parada ni un barrio), cerca de la referencia y,
    entre varios, el que más parece una sala. Con strict (búsqueda solo por las palabras propias) se exige
    que sea una sala o un edificio y que su nombre lleve esas palabras."""
    words = set(norm(venue).split())
    best = None
    for r in results or []:
        sc = _score(r, words)
        if sc <= 0:
            continue
        try:
            p = (round(float(r["lat"]), 6), round(float(r["lon"]), 6))
        except (KeyError, TypeError, ValueError):
            continue
        d = km(p, ref)
        # Una sala lejos del centro puede ser buena (un estadio); un bar con el mismo nombre a 10 km, no
        if d > (MAX_KM if sc >= 2 else 4):
            continue
        if strict:
            name = set(norm(r.get("name") or r.get("display_name", "").split(",")[0]).split())
            if sc < 2 or not distinctive(venue, city) <= name or not hint_ok(words, r.get("type")):
                continue
        if best is None or sc > best[0]:
            cls = r.get("category") or r.get("class")
            best = (sc, {"lat": p[0], "lon": p[1], "osm": "%s/%s" % (r.get("osm_type", ""), r.get("osm_id", "")),
                         "tipo": "%s=%s" % (cls, r.get("type")), "nombre": (r.get("name") or "")[:80]})
    return best[1] if best else None


def hint_ok(venue_words, typ):
    """En la búsqueda por palabras propias, una biblioteca, una iglesia o un colegio solo valen si el nombre lo dice («Sala Rekalde» no es
    la biblioteca de Rekalde; «Cine Andra Mari» no es la iglesia de Andra Mari)."""
    if typ not in _HINT_TYPES:
        return True
    return any(venue_words & words and typ in types for words, types in _HINTS)


def distinctive(venue, city=""):
    """Las palabras propias del nombre de la sala, sin las genéricas, las de la localidad ni lo que va entre paréntesis."""
    skip = _GENERIC_WORDS | set(norm(city).split())
    return {w for w in norm(_PAREN.sub(" ", venue or "")).split() if len(w) >= 4 and w not in skip and not w.isdigit()}


def _search(q, ref):
    lat, lon = ref
    params = {"q": q, "format": "jsonv2", "countrycodes": "es", "limit": 5, "bounded": 1, "accept-language": "es",
              "viewbox": "%.5f,%.5f,%.5f,%.5f" % (lon - BOX[1], lat + BOX[0], lon + BOX[1], lat - BOX[0])}
    r = _session.get(URL, params=params, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=(10, 30))
    if r.status_code in (403, 429) or r.status_code >= 500:
        raise RuntimeError("Nominatim ha respondido %d: se para la búsqueda" % r.status_code)
    if r.status_code != 200:
        return []  # consulta que no le gusta (400): sin resultado, se sigue con la siguiente
    return r.json()


def geocode(events, log, cache=None, budget=90.0, search=_search, sleep=time.sleep, today=None, path=PATH):
    """Busca las salas pendientes durante como mucho `budget` segundos y guarda la caché.
    Devuelve (encontradas, no encontradas, pendientes que quedan)."""
    cache = load(path) if cache is None else cache
    today = today or date.today()
    fix_coords(events)
    todo = pending(events, cache, today)
    started, found, missed, done = time.time(), 0, 0, 0
    last = 0.0
    try:
        for k, city, venue, ref in todo:
            if time.time() - started > budget:
                break
            hit = None
            for q, strict in plan(venue, city):
                wait = PAUSE - (time.time() - last)
                if wait > 0:
                    sleep(wait)
                last = time.time()
                hit = pick(search(q, ref), ref, venue, strict, city)
                if hit:
                    hit["q"] = q
                    break
            done += 1
            if hit:
                cache[k] = dict(hit, ok=True, checked=today.isoformat())
                found += 1
            else:
                cache[k] = {"ok": False, "checked": today.isoformat()}
                missed += 1
    except Exception as exc:  # noqa: BLE001 - un fallo del buscador no debe tumbar la descarga
        log("Salas: búsqueda interrumpida (%s: %s)" % (exc.__class__.__name__, str(exc)[:120]))
    if done:
        save(cache, path)
    return found, missed, len(todo) - done


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Busca en OpenStreetMap las salas pendientes de data/events.json")
    ap.add_argument("--events", default=os.path.join(ROOT, "data", "events.json"))
    ap.add_argument("--budget", type=float, default=90.0, help="segundos como máximo")
    args = ap.parse_args()
    with open(args.events, encoding="utf-8") as fh:
        events = json.load(fh)["events"]
    found, missed, left = geocode(events, lambda m: print(m, flush=True), budget=args.budget)
    print("Salas: %d encontradas, %d no encontradas, %d pendientes" % (found, missed, left), flush=True)


if __name__ == "__main__":
    main()
