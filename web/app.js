const messages = document.getElementById("messages");
const form = document.getElementById("form");
const input = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const newButton = document.getElementById("new-button");

const WELCOME = "Hola, soy el asistente de EventHub. Pregúntame por eventos, entradas, pedidos o nuestras políticas.";

// Each conversation has its own session_id. A new one is created on page load and on "Nueva conversación".
let sessionId = crypto.randomUUID();

// textContent, not innerHTML: neither the user nor the model must be able to inject HTML.
function show(text, type) {
  const bubble = document.createElement("div");
  bubble.className = `message ${type}`;
  bubble.textContent = text;
  messages.append(bubble);
  messages.scrollTop = messages.scrollHeight;
}

function startConversation() {
  sessionId = crypto.randomUUID();
  messages.replaceChildren();
  show(WELCOME, "bot");
  input.focus();
}

async function requestResponse(message) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  if (typeof data.response !== "string" || !data.response.trim()) {
    throw new Error("Respuesta sin texto");
  }
  // tools only comes from step 3; anything that is not a list is ignored.
  return { text: data.response, tools: Array.isArray(data.tools) ? data.tools : [] };
}

// ---------------------------------------------------------------------------
// Tools used in the turn (step 3): a section above the answer, inside the same bubble.
// Everything is built with createElement and textContent, never innerHTML.
// ---------------------------------------------------------------------------

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const euros = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

function formatPrice(value) {
  return typeof value === "number" ? euros.format(value) : String(value ?? "—");
}

// "2026-12-12" -> "12/12/2026"; anything else is shown as it comes.
function formatDate(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value ?? ""));
  return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value ?? "—");
}

function parseResult(result) {
  try {
    return JSON.parse(result);
  } catch {
    return null;
  }
}

// get_order(order_id="PED-1001", email="ana@…"): the call as the model made it, without empty arguments.
function formatArguments(args) {
  if (!args || typeof args !== "object") return "()";
  const shown = Object.entries(args)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([name, value]) => `${name}=${JSON.stringify(value)}`);
  return `(${shown.join(", ")})`;
}

// Short label next to the call: what came back, at a glance.
function resultChip(data) {
  if (data && Array.isArray(data.events)) {
    const count = data.events.length;
    return count === 0
      ? { text: "0 eventos", tone: "empty" }
      : { text: `${count} evento${count === 1 ? "" : "s"}`, tone: "ok" };
  }
  if (data && typeof data.error === "string") return { text: "Sin coincidencia", tone: "bad" };
  if (data && typeof data.status === "string") return { text: `Pedido ${data.status}`, tone: "ok" };
  return { text: "Resultado", tone: "neutral" };
}

function eventsTable(events) {
  const wrapper = element("div", "tool-table");
  const table = element("table");
  const head = table.createTHead().insertRow();
  for (const title of ["Evento", "Ciudad", "Fecha", "Precio", "Entradas"]) {
    head.append(element("th", "", title));
  }
  const body = table.createTBody();
  for (const event of events) {
    const row = body.insertRow();
    const tickets = Number(event.available_tickets);
    row.append(
      element("td", "", String(event.name ?? "—")),
      element("td", "", String(event.city ?? "—")),
      element("td", "nowrap", formatDate(event.date)),
      element("td", "nowrap number", formatPrice(event.price)),
      tickets === 0
        ? element("td", "nowrap sold-out", "Agotado")
        : element("td", "nowrap number", String(event.available_tickets ?? "—")),
    );
  }
  wrapper.append(table);
  return wrapper;
}

function orderSheet(order) {
  const sheet = element("dl", "tool-sheet");
  const rows = [
    ["Pedido", order.order_id],
    ["Estado", order.status],
    ["Evento", order.event],
    ["Fecha del evento", formatDate(order.event_date)],
    ["Entradas", order.quantity],
    ["Total", formatPrice(order.total)],
    ["Comprado el", formatDate(order.purchase_date)],
  ];
  for (const [label, value] of rows) {
    sheet.append(element("dt", "", label), element("dd", "", String(value ?? "—")));
  }
  return sheet;
}

// The readable view of the result, plus the raw JSON that the model actually receives.
function resultView(result, data) {
  const view = element("div", "tool-body");
  if (data && Array.isArray(data.events)) {
    view.append(
      data.events.length
        ? eventsTable(data.events)
        : element("p", "tool-note", "Ningún evento cumple los filtros."),
    );
  } else if (data && typeof data.error === "string") {
    view.append(element("p", "tool-note bad", data.error));
  } else if (data && typeof data.status === "string") {
    view.append(orderSheet(data));
  }

  const raw = element("details", "tool-raw");
  raw.append(element("summary", "", "JSON que recibe el modelo"));
  raw.append(element("pre", "", data ? JSON.stringify(data, null, 2) : String(result ?? "")));
  view.append(raw);
  return view;
}

function toolBlock(tool) {
  const data = parseResult(tool.result);
  const chip = resultChip(data);

  const block = element("details", "tool");
  const summary = element("summary");
  const call = element("code", "tool-call");
  call.append(element("span", "tool-name", String(tool.name ?? "?")), element("span", "tool-args", formatArguments(tool.args)));
  summary.append(call, element("span", `chip ${chip.tone}`, chip.text));
  block.append(summary, resultView(tool.result, data));
  return block;
}

function showBotAnswer({ text, tools }) {
  if (!tools.length) {
    show(text, "bot");
    return;
  }
  const bubble = element("div", "message bot has-tools");
  const section = element("div", "tools");
  section.append(element("p", "tools-title", tools.length === 1 ? "Herramienta usada" : "Herramientas usadas"));
  for (const tool of tools) {
    section.append(toolBlock(tool));
  }
  bubble.append(section, element("div", "answer", text));
  messages.append(bubble);
  messages.scrollTop = messages.scrollHeight;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  show(message, "user");
  input.value = "";
  sendButton.disabled = true;
  newButton.disabled = true;

  try {
    showBotAnswer(await requestResponse(message));
  } catch (error) {
    console.error(error);
    show("No he podido obtener una respuesta. Inténtalo de nuevo.", "error");
  } finally {
    sendButton.disabled = false;
    newButton.disabled = false;
    input.focus();
  }
});

// Shows in the header which step of the assignment is running.
async function showStep() {
  try {
    const response = await fetch("/info");
    const data = await response.json();
    if (typeof data.step === "string") {
      document.getElementById("step").textContent = data.step;
      document.title = `EventHub · ${data.step}`;
    }
  } catch (error) {
    console.error(error);
  }
}

newButton.addEventListener("click", startConversation);

showStep();
startConversation();
