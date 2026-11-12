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
  return data.response;
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
    show(await requestResponse(message), "bot");
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
