import requests, json
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
def get(u):
    try:
        r = requests.get(u, headers=H, timeout=30); return r
    except Exception as e:
        print("[ERR]", u, type(e).__name__, str(e)[:120]); return None
print("##### openfootball")
for u in ["https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.1.json",
          "https://raw.githubusercontent.com/openfootball/football.json/master/2025-26/es.1.json",
          "https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.2.json"]:
    r = get(u)
    if r is None: continue
    print(r.status_code, u, len(r.content))
    if r.status_code == 200:
        d = r.json(); ms = d.get("matches", []); print(" name:", d.get("name"), "matches:", len(ms))
        print(" first:", ms[:1]); print(" last:", ms[-1:])
        print(" sample dates >= 2026-11-17:", [m["date"] for m in ms if m["date"] >= "2026-11-17"][:5])
print("##### thesportsdb")
B = "https://www.thesportsdb.com/api/v1/json/123/"
for lid, s in (("4335", "2026-2027"), ("4408", "2026-2027"), ("4400", "2026-2027")):
    r = get(B + "eventsseason.php?id=%s&s=%s" % (lid, s))
    if r is None: continue
    d = r.json() if r.status_code == 200 and r.text.strip().startswith("{") else {}
    ev = d.get("events") or []
    print(lid, s, r.status_code, "events:", len(ev), [e["dateEvent"] for e in ev[:2]], [e["dateEvent"] for e in ev[-2:]])
for sport in ("Soccer", "Basketball", "Handball", "Volleyball", "Futsal", "Rugby", "Ice Hockey", "Motorsport", "Cycling", "Tennis"):
    r = get(B + "search_all_leagues.php?c=Spain&s=" + sport.replace(" ", "%20"))
    if r is None or r.status_code != 200: print(sport, getattr(r, "status_code", None)); continue
    try: ls = r.json().get("countries") or []
    except Exception: ls = []
    print(sport, [(l["idLeague"], l["strLeague"]) for l in ls])
print("##### espn / otros")
for u in ["https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard?dates=20261120-20261130",
          "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard",
          "https://api.football-data.org/v4/competitions/PD/matches"]:
    r = get(u)
    if r is not None: print(r.status_code, u, r.text[:200].replace("\n", " "))
