"""Extra step. The assistant's tools: search events, look up an order and reserve tickets.

search_events and get_order are the ones from step 3, but they read the working copy of
the data (data/runtime/) instead of data/. reserve_tickets is new: it is the only tool that
writes. It takes tickets away from events.json and adds an order to orders.json.

The confirmation before reserving is asked by the model (the docstring tells it when to
call the tool). The checks that must always hold (the event exists, there are enough
tickets, at most 6 per order) are done here, in code.
"""

import json
import os
import re
import shutil
import threading
import unicodedata
from datetime import date
from pathlib import Path

from langchain.tools import tool

from common.config import DATA_DIR
from common.data import load_events, load_orders

# Working copy of events.json and orders.json: the reservations are written here, so the
# data in git (and what steps 1 to 3 read) never changes. It is in .gitignore.
RUNTIME_DIR = DATA_DIR / "runtime"

ORDER_NOT_FOUND = "No hay ningún pedido con ese número y ese email."
MAX_TICKETS_PER_ORDER = 6  # policies.md: «Máximo 6 entradas por pedido y evento».
MANAGEMENT_FEE = 2.0  # policies.md: «gastos de gestión (2 € por entrada)».
RESERVED = "reservado"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# FastAPI runs each request in its own thread. Two reservations at the same time must not
# read the same availability and both write it: the read-check-write is done under a lock.
_write_lock = threading.Lock()


def reset_runtime_data() -> None:
    """Copies the original events.json and orders.json to RUNTIME_DIR.

    Called when the server starts: each run begins with the data in git, so the tests
    can be repeated. The reservations of a previous run are lost.
    """
    RUNTIME_DIR.mkdir(exist_ok=True)
    for name in ("events.json", "orders.json"):
        shutil.copyfile(DATA_DIR / name, RUNTIME_DIR / name)


def save_json(path: Path, data: list[dict]) -> None:
    """Writes the file atomically: a temporary file that then replaces the old one.

    If the process stops in the middle, the old file stays whole instead of half written.
    """
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def normalize(text: str | None) -> str:
    """Lowercase, no accents and no surrounding spaces: 'Málaga ' -> 'malaga'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def to_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def error(message: str) -> str:
    return to_json({"error": message})


def order_summary(order: dict, event: dict) -> dict:
    """The order as the tools return it (the web page shows it as a sheet)."""
    return {
        "order_id": order["id"],
        "status": order.get("status"),
        "event": event.get("name"),
        "event_date": event.get("date"),
        "quantity": order.get("quantity"),
        "total": order.get("total"),
        "purchase_date": order.get("purchase_date"),
    }


def next_order_id(orders: list[dict]) -> str:
    """PED- followed by the highest existing number plus one: PED-1006 -> PED-1007."""
    numbers = [
        int(match.group(1))
        for order in orders
        if (match := re.fullmatch(r"PED-(\d+)", str(order.get("id", ""))))
    ]
    return f"PED-{max(numbers, default=1000) + 1}"


def check_request(event_id: str, quantity: int, email: str) -> tuple[dict | None, str | None]:
    """The rules of a reservation, except the tickets left: (event, None) or (None, error).

    The tickets left are checked in reserve_tickets, under the lock, just before writing.
    """
    # bool is a subclass of int: True would count as 1 ticket.
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        return None, "La cantidad debe ser un número entero de entradas."
    if not 1 <= quantity <= MAX_TICKETS_PER_ORDER:
        return None, f"Se pueden reservar entre 1 y {MAX_TICKETS_PER_ORDER} entradas por pedido."
    if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email.strip()):
        return None, "El email no es válido."
    event = next(
        (event for event in load_events(RUNTIME_DIR) if normalize(event.get("id")) == normalize(str(event_id))),
        None,
    )
    if event is None:
        return None, "No hay ningún evento con ese id."
    # ISO dates (AAAA-MM-DD) compare correctly as text.
    if str(event.get("date", "")) < date.today().isoformat():
        return None, "El evento ya se ha celebrado."
    return event, None


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
        for event in load_events(RUNTIME_DIR)
        if (not wanted_city or normalize(event.get("city")) == wanted_city)
        and (not wanted_category or normalize(event.get("category")) == wanted_category)
    ]
    return to_json({"events": events})


@tool(parse_docstring=True)
def get_order(order_id: str, email: str) -> str:
    """Consulta el estado de un pedido de EventHub.

    Úsala cuando el cliente pregunte por un pedido suyo. Necesita el número de pedido y el
    email con el que se hizo la compra: si el cliente no ha dado los dos en la conversación,
    pídeselos antes.
    Devuelve un JSON con el pedido (estado, evento, cantidad, total y fecha de compra) o con
    un "error" si no hay ningún pedido con ese número y ese email.

    Args:
        order_id: número de pedido, por ejemplo "PED-1001".
        email: email con el que se hizo la compra.
    """
    wanted_id, wanted_email = normalize(order_id), normalize(email)
    order = next(
        (order for order in load_orders(RUNTIME_DIR) if normalize(order.get("id")) == wanted_id),
        None,
    )
    # A wrong email and a missing order give the same answer, so nobody can find out
    # which order numbers exist by trying them.
    if not wanted_id or not wanted_email or order is None or normalize(order.get("email")) != wanted_email:
        return error(ORDER_NOT_FOUND)

    event = next(
        (event for event in load_events(RUNTIME_DIR) if event.get("id") == order.get("event_id")),
        {},
    )
    return to_json(order_summary(order, event))


@tool(parse_docstring=True)
def reserve_tickets(event_id: str, quantity: int, email: str) -> str:
    """Reserva entradas de un evento de EventHub y crea un pedido en estado "reservado".

    Necesita el id del evento (sácalo de search_events), el número de entradas y el email
    del cliente: si falta alguno, pídeselo antes. Antes de llamarla, di al cliente qué vas a
    reservar (evento, fecha, número de entradas, email y total: precio más 2 € de gastos de
    gestión por entrada) y pregúntale si lo confirma. Llámala solo cuando el cliente lo
    confirme de forma expresa en su mensaje siguiente; si cambia algún dato, vuelve a
    preguntar. Llámala una sola vez por reserva confirmada.
    Devuelve un JSON con el pedido creado (número, estado, evento, fecha, entradas, total y
    fecha de reserva) y las entradas que quedan, o con un "error" que dice por qué no se ha
    reservado.

    Args:
        event_id: id del evento, por ejemplo "EV-001".
        quantity: número de entradas, de 1 a 6.
        email: email del cliente, al que irá el pedido.
    """
    with _write_lock:
        found, problem = check_request(event_id, quantity, email)
        if found is None:
            return error(problem)
        email = email.strip()
        # The same event, but from the list that will be written back.
        events = load_events(RUNTIME_DIR)
        event = next(event for event in events if event.get("id") == found["id"])
        available = int(event.get("available_tickets", 0))
        if available == 0:
            return error("El evento está agotado.")
        if quantity > available:
            return error(f"Solo quedan {available} entradas para este evento.")

        orders = load_orders(RUNTIME_DIR)
        order = {
            "id": next_order_id(orders),
            "email": email,
            "event_id": event["id"],
            "quantity": quantity,
            "total": round(quantity * (float(event["price"]) + MANAGEMENT_FEE), 2),
            "status": RESERVED,
            "purchase_date": date.today().isoformat(),
        }
        event["available_tickets"] = available - quantity
        orders.append(order)
        save_json(RUNTIME_DIR / "events.json", events)
        save_json(RUNTIME_DIR / "orders.json", orders)

    return to_json({**order_summary(order, event), "tickets_left": event["available_tickets"]})
