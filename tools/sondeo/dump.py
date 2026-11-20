import requests, re, html, json
H = {"User-Agent": "Mozilla/5.0 (compatible; PlanikaBot/1.0; +https://planikaapp.com)", "Accept": "*/*"}
B = "https://jimmyjazzgasteiz.com"
def strip(t):
    t = re.sub(r"\[/?et_pb[^\]]*\]", " ", t)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()
r = requests.get(B + "/aviso-legal/", headers=H, timeout=40)
t = re.sub(r"<(script|style).*?</\1>", " ", r.text, flags=re.S)
s = strip(t); i = s.find("Queda prohibido"); print("LEGAL:", s[i-200:i+2500])
r = requests.get(B + "/wp-json/wp/v2/posts?per_page=100&categories=1336&_fields=id,link,title,excerpt,content,categories,featured_media", headers=H, timeout=60)
print("total", r.headers.get("x-wp-total"), r.headers.get("x-wp-totalpages"))
posts = r.json()
for p in posts[:40]:
    print("\n---", p["link"], p["categories"])
    print("T:", html.unescape(p["title"]["rendered"]), "| EX:", strip(p["excerpt"]["rendered"]))
    c = p["content"]["rendered"]
    print("TXT:", strip(c)[:500])
    print("URLS:", sorted(set(u for u in re.findall(r'(?:url|href|button_url|link_option_url)=["»″\']+([^"«″\' ]+)', c) if "http" in u))[:6])
