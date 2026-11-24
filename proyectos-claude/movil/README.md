# 📱 Las 5 apps para Android (APK)

Cinco apps independientes que funcionan **en cualquier Android (6.0 o superior)**, sin servidor ni ordenador:
todo va dentro del teléfono y hablan directamente con la IA que elijas: **gratis** (Google Gemini, Groq, OpenRouter) o Claude.

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

## Primera vez: elige la IA (hay opción GRATIS)

Cada app te lo pide al usarla por primera vez (o en el botón **✳ IA**). Puedes elegir:

| IA | Precio | Cómo conseguir la clave |
|---|---|---|
| **Google Gemini 3.8 Flash** (el más fácil) | **Gratis**, pero pocos usos al día | aistudio.google.com/apikey → *Create API key* (con tu cuenta de Google, sin tarjeta) |
| **NVIDIA** (Kimi K2.6, GLM, Nemotron) | **Gratis**, ~40 peticiones/minuto: la que más rinde | build.nvidia.com → crear cuenta (verifica tu teléfono) → *Generate API Key* |
| **Groq** (Qwen 3.8) | **Gratis**, el más rápido (~1.000 peticiones/día) | console.groq.com/keys → *Create API Key* |
| **OpenRouter** (`openrouter/free`) | **Gratis**, pocos usos al día | openrouter.ai/keys → *Create Key* |
| **Claude** (Anthropic) | De pago | console.anthropic.com → Billing (saldo) → API Keys |

- La clave se guarda **solo en ese teléfono**. Si pasas las apps a otra persona, que ponga **su propia clave**.
- Con las IAs gratuitas, la búsqueda en internet (agente de contenido, «Busca», Jarvis) usa un buscador gratuito
  (DuckDuckGo y, si falla, Wikipedia). Claude trae su propia búsqueda web, más completa.
- Los planes gratuitos tienen límites: si sale «Has llegado al límite gratuito», espera un minuto (o al día siguiente).
  El **Equipo de agentes** hace muchas llamadas seguidas y es el que antes llega al límite.
- En el plan gratuito de Gemini, Google puede usar lo que escribes para mejorar sus productos: no pongas datos muy sensibles.
- **¿Cuál elegir?** Para empezar, Gemini (solo necesitas tu cuenta de Google). Si se te acaban los usos del día,
  pásate a **NVIDIA** (la mejor gratuita en calidad y cantidad) o a **Groq**. Claude sigue siendo el más capaz, pero es de pago.

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

Con **Gemini, Groq u OpenRouter (`:free`)** no pagas nada. Con **Claude**, cada uso se cobra en la cuenta de quien
puso la clave (lo más caro: Equipo de agentes y Agente de contenido); para gastar menos elige **Claude Sonnet 5.5** en **✳ IA**.

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
