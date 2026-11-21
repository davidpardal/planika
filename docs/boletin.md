# Boletín semanal «Planes del finde»

## Qué hace Planika sola (cada día, en la actualización)

- `site/boletin/index.html` → https://planikaapp.com/boletin/ : la edición del próximo finde (o del que está en
  curso) con los datos del día: lo más destacado, gratis, con niños y las 6 ciudades con más planes, con
  enlace a cada ficha y a las páginas «fin de semana» de cada ciudad.
- `site/boletin/email.html` y `email.json`: la misma edición lista para enviar (HTML para email, asunto y
  texto de vista previa). Los enlaces llevan `utm_source=boletin` para verlo en Analytics.
- De jueves a domingo, `site/boletin/AAAA-MM-DD.html` (archivo de cada edición) y
  `feeds/boletin.xml` (RSS con las últimas ediciones, para servicios de «RSS a email»).

Nada se inventa: todo sale de la agenda del día.

## Lo que tienes que hacer tú: elegir el servicio de envío

Recomendado: **Brevo** (plan gratis: 300 emails al día, contactos ilimitados, formularios de alta y API).
El envío semanal ya está preparado para Brevo (`.github/workflows/boletin.yml`).

1. Crea la cuenta en https://www.brevo.com y **verifica el remitente** (por ejemplo, el email de Planika).
2. *Contactos → Listas*: crea la lista «Planes del finde» y apunta su **número (ID)**.
3. *Contactos → Formularios*: crea un formulario de alta para esa lista, con **doble confirmación**
   (recomendable en la UE: deja constancia del consentimiento). Copia el **enlace para compartir** del formulario y pásamelo: lo pongo en
   `data/boletin.json` (`form_url`) y aparece el botón «Recíbelo cada jueves en tu email».
4. *SMTP & API → API Keys*: crea una clave. **No me la pases**: guárdala tú en GitHub →
   *Settings → Secrets and variables → Actions*:
   - Secreto `BREVO_API_KEY` = la clave.
   - Variables: `BREVO_LIST_ID` = número de la lista, `BREVO_SENDER_EMAIL` = remitente verificado
     (opcional `BREVO_SENDER_NAME`, por defecto «Planika»).
5. Listo. Cada **jueves a las 9:12** (10:12 en horario de verano) se crea en Brevo la campaña de ese finde **en borrador**: la revisas
   y pulsas *Enviar*. Cuando te fíes, crea la variable `BOLETIN_ENVIO` = `auto` y se enviará sola.
   Para probarlo cualquier día: *Actions → Boletín «Planes del finde» → Run workflow* (solo funciona con la
   edición de esta semana).

Con más de 300 suscriptores hará falta un plan de pago de Brevo (desde unos 9 USD al mes) o enviar en dos días.

## Otros servicios

- **Mailchimp / MailerLite (planes de pago)**: campaña «RSS» con `https://planikaapp.com/feeds/boletin.xml`,
  envío semanal los jueves. Su etiqueta de baja va en `unsubscribe_tag` de `data/boletin.json`
  (Mailchimp: `*|UNSUB|*`; MailerLite: `{$unsubscribe}`).
- **Manual con cualquier servicio**: copia el código de https://planikaapp.com/boletin/email.html en el editor
  HTML del servicio.
