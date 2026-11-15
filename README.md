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
- `site/p/<provincia>.html` y `site/t/<tipo>.html`: páginas estáticas con URL propia para buscadores, enlazadas desde el pie de la web y el `sitemap.xml`.
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
| TheSportsDB | próximos partidos de LaLiga, LaLiga 2, ACB, Copa del Rey y Supercopa | API JSON (clave pública de pruebas; `THESPORTSDB_KEY` para una propia) |
| Ayuntamiento de Lorca | Lorca (Murcia); su CSV lleva meses sin eventos nuevos | CSV |
| Ticketmaster Discovery API | toda España, con entradas | API JSON (clave) |
| Visitas permanentes (`data/curated.json`) | todas las provincias con poca agenda: museos, monumentos, espacios naturales y salas, sin fecha única | JSON mantenido a mano |

Las visitas permanentes no salen de una agenda. Están en `data/curated.json` y `fetch_events.py` las mezcla en cada ejecución (también con `--rebuild`), así que sobreviven a la regeneración diaria. En la web aparecen como «Visita permanente»: entran en los filtros de provincia y en el mapa, quedan detrás de los planes con fecha y no marcan todos los días del calendario.

Fuentes revisadas y descartadas por estar paradas o no ser accesibles por programa: Canarias (CSV parado en 2021), Gijón (JSON parado en 2025), Terrassa (CSV de 2024), municipios de Córdoba vía Eprinsa (datos de 2022), Zaragoza (la API devuelve HTML a peticiones automatizadas), Alcobendas (bloquea el acceso), Cáceres y Santa Cruz de Tenerife (portales que solo sirven HTML), L'Hospitalet y Región de Murcia Digital (recursos vacíos o caídos), Castilla-La Mancha (sin datos descargables), Vigo (solo publica la agenda del día). Webs comerciales como Fever, entradas.com o Wikiloc no se raspan porque sus condiciones de uso lo prohíben.

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
