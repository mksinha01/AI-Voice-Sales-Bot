/**
 * static/js/live-chat.js
 * Handles real-time live chat bubble rendering, typing animations, timestamps, and smooth auto-scroll.
 */

const LiveChat = {
  chatBox: null,
  seenIds: new Set(),
  typingElem: null,

  init() {
    this.chatBox = document.getElementById("live-chat-box");
  },

  clear() {
    if (!this.chatBox) this.init();
    if (this.chatBox) {
      this.chatBox.innerHTML = "";
    }
    this.seenIds.clear();
    this.typingElem = null;
  },

  showConnecting(title = "Alex • AI Agent", desc = "Connecting to live voice channel & initializing SaaS playbooks...") {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    this.removeConnecting();
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble-nix bot";
    bubble.id = "connecting-placeholder";
    bubble.innerHTML = `
      <div class="chat-meta-nix">
        <span>${title.toUpperCase()}</span>
        <span style="color: var(--accent-lime);">CONNECTING...</span>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <span>${desc}</span>
        <div class="typing-dot" style="display: inline-block;"></div>
      </div>
    `;
    this.chatBox.appendChild(bubble);
    this.scrollToBottom();
  },

  removeConnecting() {
    const el = document.getElementById("connecting-placeholder");
    if (el) el.remove();
  },

  showTyping(speaker = "Alex") {
    if (!this.chatBox) this.init();
    if (!this.chatBox) return;

    if (this.typingElem) {
      this.scrollToBottom();
      return;
    }

    const bubble = document.createElement("div");
    bubble.className = "typing-bubble-nix";
    bubble.id = "live-typing-indicator";
    bubble.innerHTML = `
      <span style="font-size: 0.68rem; font-weight: 700; color: var(--accent-lime); letter-spacing: 0.05em; margin-right: 4px;">
        ${speaker.toUpperCase()} IS TYPING
      </span>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;

    this.typingElem = bubble;
    this.chatBox.appendChild(bubble);
    this.scrollToBottom();
  },

  hideTyping() {
    if (this.typingElem) {
      this.typingElem.remove();
      this.typingElem = null;
    }
    const existing = document.getElementById("live-typing-indicator");
    if (existing) existing.remove();
  },

  appendMessage(speaker, text, timestamp, id = null) {
    if (!this.chatBox) this.init();
    if (!this.chatBox || !text || !text.trim()) return;

    // Remove typing indicator and connecting banner as new message arrives
    this.hideTyping();
    this.removeConnecting();

    const trimmed = text.trim();
    const textKey = `${speaker.toLowerCase()}:${trimmed.slice(0, 80)}`;
    if (id && this.seenIds.has(`id:${id}`)) return;
    if (this.seenIds.has(textKey)) {
      if (id) this.seenIds.add(`id:${id}`);
      return;
    }
    this.seenIds.add(textKey);
    if (id) this.seenIds.add(`id:${id}`);

    const timeStr = timestamp
      ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      : new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const isBot = speaker.toLowerCase() === "bot";

    const bubble = document.createElement("div");
    bubble.className = `chat-bubble-nix ${isBot ? 'bot' : 'customer'}`;

    const meta = document.createElement("div");
    meta.className = "chat-meta-nix";
    meta.innerHTML = `<span>${isBot ? 'ALEX &bull; AI AGENT' : 'PROSPECT'}</span><span>${timeStr}</span>`;

    const content = document.createElement("div");
    content.textContent = trimmed;

    bubble.appendChild(meta);
    bubble.appendChild(content);
    this.chatBox.appendChild(bubble);

    // Auto-scroll so older messages go upper smoothly
    this.scrollToBottom();
  },

  scrollToBottom() {
    if (!this.chatBox) return;
    this.chatBox.scrollTop = this.chatBox.scrollHeight;
    requestAnimationFrame(() => {
      if (this.chatBox) {
        this.chatBox.scrollTop = this.chatBox.scrollHeight;
      }
    });
  }
};
