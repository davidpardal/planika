# -*- coding: utf-8 -*-
"""Crea en Brevo la campaña del boletín «Planes del finde» con la edición de esta semana.

Lo lanza .github/workflows/boletin.yml los jueves. Necesita (en GitHub, nunca en el código):
  secreto  BREVO_API_KEY        clave de API de Brevo (SMTP & API -> API Keys)
  variable BREVO_LIST_ID        número de la lista de suscriptores
  variable BREVO_SENDER_EMAIL   remitente verificado en Brevo (y BREVO_SENDER_NAME, por defecto «Planika»)
  variable BOLETIN_ENVIO        «auto» para enviarla sola; cualquier otro valor la deja como borrador
Sin la clave no hace nada. Por defecto deja la campaña en borrador para revisarla y enviarla desde Brevo.
"""
import json
import os
import sys
from datetime import date, timedelta

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.brevo.com/v3"


def this_friday(t0):
    return t0 + timedelta(days=(4 - t0.weekday()) % 7)


def main(env=os.environ, session=requests, t0=None):
    key = env.get("BREVO_API_KEY")
    if not key:
        print("Boletín: sin BREVO_API_KEY; no se crea ninguna campaña.")
        return 0
    t0 = t0 or date.today()
    with open(os.path.join(ROOT, "site", "boletin", "email.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    with open(os.path.join(ROOT, "site", "boletin", "email.html"), encoding="utf-8") as fh:
        body = fh.read()
    if meta.get("edicion") != this_friday(t0).isoformat():
        print("Boletín: la edición guardada (%s) no es la de este finde; no se envía nada." % meta.get("edicion"))
        return 1
    if not env.get("BREVO_LIST_ID") or not env.get("BREVO_SENDER_EMAIL"):
        print("Boletín: faltan las variables BREVO_LIST_ID o BREVO_SENDER_EMAIL.")
        return 1
    headers = {"api-key": key, "accept": "application/json", "content-type": "application/json"}
    payload = {
        "name": "Planes del finde %s" % meta["edicion"],
        "subject": meta["asunto"],
        "previewText": meta.get("vista_previa", ""),
        "sender": {"name": env.get("BREVO_SENDER_NAME") or "Planika", "email": env["BREVO_SENDER_EMAIL"]},
        "htmlContent": body,
        "recipients": {"listIds": [int(env["BREVO_LIST_ID"])]},
    }
    r = session.post(API + "/emailCampaigns", headers=headers, data=json.dumps(payload), timeout=60)
    if r.status_code >= 300:
        print("Boletín: Brevo ha respondido %d al crear la campaña: %s" % (r.status_code, r.text[:300]))
        return 1
    cid = r.json().get("id")
    print("Boletín: campaña %s creada en Brevo (%s)." % (cid, meta["asunto"]))
    if (env.get("BOLETIN_ENVIO") or "").strip().lower() != "auto":
        print("Queda en borrador: revísala y envíala desde Brevo (Campañas).")
        return 0
    r = session.post("%s/emailCampaigns/%s/sendNow" % (API, cid), headers=headers, timeout=60)
    if r.status_code >= 300:
        print("Boletín: Brevo ha respondido %d al enviar: %s" % (r.status_code, r.text[:300]))
        return 1
    print("Boletín enviado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
