# -*- coding: utf-8 -*-
"""Clasificación asistida por Claude (opcional). Se activa con ANTHROPIC_API_KEY y PLANIKA_LLM=1.

Solo se envían los eventos cuya categoría es dudosa ("otros") o todos con PLANIKA_LLM=all.
Los resultados se guardan en data/llm_cache.json para no repetir peticiones noche tras noche.
"""
import json
import os
import re

from .classify import CATEGORIES, CATEGORY_KEYS
from .util import DATA_DIR

CACHE = os.path.join(DATA_DIR, "llm_cache.json")
MODEL = os.environ.get("PLANIKA_LLM_MODEL", "claude-opus-5")
BATCH = 40

SYSTEM = (
    "Eres el clasificador de Planika, una agenda de planes de ocio en España. "
    "Para cada evento devuelve la categoría más adecuada entre estas claves: "
    + ", ".join("%s (%s)" % (k, n) for k, n, _ in CATEGORIES)
    + ". Además, si el título no está en castellano, da una traducción breve al castellano en 'titulo_es'; "
    "si ya está en castellano deja 'titulo_es' vacío. Responde únicamente con un array JSON de objetos "
    "{\"id\": ..., \"categoria\": ..., \"titulo_es\": ...}, sin texto adicional."
)


def _load_cache():
    try:
        with open(CACHE, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def enrich(events, log, mode="otros"):
    """Reclasifica (y traduce títulos) con Claude. Devuelve el número de eventos modificados."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log("LLM: omitido (sin ANTHROPIC_API_KEY)")
        return 0
    try:
        import anthropic  # importación tardía: dependencia opcional
    except ImportError:
        log("LLM: omitido (pip install anthropic)")
        return 0
    cache = _load_cache()
    todo = [e for e in events if (mode == "all" or e["category"] == "otros") and e["id"] not in cache]
    client = anthropic.Anthropic()
    done = 0
    for i in range(0, len(todo), BATCH):
        chunk = todo[i:i + BATCH]
        payload = [{"id": e["id"], "titulo": e["title"], "tipo_fuente": e.get("subtype", ""),
                    "descripcion": (e.get("description") or "")[:160]} for e in chunk]
        try:
            text = _ask(client, json.dumps(payload, ensure_ascii=False))
            answers = json.loads(re.search(r"\[.*\]", text, re.S).group(0))
        except Exception as exc:  # noqa: BLE001
            log("LLM: error en lote %d: %s" % (i // BATCH, exc))
            continue
        for a in answers:
            cat = a.get("categoria")
            if a.get("id") and cat in CATEGORY_KEYS:
                cache[a["id"]] = {"category": cat, "title_es": (a.get("titulo_es") or "").strip()[:200]}
                done += 1
    changed = 0
    for e in events:
        c = cache.get(e["id"])
        if not c:
            continue
        if c["category"] != e["category"]:
            e["category"] = c["category"]
            changed += 1
        if c.get("title_es") and c["title_es"].lower() != e["title"].lower():
            e["title_es"] = c["title_es"]
    try:
        with open(CACHE, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, ensure_ascii=False, separators=(",", ":"))
    except OSError:
        pass
    log("LLM: %d eventos consultados a %s, %d categorías cambiadas" % (done, MODEL, changed))
    return changed


def _ask(client, user_text):
    kwargs = dict(model=MODEL, max_tokens=4096, system=SYSTEM, messages=[{"role": "user", "content": user_text}])
    try:
        # Reserva automática en otro modelo si el principal declina la petición
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-06-01"],
                                           fallbacks=[{"model": "claude-opus-4-8"}], **kwargs)
    except TypeError:  # SDK anterior sin soporte de fallbacks
        resp = client.messages.create(**kwargs)
    if getattr(resp, "stop_reason", "") == "refusal":
        raise RuntimeError("la petición fue rechazada por el modelo")
    return "".join(getattr(b, "text", "") for b in resp.content)
