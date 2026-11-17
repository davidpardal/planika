import requests, time, json
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
B = "https://www.thesportsdb.com/api/v1/json/123/"
def get(u):
    try:
        r = requests.get(B + u, headers=H, timeout=30)
        return r.json() if r.status_code == 200 and r.text.strip().startswith("{") else {"_status": r.status_code}
    except Exception as e:
        return {"_err": str(e)[:100]}
for lid, name in (("4408", "ACB"), ("4534", "ASOBAL"), ("5486", "Liga Femenina"), ("4832", "Copa Rey bal")):
    d = get("eventsnextleague.php?id=%s" % lid); ev = d.get("events") or []
    print(name, "next:", len(ev), [(e["dateEvent"], e.get("strTime"), e["strHomeTeam"], e["strAwayTeam"]) for e in ev[:3]], d.get("_status", ""))
    time.sleep(2.2)
# eventsday por fechas: ¿cuántos partidos devuelve y con qué hora?
for lid, name in (("4408", "ACB"), ("4534", "ASOBAL")):
    for day in ("2026-11-21", "2026-11-22", "2026-11-28", "2026-11-29", "2026-12-05", "2026-12-06"):
        d = get("eventsday.php?d=%s&l=%s" % (day, lid)); ev = d.get("events") or []
        print(name, day, len(ev), [(e.get("strTime"), e["strHomeTeam"], e["strVenue"]) for e in ev][:5], d.get("_status", ""), d.get("_err", ""))
        time.sleep(2.2)
