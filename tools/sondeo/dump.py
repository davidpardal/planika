import sys, requests, re
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
def show(u, n=2500, find=None):
    r = requests.get(u, headers=H, timeout=25)
    t = r.text
    if find:
        i = t.find(find); t = t[max(0,i-200):] if i >= 0 else t
    print("=====", u, r.status_code, len(t)); print(t[:n]); print()
show("https://www.vitoria-gasteiz.org/we001/was/rssAction.do?idioma=es&accion=actividadesCuadroMando&claveTema=&claveArea=38", 3500, "<item")
show("https://www.vitoria-gasteiz.org/we001/was/rssAction.do?accion=calendario&idCalendario=246&idioma=es&claveArea=", 1200, "<item")
import json
for u in ["https://opendata.vlci.valencia.es/api/3/action/package_search?q=eventos&rows=15",
          "https://opendata.aragon.es/ckan/api/3/action/package_search?q=agenda&rows=15",
          "https://datosabiertos.navarra.es/api/3/action/package_search?q=agenda&rows=15"]:
    d = requests.get(u, headers=H, timeout=25).json()
    print("=====", u)
    for p in d["result"]["results"]:
        print(" -", p.get("title"), "| mod:", p.get("metadata_modified"))
        for r in p.get("resources", [])[:6]:
            print("     ", r.get("format"), r.get("url"))
