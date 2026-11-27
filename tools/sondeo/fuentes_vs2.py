"""Sondeo 2: marcado de los listados (AAIICC, ICAS, Visit València, valencia.es) para escribir los conectores."""
import re
from datetime import date

import requests

H = {"User-Agent": "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"}
S = requests.Session()
S.headers.update(H)


def get(u, **kw):
    r = S.get(u, timeout=40, **kw)
    print("[%s] %s len=%d %s" % (r.status_code, r.headers.get("content-type", "")[:30], len(r.content), r.url))
    return r


def section(t):
    print("\n" + "=" * 20, t, "=" * 20)


# --- AAIICC: un elemento del listado en bruto, nº de elementos por página, última página
section("AAIICC listado")
base = "https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia/actividades"
r = get(base)
t = r.text
links = re.findall(r'href="(/aaiicc/agendaculturaldeandalucia/evento/[^"]+)"', t)
print("enlaces a /evento/ en la pagina:", len(links), len(set(links)))
i = t.find(links[0]) if links else -1
print("HTML alrededor del primero:\n", re.sub(r"\n\s*\n", "\n", t[max(0, i - 2500):i + 2500]))
pages = re.findall(r'href="\?[^"]*page=(\d+)[^"]*"', t)
print("paginas enlazadas:", sorted(set(map(int, pages))))
for sel in re.findall(r'<select[^>]*name="(province|topic|audience)"[^>]*>(.*?)</select>', t, re.S):
    print("select", sel[0], re.findall(r'<option[^>]*value="([^"]*)"[^>]*>([^<]*)<', sel[1]))
# filtros: por provincia y fechas
for q in ("?province=41", "?province=Sevilla", "?date_from=2026-12-01&date_to=2026-12-31", "?page=40"):
    rr = get(base + q)
    m = re.search(r"(\d+)\s+Actividades", rr.text)
    print("   ", q, "->", m.group(0) if m else "-", "eventos en pagina:", len(set(re.findall(r'/agendaculturaldeandalucia/evento/[^"]+', rr.text))))

section("AAIICC ics de un evento")
r = get("https://www.juntadeandalucia.es/aaiicc/agendaculturaldeandalucia/activity/77169/ics-download")
print(r.text[:1500])

# --- ICAS: cuantos eventos futuros trae el ics y con que campos
section("ICAS ics")
r = get("https://icas.sevilla.org/agenda/ics_view")
ev = r.text.replace("\r\n ", "").split("BEGIN:VEVENT")[1:]
hoy = date.today().strftime("%Y%m%d")
fut = []
for e in ev:
    m = re.search(r"DTEND[^:]*:(\d{8})", e) or re.search(r"DTSTART[^:]*:(\d{8})", e)
    if m and m.group(1) >= hoy:
        fut.append(e)
print("VEVENT total", len(ev), "futuros/en curso", len(fut))
campos = {}
for e in fut:
    for k in re.findall(r"^([A-Z-]+)[;:]", e, re.M):
        campos[k] = campos.get(k, 0) + 1
print("campos:", campos)
for e in fut[:12]:
    s = re.search(r"SUMMARY:(.*)", e)
    a = re.search(r"DTSTART[^:]*:(\S+)", e)
    b = re.search(r"DTEND[^:]*:(\S+)", e)
    loc = re.search(r"LOCATION:(.*)", e)
    cat = re.search(r"CATEGORIES:(.*)", e)
    print("  -", a and a.group(1), b and b.group(1), "|", s and s.group(1)[:80], "|", loc and loc.group(1)[:60], "|", cat and cat.group(1)[:50])
print("muestra completa:\n", fut[-1][:1500] if fut else "-")

# --- Visit València: marcado de una tarjeta del listado mensual y JSON-LD de una ficha
section("Visit Valencia")
r = get("https://www.visitvalencia.com/agenda-valencia/agenda-mensual?date=2026-12")
t = r.text
cards = re.findall(r'href="(/agenda-valencia/[a-z0-9-]+)"', t)
print("fichas enlazadas:", len(cards), len(set(cards)))
i = t.find("Del 0")
print("HTML alrededor de 'Del':\n", re.sub(r"\n\s*\n", "\n", t[max(0, i - 2000):i + 800]))
for c in ["/agenda-valencia/comedia-musical-la-gran-cena-en-la-sala-russafa", "/agenda-valencia/musical-familiar-rudolph-en-roig-arena"]:
    rr = get("https://www.visitvalencia.com" + c)
    for ld in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', rr.text, re.S)[:2]:
        print("   ld+json:", re.sub(r"\s+", " ", ld)[:1500])
    txt = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", rr.text, flags=re.S))
    j = txt.find("Del ")
    print("   texto:", re.sub(r"\s+", " ", txt[j - 300:j + 900]))

# --- valencia.es: ¿de donde salen los eventos del listado?
section("valencia.es agenda")
r = get("https://www.valencia.es/cas/agenda-de-la-ciudad")
t = r.text
for pat in (r"https?://[^\"' ]*(?:agenda|calendar|evento)[^\"' ]*", r"/o/[^\"' ]+", r"(?:url|href)\s*[:=]\s*[\"']([^\"']*(?:agenda|json|ajax|resource)[^\"']*)"):
    print(pat, "->", sorted(set(re.findall(pat, t)))[:25])
i = t.find("Viernes 27")
print("HTML alrededor de la fecha:\n", re.sub(r"\n\s*\n", "\n", t[max(0, i - 1500):i + 3000]))
for q in ("?fch-inicio=01/12/2026&fch-fin=31/12/2026&selectCat=TODAS", "?selfechas=1&fch-inicio=2026-12-01&fch-fin=2026-12-31"):
    rr = get("https://www.valencia.es/cas/agenda-de-la-ciudad" + q)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", rr.text, flags=re.S)))
    j = txt.find("Aplicar rango")
    print("   ", q, txt[j:j + 900])
