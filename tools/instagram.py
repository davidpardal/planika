"""Dibuja los carruseles de Instagram del finde (planes/instagram.py) y los deja en site/ig/ para guardarlos desde el
móvil: una carpeta por ciudad con las diapositivas en JPEG (1080×1350) y site/ig/index.html con el texto del post.

    python3 tools/instagram.py site

Necesita Playwright con Chromium. En el workflow diario corre después de guardar los datos y no bloquea la
publicación si falla. site/ig/ no va a git (.gitignore): se publica con la web y se rehace cada día.
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from planes import instagram  # noqa: E402
from planes.util import now_madrid, today  # noqa: E402


def load_events():
    with open(os.path.join(ROOT, "data", "events.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    return data["events"] if isinstance(data, dict) else data


def main(site_dir):
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
    upd = now_madrid().strftime("%d/%m/%Y a las %H:%M")
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(instagram.index_page(eds, files, upd))
    print("Instagram: %d carruseles en %s" % (len(eds), out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "site"))
