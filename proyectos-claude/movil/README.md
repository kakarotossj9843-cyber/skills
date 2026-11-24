# 📱 Las 5 apps para Android (APK)

Cinco apps independientes que funcionan **en cualquier Android (6.0 o superior)**, sin servidor ni ordenador:
todo va dentro del teléfono y hablan directamente con Claude.

| App | Archivo | Qué hace en el móvil |
|---|---|---|
| 🤖 Jarvis | `apk/Jarvis.apk` | Asistente: agenda, tareas, memoria, búsquedas en internet y WhatsApp/correos/llamadas listos para enviar con un toque |
| 🧠 Segundo cerebro | `apk/Segundo-cerebro.apk` | Tus notas de vida, negocio y áreas; Claude las busca, ordena y amplía; grafo visual |
| 📊 Panel de tu vida | `apk/Panel-de-tu-vida.apk` | Ventas, hábitos, tareas, negocio y dinero con gráficos, en soles, dólares, bolivianos y euros |
| 🌙 Agente de contenido | `apk/Agente-de-contenido.apk` | Investiga a la competencia, mira las noticias y escribe tus guiones |
| 👑 Equipo de agentes | `apk/Equipo-de-agentes.apk` | Un jefe que reparte tu encargo entre Busca, Escribe, Diseña y Revisa |

## Instalar

1. Descarga el `.apk` en el teléfono (desde GitHub, o que te lo pasen por WhatsApp/Drive).
2. Ábrelo. Android pedirá **«Permitir instalar apps de esta fuente»**: actívalo para tu navegador/WhatsApp y pulsa **Instalar**.
3. Si sale *Play Protect* avisando de que es una app desconocida: **«Instalar de todas formas»** (es normal en apps que no vienen de Google Play).

## Primera vez: tu clave de Claude

Cada app te la pide al usarla por primera vez (o en el botón **✳ Claude**):

1. Entra en **console.anthropic.com** y crea una cuenta.
2. En **Billing** añade saldo (unos pocos dólares dan para mucho).
3. En **API Keys → Create Key**, copia la clave (`sk-ant-...`) y pégala en la app.

La clave se guarda **solo en ese teléfono**. Si le pasas las apps a otra persona, que ponga **su propia clave**:
así cada uno paga lo suyo y nadie ve tus datos.

## Tus datos

- Todo se guarda **en el teléfono** (no hay servidor). Si desinstalas la app, se borran.
- Usa **💾 Copia → Guardar copia** de vez en cuando (y antes de cambiar de móvil). Se guarda un archivo `.json`
  que puedes mandar a Drive o a tu correo, y luego **Restaurar una copia** en el móvil nuevo.
- El panel trae **«Cargar datos de ejemplo»** para verlo funcionando antes de meter los tuyos.

## Diferencias con la versión de servidor

- **Jarvis** no entra en tu Gmail, Google Calendar ni Notion (eso necesita un servidor). En su lugar lleva su propia
  agenda y tareas, y prepara WhatsApp, correos y llamadas para que los envíes tú con un toque.
- **Agente de contenido**: en el móvil trabaja cuando pulsas ▶ (o al abrir la app cada día, si lo activas en ⚙️ Ajustes).
  Deja la app abierta unos minutos mientras trabaja.
- **Panel**: sin importación de Stripe (necesitaría guardar una clave secreta en el móvil).

## Coste

Cada uso de Claude se cobra en la cuenta de quien puso la clave. Lo más caro es el **Equipo de agentes** y el
**Agente de contenido** (muchas llamadas y búsquedas web). Para gastar menos, en **✳ Claude** elige
**Claude Sonnet 5.5**. El consumo se ve en console.anthropic.com → Usage.

## Volver a fabricar los APK (si cambias algo)

En Ubuntu/Debian (o WSL en Windows):

```bash
sudo apt install aapt apksigner zipalign android-sdk-platform-23 dalvik-exchange default-jdk
python3 movil/android/construir.py          # las 5  → movil/apk/
python3 movil/android/construir.py panel    # solo una
```

- Cada app es una web (`movil/<app>/index.html` + `datos.js`) con el código común de `movil/comun/`,
  metida en una cáscara Android mínima (`movil/android/MainActivity.java`).
- **La firma** (`movil/android/firma.keystore`) no se sube a GitHub. Guárdala: para que una versión nueva se instale
  encima de la anterior sin perder datos, tiene que estar firmada con la misma. Para subir de versión:
  `APK_VERSION_CODE=2 APK_VERSION_NAME=1.1 python3 movil/android/construir.py`.
- Para publicarlas en Google Play hace falta una cuenta de desarrollador (25 USD) y generar el formato `.aab`
  (con Android Studio o PWABuilder).
