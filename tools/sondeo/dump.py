import requests
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
for u in ["https://api-live.euroleague.net/v1/schedules?seasonCode=E2026",
          "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
          "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games",
          "https://api-live.euroleague.net/v1/teams?seasonCode=E2026"]:
    try:
        r = requests.get(u, headers=H, timeout=30)
        t = r.text
        print("==", r.status_code, r.headers.get("content-type"), len(t), u)
        i = t.find("<item") if "<item" in t else t.find("{")
        print(t[:900].replace("\n", " "))
        if "<item" in t: print("... item:", t[t.find("<item"):t.find("<item") + 900].replace("\n", " "))
    except Exception as e:
        print("[ERR]", u, type(e).__name__, str(e)[:150])
