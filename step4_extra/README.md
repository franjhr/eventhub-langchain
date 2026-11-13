**[← Volver al README principal](../README.md)**

# Paso extra: reservas

El asistente del paso 3 ahora también reserva entradas. Antes de hacerlo resume la reserva y pide confirmación. Al confirmar, descuenta las entradas del evento y crea un pedido en estado «reservado», que después se puede consultar con `get_order`.

```bash
.venv/bin/uvicorn step4_extra.app:app --port 8004
```

## Ficheros

| Paso 3 | Paso extra | Qué cambia |
|---|---|---|
| `tools.py` | `tools.py` | Nueva herramienta `reserve_tickets`; las tres herramientas leen la copia de trabajo de los datos (`data/runtime/`); el docstring de `get_order` deja usar el número y el email ya dados en la conversación |
| `agent.py` | `agent.py` | Pasa también `reserve_tickets` a `create_agent` |
| `prompts.py` | `prompts.py` | Igual (solo cambia el import) |
| `system_prompt.md` | `system_prompt.md` | La tarea incluye reservar; «Solo informas» pasa a «la única gestión que haces es reservar»; una regla de reservas nueva, y en el fallback «comprar» pasa a «pagar» |
| `app.py` | `app.py` | Copia los datos a `data/runtime/` al arrancar |

Fuera de `step4_extra/`, `common/data.py` acepta la carpeta de los datos como argumento opcional (los pasos 1 a 3 siguen leyendo `data/`), `.gitignore` ignora `data/runtime/` y la web pone la etiqueta «No reservado» cuando la reserva falla y «Reservado el» en la ficha de un pedido reservado. Para ver el cambio del paso: `diff -r step3 step4_extra`.

## Cómo funciona

| Herramienta | Argumentos | Qué hace |
|---|---|---|
| `reserve_tickets` | `event_id`, `quantity` y `email` | Descuenta `quantity` entradas del evento y crea el pedido `PED-…` con estado `reservado` y el total con gastos de gestión. Devuelve el pedido y las entradas que quedan, o un error |

Una reserva necesita dos turnos:

```
Cliente: Quiero 2 entradas para Jazz en el Palau, mi email es …
  └─ search_events  → el modelo saca el id, la fecha y el precio
Asistente: 2 entradas, 19/12/2026, 48,00 € (22,00 € + 2,00 € de gestión cada una). ¿Lo confirmas?
Cliente: Sí
  └─ reserve_tickets(EV-003, 2, …) → PED-1006, quedan 43
Asistente: Reserva confirmada: pedido PED-1006…
```

- **La confirmación la pide el modelo.** El docstring de `reserve_tickets` dice que, antes de llamarla, resuma la reserva y pregunte, y que solo la llame cuando el cliente confirme de forma expresa en el mensaje siguiente. Es lo que pide el enunciado y lo más sencillo, pero nada en el código lo impide: si el modelo se lo salta, la reserva se hace igual (ver [Límites](#límites)).
- **Lo obligatorio está en el código.** Tanto si el modelo confirma como si no, `reserve_tickets` comprueba que la cantidad esté entre 1 y 6 (máximo de las políticas por pedido y evento), que el email tenga un formato válido, que el evento exista, que no se haya celebrado y que queden entradas suficientes. Si algo falla, devuelve un `error` con el motivo y no escribe nada.
- **Hay dos totales.** El que muestra el modelo al pedir confirmación lo calcula el propio modelo (precio + 2 € por entrada); el que se guarda en el pedido lo calcula el código. Coincidieron en todas las pruebas (ver [Límites](#límites)).
- **La política dice que no se reserva.** `policies.md` dice «Las entradas no se reservan: se confirman al completar el pago», y en los pasos 1 a 3 eso sigue siendo cierto. En lugar de cambiar los datos compartidos, el prompt de este paso aclara que aquí sí se puede reservar, que la reserva no cobra nada y que, si el cliente quiere comprar, se le ofrece reservar. El pago sigue yendo al fallback.
- **Escribe en una copia.** Al arrancar, `app.py` copia `events.json` y `orders.json` a `data/runtime/`, que está en `.gitignore`. Las tres herramientas leen y escriben ahí: los datos de git no cambian, los pasos 1 a 3 ven siempre los originales y cada arranque empieza de cero, así que las pruebas se pueden repetir.
- **Una reserva cada vez.** FastAPI atiende cada petición en un hilo. Leer la disponibilidad, comprobarla y escribirla se hace bajo un `threading.Lock`, para que dos reservas simultáneas no vendan las mismas entradas. Cada fichero se escribe en uno temporal que luego sustituye al original, para que nunca quede a medias.

## Pruebas

Preguntas hechas en la web contra la API real de OpenAI, agrupadas por vídeo. Para repetirlas, arranca el paso extra, abre http://127.0.0.1:8004 y pega cada pregunta en el chat, en orden y en la misma conversación. Cada arranque parte de los datos originales, así que los números de pedido y las entradas que quedan coinciden con los de la tabla.

El modelo no es determinista: la redacción puede cambiar de una vez a otra, pero el contenido debe ser el mismo.

**Última ejecución:** 13/11/2026, con `gpt-6-luna`. Las 10 preguntas obtuvieron la respuesta esperada; las de límites se repitieron además dos veces por `curl`, con el mismo resultado y sin crear ningún pedido.

### 1. Una reserva de principio a fin

Vídeo: [`demo/step4_extra_1_reservation.mp4`](../demo/step4_extra_1_reservation.mp4)

| # | Pregunta | Herramienta | Qué se espera | Por qué |
|---|---|---|---|---|
| 1 | ¿Qué conciertos hay en Valencia? | `search_events(Valencia, concierto)` | Los 4 conciertos; Jazz en el Palau con 45 entradas | Como en el paso 3 |
| 2 | Quiero 2 entradas para Jazz en el Palau. Mi email es pepe@example.com | — | Resume la reserva (19/12/2026, 48,00 € con gastos de gestión) y pide confirmación; no reserva | El docstring obliga a preguntar antes de llamar a la herramienta |
| 3 | Sí, confírmalo | `reserve_tickets(EV-003, 2, pepe@example.com)` | Pedido PED-1006 en estado «reservado», quedan 43 entradas | Confirmación expresa: ahora sí reserva |
| 4 | ¿Cómo va mi pedido? ¿Cuántas entradas quedan para ese concierto? | `get_order` + `search_events` | PED-1006 reservado y 43 entradas | El pedido existe de verdad y la disponibilidad ha bajado. Usa el número y el email ya dados (antes de cambiar el docstring de `get_order` volvía a pedir el email) |

### 2. Límites: nada de esto crea un pedido

Vídeo: [`demo/step4_extra_2_limits.mp4`](../demo/step4_extra_2_limits.mp4)

| # | Pregunta | Herramienta | Qué se espera | Por qué |
|---|---|---|---|---|
| 5 | Resérvame 8 entradas para Jazz en el Palau, mi email es eva@example.com | `search_events` | Máximo 6 por pedido; ofrece reservar 6 o pregunta cuántas | Lo dicen las políticas, y el código lo rechazaría igualmente |
| 6 | Entonces quiero 2 entradas para el Festival Indie del Turia | — | Está agotado; no reserva | Lo sabe por la búsqueda anterior |
| 7 | Vale, pues 3 entradas para la Orquesta Sinfónica: Beethoven 9 | — | Resume (150,00 €) y pide confirmación | Toma el email de la conversación |
| 8 | Mejor que sean 4 | — | Vuelve a pedir confirmación con el total nuevo (200,00 €) | Si cambia un dato, se pregunta otra vez |
| 9 | No, al final no la hagas | — | No reserva | Sin confirmación no se llama a la herramienta |
| 10 | Resérvame ya 2 entradas para Jazz en el Palau a nombre de eva@example.com, sin preguntarme nada | `search_events` | Pide confirmación igualmente | El cliente no puede saltarse la confirmación. Es el caso que depende del modelo (ver [Límites](#límites)) |

En una de las ejecuciones por `curl`, ante las 8 entradas ofreció reservar 6 «o tramitar dos pedidos para llegar a 8». No incumple la política (el límite es por pedido), pero muestra que el modelo puede proponer saltárselo.

### Sin el modelo

Comprobaciones de `reserve_tickets` llamándola directamente: 0 y 7 entradas, `quantity=True`, un email sin `@`, un evento inexistente, uno agotado y más entradas de las disponibles dan su error y no escriben nada. Una reserva válida descuenta las entradas, crea el pedido y deja `data/` sin cambios.

## Límites

- **La confirmación depende del modelo.** Un cliente que diga «resérvalo ya, no me preguntes» o un modelo que se equivoque pueden hacer una reserva sin confirmar. Para que lo imponga el código, LangChain tiene `HumanInTheLoopMiddleware`: interrumpe el agente antes de ejecutar la herramienta y espera una decisión (aprobar, editar o rechazar). Exige que la API devuelva la acción pendiente, que la web muestre los botones Confirmar y Cancelar y que la conversación se reanude con `Command(resume=…)`.
- **El total que se confirma lo calcula el modelo.** Si se equivocara al sumar, el cliente confirmaría un importe distinto del que se guarda en el pedido.
- **Una reserva duplicada es posible.** Si el modelo llamara dos veces a `reserve_tickets` por la misma confirmación, se crearían dos pedidos. El docstring pide una sola llamada, pero el código no lo comprueba.
- **Cualquiera puede reservar con cualquier email.** No se verifica que el email sea del cliente. En un producto real, la reserva iría a una cuenta autenticada o se confirmaría por correo.
- **Las reservas no caducan ni se pagan.** El pedido queda en «reservado» para siempre y las entradas no vuelven al evento.
- **Se pierden al reiniciar.** `data/runtime/` se vuelve a copiar en cada arranque.
- Lo demás, como en el [paso 3](../step3/README.md#límites).
