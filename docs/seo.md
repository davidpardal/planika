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
| Tipo de plan | `/t/<tipo>.html` | conciertos, teatro, exposiciones, planes con niños… en España |
| Provincia | `/p/<provincia>.html` + `/p/<provincia>-pagina-N.html` | qué hacer en X (listado completo, 150 por página) |
| Provincia: finde, gratis | `/p/<provincia>-fin-de-semana.html`, `-gratis.html` (3 o más planes) | planes este finde / gratis en X |
| Provincia × tipo | `/p/<provincia>-<tipo>.html` (5 o más planes) | conciertos en X, teatro en X… |
| Ciudad | `/c/<ciudad>.html` (100 o más planes con fecha y sin provincia del mismo nombre) | qué hacer en Bilbao, Donostia, Vitoria, Pamplona |
| Ficha | `/e/<titulo>-<id>.html` | el plan concreto |

Cada hub tiene título, H1 y descripción propios, un texto de introducción calculado con los datos de la página
(cuántos planes, de qué tipo, en qué localidades y lugares, cuántos gratis), migas de pan visibles y en
JSON-LD (`BreadcrumbList`) y un `ItemList` con los primeros planes. Todas las fichas quedan a 3 clics de la portada.

Las URL con parámetros (`/?e=`, `/?prov=`…) son la app con filtros; tienen canonical a `/` y `robots.txt`
no las deja rastrear (`Disallow: /?`), como recomienda Google para la navegación facetada.

## Fichas indexables

Todas las fichas se publican, pero solo se indexan las que tienen información suficiente
(`seo.quality_score` ≥ 2): descripción (≥ 40 caracteres suma 1; ≥ 120, 2), lugar o dirección, hora, imagen y
precio o entradas. Las demás llevan `noindex,follow` y no van al sitemap: siguen siendo útiles para quien
llega desde la app, y Google dedica el rastreo a las páginas con contenido. Cuando la fuente completa los datos,
la ficha pasa a indexable sola.

## Eventos pasados

La ficha existe mientras el plan está en la agenda (por fecha o en curso). Cuando termina, la URL deja de
existir y GitHub Pages responde **404**, que es la señal correcta para Google; la página 404 propone buscar
planes parecidos con las palabras del nombre y enlaza al fin de semana y a los planes gratis. No se redirige a
hubs: una redirección masiva a una página distinta Google la trata como soft 404.

## Sitemaps

`/sitemap.xml` es un índice con `sitemap-paginas.xml` y `sitemap-fichas.xml` (se trocea a partir de 45.000 URL).
El `lastmod` de cada URL solo cambia cuando cambia su contenido: se guarda una huella por URL en
`data/sitemap_state.json`. En las fichas la huella es de los datos del propio plan (no de la lista
"Más planes", que rota cada día).

## Datos estructurados

- Fichas: `Event` (o su subtipo: `MusicEvent`, `TheaterEvent`…), con `Offer` solo si hay precio o entradas
  reales y sin `availability` (las fuentes no lo dan). Visitas permanentes: `TouristAttraction`, nunca `Event`.
- Hubs: `ItemList` + `BreadcrumbList`. Portada: `WebSite` + `Organization`.
