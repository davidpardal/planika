# Planika como app (móvil, Google Play y App Store)

## 1. Ya funciona: app instalable desde la web (PWA)

Desde planikaapp.com cualquiera puede instalar Planika sin pasar por ninguna tienda:

- **Android (Chrome, Samsung Internet, Edge):** sale el botón «📲 Instala Planika en tu móvil» en la portada, o
  el aviso del propio navegador. Queda con su icono en la pantalla de inicio y se abre a pantalla completa.
- **iPhone/iPad (Safari):** el mismo botón explica los tres pasos (Compartir → Añadir a pantalla de inicio).
- **Sin conexión:** la portada abre con los planes de la última visita y los favoritos; las fichas ya vistas
  también. Lo demás muestra una página «Sin conexión».

Piezas: `site/manifest.webmanifest`, `site/sw.js` (service worker), `site/offline.html`, iconos PNG
(`icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `apple-touch-icon.png`) y capturas en
`site/capturas/`. En Google Analytics: eventos `pwa_install_click`, `pwa_install_choice`, `pwa_installed`
y `pwa_open`; las aperturas desde la app llegan con `utm_source=app`.

## 2. Google Play (Android): la misma web empaquetada (TWA)

Una *Trusted Web Activity* publica la web tal cual como app de Android: se actualiza sola cada día con la
web, sin mantener otro código. No hace falta Android Studio.

### Lo que tienes que hacer tú

1. **Cuenta de Google Play Console** (25 USD, pago único): https://play.google.com/console/signup
   - Cuenta **personal**: Google exige una **prueba cerrada con al menos 12 personas durante 14 días
     seguidos** antes de dejarte publicar en abierto. Cuenta unas 3 semanas en total.
   - Cuenta de **organización**: se salta esa prueba, pero necesita número D-U-N-S (puede tardar hasta 30 días).
2. **Generar el paquete** en https://www.pwabuilder.com → escribe `https://planikaapp.com` → *Package for
   stores* → *Android* → *Generate*. Datos recomendados:
   - Package ID: `com.planikaapp.twa` · Nombre: `Planika` · Nombre corto: `Planika`
   - Signing key: *Create new* (guarda el `.keystore` y las contraseñas en un sitio seguro: sin ellos no
     podrás publicar actualizaciones). **No me las pases.**
   - Descarga el zip: trae el `.aab` (lo que se sube a Play) y un `assetlinks.json`.
3. En Play Console → *Crear app* → sube el `.aab` a **Prueba cerrada** (o *Prueba interna* para probarlo tú).
   Acepta **Play App Signing**.
4. En *Configuración → Integridad de la app → Firma de apps*, copia la **huella SHA-256** del certificado
   de firma de la app y **pásamela** (es pública, no es una contraseña). Yo publico
   `https://planikaapp.com/.well-known/assetlinks.json` con ella y con la del zip; sin ese archivo la app
   muestra la barra de direcciones de Chrome arriba.
5. **Ficha de Play** (textos e imágenes; tienes todo en `docs/play/` y `site/capturas/`):
   - Icono 512×512: `docs/play/icono-512.png`
   - Gráfico destacado 1024×500: `docs/play/grafico-destacado-1024x500.png`
   - Capturas de teléfono: `site/capturas/app-portada.jpg`, `app-planes.jpg`, `app-mapa.jpg`
   - Descripción breve (80 car.): «Conciertos, teatro, expos, deporte y fiestas de toda España en una agenda»
   - Política de privacidad: `https://planikaapp.com/privacidad.html`
   - Cuestionarios: clasificación de contenido, público objetivo y **seguridad de los datos**. En este
     último hay que declarar lo que recoge Google Analytics (actividad en la app e identificadores del
     dispositivo, con fines de analítica). La ubicación de «Cerca de mí» se usa solo dentro del móvil para
     filtrar y no se envía a ningún servidor.
6. Con 12+ personas apuntadas al enlace de la prueba cerrada durante 14 días, pide el **acceso a producción**.

## 3. App Store (iPhone)

Apple suele rechazar apps que son solo una web empaquetada (norma 4.2, «funcionalidad mínima») y pide cuenta
de Apple Developer (99 USD al año) y un Mac con Xcode. Recomendación: de momento, instalación desde Safari
(punto 1), que ya da icono, pantalla completa y uso sin conexión. Si más adelante quieres la App Store, la
vía es Capacitor con alguna función nativa (avisos de planes guardados, widget de «planes de hoy»):

```bash
npm install @capacitor/core @capacitor/cli @capacitor/ios
npx cap init Planika com.planikaapp.app --web-dir=site
npx cap add ios && npx cap open ios
```

Icono para iOS (1024×1024, sin transparencia): `docs/play/icono-ios-1024.png`.
