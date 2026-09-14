const messagesEl = document.getElementById("messages");
const emptyStateEl = document.getElementById("emptyState");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("chatInput");
const sendBtnEl = document.getElementById("sendBtn");
const newChatBtnEl = document.getElementById("newChatBtn");

const chatHistory = [];
let typingEl = null;

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideEmptyState() {
  if (emptyStateEl) {
    emptyStateEl.remove();
  }
}

function addMessage(role, content, extraClass = "") {
  hideEmptyState();

  const row = document.createElement("div");
  row.className = `message ${role} ${extraClass}`.trim();

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesEl.appendChild(row);
  scrollToBottom();
  return row;
}

function showTyping() {
  hideEmptyState();
  typingEl = document.createElement("div");
  typingEl.className = "message assistant typing";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const dots = document.createElement("div");
  dots.className = "typing-dots";
  dots.innerHTML = "<span></span><span></span><span></span>";

  bubble.appendChild(dots);
  typingEl.appendChild(avatar);
  typingEl.appendChild(bubble);
  messagesEl.appendChild(typingEl);
  scrollToBottom();
}

function hideTyping() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

function setSending(isSending) {
  sendBtnEl.disabled = isSending;
  inputEl.disabled = isSending;
}

function autosizeInput() {
  inputEl.style.height = "auto";
  inputEl.style.height = `${Math.min(inputEl.scrollHeight, 192)}px`;
}

async function sendMessage(text) {
  addMessage("user", text);
  chatHistory.push({ role: "user", content: text });

  setSending(true);
  showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(-10),
      }),
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();
    hideTyping();
    addMessage("assistant", data.reply);
    chatHistory.push({ role: "assistant", content: data.reply });
  } catch (error) {
    hideTyping();
    addMessage("assistant", `Error: ${error.message}`, "error");
  } finally {
    setSending(false);
    inputEl.focus();
  }
}

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = "";
  autosizeInput();
  sendMessage(text);
});

inputEl.addEventListener("input", autosizeInput);

inputEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formEl.requestSubmit();
  }
});

newChatBtnEl.addEventListener("click", () => {
  chatHistory.length = 0;
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyStateEl);
  inputEl.value = "";
  autosizeInput();
  inputEl.focus();
});

inputEl.focus();
