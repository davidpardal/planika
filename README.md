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
```

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
| Ayuntamiento de Lorca | Lorca (Murcia); su CSV lleva meses sin eventos nuevos | CSV |
| Ticketmaster Discovery API | toda España, con entradas | API JSON (clave) |

Fuentes revisadas y descartadas: Canarias (el CSV público no se actualiza desde 2021), Zaragoza (la API devuelve HTML a peticiones automatizadas), Cartagena (recurso retirado), Castilla-La Mancha (solo publica la web, sin datos descargables).

Para añadir una fuente nueva crea `planes/src_<nombre>.py` con `NAME`, `HOME` y una función `fetch(log)` que devuelva una lista construida con `planes.util.event(...)`, y añade `<nombre>` a la lista `SOURCES` de `fetch_events.py`.

## Tipos de plan

Música y conciertos · Teatro y danza · Exposiciones y museos · Cine · Deporte · Gastronomía, ferias y mercados · Infantil y familiar · Fiestas y tradiciones · Naturaleza, rutas y visitas · Charlas, libros y talleres · Otros.

La clasificación usa primero la categoría que declara cada fuente y, si no la hay, palabras clave en el título y la descripción (`planes/classify.py`).

## Publicar en planikaapp.com con GitHub Pages y actualización diaria

1. Crea un repositorio en GitHub y sube esta carpeta (`git init && git add . && git commit -m "Planika" && git push`).
2. En *Settings → Pages* elige **GitHub Actions** como origen.
3. En *Settings → Pages → Custom domain* escribe `planikaapp.com` y marca **Enforce HTTPS** cuando el certificado esté listo (unos minutos). El archivo `site/CNAME` ya contiene el dominio para que no se pierda en cada despliegue.
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
