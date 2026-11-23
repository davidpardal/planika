# Cuentas (opcionales)

Quien quiera puede entrar con su email (sin contraseña) para tener sus **favoritos** y **«Mi ciudad»** en todos sus
dispositivos. Sin cuenta, Planika funciona igual que siempre: los favoritos se quedan en el navegador.

## Cómo está hecho

- **Supabase**, cuenta planikaapp.com@gmail.com, organización «Planika», proyecto `rqjrrdtdscvcimwzrwxj`, región UE
  (Irlanda, eu-west-1), plan gratuito. El esquema completo está en `supabase/esquema.sql`.
- Tablas `public.favorites` (usuario, plan) y `public.profiles` (usuario, ciudad). Con RLS: cada persona solo ve y
  cambia sus filas; el rol anónimo no tiene acceso. Máximo 2.000 favoritos por cuenta.
- `public.delete_my_account()` borra la cuenta de quien la llama (y en cascada sus favoritos y su ciudad).
- Tarea diaria `planika-limpiar-sin-confirmar` (pg_cron, 03:17 UTC): borra a quien pidió el enlace por email y
  nunca entró, pasados 7 días.
- Trigger `minimizar_datos_google` en `auth.users` y `auth.identities`: quita nombre y foto que manda Google.
- `public.ping()` devuelve la hora: el trabajo `cuentas-ping` de `update.yml` la llama a diario para que el proyecto
  gratuito no se pause tras una semana sin uso.
- `site/app.js` habla directamente con la API de Supabase (sin librerías). La clave que lleva es la *publishable*,
  pública por diseño; la seguridad la ponen las políticas RLS. **Nunca** se usa la clave `service_role`.
- Al entrar, los favoritos del dispositivo se suben a la cuenta; a partir de ahí la cuenta manda. Los cambios sin
  conexión se guardan en cola (`planika_fav_ops`) y se envían al volver la conexión o al abrir Planika.
- Si la vuelta del inicio de sesión llega a un navegador donde no se empezó (por ejemplo, se empezó desde la app
  instalada) o es de otro email, Planika pregunta «¿Entrar como …?» antes de entrar. Así nadie puede colarte su sesión con un enlace
  preparado y quedarse con tus favoritos.
- «Mi ciudad» se guarda como `comunidad|provincia|localidad` (lo mismo que el filtro «Dónde»). Al abrir Planika sin
  filtros en la dirección, se aplica.

## Entrar con Google (lo que está activo)

Se entra con «Continuar con Google». No hace falta enviar correos (ni Brevo). Google comparte email, nombre y foto;
un trigger de la base de datos (`minimizar_datos_google`) descarta nombre y foto al recibirlos.

Desde el navegador de Instagram, Facebook o TikTok Google no deja entrar: en ese caso el botón no sale y se explica
cómo abrir Planika en Safari o Chrome.

Mientras `ACCOUNTS_PUBLIC = false` (en `site/app.js`), el botón «Entrar» solo aparece en el navegador donde se abra
`https://planikaapp.com/?cuentas=1` (se recuerda; `?cuentas=0` lo quita).

### Pasos en Google Cloud (https://console.cloud.google.com/auth/overview)

1. Crea un proyecto (por ejemplo «Planika») y entra en **Google Auth Platform**.
2. **Branding**: nombre de la app «Planika», email de asistencia, página principal `https://planikaapp.com`,
   política de privacidad `https://planikaapp.com/privacidad.html` y, en dominios autorizados, `planikaapp.com` y
   `rqjrrdtdscvcimwzrwxj.supabase.co`.
3. **Audience**: tipo *External*. Mientras está en *Testing* solo pueden entrar los usuarios de prueba que añadas
   (añade tu Gmail). Para abrirlo a todo el mundo, *Publish app*.
4. **Data Access**: deja solo `openid`, `.../auth/userinfo.email` y `.../auth/userinfo.profile` (no piden revisión).
5. **Clients → Create client** → *Web application*:
   - Authorized JavaScript origins: `https://planikaapp.com`
   - Authorized redirect URIs: `https://rqjrrdtdscvcimwzrwxj.supabase.co/auth/v1/callback`
   - Guarda el **Client ID** y el **Client secret**.

### Pasos en Supabase (https://supabase.com/dashboard/project/rqjrrdtdscvcimwzrwxj)

1. **Authentication → URL Configuration**: Site URL `https://planikaapp.com` y en Redirect URLs `https://planikaapp.com/**`.
2. **Authentication → Sign In / Providers → Google**: activar y pegar Client ID y Client secret (el secreto solo ahí,
   nunca en un chat ni en el repositorio).
3. Opcional: en el mismo sitio, desactivar **Email** mientras no se use el correo.

Google mostrará «continuar a rqjrrdtdscvcimwzrwxj.supabase.co» en su pantalla: es la dirección del proyecto. Para
que salga un dominio propio (por ejemplo `cuentas.planikaapp.com`) hace falta el dominio personalizado de Supabase,
que es de pago.

## Entrar con el email (más adelante)

Está programado pero apagado (`EMAIL_LOGIN = false`). Para activarlo hace falta SMTP propio, porque sin él Supabase
solo envía correos a los miembros del equipo del proyecto:

1. **Authentication → Emails → SMTP Settings**: activar *Custom SMTP* con Brevo (host `smtp-relay.brevo.com`,
   puerto `587`, login SMTP y clave SMTP de Brevo; remitente de `planikaapp.com` verificado en Brevo).
2. **Authentication → Emails → Templates**: pegar las plantillas de abajo en *Magic link* y en *Confirm signup*.
3. **Authentication → Rate Limits**: con SMTP propio son 30 correos por hora; súbelo antes de anunciarlo.
4. Poner `EMAIL_LOGIN = true`. En privacidad, volver a nombrar Brevo y el enlace por email.

Si alguien usa el formulario para mandar correos a lo loco, se puede añadir un captcha (Cloudflare Turnstile) en
Authentication → Attack Protection.

## Plantillas de email

Asunto (*Magic link*): `Tu enlace para entrar en Planika`
Asunto (*Confirm signup*): `Confirma tu email para entrar en Planika`

```html
<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:480px;margin:0 auto;color:#1a1033">
  <h2 style="margin:0 0 12px">Entra en Planika</h2>
  <p>Pulsa el botón para entrar. El enlace caduca en una hora y solo sirve una vez.</p>
  <p><a href="{{ .ConfirmationURL }}" style="display:inline-block;background:#ff3d81;color:#fff;padding:12px 20px;border-radius:999px;font-weight:700;text-decoration:none">Entrar en Planika</a></p>
  <p>¿Usas Planika instalada en el móvil? Escribe este código en la ventana «Revisa tu correo»:</p>
  <p style="font-size:28px;font-weight:800;letter-spacing:4px;margin:8px 0">{{ .Token }}</p>
  <p style="color:#4a4263;font-size:13px">Si no has pedido entrar en Planika, ignora este correo.</p>
</div>
```

## Avisos

- Algunos correos de empresa abren los enlaces solos para revisarlos y los gastan: entonces el enlace da «caducado» y
  hay que pedir otro.
- La app instalada (iPhone sobre todo) puede abrir Google fuera de la app; si la vuelta llega a Safari, entras en
  Safari (y Planika pregunta «¿Entrar como …?»). Hay que probarlo en un iPhone con Planika instalada.

## Pruebas

- `tests` de Python: sin cambios (la parte nueva es JavaScript).
- Navegador con Supabase simulado: alta con código, unión de favoritos, ciudad, renovación de sesión, enlace
  caducado, salir y borrar la cuenta.
- Contra el Supabase real (rama `sondeo`, `tools/sondeo/e2e_cuentas.py`) con un usuario de prueba desechable que la
  propia prueba borra al final.
