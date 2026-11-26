"""Dibuja los carruseles de Instagram (planes/instagram.py) y los deja en site/ig/ para guardarlos desde el móvil: una
carpeta por carrusel con las diapositivas en JPEG (1080×1350) y site/ig/index.html con el texto del post. Con --reels,
añade los reels de esa carpeta (la rama «reels» del repositorio: reels.json + vídeos MP4 y su portada en JPEG).

    python3 tools/instagram.py site [--reels /tmp/reels]

reels.json: {"reels": [{"file": "x.mp4", "poster": "x.jpg", "title": "…", "caption": "…", "kind": "viral|explicacion",
"made": "AAAA-MM-DD", "until": "AAAA-MM-DD" (opcional: a partir del día siguiente ya no sale)}]}

Necesita Playwright con Chromium. En el workflow diario corre después de guardar los datos y no bloquea la
publicación si falla. site/ig/ no va a git (.gitignore): se publica con la web y se rehace cada día.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from planes import instagram  # noqa: E402
from planes.util import iso, now_madrid, today  # noqa: E402


def load_events():
    with open(os.path.join(ROOT, "data", "events.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    return data["events"] if isinstance(data, dict) else data


def load_reels(src, out, now=None):
    """Copia a out/reels/ los reels vigentes de src y devuelve sus datos (rutas relativas a site/ig/), los más nuevos primero."""
    now = now or iso(today())
    try:
        with open(os.path.join(src, "reels.json"), encoding="utf-8") as fh:
            items = json.load(fh).get("reels") or []
    except (OSError, ValueError):
        return []
    os.makedirs(os.path.join(out, "reels"), exist_ok=True)
    keep = []
    for r in sorted(items, key=lambda r: r.get("made") or "", reverse=True):
        f = os.path.basename(str(r.get("file") or ""))
        if not f.endswith(".mp4") or not os.path.exists(os.path.join(src, f)) or (r.get("until") and r["until"] < now):
            continue
        shutil.copy(os.path.join(src, f), os.path.join(out, "reels", f))
        poster = os.path.basename(str(r.get("poster") or ""))
        if poster and os.path.exists(os.path.join(src, poster)):
            shutil.copy(os.path.join(src, poster), os.path.join(out, "reels", poster))
        else:
            poster = ""
        keep.append(dict(r, file="reels/" + f, poster=("reels/" + poster) if poster else ""))
    return keep


def main(site_dir, reels_dir=""):
    from playwright.sync_api import sync_playwright
    eds = instagram.editions(load_events(), today())
    out = os.path.join(site_dir, "ig")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    files = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for ed in eds:
            d = os.path.join(out, ed["slug"])
            os.makedirs(d, exist_ok=True)
            files[ed["slug"]] = []
            for k, doc in enumerate(instagram.slides(ed), 1):
                page.set_content(doc, wait_until="load")
                page.evaluate("document.fonts.ready")
                fn = "%s/%s-%d.jpg" % (ed["slug"], ed["slug"], k)
                page.screenshot(path=os.path.join(out, fn), type="jpeg", quality=90)
                files[ed["slug"]].append(fn)
            print("Instagram: %s, %d diapositivas" % (ed["city"], len(files[ed["slug"]])))
        browser.close()
    reels = load_reels(reels_dir, out) if reels_dir else []
    upd = now_madrid().strftime("%d/%m/%Y a las %H:%M")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(instagram.index_page(eds, files, upd, reels))
    print("Instagram: %d carruseles y %d reels en %s" % (len(eds), len(reels), out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("site", nargs="?", default=os.path.join(ROOT, "site"))
    ap.add_argument("--reels", default="", help="carpeta con reels.json y los vídeos (la rama «reels»)")
    args = ap.parse_args()
    main(args.site, args.reels)
