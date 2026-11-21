"""Sondeo: cadena de redirecciones de las variantes del dominio y DNS."""
import socket, subprocess
import requests
for u in ["http://planikaapp.com/", "https://www.planikaapp.com/", "http://www.planikaapp.com/", "https://planikaapp.com/",
          "https://davidpardal.github.io/planika/", "https://www.planikaapp.com/p/bizkaia.html"]:
    try:
        r = requests.get(u, allow_redirects=False, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        print(u, "->", r.status_code, r.headers.get("location"), r.headers.get("server"))
    except Exception as e:
        print(u, "ERROR", e)
for h in ["planikaapp.com", "www.planikaapp.com"]:
    print(h, subprocess.run(["dig", "+short", h, "A"], capture_output=True, text=True).stdout.split())
    print(h, "CNAME", subprocess.run(["dig", "+short", h, "CNAME"], capture_output=True, text=True).stdout.split())
