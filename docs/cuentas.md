# Cuentas (opcionales)

Quien quiera puede entrar con su email (sin contraseña) para tener sus **favoritos** y **«Mi ciudad»** en todos sus
dispositivos. Sin cuenta, Planika funciona igual que siempre: los favoritos se quedan en el navegador.

## Cómo está hecho

- **Supabase**, proyecto `planika` (`jygalcbsfrntavhqahpx`), región UE (París), plan gratuito.
- Tablas `public.favorites` (usuario, plan) y `public.profiles` (usuario, ciudad). Con RLS: cada persona solo ve y
  cambia sus filas; el rol anónimo no tiene acceso. Máximo 2.000 favoritos por cuenta.
- `public.delete_my_account()` borra la cuenta de quien la llama (y en cascada sus favoritos y su ciudad).
- `public.ping()` devuelve la hora: el trabajo `cuentas-ping` de `update.yml` la llama a diario para que el proyecto
  gratuito no se pause tras una semana sin uso.
- `site/app.js` habla directamente con la API de Supabase (sin librerías). La clave que lleva es la *publishable*,
  pública por diseño; la seguridad la ponen las políticas RLS. **Nunca** se usa la clave `service_role`.
- Al entrar, los favoritos del dispositivo se suben a la cuenta; a partir de ahí la cuenta manda. Los cambios sin
  conexión se guardan en cola (`planika_fav_ops`) y se envían al volver la conexión o al abrir Planika.
- «Mi ciudad» se guarda como `comunidad|provincia|localidad` (lo mismo que el filtro «Dónde»). Al abrir Planika sin
  filtros en la dirección, se aplica.

## Activarlo para todo el mundo

Mientras `ACCOUNTS_PUBLIC = false` (en `site/app.js`), el botón «Entrar» solo aparece en el navegador donde se abra
`https://planikaapp.com/?cuentas=1` (se recuerda; `?cuentas=0` lo quita). Para abrirlo al público, antes hay que
hacer esto en el panel de Supabase (https://supabase.com/dashboard/project/jygalcbsfrntavhqahpx):

1. **Authentication → URL Configuration**
   - *Site URL*: `https://planikaapp.com`
   - *Redirect URLs*: `https://planikaapp.com/**`
2. **Authentication → Emails → SMTP Settings**: activar *Custom SMTP* con Brevo. Sin esto, Supabase solo envía
   correos a los miembros del equipo del proyecto (y unos pocos por hora).
   - Host `smtp-relay.brevo.com`, puerto `587`.
   - Usuario y contraseña: los de Brevo → *SMTP & API* → *SMTP* (la contraseña es una clave SMTP que generas allí;
     pégala solo en Supabase, nunca en un chat ni en el repositorio).
   - Remitente: una dirección de `planikaapp.com` con el dominio verificado en Brevo (por ejemplo
     `hola@planikaapp.com`), nombre «Planika».
3. **Authentication → Emails → Templates**: pegar las plantillas de abajo en *Magic link* y en *Confirm signup*
   (a quien entra por primera vez le llega la de *Confirm signup*).
4. Probar con `?cuentas=1` desde un email que no sea del equipo de Supabase y, si llega, poner
   `ACCOUNTS_PUBLIC = true`.
5. Opcional: **Authentication → Sign In / Providers → Google** y después `GOOGLE_LOGIN = true`.

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

## Pruebas

- `tests` de Python: sin cambios (la parte nueva es JavaScript).
- Navegador con Supabase simulado: alta con código, unión de favoritos, ciudad, renovación de sesión, enlace
  caducado, salir y borrar la cuenta.
- Contra el Supabase real (rama `sondeo`, `tools/sondeo/e2e_cuentas.py`) con un usuario de prueba desechable que la
  propia prueba borra al final.
