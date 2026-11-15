import sys, requests
URLS = [l.strip() for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0)"}
for u in URLS:
    try:
        r = requests.get(u, headers=H, timeout=25)
        t = r.text[:350].replace("\n", " ")
        print(f"[{r.status_code}] {r.headers.get('content-type','')[:30]} len={len(r.content)} {u}\n    {t}\n")
    except Exception as e:
        print(f"[ERR] {u}\n    {type(e).__name__}: {str(e)[:150]}\n")
