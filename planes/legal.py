# -*- coding: utf-8 -*-
"""Páginas legales: privacidad y cookies, y aviso legal.

Los datos del titular (nombre, NIF, domicilio, correo) se leen de data/legal.json; los que falten no se
muestran. Sin correo, el contacto es la página de incidencias del repositorio en GitHub.
"""
import html
import json
import os

from . import static

SITE_URL = static.SITE_URL
UPDATED = "25 de noviembre de 2026"
CONTACT_FALLBACK = "https://github.com/davidpardal/planika/issues"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "legal.json")


def load_config(path=CONFIG_PATH):
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError):
        cfg = {}
    return {k: str(cfg.get(k) or "").strip() for k in ("nombre", "nif", "domicilio", "email")}


def _contact(cfg):
    if cfg["email"]:
        m = html.escape(cfg["email"], quote=True)
        return '<a href="mailto:%s">%s</a>' % (m, m)
    return '<a href="%s" target="_blank" rel="noopener">la página de incidencias de Planika en GitHub</a>' % CONTACT_FALLBACK


def _holder(cfg):
    rows = []
    if cfg["nombre"]:
        rows.append("<li><strong>Titular:</strong> %s</li>" % html.escape(cfg["nombre"]))
    if cfg["nif"]:
        rows.append("<li><strong>NIF:</strong> %s</li>" % html.escape(cfg["nif"]))
    if cfg["domicilio"]:
        rows.append("<li><strong>Domicilio:</strong> %s</li>" % html.escape(cfg["domicilio"]))
    rows.append("<li><strong>Contacto:</strong> %s</li>" % _contact(cfg))
    return "<ul>%s</ul>" % "".join(rows)


_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s · Planika</title><meta name="description" content="%(desc)s">
<meta name="robots" content="index,follow">
<link rel="canonical" href="%(site)s/%(file)s">
<meta property="og:site_name" content="Planika"><meta property="og:locale" content="es_ES"><meta property="og:type" content="website">
<meta property="og:title" content="%(title)s · Planika"><meta property="og:description" content="%(desc)s"><meta property="og:url" content="%(site)s/%(file)s">
<meta property="og:image" content="%(site)s/og.jpg"><meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="styles.css"><link rel="icon" href="icon.svg" type="image/svg+xml">
%(analytics)s
</head><body>
<header class="hero"><div class="wrap"><div class="brand"><a href="./" style="text-decoration:none;color:inherit"><h1>Planika</h1></a></div>
<p class="tagline">%(title)s</p>
<p class="meta"><a class="btn primary" href="./">Explorar Planika</a> &nbsp; Última actualización: %(updated)s</p></div></header>
<main class="wrap legal" style="max-width:820px;line-height:1.6">
%(body)s
<nav class="foot" style="border:0;margin-top:30px"><h2>Otras páginas</h2><p><a href="./">Inicio</a> · <a href="privacidad.html">Privacidad y cookies</a> · <a href="privacidad.html#cookies" data-privacy-settings>Configurar cookies</a> · <a href="aviso-legal.html">Aviso legal</a> · <a href="https://www.instagram.com/planikaapp/" target="_blank" rel="noopener">Instagram</a> · <a href="fuentes.html">Fuentes de datos</a></p></nav>
</main></body></html>
"""


def privacy_page(cfg=None):
    cfg = cfg if cfg is not None else load_config()
    body = """
<h2>Resumen</h2>
<p>Planika no tiene cuentas de usuario ni muestra publicidad. Google Analytics 4 (GA4) se utiliza únicamente si aceptas las cookies de analítica. Si las rechazas, GA4 no se carga. Puedes cambiar tu decisión desde el enlace «Configurar cookies» del pie de cada página.</p>

<h2>Responsable</h2>
%(holder)s

<h2>Qué datos se tratan y para qué</h2>
<h3>Visitas (analítica)</h3>
<p>Usamos Google Analytics 4 (Google Ireland Limited) para obtener estadísticas de uso, como páginas consultadas, interacciones, información técnica del navegador y datos aproximados de ubicación. GA4 puede utilizar cookies y tecnologías similares y transmitir datos a Google. La analítica permanece desactivada hasta que das tu consentimiento mediante el panel de privacidad. Base jurídica: consentimiento (art. 6.1.a del RGPD y normativa aplicable sobre almacenamiento o acceso a información en el dispositivo). Si rechazas, la etiqueta de GA4 no se carga. Puedes retirar o cambiar el consentimiento en cualquier momento con el enlace «Configurar cookies» del pie de cada página.</p>
<h3>Favoritos</h3>
<p>Cuando marcas un plan como favorito, Planika lo guarda en el almacenamiento local de tu navegador (clave <code>planika_favs</code>). Se queda en tu dispositivo, no se envía a ningún servidor y puedes borrarlo en cualquier momento limpiando los datos del sitio. Es un almacenamiento necesario para una función que tú pides, por lo que no requiere consentimiento.</p>
<h3>Ubicación («Cerca de mí»)</h3>
<p>Solo si pulsas el botón, el navegador te pide permiso y Planika usa tu posición para ordenar los planes por distancia. El cálculo se hace en tu dispositivo: la posición no se envía ni se guarda.</p>
<h3>Formulario para organizadores</h3>
<p>Si publicas un evento con el formulario (Google Forms), recibimos los datos que escribes: los del evento y los de contacto. Los usamos para revisar y publicar tu evento y para ponernos en contacto contigo si hace falta. Base jurídica: tu consentimiento y la gestión de tu solicitud (art. 6.1.a y 6.1.b). Los conservamos mientras sean necesarios para esa gestión. Google trata los datos del formulario como proveedor del servicio.</p>
<h3>Servidores y contenidos de terceros</h3>
<p>La web se aloja en GitHub Pages, que registra datos técnicos de conexión (como la dirección IP) para prestar el servicio. Las imágenes de algunos planes se cargan directamente desde los servidores de sus organizadores o fuentes, que pueden ver tu dirección IP al pedirlas. Si compartes un plan de «Mis planes» con un enlace, ese plan (su nombre, los planes que incluye con su día y sus notas) se guarda en Supabase, con servidores en la Unión Europea (Irlanda), para que quien tenga el enlace pueda verlo y editarlo; Supabase registra datos técnicos de conexión (como la dirección IP) y los planes compartidos se borran 6 meses después de su último cambio. Los enlaces a webs de organizadores, entradas y Google Calendar llevan a sitios con sus propias políticas.</p>

<h2 id="cookies">Cookies</h2>
<p><a href="#cookies" data-privacy-settings><strong>Cambiar mis preferencias de cookies</strong></a></p>
<p>GA4 solo se carga después de aceptar las cookies de analítica. Según la configuración y el navegador, Google Analytics puede instalar cookies como <code>_ga</code> y <code>_ga_*</code> para distinguir usuarios y sesiones. Si rechazas, la etiqueta no se carga. La elección se guarda en el almacenamiento local del navegador para recordar tu decisión; este almacenamiento se utiliza para conservar la preferencia. Puedes cambiarla o retirar el consentimiento desde el enlace «Configurar cookies» del pie de cada página.</p>

<h2>Tus derechos</h2>
<p>Puedes pedir acceso, rectificación, supresión, oposición, limitación del tratamiento y portabilidad de tus datos escribiendo a %(contact)s. Si crees que no hemos tratado bien tus datos, puedes reclamar ante la <a href="https://www.aepd.es" target="_blank" rel="noopener">Agencia Española de Protección de Datos</a>.</p>

<h2>Cambios</h2>
<p>Si cambia algo de lo anterior (por ejemplo, si se añaden cuentas de usuario o se activan servicios de pago), actualizaremos esta página y su fecha.</p>
""" % dict(holder=_holder(cfg), contact=_contact(cfg))
    return _PAGE % dict(title="Privacidad y cookies", file="privacidad.html", site=SITE_URL, analytics=static.BEACON,
                        desc="Qué datos trata Planika, cómo utiliza Google Analytics 4 con consentimiento y cómo ejercer tus derechos.",
                        updated=UPDATED, body=body)


def legal_page(cfg=None):
    cfg = cfg if cfg is not None else load_config()
    body = """
<h2>Titular del sitio</h2>
<p>Planika (%(site)s) es un servicio informativo gratuito. Datos del titular, según el artículo 10 de la Ley 34/2002 de servicios de la sociedad de la información (LSSI):</p>
%(holder)s

<h2>Qué es Planika</h2>
<p>Planika reúne en un solo sitio la agenda de planes de ocio de España (conciertos, teatro, fiestas, deporte, planes con niños y más) a partir de portales de datos abiertos, agendas oficiales y APIs públicas, más una selección de visitas permanentes. No organiza los eventos ni vende entradas: cada plan enlaza a la web de su organizador o de su venta oficial. La lista de fuentes está en la página de <a href="fuentes.html">fuentes de datos</a>.</p>

<h2>Exactitud de la información</h2>
<p>La información de cada plan (fechas, horarios, precios, lugar) procede de terceros y puede cambiar o contener errores. Comprueba siempre los datos en la web del organizador antes de desplazarte o comprar. Planika no se hace responsable de cancelaciones, cambios ni de las compras que hagas en webs externas.</p>

<h2>Propiedad intelectual y reutilización</h2>
<p>Los textos, imágenes y datos de cada plan pertenecen a sus organizadores o a las fuentes que los publican, y se reutilizan citando la fuente en cada ficha. El diseño, el código y la agrupación de datos de Planika son de su titular; el código está publicado en <a href="https://github.com/davidpardal/planika" target="_blank" rel="noopener">GitHub</a>. Si eres titular de un contenido y quieres que se corrija o se retire, escríbenos a %(contact)s y lo atenderemos lo antes posible.</p>

<h2>Eventos enviados por organizadores</h2>
<p>Quien envía un evento declara que tiene derecho a difundir su información e imágenes. Planika puede rechazar o retirar cualquier envío que sea inexacto, engañoso o ilegal. Si en el futuro se ofrecen destacados u otros servicios de pago, se identificarán claramente como tales.</p>

<h2>Enlaces externos</h2>
<p>Planika enlaza a webs de terceros sobre cuyo contenido no tiene control ni responsabilidad.</p>

<h2>Protección de datos</h2>
<p>Consulta la página de <a href="privacidad.html">privacidad y cookies</a>.</p>

<h2>Legislación aplicable</h2>
<p>Este sitio se rige por la legislación española. Para cualquier conflicto serán competentes los juzgados y tribunales que correspondan conforme a la normativa vigente, sin perjuicio de los derechos que la ley reconozca a los consumidores.</p>
""" % dict(site=SITE_URL, holder=_holder(cfg), contact=_contact(cfg))
    return _PAGE % dict(title="Aviso legal", file="aviso-legal.html", site=SITE_URL, analytics=static.BEACON,
                        desc="Titular, condiciones de uso y responsabilidad de Planika, agenda gratuita de planes de ocio en España.",
                        updated=UPDATED, body=body)


def write_legal_pages(site_dir, cfg=None):
    cfg = cfg if cfg is not None else load_config()
    out = []
    for fn, render in (("privacidad.html", privacy_page), ("aviso-legal.html", legal_page)):
        with open(os.path.join(site_dir, fn), "w", encoding="utf-8") as fh:
            fh.write(render(cfg))
        out.append(fn)
    return out
