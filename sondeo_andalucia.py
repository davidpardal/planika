import time, requests, json, socket
URL = "https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json"
UA = "Planika/1.0 (+https://planikaapp.com; agregador de agendas publicas)"
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
def probe(label, headers, stream=False, url=URL):
    t = time.time()
    try:
        r = requests.get(url, headers=headers, timeout=(15, 120), stream=stream)
        n = len(r.content)
        try:
            data = r.json(); cnt = len(data) if isinstance(data, list) else type(data).__name__
        except Exception as e:
            cnt = "nojson " + repr(r.content[:120])
        print("RES", label, r.status_code, n, "bytes", cnt, "items", "%.1fs" % (time.time() - t), dict((k, v) for k, v in r.headers.items() if k.lower() in ("content-encoding", "content-type", "server", "content-length", "transfer-encoding")), flush=True)
    except Exception as e:
        print("RES", label, "ERROR", type(e).__name__, str(e)[:200], "%.1fs" % (time.time() - t), flush=True)
print("IP", socket.gethostbyname("datos.juntadeandalucia.es"))
for i in range(2):
    probe("planika-identity-%d" % i, {"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Accept-Encoding": "identity"})
    probe("planika-gzip-%d" % i, {"User-Agent": UA, "Accept": "application/json, text/plain, */*", "Accept-Encoding": "gzip, deflate"})
    probe("browser-gzip-%d" % i, {"User-Agent": BROWSER, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"})
probe("paged", {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}, url="https://datos.juntadeandalucia.es/api/v0/schedule/all?format=json&limit=50")
probe("home", {"User-Agent": BROWSER}, url="https://datos.juntadeandalucia.es/api/v0/")
