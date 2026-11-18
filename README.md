# Planika · planes de ocio en España

**Planika** (<https://planikaapp.com>) es una web estática que reúne planes de ocio (conciertos, teatro, exposiciones, cine, deporte, ferias, fiestas…) de agendas públicas de toda España, clasificados por **provincia** y **tipo de plan**, con vista de **calendario**, enlaces a la web del organizador (información y entradas) y botones para **añadir cada plan a tu calendario** (Google, Apple/iCal, Outlook, Microsoft 365, Yahoo).

## Cómo funciona

```
fetch_events.py  ──►  planes/src_*.py (un adaptador por fuente)
                       │  descarga + normaliza + clasifica + deduplica
                       ▼
                 site/data/events.js   (y events.json)
                       ▼
                 site/index.html + app.js + styles.css   (web 100 % estática)
```

No hay backend: el script Python genera un archivo de datos y la web lo lee en el navegador. Se puede alojar gratis en GitHub Pages, Netlify, Cloudflare Pages o cualquier servidor de archivos estáticos.

## Puesta en marcha

```bash
pip install -r requirements.txt
python3 fetch_events.py            # descarga los próximos 180 días
python3 -m http.server -d site 8000
```

Abre <http://localhost:8000>.

Opciones útiles:

```bash
python3 fetch_events.py --days 90                 # horizonte más corto
python3 fetch_events.py --sources madrid,euskadi  # solo algunas fuentes
python3 fetch_events.py --llm otros               # reclasificar con Claude los planes dudosos (ver abajo)
python3 -m unittest discover -s tests             # pruebas de fechas, provincias, clasificación y sesiones
```

Además de `site/data/events.js`, cada ejecución genera:

- `site/feeds/`: RSS general, por provincia y por tipo de plan (próximos 30 días), para suscribirse desde cualquier lector.
- Páginas estáticas para buscadores: `site/p/` (provincias, con su listado completo paginado, fin de semana, gratis y provincia × tipo), `site/c/` (ciudades con mucha agenda y sin provincia del mismo nombre: Bilbao, Donostia…), `site/t/` (tipos de plan), `planes-hoy.html`, `planes-este-fin-de-semana.html`, `planes-gratis.html` y `festivales.html`, y una ficha por plan en `site/e/`.
- `site/sitemap.xml` (índice) con `sitemap-paginas.xml` y `sitemap-fichas.xml`, y `site/robots.txt`. El `lastmod` solo cambia cuando cambia la página (`data/sitemap_state.json`). Detalles en [docs/seo.md](docs/seo.md); `python3 tools/seo_check.py site` revisa el sitio generado.
- `data/health.json`: histórico de eventos por fuente y alertas cuando una fuente falla o cae mucho. En GitHub Actions, las alertas abren automáticamente un *issue*.

## Qué ofrece la web

- Filtros por comunidad, provincia, tipo de plan, fechas, gratis, con entradas, horario (mañana, tarde, noche), público (familiar o adultos) y precio máximo.
- Vistas de **lista**, **calendario** mensual y **mapa** con agrupación de puntos, más un panel de cobertura por provincia.
- **Cerca de mí**: con la ubicación del móvil, muestra solo los planes a 10, 25, 50 o 100 km y los ordena por distancia.
- **Favoritos** guardados en el navegador, **compartir** un plan (enlace directo a su ficha) o los filtros actuales, y **suscripción RSS** a esos filtros.
- Las funciones repetidas de una misma obra se agrupan en una tarjeta con todas sus fechas.
- Botón de **añadir al calendario** (Google, Apple/iCal, Outlook, Microsoft 365, Yahoo) y enlaces a entradas e información.
- Instalable como app (PWA) desde el navegador del móvil.

### Clasificación y traducción con Claude (opcional)

El script clasifica por la categoría que declara cada fuente y, si no la hay, por palabras clave. Para afinar los casos dudosos (categoría "Otros") y traducir al castellano los títulos en catalán, euskera o gallego, puede consultar a Claude:

1. Crea una clave en <https://console.anthropic.com/> y ponla en `.env` como `ANTHROPIC_API_KEY=`.
2. Ejecuta `python3 fetch_events.py --llm otros` (o `--llm all` para reclasificar todo una vez; los resultados se guardan en `data/llm_cache.json` y no se repiten).
3. En GitHub, añade el secreto `ANTHROPIC_API_KEY` y la variable de repositorio `PLANIKA_LLM=otros` (*Settings → Secrets and variables → Actions → Variables*).

Usa el modelo `claude-opus-5` por defecto; cámbialo con `PLANIKA_LLM_MODEL` (por ejemplo `claude-haiku-4-5` para abaratar). Con unos cientos de planes dudosos al día el coste es de céntimos.

### Analítica (opcional)

En `site/index.html` hay comentadas dos líneas para Plausible y Umami, dos analíticas sin cookies. Crea cuenta en una de ellas, descomenta su línea y pon tu dominio o identificador.

### App en las tiendas

Ver [docs/app-stores.md](docs/app-stores.md): empaquetado con Capacitor (iOS y Android) o TWA (Android), que requiere cuentas de desarrollador de Apple y Google.

### Ticketmaster (opcional, recomendado)

Ticketmaster cubre toda España con enlace directo de compra. Necesita una clave gratuita:

1. Crea una cuenta en <https://developer.ticketmaster.com/> y copia la *Consumer Key* de tu app.
2. `cp .env.example .env` y pega la clave en `TICKETMASTER_API_KEY=`.
3. Vuelve a ejecutar `python3 fetch_events.py`.

El límite gratuito es de 5 000 peticiones al día y 5 por segundo; el script hace unas 150 peticiones por ejecución.

## Fuentes de datos

| Fuente | Cobertura | Formato |
|---|---|---|
| Ayuntamiento de Madrid (datos.madrid.es) | Madrid ciudad, próximos 100 días | JSON |
| Open Data Euskadi / Kulturklik | Álava, Bizkaia, Gipuzkoa | API JSON paginada |
| Agenda cultural de Catalunya (Generalitat) | Barcelona, Girona, Lleida, Tarragona | Socrata JSON |
| Junta de Castilla y León | las 9 provincias | Opendatasoft JSON |
| Institut Valencià de Cultura (GVA) | Valencia, Castellón, Alicante | JSON |
| Ayuntamiento de Málaga | Málaga ciudad | CSV anual |
| Junta de Andalucía (agenda de eventos) | las 8 provincias | JSON |
| Ajuntament de Barcelona | Barcelona ciudad (agenda cultural completa, con sesiones) | JSON |
| Axenda de Cultura de Galicia (Xunta) | las 4 provincias gallegas | iCalendar |
| Ayuntamiento de Cartagena | Cartagena (Murcia) | CSV |
| Cabildo de Tenerife | eventos deportivos de la isla | JSON |
| TheSportsDB | partidos de LaLiga 2, ACB, ASOBAL, Liga Femenina de baloncesto, Copa del Rey y Supercopa (ACB, ASOBAL y Liga F: consulta día a día los próximos 14 días; horas convertidas de UTC a Madrid) | API JSON (clave pública de pruebas; `THESPORTSDB_KEY` para una propia) |
| Ayuntamiento de Lorca | Lorca (Murcia); su CSV lleva meses sin eventos nuevos | CSV |
| Ayuntamiento de Zaragoza | Zaragoza ciudad (agenda de actividades completa) | API JSON paginada |
| esMADRID (Madrid Destino) | Madrid ciudad: conciertos, teatro, exposiciones y grandes eventos | XML |
| Diputació de Barcelona | provincia de Barcelona: turismo, parques naturales y teatros municipales | API JSON |
| Ayuntamiento de Murcia | Murcia y pedanías, próximos eventos | RSS |
| Ayuntamiento de Vitoria-Gasteiz | Agenda de actividades culturales (sin lugar ni descripción en el feed) | RSS |
| Deporte profesional | Partidos en casa de equipos españoles: LaLiga (openfootball, dominio público), Euroliga y EuroCup (API pública de euroleague.net) | JSON / XML |
| Agendas municipales (`planes/src_municipios.py`) | Mérida, Teruel, Ejea de los Caballeros, Siero, Puertollano, Diputación de Albacete, Elche, Orihuela, Villena y Torrent | API JSON de «The Events Calendar» (WordPress) |
| Ticketmaster Discovery API | toda España, con entradas | API JSON (clave) |
| Visitas permanentes (`data/curated.json`) | todas las provincias con poca agenda: museos, monumentos, espacios naturales y salas, sin fecha única | JSON mantenido a mano |

Las visitas permanentes no salen de una agenda. Están en `data/curated.json` y `fetch_events.py` las mezcla en cada ejecución (también con `--rebuild`), así que sobreviven a la regeneración diaria. En la web aparecen como «Visita permanente»: entran en los filtros de provincia y en el mapa, quedan detrás de los planes con fecha y no marcan todos los días del calendario.

Fuentes revisadas y descartadas por estar paradas o no ser accesibles por programa: Canarias (CSV parado en 2021), Gijón (JSON parado en 2025), Terrassa (CSV de 2024), municipios de Córdoba vía Eprinsa (datos de 2022), Alcobendas (bloquea el acceso), Cáceres y Santa Cruz de Tenerife (portales que solo sirven HTML), L'Hospitalet y Región de Murcia Digital (recursos vacíos o caídos), Castilla-La Mancha (sin datos descargables), Vigo (solo publica la agenda del día). Webs comerciales como Fever, entradas.com o Wikiloc no se raspan porque sus condiciones de uso lo prohíben.

Muchos ayuntamientos publican su agenda con WordPress y el plugin «The Events Calendar», que expone una API pública. Si `https://<web>/wp-json/tribe/events/v1/events` devuelve `{"events": [...]}`, añadir ese municipio es una línea en `SITES` de `planes/src_municipios.py`. Revisadas sin esa API (noviembre de 2026): unas 330 webs de ayuntamientos y diputaciones, entre ellas las capitales de Castilla-La Mancha, Extremadura, Asturias, Cantabria, La Rioja, Baleares y Canarias.

Para añadir una fuente nueva crea `planes/src_<nombre>.py` con `NAME`, `HOME` y una función `fetch(log)` que devuelva una lista construida con `planes.util.event(...)`, y añade `<nombre>` a la lista `SOURCES` de `fetch_events.py`.

## Tipos de plan

Música y conciertos · Teatro y danza · Exposiciones y museos · Cine · Deporte · Gastronomía, ferias y mercados · Infantil y familiar · Fiestas y tradiciones · Naturaleza, rutas y visitas · Charlas, libros y talleres · Otros.

La clasificación usa primero la categoría que declara cada fuente y, si no la hay, palabras clave en el título y la descripción (`planes/classify.py`).

## Publicar en planikaapp.com con GitHub Pages y actualización diaria

1. Crea un repositorio en GitHub y sube esta carpeta (`git init && git add . && git commit -m "Planika" && git push`).
2. En *Settings → Pages* elige **GitHub Actions** como origen.
3. En *Settings → Pages → Custom domain* escribe `planikaapp.com` y marca **Enforce HTTPS** cuando el certificado esté listo (unos minutos). Mientras el DNS no esté configurado, deja el campo vacío: con el dominio puesto, GitHub redirige la dirección provisional `https://davidpardal.github.io/planika/` al dominio y la web deja de verse.
4. En el panel DNS del registrador del dominio crea estos registros:

   | Tipo | Nombre | Valor |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | AAAA | `@` | `2606:50c0:8000::153`, `2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153` |
   | CNAME | `www` | `<tu-usuario>.github.io` |

   La propagación tarda entre minutos y 24 horas. Comprueba con `dig planikaapp.com +short`.
5. Opcional: en *Settings → Secrets → Actions* crea `TICKETMASTER_API_KEY`.
6. El workflow `.github/workflows/update.yml` descarga las agendas cada día a las 04:15 UTC, guarda los datos y publica la web.

Alternativa sin GitHub: cualquier hosting estático (Netlify, Cloudflare Pages, Vercel) sirve la carpeta `site/`; en ese caso programa `python3 fetch_events.py` en el proceso de build o en un cron.

## App instalable (PWA)

`site/manifest.webmanifest` e `site/icon.svg` permiten instalar Planika en el móvil desde el navegador ("Añadir a pantalla de inicio") con icono y pantalla completa. Para publicarla en App Store o Google Play haría falta empaquetarla (por ejemplo con Capacitor o un TWA), lo que queda fuera de este repositorio.

## Estructura

```
fetch_events.py        orquestador
planes/util.py         HTTP, fechas, limpieza de texto, provincias y municipios
planes/classify.py     tipos de plan
planes/src_*.py        adaptadores por fuente
data/municipios.json   municipio → provincia (códigos INE)
site/                  la web (index.html, app.js, styles.css, data/events.js, CNAME, manifest, icono)
```

Los datos pertenecen a sus respectivos publicadores bajo sus licencias de datos abiertos; comprueba siempre fechas y precios en la fuente original.

## Cloudflare Pages (opcional)

El flujo de trabajo puede publicar también en Cloudflare Pages (gratis; la web tiene ~6.900 archivos y el límite es 20.000). Está apagado por defecto:

1. En Cloudflare: *Workers & Pages → Create → Pages → Direct Upload*, proyecto llamado `planika`.
2. Crea un token de API con el permiso *Account → Cloudflare Pages → Edit* y copia el *Account ID*.
3. En GitHub (*Settings → Secrets and variables → Actions*): secretos `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`, y la variable `CLOUDFLARE_ENABLED` con valor `true`.
4. Para usar el dominio: en el proyecto, *Custom domains → planikaapp.com*, y en OVH apunta el DNS a Cloudflare según te indique. Después quita el dominio de GitHub Pages.

`site/_headers` define la caché y cabeceras de seguridad (GitHub Pages lo ignora).
