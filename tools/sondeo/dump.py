import requests, re
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
d = requests.get("https://raw.githubusercontent.com/openfootball/football.json/master/2026-27/es.1.json", headers=H, timeout=30).json()
print("LALIGA", sorted({m["team1"] for m in d["matches"]}))
print("times missing:", sum(1 for m in d["matches"] if "time" not in m), "of", len(d["matches"]))
for comp in ("E", "U"):
    t = requests.get("https://api-live.euroleague.net/v1/teams?seasonCode=%s2026" % comp, headers=H, timeout=30).text
    for m in re.finditer(r'<club code="(\w+)".*?<name>(.*?)</name>.*?<countrycode>(\w+)</countrycode>.*?<arena name="(.*?)"', t, re.S):
        if m.group(3) == "ESP": print(comp, m.group(1), "|", m.group(2), "|", m.group(4))
    s = requests.get("https://api-live.euroleague.net/v1/schedules?seasonCode=%s2026" % comp, headers=H, timeout=30).text
    print(comp, "games:", s.count("<item>"), "dates:", re.findall(r"<date>(.*?)</date>", s)[:2], "played:", s.count("<played>true"))
