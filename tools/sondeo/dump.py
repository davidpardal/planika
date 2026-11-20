import requests, json
K = "90fc021a491df512d0db3e97830567b5"
for u in ("https://planikaapp.com/%s.txt" % K, "https://www.planikaapp.com/%s.txt" % K):
    try:
        r = requests.get(u, timeout=30, allow_redirects=True)
        print(u, "->", r.url, r.status_code, r.headers.get("content-type"), repr(r.text[:80]))
    except Exception as e: print(u, "ERR", e)
body = {"host": "planikaapp.com", "key": K, "keyLocation": "https://planikaapp.com/%s.txt" % K, "urlList": ["https://planikaapp.com/planes-hoy.html"]}
for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow", "https://yandex.com/indexnow"):
    try:
        r = requests.post(ep, json=body, timeout=30)
        print(ep, r.status_code, r.reason, repr(r.text[:300]))
    except Exception as e: print(ep, "ERR", e)
