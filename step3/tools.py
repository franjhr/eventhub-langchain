"""Step 3. The assistant's tools: search events and look up an order.

The model only sees each tool's name, its arguments and its docstring, so the docstrings
explain when to use the tool and what it returns. The checks that matter (the email must
match the order) are done here, in code, not in the prompt.

Both tools return JSON text. The data is read on every call, so changes to the JSON files
are seen without restarting the server.
"""

import json
import unicodedata

from langchain.tools import tool

from common.data import load_events, load_orders

ORDER_NOT_FOUND = "No hay ningún pedido con ese número y ese email."


def normalize(text: str | None) -> str:
    """Lowercase, no accents and no surrounding spaces: 'Málaga ' -> 'malaga'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def to_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


@tool(parse_docstring=True)
def search_events(city: str | None = None, category: str | None = None) -> str:
    """Busca eventos de EventHub por ciudad y por categoría.

    Úsala siempre que el cliente pregunte qué eventos hay, por su fecha, su precio o si
    quedan entradas. Los dos filtros son opcionales: sin filtros devuelve todos los eventos.
    Devuelve un JSON con la lista "events": id, nombre, ciudad, categoría, fecha (AAAA-MM-DD),
    precio en euros y entradas disponibles (0 = agotado). Si la lista está vacía, no hay
    eventos con esos filtros.

    Args:
        city: ciudad del evento, por ejemplo "Valencia" o "Madrid".
        category: tipo de evento: "concierto", "teatro", "deporte", "comedia" o "feria".
    """
    wanted_city, wanted_category = normalize(city), normalize(category)
    events = [
        event
        for event in load_events()
        if (not wanted_city or normalize(event.get("city")) == wanted_city)
        and (not wanted_category or normalize(event.get("category")) == wanted_category)
    ]
    return to_json({"events": events})


@tool(parse_docstring=True)
def get_order(order_id: str, email: str) -> str:
    """Consulta el estado de un pedido de EventHub.

    Úsala cuando el cliente pregunte por un pedido suyo. Necesita el número de pedido y el
    email con el que se hizo la compra: si el cliente no ha dado los dos, pídeselos antes.
    Devuelve un JSON con el pedido (estado, evento, cantidad, total y fecha de compra) o con
    un "error" si no hay ningún pedido con ese número y ese email.

    Args:
        order_id: número de pedido, por ejemplo "PED-1001".
        email: email con el que se hizo la compra.
    """
    wanted_id, wanted_email = normalize(order_id), normalize(email)
    order = next(
        (order for order in load_orders() if normalize(order.get("id")) == wanted_id),
        None,
    )
    # A wrong email and a missing order give the same answer, so nobody can find out
    # which order numbers exist by trying them.
    if not wanted_id or not wanted_email or order is None or normalize(order.get("email")) != wanted_email:
        return to_json({"error": ORDER_NOT_FOUND})

    event = next((event for event in load_events() if event.get("id") == order.get("event_id")), {})
    return to_json(
        {
            "order_id": order["id"],
            "status": order.get("status"),
            "event": event.get("name"),
            "event_date": event.get("date"),
            "quantity": order.get("quantity"),
            "total": order.get("total"),
            "purchase_date": order.get("purchase_date"),
        }
    )
