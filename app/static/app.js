const messagesEl = document.getElementById("messages");
const emptyStateEl = document.getElementById("emptyState");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("chatInput");
const sendBtnEl = document.getElementById("sendBtn");
const newChatBtnEl = document.getElementById("newChatBtn");
const modeSelectEl = document.getElementById("modeSelect");
const modelBadgeEl = document.getElementById("modelBadge");
const footerModelEl = document.getElementById("footerModel");

const chatHistory = [];
let typingEl = null;

async function loadModes() {
  try {
    const res = await fetch("/api/chat/modes");
    if (res.ok) {
      const data = await res.json();
      if (data.default_mode && modeSelectEl) {
        modeSelectEl.value = data.default_mode;
        updateModelLabels(data.default_mode === "gemini" ? "gemini-3.8-flash" : "mock-sld-llm-v2");
      }
    }
  } catch (err) {
    console.warn("Could not load chat modes:", err);
  }
}

function updateModelLabels(modelName) {
  if (modelBadgeEl) modelBadgeEl.textContent = modelName;
  if (footerModelEl) footerModelEl.textContent = modelName;
}

if (modeSelectEl) {
  modeSelectEl.addEventListener("change", () => {
    const isGemini = modeSelectEl.value === "gemini";
    updateModelLabels(isGemini ? "gemini-3.8-flash" : "mock-sld-llm-v2");
  });
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function hideEmptyState() {
  if (emptyStateEl && emptyStateEl.parentNode) {
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

  const currentMode = modeSelectEl ? modeSelectEl.value : "mock";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: chatHistory.slice(-10),
        mode: currentMode,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Backend returned ${response.status}`);
    }

    const data = await response.json();
    hideTyping();
    addMessage("assistant", data.reply);
    chatHistory.push({ role: "assistant", content: data.reply });
    if (data.model) {
      updateModelLabels(data.model);
    }
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
  if (emptyStateEl) {
    messagesEl.appendChild(emptyStateEl);
  }
  inputEl.value = "";
  autosizeInput();
  inputEl.focus();
});

loadModes();
inputEl.focus();
