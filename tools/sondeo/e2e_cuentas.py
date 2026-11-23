"""Prueba de extremo a extremo de las cuentas contra el Supabase real (usuario de prueba desechable)."""
import json, os, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

SB = "https://jygalcbsfrntavhqahpx.supabase.co"
KEY = "sb_publishable_rBesGXlh8l4CO2oFtJOqjw_wkS03xl4"
BASE = "http://localhost:8765/"
EMAIL, PW = os.environ["E2E_EMAIL"], os.environ["E2E_PW"]
fails = []


def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        fails.append(msg)


def call(method, path, body=None, token=None, prefer=None):
    h = {"apikey": KEY, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if prefer:
        h["Prefer"] = prefer
    req = urllib.request.Request(SB + path, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def login():
    st, s = call("POST", "/auth/v1/token?grant_type=password", {"email": EMAIL, "password": PW})
    return st, s


def favs(tok):
    st, rows = call("GET", "/rest/v1/favorites?select=event_id", token=tok)
    return set(r["event_id"] for r in rows) if st == 200 else ("ERR", st, rows)


def ls(page, k):
    return page.evaluate("k => localStorage.getItem(k)", k)


st, r = call("POST", "/rest/v1/rpc/ping", {})
check(st == 200, "ping anónimo responde (%s %s)" % (st, r))
st, r = call("GET", "/rest/v1/favorites?select=event_id")
check(st in (401, 403), "anónimo no puede leer favoritos (%s)" % st)
st, r = call("POST", "/rest/v1/rpc/delete_my_account", {})
check(st in (401, 403), "anónimo no puede llamar a delete_my_account (%s)" % st)

st, s = login()
check(st == 200 and s.get("access_token"), "login de prueba con contraseña (%s)" % st)
if fails:
    sys.exit(1)

with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script("try{localStorage.setItem('planika_analytics_consent','rejected')}catch(e){}")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    page.goto(BASE + "?cuentas=1"); page.wait_for_selector("article.card")
    ids = page.eval_on_selector_all("#list article.card .fav.corner", "els => els.slice(0,6).map(e => e.dataset.fav)")
    page.evaluate("ids => localStorage.setItem('planika_favs', JSON.stringify(ids))", ids[:2])

    # Vuelta del enlace del email (mismo formato que manda Supabase)
    page.goto(BASE + "#access_token=%s&expires_at=%d&expires_in=%d&refresh_token=%s&token_type=bearer&type=magiclink"
              % (s["access_token"], s["expires_at"], s["expires_in"], s["refresh_token"]))
    page.wait_for_selector("article.card")
    page.wait_for_function("!localStorage.getItem('planika_fav_ops') && localStorage.getItem('planika_sesion')", timeout=15000)
    page.wait_for_timeout(1500)
    tok = json.loads(ls(page, "planika_sesion"))["access_token"]
    check(favs(tok) == set(ids[:2]), "al entrar, los favoritos del dispositivo están en la cuenta")
    check(page.inner_text("#accountLabel") == "Mi cuenta", "botón «Mi cuenta»")

    page.click('#list .fav.corner[data-fav="%s"]' % ids[2])
    page.wait_for_function("!localStorage.getItem('planika_fav_ops')", timeout=10000)
    check(favs(tok) == set(ids[:3]), "marcar favorito lo guarda en la cuenta")
    page.click('#list .fav.corner[data-fav="%s"]' % ids[0])
    page.wait_for_function("!localStorage.getItem('planika_fav_ops')", timeout=10000)
    check(favs(tok) == set(ids[1:3]), "quitar favorito lo borra de la cuenta")
    st, r = call("POST", "/rest/v1/favorites", [{"event_id": ids[1]}], token=tok, prefer="resolution=ignore-duplicates,return=minimal")
    check(st in (200, 201) and favs(tok) == set(ids[1:3]), "repetir un favorito no falla ni duplica (%s %s)" % (st, r))
    st, r = call("POST", "/rest/v1/favorites", [{"event_id": "x", "user_id": "00000000-0000-0000-0000-000000000001"}], token=tok)
    check(st in (401, 403), "no puede escribir favoritos de otro usuario (%s)" % st)

    page.fill("#where", "Bilbao"); page.wait_for_timeout(300); page.keyboard.press("Enter"); page.wait_for_timeout(500)
    where = page.input_value("#where")
    page.click("#accountBtn"); page.click("#accPlaceSet")
    page.wait_for_function("document.getElementById('accMsg').textContent.indexOf('Guardado') === 0", timeout=10000)
    st, r = call("GET", "/rest/v1/profiles?select=place", token=tok)
    check(st == 200 and r and r[0]["place"] and r[0]["place"].split("|")[2] == where, "«Mi ciudad» guardada (%s → %s)" % (where, r))
    page.click("#accPlaceDel"); page.wait_for_timeout(1500)
    st, r = call("GET", "/rest/v1/profiles?select=place", token=tok)
    check(st == 200 and r and r[0]["place"] is None, "quitar ciudad (%s)" % r)
    page.click("#accPlaceSet"); page.wait_for_timeout(1500); page.click("#accountClose")

    # Otro «dispositivo»: contexto nuevo con el enlace de otro inicio de sesión
    st, s2 = login()
    ctx2 = br.new_context(); ctx2.add_init_script("try{localStorage.setItem('planika_analytics_consent','rejected')}catch(e){}")
    p2 = ctx2.new_page()
    p2.goto(BASE + "#access_token=%s&expires_in=3600&refresh_token=%s&token_type=bearer&type=magiclink" % (s2["access_token"], s2["refresh_token"]))
    p2.wait_for_selector("article.card")
    p2.wait_for_function("document.getElementById('favCount').textContent === '2'", timeout=15000)
    p2.wait_for_timeout(1000)
    check(p2.input_value("#where") == where, "en otro dispositivo aparecen los favoritos y la ciudad (%s)" % p2.input_value("#where"))

    # Token caducado → se renueva
    old = json.loads(ls(page, "planika_sesion"))
    old["expires_at"] = 1
    page.evaluate("s => localStorage.setItem('planika_sesion', JSON.stringify(s))", old)
    page.reload(); page.wait_for_selector("article.card"); page.wait_for_timeout(3000)
    new = json.loads(ls(page, "planika_sesion") or "null")
    check(new and new["refresh_token"] != old["refresh_token"] and new["expires_at"] > time.time(), "renueva la sesión caducada")
    check(page.inner_text("#favCount") == "2", "favoritos tras renovar")

    # Salir en el segundo dispositivo revoca solo su sesión
    s2r = json.loads(p2.evaluate("() => localStorage.getItem('planika_sesion')"))["refresh_token"]
    p2.click("#accountBtn"); p2.click("#accLogout")
    p2.wait_for_function("document.getElementById('accountLabel').textContent === 'Entrar'", timeout=10000)
    p2.wait_for_timeout(1500)
    st, r = call("POST", "/auth/v1/token?grant_type=refresh_token", {"refresh_token": s2r})
    check(st >= 400, "tras «Salir», su sesión ya no sirve (%s)" % st)
    check(favs(json.loads(ls(page, "planika_sesion"))["access_token"]) == set(ids[1:3]), "el primer dispositivo sigue con sesión")
    ctx2.close()

    # Borrar la cuenta
    page.click("#accountBtn"); page.click("#accDel"); page.click("#accDelYes")
    page.wait_for_function("document.getElementById('accMsg').textContent.indexOf('Cuenta borrada') === 0", timeout=15000)
    st, r = login()
    check(st >= 400, "tras borrar la cuenta ya no se puede entrar (%s)" % st)
    check(len(json.loads(ls(page, "planika_favs"))) == 2, "los favoritos siguen en el dispositivo")
    check(not errors, "sin errores en la consola: %s" % errors[:3])
    br.close()

print("\n%d fallos" % len(fails))
sys.exit(1 if fails else 0)
