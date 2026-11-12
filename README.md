# Asistente de EventHub con LangChain

Asistente de atención al cliente de EventHub, una plataforma de venta de entradas para eventos. Se construye con LangChain en tres pasos, y cada paso se puede ejecutar y revisar por separado.

## Pasos

Cada paso tiene su propio README con la explicación, las preguntas de prueba y los vídeos:

| Paso | Qué añade | Documentación | Estado |
|---|---|---|---|
| **1 · Cadena base** | Cadena LCEL que responde solo a partir de las políticas | **[Ver el paso 1 →](step1/README.md)** | ✅ Hecho |
| **2 · Memoria** | Memoria de la conversación, aislada por `session_id` y limitada a los últimos 10 mensajes | **[Ver el paso 2 →](step2/README.md)** | ✅ Hecho |
| **3 · Herramientas** | Herramientas para consultar eventos y pedidos | *Pendiente* | ⏳ Pendiente |

Para ver qué cambia de un paso al siguiente: `diff -r step1 step2`.

## Esquema

```
Navegador (web/)  ──►  common/server.py  ──►  stepN/app.py  ──►  LangChain  ──►  OpenAI
     ▲               POST /chat           respond(question,      paso 1: prompt | llm | parser
     │               valida la petición   session_id)            paso 2: create_agent + memoria
     └──────────────  {"response": "..."}  ◄──────────────────────────────────────────────┘
```

Todos los pasos comparten la misma API y la misma web. Cada paso solo aporta su función `respond(question, session_id)`.

## Qué hay en cada carpeta

- `step1/`, `step2/`, `step3/`: el código de cada paso y su README.
- `common/`: lo que comparten los tres pasos.
  - `config.py`: lee la clave y el modelo del `.env`.
  - `data.py`: carga los ficheros de `data/`.
  - `server.py`: aplicación FastAPI con `POST /chat`, `GET /info` y la web.
- `data/`: datos de EventHub: `policies.md`, `events.json` y `orders.json`.
- `web/`: página del chat (HTML, CSS y JavaScript). Muestra qué paso está corriendo.
- `demo/`: vídeos de las pruebas de cada paso.

## Cómo ejecutarlo

Necesitas Python 3.12 o superior y una clave de la API de OpenAI. Los comandos se ejecutan desde la raíz del proyecto.

1. Crea el entorno virtual e instala las dependencias:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. Copia `.env.example` a `.env` y escribe en `OPENAI_API_KEY` tu clave, que puedes crear en https://platform.openai.com/api-keys:

   ```bash
   cp .env.example .env
   ```

3. Arranca el paso que quieras probar (`step1`, `step2` o `step3`):

   ```bash
   .venv/bin/uvicorn step1.app:app --port 8001
   ```

4. Abre http://127.0.0.1:8001 y escribe un mensaje, o pruébalo desde la terminal:

   ```bash
   curl -X POST http://127.0.0.1:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "¿Cuál es la política de devoluciones?", "session_id": "prueba-0001"}'
   ```

**Modelo:** `OPENAI_MODEL` viene configurado como `gpt-6-luna`. Es un modelo de razonamiento, así que no admite cambiar `temperature`; en su lugar, la cadena usa `reasoning_effort="low"`. Si pones un modelo que no admita `reasoning_effort`, el asistente responderá «Asistente no disponible» y el error aparecerá en el log del servidor.

## Límites

- 2000 caracteres por mensaje y `session_id` de 8 a 64 caracteres, solo letras, números y guiones (`common/server.py`).
- Si editas `data/policies.md` o el prompt de un paso, reinicia el servidor: se leen al arrancar.
- Desde el paso 2, la memoria de las conversaciones está en la RAM: se pierde al reiniciar el servidor.
