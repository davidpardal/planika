#!/usr/bin/env python3
"""Publica en Instagram (@planikaapp) un carrusel o un reel de planikaapp.com/ig con la API oficial de Instagram
(Business Login for Instagram, permiso instagram_business_content_publish).

Lo lanza el botón «Publicar en Instagram» de /ig a través del workflow instagram.yml, que solo puede disparar quien
tenga permiso de escritura en el repositorio. La clave de Instagram está en el secreto INSTAGRAM_TOKEN.

    python3 tools/ig_publicar.py carrusel <slug> --texto-archivo pie.txt [--resultado r.txt]
    python3 tools/ig_publicar.py reel reels/<archivo>.mp4 --texto-archivo pie.txt [--resultado r.txt]
    python3 tools/ig_publicar.py comprobar [--nuevo ruta]   # ¿sigue valiendo la clave? (y la renueva 60 días)

Las imágenes y los vídeos se publican desde su dirección pública (Instagram los descarga de ahí). No se publica dos
veces lo mismo: si la primera línea del pie coincide con un post de los últimos 3 días, se para.
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

SITE = "https://planikaapp.com/ig/"
API = "https://graph.instagram.com/v26.0/"
REFRESH = "https://graph.instagram.com/refresh_access_token"
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REEL = re.compile(r"^reels/[a-z0-9]+(-[a-z0-9]+)*\.mp4$")
MAX_SLIDES = 10      # máximo de Instagram por carrusel
MAX_CAPTION = 2200   # máximo de Instagram por pie


class IgError(Exception):
    pass


class Api:
    def __init__(self, token, session=None, sleep=time.sleep):
        self.token, self.s, self.sleep = token, session or requests.Session(), sleep

    def _check(self, r):
        try:
            j = r.json()
        except ValueError:
            j = {}
        if r.status_code >= 400 or "error" in j:
            msg = (j.get("error") or {}).get("message") or "HTTP %s" % r.status_code
            raise IgError(msg)  # el mensaje de Meta nunca incluye la clave
        return j

    def get(self, path, **params):
        params["access_token"] = self.token
        return self._check(self.s.get(API + path, params=params, timeout=60))

    def post(self, path, **data):
        data["access_token"] = self.token
        return self._check(self.s.post(API + path, data=data, timeout=120))

    def wait(self, cid, tries=40, every=6):
        """Espera a que Instagram termine de procesar el contenedor (los vídeos tardan un poco)."""
        for _ in range(tries):
            st = self.get(cid, fields="status_code").get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise IgError("Instagram no ha podido procesar el archivo (%s)" % st)
            self.sleep(every)
        raise IgError("Instagram tarda demasiado en procesar el archivo; prueba otra vez en unos minutos")


def slide_urls(slug, session=None):
    """Las diapositivas publicadas hoy del carrusel: slug/slug-1.jpg, slug-2.jpg… hasta la primera que falte."""
    if not SLUG.match(slug or ""):
        raise IgError("carrusel no válido: %r" % slug)
    s = session or requests.Session()
    urls = []
    for k in range(1, MAX_SLIDES + 1):
        u = "%s%s/%s-%d.jpg" % (SITE, slug, slug, k)
        if s.head(u, timeout=30, allow_redirects=True).status_code != 200:
            break
        urls.append(u)
    if len(urls) < 2:
        raise IgError("el carrusel %s no está hoy en /ig (¿ha cambiado la agenda?)" % slug)
    return urls


def reel_url(path, session=None):
    if not REEL.match(path or ""):
        raise IgError("reel no válido: %r" % path)
    u = SITE + path
    if (session or requests.Session()).head(u, timeout=30, allow_redirects=True).status_code != 200:
        raise IgError("el reel %s no está en /ig" % path)
    return u


def already_posted(api, uid, caption, now=None):
    """¿Hay un post de los últimos 3 días con la misma primera línea? (evita publicar dos veces con dos toques)"""
    first = (caption or "").strip().split("\n")[0].strip()
    if not first:
        return False
    now = now or datetime.now(timezone.utc)
    for m in api.get("%s/media" % uid, fields="caption,timestamp", limit=12).get("data") or []:
        ts = datetime.strptime(m.get("timestamp", "1970-01-01T00:00:00+0000"), "%Y-%m-%dT%H:%M:%S%z")
        if now - ts < timedelta(days=3) and (m.get("caption") or "").strip().split("\n")[0].strip() == first:
            return True
    return False


def publish_carousel(api, uid, urls, caption):
    kids = [api.post("%s/media" % uid, image_url=u, is_carousel_item="true")["id"] for u in urls]
    for k in kids:
        api.wait(k, tries=20, every=3)
    cid = api.post("%s/media" % uid, media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    api.wait(cid, tries=20, every=3)
    return api.post("%s/media_publish" % uid, creation_id=cid)["id"]


def publish_reel(api, uid, url, caption):
    cid = api.post("%s/media" % uid, media_type="REELS", video_url=url, caption=caption, share_to_feed="true")["id"]
    api.wait(cid)
    return api.post("%s/media_publish" % uid, creation_id=cid)["id"]


def publish(api, kind, path, caption, session=None):
    """Devuelve (enlace del post, cuenta)."""
    caption = (caption or "").strip()
    if len(caption) > MAX_CAPTION:
        raise IgError("el pie tiene %d caracteres (Instagram admite %d)" % (len(caption), MAX_CAPTION))
    me = api.get("me", fields="user_id,username")
    uid = me.get("user_id") or me.get("id")
    if kind == "carrusel":
        urls = slide_urls(path, session)
        if already_posted(api, uid, caption):
            raise IgError("ya está publicado (un post de los últimos 3 días empieza igual)")
        mid = publish_carousel(api, uid, urls, caption)
    elif kind == "reel":
        url = reel_url(path, session)
        if already_posted(api, uid, caption):
            raise IgError("ya está publicado (un post de los últimos 3 días empieza igual)")
        mid = publish_reel(api, uid, url, caption)
    else:
        raise IgError("tipo no válido: %r" % kind)
    link = api.get(mid, fields="permalink").get("permalink") or "https://www.instagram.com/%s/" % me.get("username", "")
    return link, me.get("username", "")


def check_and_refresh(token, session=None):
    """La clave sigue valiendo (GET me; si no, IgError) y se renueva otros 60 días. Devuelve la clave nueva, o "" si
    Instagram no la renueva hoy (una clave de menos de 24 horas no se puede renovar todavía)."""
    s = session or requests.Session()
    Api(token, s).get("me", fields="user_id,username")
    try:
        j = Api(token, s)._check(s.get(REFRESH, params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=60))
    except (IgError, requests.RequestException):
        return ""
    return j.get("access_token") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tipo", choices=["carrusel", "reel", "comprobar"])
    ap.add_argument("ruta", nargs="?", default="")
    ap.add_argument("--texto-archivo", default="")
    ap.add_argument("--resultado", default="", help="aquí se escribe una línea con el resultado (para el aviso)")
    ap.add_argument("--nuevo", default="", help="comprobar: archivo donde dejar la clave renovada")
    args = ap.parse_args()
    token = os.environ.get("INSTAGRAM_TOKEN", "").strip()

    def out(line):
        if token:
            line = line.replace(token, "***")  # un error de red puede llevar la URL con la clave
        print(line)
        if args.resultado:
            with open(args.resultado, "w", encoding="utf-8") as fh:
                fh.write(line + "\n")

    if not token:
        out("❌ Instagram sin configurar: falta el secreto INSTAGRAM_TOKEN")
        return 1
    try:
        if args.tipo == "comprobar":
            new = check_and_refresh(token)
            if args.nuevo and new:
                with open(args.nuevo, "w", encoding="utf-8") as fh:
                    fh.write(new)
            out("✅ La clave de Instagram vale" + (" y se ha renovado" if new else " (hoy no se ha renovado)"))
            return 0
        caption = open(args.texto_archivo, encoding="utf-8").read() if args.texto_archivo else ""
        link, user = publish(Api(token), args.tipo, args.ruta, caption)
        out("✅ Publicado en @%s: %s" % (user, link))
        return 0
    except (IgError, requests.RequestException) as exc:
        out("❌ No se ha publicado %s: %s" % (args.ruta or "", exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
