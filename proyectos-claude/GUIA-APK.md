# 📲 Cómo tener las apps en el móvil (y sacar el APK)

Las 5 apps funcionan en **un servidor** que guarda tu clave de Claude. El móvil solo las abre, igual que
Instagram abre los servidores de Instagram. Por eso el camino es:

1. **Subirlas a internet** → tendrás una dirección tipo `https://mis-apps-claude.onrender.com`.
2. **Instalarlas** en Android o iPhone desde esa dirección (icono en la pantalla de inicio, pantalla completa).
3. **(Opcional) Sacar el APK** con PWABuilder para pasarlo a otros Android o subirlo a Google Play.

> Tu clave de Claude **nunca** va dentro del APK: se queda en el servidor. El APK solo abre la dirección.

---

## Paso 0 · Probarlo antes en tu ordenador (opcional)

```bash
cd proyectos-claude
pip install -r requirements.txt
python servidor.py          # → http://localhost:8080
```

Para verlo en tu móvil con la **misma wifi**: añade `APP_PASSWORD=una-contraseña` al `.env` y arranca con
`HOST=0.0.0.0 python servidor.py`. En el móvil abre `http://IP-de-tu-ordenador:8080`
(la IP la ves con `ipconfig` en Windows o `ifconfig` en Mac/Linux, p. ej. `192.168.1.20`).
Así lo pruebas, pero la instalación como app y el APK necesitan el Paso 1 (dirección `https://`).

---

## Paso 1 · Subirlas a internet con Render (unos 10 minutos)

1. Entra en **render.com** y crea una cuenta con **«Sign in with GitHub»**.
2. Arriba a la derecha: **New → Blueprint**.
3. Elige el repositorio **`skills`**. Render encuentra el archivo `render.yaml` y te muestra el servicio
   **mis-apps-claude**.
4. Te pedirá dos valores (se guardan cifrados en Render, no en GitHub):
   - **`ANTHROPIC_API_KEY`** → tu clave `sk-ant-...`
   - **`APP_PASSWORD`** → la contraseña que tendrás que escribir para entrar a las apps. Que sea larga.
5. Pulsa **Apply** y espera a que el estado pase a **Live** (la primera vez tarda unos 5 minutos).
6. Copia la dirección que te da Render (p. ej. `https://mis-apps-claude.onrender.com`) y ábrela:
   verás la pantalla **«Mis apps con Claude»**. Si abres `…/salud` debe decir `"claude": true`.

**Coste**: el `render.yaml` usa el plan **Starter (~7 USD/mes)** con un disco de 1 GB, para que tus datos
(panel, notas, guiones…) **no se borren** al reiniciar. Si solo quieres probar gratis, en Render cambia el plan a
**Free** y quita el disco: funciona igual, pero se «duerme» tras 15 min sin uso y **pierde los datos** al reiniciar.
A esto se suma lo que gastes en Claude (console.anthropic.com → Usage).

---

## Paso 2 · Instalarla en el móvil (sin APK)

Abre tu dirección en el móvil y escribe la contraseña (solo la primera vez; sirve para las 5 apps).

- **Android (Chrome)**: en la pantalla de inicio de la web pulsa **«Instalar»**, o menú **⋮ → Instalar app**.
- **iPhone (Safari)**: botón **Compartir** (cuadrado con flecha) → **«Añadir a pantalla de inicio»**.

Puedes instalar **la pantalla de inicio** (una app con las 5 dentro) o **cada app por separado**: entra en
`…/panel/`, `…/jarvis/`, etc., y haz lo mismo. Cada una tiene su icono.

Para otra persona: pásale la dirección y la contraseña, y que haga lo mismo.

---

## Paso 3 · Sacar el APK (Android)

1. Entra en **pwabuilder.com**, pega tu dirección (`https://mis-apps-claude.onrender.com/`, o la de una app
   concreta, p. ej. `…/panel/`) y pulsa **Start**.
2. Pulsa **Package for stores → Android → Generate Package**. En las opciones:
   - **Package ID**: algo como `com.tunombre.misapps` (sin espacios ni tildes).
   - **App name**: el nombre que verás bajo el icono.
   - Deja que PWABuilder **cree la firma** (signing key) nueva.
3. Descarga el `.zip`. Dentro hay:
   - `*.apk` → **el que se instala** en los móviles.
   - `*.aab` → el que se sube a Google Play (si algún día la publicas).
   - `signing.keystore` y `signing-key-info.txt` → **guárdalos bien**: sin ellos no podrás actualizar la app.
   - `assetlinks.json` → para el paso 4.
4. **Quitar la barra del navegador** (recomendado): en Render → tu servicio → **Environment** → añade la variable
   **`ASSETLINKS_JSON`** y pega dentro **todo el contenido** de `assetlinks.json`. Guarda (se redespliega solo).
   Comprueba que `https://tu-direccion/.well-known/assetlinks.json` lo muestra.
5. **Instalar el APK**: pásalo al móvil (WhatsApp, Drive, cable…), ábrelo y acepta
   **«Permitir instalar apps de esta fuente»**. Android avisará de que es de origen desconocido: es normal
   en APKs que no vienen de Google Play.

Para **Google Play**: cuenta de desarrollador (25 USD, pago único) en play.google.com/console y sube el `.aab`.

> **iPhone no usa APK.** En iPhone se instala como en el Paso 2 (Añadir a pantalla de inicio). Para la App Store
> hace falta una cuenta de Apple Developer (99 USD/año); PWABuilder también genera ese paquete.

---

## ⚠️ Antes de compartirla con otros

- **Todos ven los mismos datos.** Jarvis, el segundo cerebro y el panel son de **una persona**: quien tenga la
  contraseña verá tu panel, tus notas y tu correo. Compártela solo con quien confíes.
- **Cada uso gasta tu saldo de Claude.** El agente de contenido y el equipo de agentes son los que más gastan.
- Si quieres que **cada persona tenga sus propios datos**, hace falta añadir cuentas de usuario: es otro proyecto.

## Integraciones en el servidor

En Render → **Environment** puedes añadir las mismas variables que en el `.env` (Notion, Twilio, Stripe, nicho del
agente de contenido…). Para WhatsApp pon `PUBLIC_BASE_URL=https://tu-direccion/jarvis` y en Twilio el webhook
`https://tu-direccion/jarvis/whatsapp`. Para Gmail/Calendar autoriza en tu ordenador
(`python -m jarvis.setup_google`) y sube el `token.json` resultante al disco del servidor (`/data/token.json`).

## Si algo falla

- **Pide la contraseña todo el rato** → es la de `APP_PASSWORD` en Render (distingue mayúsculas).
- **«Define …_WEB_TOKEN para usarlo fuera de localhost»** → falta `APP_PASSWORD` en Render.
- **Claude no responde** → revisa `ANTHROPIC_API_KEY` y que tengas saldo; `…/salud` debe decir `"claude": true`.
- **No sale «Instalar»** → la dirección tiene que ser `https://` (la de Render lo es) y abrirse en Chrome o Safari.
- Los registros del servidor están en Render → tu servicio → **Logs**.
