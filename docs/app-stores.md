# Planika como app nativa (App Store y Google Play)

La web ya es una PWA instalable (manifiesto + icono). Para publicarla en las tiendas hace falta empaquetarla; la vía más sencilla es **Capacitor**, que envuelve la web en una app nativa sin reescribirla.

## Requisitos (cuentas y herramientas que debes tener tú)

- Cuenta de **Apple Developer** (99 USD/año) y un Mac con Xcode para iOS.
- Cuenta de **Google Play Console** (25 USD una vez) y Android Studio para Android.
- Node.js 18 o superior.

## Pasos

```bash
cd planes-ocio
npm init -y
npm install @capacitor/core @capacitor/cli
npx cap init Planika com.planikaapp.app --web-dir=site
npm install @capacitor/ios @capacitor/android
npx cap add ios
npx cap add android
```

Para que la app cargue siempre los datos actualizados en vez de los que lleva empaquetados, en `capacitor.config.json` apunta al sitio publicado:

```json
{
  "appId": "com.planikaapp.app",
  "appName": "Planika",
  "webDir": "site",
  "server": { "url": "https://planikaapp.com", "cleartext": false }
}
```

Después:

```bash
npx cap sync
npx cap open ios      # compila y firma en Xcode, sube con Transporter o desde Xcode
npx cap open android  # genera el .aab firmado y súbelo a Play Console
```

## Alternativa Android sin Capacitor: TWA

Una *Trusted Web Activity* publica la PWA tal cual en Google Play. Se genera con [Bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap): `npx @bubblewrap/cli init --manifest https://planikaapp.com/manifest.webmanifest`. Requiere servir el archivo `.well-known/assetlinks.json` en el dominio, que Bubblewrap genera.

## Iconos y pantallas

Los stores exigen iconos PNG de 1024×1024 (iOS) y 512×512 (Android) además de capturas de pantalla. Parte de `site/icon.svg` y exporta los PNG con cualquier editor vectorial.
