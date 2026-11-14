# -*- coding: utf-8 -*-
"""Ajuntament de Barcelona: agenda cultural de la ciudad (JSON completo del catálogo Open Data BCN)."""
from .classify import classify
from .util import event, http_json, iso, parse_ics, strip_html, today

BROWSER = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "application/json,*/*;q=0.8", "Accept-Language": "ca,es;q=0.9"}
DATASTORE = "https://opendata-ajuntament.barcelona.cat/data/api/3/action/datastore_search"
RESOURCE = "3abb2414-1ee0-446e-9c25-380e938adb73"

NAME = "Ajuntament de Barcelona"
URL = ("https://opendata-ajuntament.barcelona.cat/data/dataset/2767159c-1c98-46b8-a686-2b25b40cb053/"
       "resource/59b9c807-f6c1-4c10-ac51-1ace65485079/download")
HOME = "https://www.barcelona.cat/ca/que-pots-fer-a-bcn/agenda"


def fetch(log):
    t0 = iso(today())
    try:
        data = http_json(URL, headers=BROWSER, timeout=(20, 300))
    except Exception as exc:  # noqa: BLE001 - el portal bloquea a veces la descarga completa; se usa la API
        log("%s: descarga completa no disponible (%s); se usa la API datastore" % (NAME, exc.__class__.__name__))
        return _fetch_datastore(log, t0)
    out = []
    for r in data:
        if r.get("status") != "published":
            continue
        start = (r.get("start_date") or "")[:10]
        end = (r.get("end_date") or "")[:10] or start
        if not start or end < t0:
            continue
        addr = next((a for a in (r.get("addresses") or []) if a.get("main_address")), (r.get("addresses") or [{}])[0])
        lat = lon = None
        try:
            geo = ((addr.get("location_4326_latlon") or {}).get("geometries") or [{}])[0].get("coordinates")
            if geo:
                lon, lat = geo[0], geo[1]
        except (AttributeError, IndexError, TypeError):
            pass
        web = tickets = ""
        for v in r.get("values") or []:
            name = (v.get("attribute_name") or "").lower()
            val = v.get("url_value") or v.get("value") or ""
            if not str(val).startswith("http"):
                continue
            if "entrades" in name and not tickets:
                tickets = val
            elif name in ("web", "web inscripcions", "web preinscripcions") and not web:
                web = val
        cls = [c.get("name") for c in (r.get("classifications_data") or [])]
        sec = [c.get("name") for c in (r.get("secondary_filters_data") or [])]
        cls_clean = [c for c in cls if c and not c.startswith("Activitats")]
        tick = [t.get("name") for t in (r.get("tickets_data") or [])]
        free = True if "Lliure" in tick else (False if "Pagament" in tick else None)
        img = (r.get("image_data") or {}).get("image_optimized") or (r.get("image_data") or {}).get("image") or ""
        # Sesiones concretas (el campo ical trae un VEVENT por sesión)
        sessions = []
        tm = ""
        if r.get("ical"):
            for v in parse_ics(r["ical"]):
                d = (v.get("DTSTART") or "")[:8]
                if len(d) == 8:
                    sessions.append("%s-%s-%s" % (d[:4], d[4:6], d[6:8]))
                    if not tm and "T" in (v.get("DTSTART") or ""):
                        hh = v["DTSTART"].split("T")[1][:4]
                        tm = "%s:%s" % (hh[:2], hh[2:]) if hh[:2] != "00" else ""
        sessions = sorted({s for s in sessions if s >= t0})
        title = r.get("name") or ""
        ev = event(
            NAME, r.get("register_id"), title, start, end=end, time=tm,
            description=r.get("body"), subtype=(cls_clean[0] if cls_clean else (sec[0] if sec else "")),
            category=classify(cls_clean + sec, title, strip_html(r.get("body"), 200)),
            province_code="08", city=(addr.get("town") or "Barcelona").title(),
            venue=addr.get("place"), address=" ".join(str(x) for x in (addr.get("address_name"), addr.get("street_number_1")) if x),
            lat=lat, lon=lon, free=free, price="Gratuït" if free else "", url=web or (addr.get("related_entity_data") or {}).get("canonical_url") or HOME,
            tickets_url=tickets, image=img,
        )
        if ev:
            if len(sessions) >= 2 and len(sessions) <= 60:
                ev["sessions"] = sessions
            out.append(ev)
    log("%s: %d eventos" % (NAME, len(out)))
    return out


def _fetch_datastore(log, t0):
    """Versión reducida (sin descripción, imagen ni enlaces) a partir de la API datastore de CKAN."""
    out = []
    offset = 0
    while True:
        d = http_json(DATASTORE, params={"resource_id": RESOURCE, "limit": 5000, "offset": offset}, headers=BROWSER, timeout=(20, 180))
        recs = (d.get("result") or {}).get("records") or []
        for r in recs:
            start = (r.get("start_date") or "")[:10]
            end = (r.get("end_date") or "")[:10] or start
            if not start or end < t0:
                continue
            title = r.get("name") or ""
            sec = [x.strip() for x in (r.get("secondary_filters_name") or "").split(",") if x.strip()]
            ev = event(
                NAME, str(r.get("register_id") or "").strip("\ufeff"), title, start, end=end,
                subtype=sec[0] if sec else "", category=classify(sec, title),
                province_code="08", city=(r.get("addresses_town") or "Barcelona").title(),
                address=" ".join(str(x) for x in (r.get("addresses_road_name"), r.get("addresses_start_street_number")) if x),
                lat=r.get("geo_epgs_4326_lat"), lon=r.get("geo_epgs_4326_lon"), url=HOME,
            )
            if ev:
                out.append(ev)
        offset += len(recs)
        if len(recs) < 5000 or offset >= int((d.get("result") or {}).get("total") or 0):
            break
    log("%s: %d eventos (API datastore)" % (NAME, len(out)))
    return out
