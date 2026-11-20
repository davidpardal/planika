# SEO técnico de Planika

Cómo se generan las páginas para buscadores y por qué. El código está en `planes/publish.py` (hubs),
`planes/static.py` (fichas), `planes/seo.py` (indexabilidad, sitemaps y robots.txt) y `tools/seo_check.py`
(comprobación del sitio generado, que también corre en el workflow sin bloquear la publicación).

## Arquitectura

| Página | URL | Intención |
|---|---|---|
| Portada (app) | `/` | planes en España |
| Hoy, fin de semana, gratis | `/planes-hoy.html`, `/planes-este-fin-de-semana.html`, `/planes-gratis.html` | qué hacer hoy / este finde / gratis |
| Festivales | `/festivales.html` (solo con 20 o más) | festivales en España |
| Puente de diciembre | `/puente-diciembre.html` (indexable del 1 de octubre al último día del puente, con 20 o más planes) | planes para el puente de diciembre |
| Tipo de plan | `/t/<tipo>.html` | conciertos, teatro, exposiciones, planes con niños… en España |
| Provincia | `/p/<provincia>.html` + `/p/<provincia>-pagina-N.html` | qué hacer en X (listado completo, 150 por página) |
| Provincia: finde, gratis | `/p/<provincia>-fin-de-semana.html`, `-gratis.html` (3 o más planes) | planes este finde / gratis en X |
| Provincia × tipo | `/p/<provincia>-<tipo>.html` (5 o más planes) | conciertos en X, teatro en X… |
| Ciudad | `/c/<ciudad>.html` (40 o más planes con fecha y sin provincia del mismo nombre) | qué hacer en Bilbao, Donostia, Vitoria, Getxo, Mérida… |
| Ciudad: finde, gratis | `/c/<ciudad>-fin-de-semana.html`, `-gratis.html` (3 o más planes) | qué hacer este finde en Bilbao / planes gratis en Vitoria |
| Ciudad × tipo | `/c/<ciudad>-<tipo>.html` (5 o más planes; sin «otros») | conciertos en Bilbao, teatro en Vitoria… |
| Ficha | `/e/<titulo>-<id>.html` | el plan concreto |

Cada hub tiene título, H1 y descripción propios, un texto de introducción calculado con los datos de la página
(cuántos planes, de qué tipo, en qué localidades y lugares, cuántos gratis), migas de pan visibles y en
JSON-LD (`BreadcrumbList`) y un `ItemList` con los primeros planes. Todas las fichas quedan a 3 clics de la portada.

La gente busca por ciudad («qué hacer en Bilbao este fin de semana»), no por provincia: por eso cada ciudad con
página propia tiene sus subpáginas de intención, enlazadas desde su ciudad, desde la misma página de la provincia
(finde, gratis, tipo), desde el tipo de plan en España y desde las páginas nacionales de finde y gratis.
Las páginas principales de provincia y ciudad llevan el mes en el título («Qué hacer en Bilbao: planes y eventos
(noviembre 2026)»).

## Títulos de las fichas

`plan · fecha corta · lugar`, en unos 62 caracteres más « · Planika». El nombre va primero y no se recorta por
debajo de 40 caracteres: es lo que se busca y lo que distingue un plan de otro. Si no cabe todo, se recorta antes el
lugar. Si dos planes acabarían con el mismo título, primero se usa el nombre entero (cursos que solo se distinguen
por el nivel del final) y, si aún coinciden, la sala en vez de la ciudad.

Las URL con parámetros (`/?e=`, `/?prov=`…) son la app con filtros; tienen canonical a `/` y `robots.txt`
no las deja rastrear (`Disallow: /?`), como recomienda Google para la navegación facetada.

## Fichas indexables

Todas las fichas se publican, pero solo se indexan las que tienen información suficiente
(`seo.quality_score` ≥ 2): descripción (≥ 40 caracteres suma 1; ≥ 120, 2), lugar o dirección, hora, imagen y
precio o entradas. Las demás llevan `noindex,follow` y no van al sitemap: siguen siendo útiles para quien
llega desde la app, y Google dedica el rastreo a las páginas con contenido. Cuando la fuente completa los datos,
la ficha pasa a indexable sola.

## Eventos pasados

La ficha existe mientras el plan está en la agenda (por fecha o en curso). Cuando sale de la agenda, su URL
**se mantiene 60 días** con `noindex,follow`, fuera del sitemap y sin datos estructurados de evento
(`static.write_gone_pages`):

- **Ya pasó** (su fecha de fin es anterior a hoy): aviso, cuándo y dónde fue, y hasta 6 planes parecidos
  próximos (misma ciudad y tipo; si no, misma provincia y tipo; si no, misma provincia), más enlaces a su ciudad,
  provincia y tipo de plan.
- **Ya no está en la agenda** (aún no había terminado): puede que se haya cancelado, cambiado de fecha o que la
  fuente lo haya retirado; se pide comprobarlo en la web del organizador.
- **Ha cambiado de dirección** (el mismo plan sigue en la agenda con otro id, o con el mismo nombre, día y
  provincia): `meta refresh` inmediato y `canonical` a la ficha nueva. Algunas fuentes (Ajuntament de Barcelona,
  Axenda de Cultura de Galicia) cambian el id de parte de sus planes de un día a otro.

Pasados los 60 días, la URL deja de existir y GitHub Pages responde **404**, que es la señal correcta; la página
404 propone buscar planes parecidos con las palabras del nombre. No se redirige a hubs: una redirección masiva a
una página distinta Google la trata como soft 404.

El estado (fichas publicadas y fecha en que cada una salió de la agenda) se guarda entre ejecuciones en
`data/fichas_publicadas.json`, una ficha por línea para que el diff diario sea pequeño.

## Puente de diciembre

`/puente-diciembre.html` reúne los planes del puente de la Constitución y la Inmaculada. Las fechas se calculan
cada año (`publish.puente_diciembre`): del 6 al 8 de diciembre, alargado hasta el fin de semana pegado (2026:
sábado 5 – martes 8). Lleva resumen con datos, planes por día, planes gratis, Navidad en el puente (primero
mercados, belenes, luces y cabalgatas) y una sección por provincia con 5 o más planes. Del 1 de octubre al
último día del puente es indexable y se enlaza desde todos los hubs; el resto del año la URL sigue existiendo,
con `noindex`, un aviso y enlaces a la agenda, para no perder lo ganado de un año a otro.

## Sitemaps

`/sitemap.xml` es un índice con `sitemap-paginas.xml` y `sitemap-fichas.xml` (se trocea a partir de 45.000 URL).
El `lastmod` de cada URL solo cambia cuando cambia su contenido: se guarda una huella por URL en
`data/sitemap_state.json`. En las fichas la huella es de los datos del propio plan (no de la lista
"Más planes", que rota cada día).

## Datos estructurados

- Fichas: `Event` (o su subtipo: `MusicEvent`, `TheaterEvent`…), con `Offer` solo si hay precio o entradas
  reales y sin `availability` (las fuentes no lo dan). Visitas permanentes: `TouristAttraction`, nunca `Event`.
- Hubs: `ItemList` + `BreadcrumbList`. Portada: `WebSite` + `Organization`.

## Avisos a buscadores

- **Google**: el sitemap (`/sitemap.xml`) se da de alta en Search Console con el dominio verificado (registro TXT
  en el DNS). Google no usa IndexNow ni el antiguo «ping» de sitemaps.
- **Bing, Copilot, ChatGPT Search, Yandex…**: `tools/indexnow.py` envía por IndexNow las URL cuyo `lastmod` es de
  hoy o de ayer, en un paso del workflow que corre después de publicar (`indexnow`, nunca bloquea). La clave es
  `site/<clave>.txt`: es pública a propósito (sirve para comprobar que el aviso viene del dominio).
