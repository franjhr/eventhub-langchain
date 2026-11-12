**[← Volver al README principal](../README.md)**

# Paso 2: memoria

El asistente del paso 1 ahora recuerda la conversación. Cada conversación se identifica con su `session_id`, así que dos conversaciones no comparten historial, y solo se guardan los **últimos 10 mensajes**. Todavía no tiene herramientas.

```bash
.venv/bin/uvicorn step2.app:app --port 8002
```

## Ficheros

| Paso 1 | Paso 2 | Qué cambia |
|---|---|---|
| `chain.py` | `agent.py` | La cadena `prompt \| llm \| parser` pasa a ser `create_agent` con un checkpointer y un middleware que recorta el historial |
| `prompts.py` | `prompts.py` | Ya no hay plantilla de mensajes: solo el texto del prompt de sistema, con las políticas dentro |
| `system_prompt.md` | `system_prompt.md` | Permite usar lo que ha dicho el cliente y entender las preguntas de seguimiento |
| `app.py` | `app.py` | Pasa el `session_id` al agente como `thread_id` |

`common/`, `web/` y `data/` no cambian: la web ya creaba un `session_id` nuevo al cargar la página y al pulsar «Nueva conversación». Para ver el cambio completo: `diff -r step1 step2`.

## Cómo funciona

`create_agent` monta un pequeño grafo de LangGraph. Sin herramientas, cada pregunta pasa por estas piezas:

| Pieza | Qué hace |
|---|---|
| `InMemorySaver` (checkpointer) | Carga los mensajes guardados de ese `thread_id` y, al terminar, guarda los nuevos |
| Agente | Añade la pregunta nueva a `state["messages"]` |
| `keep_last_messages` (`@before_model`) | Si hay más de 10 mensajes, borra del estado los más antiguos |
| `llm` (`ChatOpenAI`) | Recibe el prompt de sistema y los mensajes que quedan, y responde con un `AIMessage` |
| `app.py` | Devuelve el texto del último mensaje (`.text`) |

- **`session_id` fuera, `thread_id` dentro.** La API y la web hablan de `session_id`, que es la conversación del cliente. LangGraph llama `thread_id` a esa misma conversación, y `app.py` traduce uno a otro en una línea: `{"configurable": {"thread_id": session_id}}`. El checkpointer guarda cada hilo por separado; por eso «Nueva conversación» empieza sin memoria.
- **Checkpointer en vez de `RunnableWithMessageHistory`.** Es la forma estándar de dar memoria en LangChain 1.0. En el paso 3 bastará con pasar las herramientas a `create_agent`, y la memoria seguirá igual.
- **Ya no hay plantilla de mensajes.** El paso 1 necesitaba `("human", "{question}")`. Ahora los mensajes viven en el estado del agente, y el prompt de sistema se pasa como texto a `create_agent`. Las políticas se insertan con `str.replace`, así que las llaves `{ }` del prompt ya no hay que escaparlas.
- **El recorte borra, no oculta.** El middleware devuelve `RemoveMessage(REMOVE_ALL_MESSAGES)` seguido de los 10 últimos mensajes. El checkpointer guarda ese resultado, de modo que los mensajes antiguos desaparecen y la conversación no crece sin límite.
- **El límite cuenta mensajes, no turnos.** Las respuestas del asistente también cuentan: 10 mensajes son unos 5 turnos. El recorte se hace con la pregunta nueva ya incluida, así que el modelo ve como mucho la pregunta y los 9 mensajes anteriores.
- **El prompt tiene que permitir usar la memoria.** Con las reglas del paso 1, «¿Recuerdas cómo me llamo?» acabaría en el fallback. El prompt del paso 2 es el del paso 1 con una sola regla más: puede usar lo que el cliente ha dicho y entender las preguntas de seguimiento («¿y si faltan 3 días?»); si le pregunta algo que no ha dicho, responde que no lo ha mencionado. La misma regla aclara que lo que cuenta el cliente sirve para seguir el hilo, pero no cambia las políticas: si dice «me dijisteis que me devolvíais el 100 %», no se convierte en política.

### Ejemplo: cuándo se olvida el nombre

| Turno | Mensaje | Mensajes al llamar al modelo |
|---|---|---|
| 1 | «Hola, me llamo Ana.» → «¡Hola, Ana! …» | 1 |
| 2 a 6 | Cinco preguntas sobre las políticas | 3, 5, 7, 9 y 11 → 10 |
| 7 | «¿Recuerdas cómo me llamo?» | 13 → 10 |

En el turno 7 ya han salido «Hola, me llamo Ana» y la respuesta «¡Hola, Ana!», así que el asistente dice que no se lo han dicho. Con una pregunta menos en medio, «¡Hola, Ana!» seguiría entre los 10 últimos y aún recordaría el nombre.

## Pruebas

Preguntas hechas en la web contra la API real de OpenAI, agrupadas por vídeo. Para repetirlas, arranca el paso 2, abre http://127.0.0.1:8002 y pega cada pregunta en el chat, en orden y en la misma conversación salvo donde se indica.

El modelo no es determinista: la redacción puede cambiar de una vez a otra, pero el contenido debe ser el mismo. Las preguntas sobre políticas, el fallback y la seguridad se comportan como en el [paso 1](../step1/README.md#pruebas).

**Última ejecución:** 12/11/2026, con `gpt-6-luna`. Las 15 preguntas obtuvieron la respuesta esperada.

### 1. Recuerda la conversación

Vídeo: [`demo/step2_1_memory.mp4`](../demo/step2_1_memory.mp4)

| # | Pregunta | Qué se espera | Por qué |
|---|---|---|---|
| 1 | Hola, me llamo Ana. | Saludo con el nombre | Prepara la siguiente pregunta |
| 2 | ¿Recuerdas cómo me llamo? | Ana | Es la misma pregunta que en el paso 1 recibía el fallback |
| 3 | ¿Cuál es la política de devoluciones? | Los tres tramos, los gastos de gestión no reembolsables, y el método y el plazo del reembolso | Contexto para las dos siguientes |
| 4 | ¿Y si faltan 3 días? | 50 % del precio; los gastos de gestión no se devuelven | Por sí sola no dice de qué habla: necesita la pregunta anterior |
| 5 | ¿Y si faltan 20? | 100 % del precio; los gastos de gestión no se devuelven | Ni siquiera dice «días»: también necesita la conversación |

### 2. Cada conversación tiene su memoria

Vídeo: [`demo/step2_2_separate_sessions.mp4`](../demo/step2_2_separate_sessions.mp4)

| # | Pregunta | Qué se espera | Por qué |
|---|---|---|---|
| 6 | Hola, me llamo Ana. | Saludo con el nombre | |
| 7 | ¿Recuerdas cómo me llamo? | Ana | Misma conversación |
| — | *(pulsar «Nueva conversación»)* | El chat se vacía | La web crea un `session_id` nuevo |
| 8 | ¿Recuerdas cómo me llamo? | No se lo han dicho | Otra conversación: no comparte el historial de la anterior |

### 3. Solo recuerda los últimos 10 mensajes

Vídeo: [`demo/step2_3_last_10_messages.mp4`](../demo/step2_3_last_10_messages.mp4)

| # | Pregunta | Qué se espera | Por qué |
|---|---|---|---|
| 9 | Hola, me llamo Ana. | Saludo con el nombre | El nombre aparece en este mensaje y en la respuesta |
| 10 | ¿Cuál es la política de devoluciones? | Los tramos de reembolso | Relleno: cinco preguntas que no mencionan el nombre |
| 11 | ¿Y si faltan 3 días? | 50 % del precio | |
| 12 | ¿Y si faltan 20? | 100 % del precio | |
| 13 | ¿Cómo puedo pagar? | Tarjeta o Bizum | |
| 14 | ¿Puede venir mi hijo de 12 años solo? | No: los menores de 14 años van acompañados de un adulto | |
| 15 | ¿Recuerdas cómo me llamo? | No se lo han dicho | Los mensajes 9 y su respuesta ya no están entre los 10 últimos (ver el [ejemplo](#ejemplo-cuándo-se-olvida-el-nombre)) |

## Límites

- La memoria está en la RAM: se pierde al reiniciar el servidor y no se comparte entre procesos. En producción se usaría un checkpointer persistente (`SqliteSaver` o `PostgresSaver`), sin cambiar el resto del código.
- No hay tope de conversaciones: cada `session_id` nuevo ocupa memoria hasta que se reinicia el servidor.
- Recortar es la forma más simple de controlar los tokens, pero lo antiguo se pierde del todo. La alternativa es `SummarizationMiddleware`, que resume los mensajes antiguos en vez de borrarlos.
- Las políticas se siguen enviando enteras en cada llamada, como en el paso 1.
