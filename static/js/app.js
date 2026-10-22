/**
 * static/js/app.js
 * Nixtio-style Dashboard Controller, Waveform Canvas, Matrix, and LiveKit Coordinator.
 */

window.AppState = {
  currentCallId: null,
  callTimerInterval: null,
  callDurationSeconds: 0,
  activeProduct: "CloudScale CRM",
  activeLanguage: "auto",
  customSystemPrompt: null,
  customProductData: null,
  isCallActive: false,
  transcriptPollInterval: null,
  activeView: "room", // "room" or "monitoring"
  productsList: []
};

window.App = {
  canvas: null,
  ctx: null,
  wavePhase: 0,
  animationFrameId: null,

  async init() {
    if (window.lucide) {
      window.lucide.createIcons();
    }

    // Subsystems
    LiveChat.init();
    Customizer.init();
    CallHistory.init();

    // Waveform & Dot Matrix
    this.initWaveform();
    this.initDotMatrix();

    // Load products
    await this.loadProducts();

    // Navigation and View Switches
    this.setupNavigation();
    this.setupSubViews();
    this.setupSearch();

    // Call Toggle Button
    const btnToggle = document.getElementById("btn-call-toggle");
    if (btnToggle) {
      btnToggle.addEventListener("click", () => {
        if (window.AppState.isCallActive) {
          this.endCall();
        } else {
          this.startCall();
        }
      });
    }

    // Header Filter Listeners
    document.getElementById("product-select")?.addEventListener("change", (e) => {
      this.onProductChanged(e.target.value);
    });

    document.getElementById("language-select")?.addEventListener("change", (e) => {
      window.AppState.activeLanguage = e.target.value;
    });

    console.log("AI Sales Intelligence Dashboard ready.");
  },

  setupNavigation() {
    const tabRoom = document.getElementById("tab-nav-room");
    const tabMon = document.getElementById("tab-nav-monitoring");
    const tabStudio = document.getElementById("tab-nav-studio");

    const navLeads = document.getElementById("tab-nav-leads");
    const navContacts = document.getElementById("tab-nav-contacts");
    const navCampaigns = document.getElementById("tab-nav-campaigns");
    const navAnalytics = document.getElementById("tab-nav-analytics");
    const navIntegrations = document.getElementById("tab-nav-integrations");
    const navSettings = document.getElementById("tab-nav-settings");
    const navHelp = document.getElementById("tab-nav-help");
    const btnCollapse = document.getElementById("btn-collapse-sidebar");

    // Navigation switches
    tabRoom?.addEventListener("click", () => this.switchToRoomView());
    tabMon?.addEventListener("click", () => this.switchToMonitoringView());
    tabStudio?.addEventListener("click", () => Customizer.openModal());

    [navLeads, navContacts, navCampaigns, navAnalytics, navIntegrations].forEach(btn => {
      btn?.addEventListener("click", () => {
        document.querySelectorAll(".sidebar-links .nav-link").forEach(l => l.classList.remove("active"));
        btn.classList.add("active");
        this.switchToMonitoringView();
      });
    });

    navSettings?.addEventListener("click", () => {
      window.location.href = "/persona-control";
    });
    navHelp?.addEventListener("click", () => Customizer.openModal());

    // Sidebar collapse toggle
    btnCollapse?.addEventListener("click", () => {
      const frame = document.getElementById("main-dashboard-frame");
      frame?.classList.toggle("sidebar-collapsed");
      const icon = document.getElementById("collapse-icon");
      if (frame?.classList.contains("sidebar-collapsed")) {
        icon?.setAttribute("data-lucide", "arrow-right");
      } else {
        icon?.setAttribute("data-lucide", "arrow-left");
      }
      if (window.lucide) window.lucide.createIcons();
    });

    // Call toolbar buttons
    document.getElementById("btn-toolbar-hangup")?.addEventListener("click", () => {
      if (window.AppState.isCallActive) this.endCall();
    });

    document.getElementById("btn-mic-toggle")?.addEventListener("click", () => {
      const micIcon = document.getElementById("mic-icon");
      if (window.LiveKitManager && LiveKitManager.room) {
        const localP = LiveKitManager.room.localParticipant;
        if (localP) {
          const isMuted = localP.isMicrophoneEnabled === false;
          localP.setMicrophoneEnabled(isMuted);
          micIcon?.setAttribute("data-lucide", isMuted ? "mic" : "mic-off");
          if (window.lucide) window.lucide.createIcons();
        }
      }
    });

    // Chat input inside cockpit
    const chatInput = document.getElementById("live-chat-input");
    const sendBtn = document.getElementById("btn-send-chat");
    const handleSend = () => {
      const val = chatInput?.value?.trim();
      if (!val) return;
      LiveChat.appendMessage("customer", val);
      chatInput.value = "";
    };
    sendBtn?.addEventListener("click", handleSend);
    chatInput?.addEventListener("keypress", (e) => {
      if (e.key === "Enter") handleSend();
    });

    // Drawer close
    document.getElementById("btn-close-analysis")?.addEventListener("click", () => {
      const drawer = document.getElementById("subview-analysis");
      if (drawer) drawer.style.display = "none";
    });
  },

  switchToRoomView() {
    window.AppState.activeView = "room";
    document.querySelectorAll(".sidebar-links .nav-link").forEach(l => l.classList.remove("active"));
    document.getElementById("tab-nav-room")?.classList.add("active");
    const viewRoom = document.getElementById("view-room");
    const viewMon = document.getElementById("view-monitoring");
    if (viewRoom) viewRoom.style.display = "flex";
    if (viewMon) viewMon.style.display = "none";
  },

  switchToMonitoringView() {
    window.AppState.activeView = "monitoring";
    document.querySelectorAll(".sidebar-links .nav-link").forEach(l => l.classList.remove("active"));
    document.getElementById("tab-nav-monitoring")?.classList.add("active");
    const viewRoom = document.getElementById("view-room");
    const viewMon = document.getElementById("view-monitoring");
    if (viewRoom) viewRoom.style.display = "none";
    if (viewMon) viewMon.style.display = "flex";
    if (window.CallHistory && CallHistory.renderTable) {
      CallHistory.renderTable();
    }
  },

  cycleNextProduct() {
    const select = document.getElementById("product-select");
    if (!select || !window.AppState.productsList.length) return;
    const nextIdx = (select.selectedIndex + 1) % window.AppState.productsList.length;
    select.selectedIndex = nextIdx;
    this.onProductChanged(select.value);
  },

  setupSearch() {
    const btnSearch = document.getElementById("btn-search-calls");
    const bar = document.getElementById("quick-search-bar");
    const btnClose = document.getElementById("btn-close-search");
    const input = document.getElementById("input-search-query");

    btnSearch?.addEventListener("click", () => {
      bar.style.display = bar.style.display === "flex" ? "none" : "flex";
      if (bar.style.display === "flex") {
        input.focus();
        this.switchToMonitoringView();
      }
    });

    btnClose?.addEventListener("click", () => {
      bar.style.display = "none";
      if (input) input.value = "";
      CallHistory.searchQuery = "";
      CallHistory.renderTable();
    });
  },

  initWaveform() {
    this.canvas = document.getElementById("waveform-canvas");
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    const resize = () => {
      this.canvas.width = this.canvas.parentElement.clientWidth;
      this.canvas.height = this.canvas.parentElement.clientHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const render = () => {
      this.drawWave();
      this.animationFrameId = requestAnimationFrame(render);
    };
    render();
  },

  drawWave() {
    if (!this.ctx || !this.canvas) return;
    const { width, height } = this.canvas;
    this.ctx.clearRect(0, 0, width, height);

    this.wavePhase += window.AppState.isCallActive ? 0.08 : 0.03;
    const currentAmp = window.AppState.isCallActive ? 24 : 10;

    // Glowing Neon Lime Line
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.lineWidth = 2.5;
    this.ctx.strokeStyle = "#c5f82a";
    this.ctx.shadowColor = "rgba(197, 248, 42, 0.6)";
    this.ctx.shadowBlur = 8;

    for (let x = 0; x < width; x++) {
      const y = (height / 2) +
        Math.sin((x * 0.02) + this.wavePhase) * (currentAmp * 0.7) +
        Math.sin((x * 0.04) + (this.wavePhase * 1.5)) * (currentAmp * 0.3);
      if (x === 0) this.ctx.moveTo(x, y);
      else this.ctx.lineTo(x, y);
    }
    this.ctx.stroke();

    // Subtle orange baseline wave
    this.ctx.beginPath();
    this.ctx.lineWidth = 1.2;
    this.ctx.strokeStyle = "rgba(255, 109, 38, 0.4)";
    this.ctx.shadowBlur = 0;
    for (let x = 0; x < width; x++) {
      const y = (height / 2) + Math.cos((x * 0.025) - this.wavePhase) * (currentAmp * 0.5);
      if (x === 0) this.ctx.moveTo(x, y);
      else this.ctx.lineTo(x, y);
    }
    this.ctx.stroke();
    this.ctx.restore();
  },

  initDotMatrix(calls = []) {
    const grid = document.getElementById("dot-matrix-grid");
    if (!grid) return;
    grid.innerHTML = "";

    const totalSlots = 48;
    for (let i = 0; i < totalSlots; i++) {
      const dot = document.createElement("div");
      dot.className = "matrix-dot";
      const call = calls[i];

      if (call) {
        const s = (call.sales_status || "").toLowerCase();
        if (s.includes("convert") || (s.includes("interest") && !s.includes("not"))) {
          dot.classList.add("lime");
        } else if (s.includes("demo")) {
          dot.classList.add("white");
        } else if (s.includes("follow") || s.includes("not")) {
          dot.classList.add("orange");
        }

        const dur = (window.CallHistory && CallHistory.formatDuration)
          ? CallHistory.formatDuration(call.duration_seconds)
          : `${call.duration_seconds || 0}s`;
        dot.title = `${call.customer_name || 'Prospect'} • ${call.sales_status || 'Call'} • ${dur} (Click to inspect)`;
        dot.style.cursor = "pointer";
        dot.onclick = () => {
          if (window.CallHistory && CallHistory.showDetails) {
            CallHistory.showDetails(call.id);
          }
        };
      } else {
        dot.title = `Call slot #${i + 1} (Awaiting call)`;
        dot.style.opacity = "0.2";
      }
      grid.appendChild(dot);
    }
  },

  setupSubViews() {
    const btnTimeline = document.getElementById("btn-view-timeline");
    const btnAnalysis = document.getElementById("btn-view-analysis");

    const viewTimeline = document.getElementById("timeline-track-list");
    const viewAnalysis = document.getElementById("subview-analysis");

    const switchView = (target) => {
      [btnTimeline, btnAnalysis].forEach(b => b?.classList.remove("active"));
      if (viewTimeline) viewTimeline.style.display = "none";
      if (viewAnalysis) viewAnalysis.style.display = "none";

      if (target === "analysis") {
        btnAnalysis?.classList.add("active");
        if (viewAnalysis) viewAnalysis.style.display = "flex";
      } else {
        btnTimeline?.classList.add("active");
        if (viewTimeline) viewTimeline.style.display = "flex";
      }
    };

    btnTimeline?.addEventListener("click", () => switchView("timeline"));
    btnAnalysis?.addEventListener("click", () => {
      switchView("analysis");
      if (window.CallHistory && CallHistory.cachedCalls && CallHistory.cachedCalls.length > 0) {
        const titleElem = document.getElementById("analysis-call-title");
        if (!titleElem || titleElem.textContent === "Post-Call Intelligence") {
          CallHistory.showDetails(CallHistory.cachedCalls[0].id);
        }
      }
    });

    document.getElementById("btn-close-analysis")?.addEventListener("click", () => {
      switchView("timeline");
    });
  },

  async loadProducts(selectedProductName = null) {
    try {
      const resp = await fetch("/api/products");
      const data = await resp.json();
      window.AppState.productsList = data.products || [];

      const select = document.getElementById("product-select");
      if (select) {
        select.innerHTML = window.AppState.productsList.map(p => {
          return `<option value="${p.name}">Product: ${p.name}</option>`;
        }).join("");
        if (selectedProductName) select.value = selectedProductName;
        this.onProductChanged(select.value);
      }
    } catch (e) {
      console.warn("Products fetch failed:", e);
    }
  },

  onProductChanged(productName) {
    window.AppState.activeProduct = productName;
    const p = window.AppState.productsList.find(item => item.name === productName);
    if (p) {
      const taglineElem = document.getElementById("active-pitch-tagline");
      const priceElem = document.getElementById("active-pitch-price");
      if (taglineElem) taglineElem.textContent = p.tagline || p.description;
      if (priceElem) priceElem.textContent = `$${p.pricing_annual || 39} / mo`;
    }
  },

  updateMetricsFromCalls(calls) {
    if (!calls) calls = [];
    const total = calls.length;
    const converted = calls.filter(c => c.sales_status === "Converted").length;
    const demo = calls.filter(c => c.sales_status === "Demo Requested").length;
    const objections = calls.filter(c => c.sales_status === "Follow-up Required" || c.sales_status === "Not Interested").length;

    const convRate = total > 0 ? (((converted + demo) / total) * 100).toFixed(1) : "6.5";
    const objRate = total > 0 ? ((objections / total) * 100).toFixed(1) : "16.1";

    const convElem = document.getElementById("kpi-conv-rate");
    const objElem = document.getElementById("kpi-obj-rate");

    if (convElem) convElem.textContent = `${convRate}%`;
    if (objElem) objElem.textContent = `${objRate}%`;
  },

  filterByStatus(status) {
    this.switchToMonitoringView();
    const pills = document.querySelectorAll(".history-filter-pill");
    pills.forEach(p => {
      if (p.getAttribute("data-status") === status) {
        p.click();
      }
    });
  },

  startTimer() {
    this.stopTimer();
    window.AppState.callDurationSeconds = 0;
    const timerElem = document.getElementById("call-timer");
    if (timerElem) timerElem.textContent = "00:00:00";

    window.AppState.callTimerInterval = setInterval(() => {
      window.AppState.callDurationSeconds += 1;
      const h = Math.floor(window.AppState.callDurationSeconds / 3600).toString().padStart(2, "0");
      const m = Math.floor((window.AppState.callDurationSeconds % 3600) / 60).toString().padStart(2, "0");
      const s = (window.AppState.callDurationSeconds % 60).toString().padStart(2, "0");
      if (timerElem) timerElem.textContent = `${h}:${m}:${s}`;
    }, 1000);
  },

  stopTimer() {
    if (window.AppState.callTimerInterval) {
      clearInterval(window.AppState.callTimerInterval);
      window.AppState.callTimerInterval = null;
    }
  },

  startTranscriptPolling(roomName) {
    this.stopTranscriptPolling();
    window.AppState.transcriptPollInterval = setInterval(async () => {
      if (!roomName) return;
      try {
        const resp = await fetch(`/api/calls/by-session/${roomName}`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (data && data.call) {
          window.AppState.currentCallId = data.call.id;
        }
        if (data && Array.isArray(data.transcripts) && data.transcripts.length > 0) {
          data.transcripts.forEach(t => {
            LiveChat.appendMessage(t.speaker_type, t.message_text, t.timestamp, t.id);
          });
        }
      } catch (err) {
        console.debug("Transcript poll tick:", err);
      }
    }, 800);
  },

  stopTranscriptPolling() {
    if (window.AppState.transcriptPollInterval) {
      clearInterval(window.AppState.transcriptPollInterval);
      window.AppState.transcriptPollInterval = null;
    }
  },

  async startCall() {
    const btn = document.getElementById("btn-call-toggle");
    const label = document.getElementById("call-toggle-label");
    const statusRole = document.getElementById("bot-role-status");
    const avatarBadge = document.getElementById("avatar-live-indicator");
    const customerName = document.getElementById("customer-name")?.value || "Valued Customer";
    const productName = window.AppState.activeProduct;
    const language = window.AppState.activeLanguage;

    label.textContent = "Connecting...";
    btn.disabled = true;

    // Switch right card to Live Chat view immediately
    document.getElementById("btn-view-chat")?.click();
    LiveChat.clear();
    LiveChat.showConnecting("Alex Closer", `Connecting to live sales voice line for ${productName}...`);

    try {
      const discloseConsent = document.getElementById("consent-check")?.checked ?? true;
      const tokenResp = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_name: productName,
          language: language,
          customer_name: customerName,
          disclose_consent: discloseConsent,
          custom_system_prompt: window.AppState.customSystemPrompt,
          custom_product_data: window.AppState.customProductData
        })
      });

      if (!tokenResp.ok) throw new Error("Could not issue LiveKit room token.");
      const { token, livekit_url, room_name, call_id } = await tokenResp.json();
      window.AppState.currentCallSession = room_name;
      if (call_id) {
        window.AppState.currentCallId = call_id;
      }

      // Start dual-channel transcript sync polling immediately
      this.startTranscriptPolling(room_name);

      const isPlaceholder = !livekit_url || livekit_url.includes("your-project") || livekit_url.includes("placeholder");

      if (isPlaceholder) {
        this.runSimulationMode(productName, language, customerName);
        return;
      }

      await LiveKitManager.connect(livekit_url, token, {
        onStatusChange: (status) => {
          if (status === "connected") {
            statusRole.textContent = "LiveKit • Connected";
            avatarBadge?.classList.add("live");
          } else if (status === "speaking") {
            statusRole.textContent = "Alex • Speaking";
            LiveChat.showTyping("Alex");
          }
        },
        onTranscript: (speaker, text, timestamp) => {
          LiveChat.appendMessage(speaker, text, timestamp);
        },
        onDisconnect: () => {
          this.onCallTerminated();
        }
      }, room_name);

      window.AppState.isCallActive = true;
      btn.disabled = false;
      btn.classList.remove("start-mode");
      label.textContent = "End Call";
      document.getElementById("call-toggle-icon")?.setAttribute("data-lucide", "phone-off");
      document.getElementById("call-state-text").textContent = "Live Call";
      document.getElementById("ai-speaking-status").textContent = "AI Agent is speaking...";
      this.startTimer();
      statusRole.textContent = "Alex • Active Call";
      avatarBadge?.classList.add("live");
      if (window.lucide) window.lucide.createIcons();

    } catch (e) {
      console.warn("LiveKit connection note:", e);
      this.runSimulationMode(productName, language, customerName);
    }
  },

  async endCall() {
    const btn = document.getElementById("btn-call-toggle");
    const label = document.getElementById("call-toggle-label");
    const statusRole = document.getElementById("bot-role-status");

    btn.disabled = true;
    label.textContent = "Synthesizing...";
    statusRole.textContent = "Gemini • Post-Analysis";
    this.stopTimer();

    await LiveKitManager.disconnect();
    this.onCallTerminated();
  },

  async onCallTerminated() {
    window.AppState.isCallActive = false;
    this.stopTranscriptPolling();

    const btn = document.getElementById("btn-call-toggle");
    const label = document.getElementById("call-toggle-label");
    const statusRole = document.getElementById("bot-role-status");
    const avatarBadge = document.getElementById("avatar-live-indicator");

    btn.disabled = false;
    btn.classList.add("start-mode");
    label.textContent = "Start Sales Call";
    document.getElementById("call-toggle-icon")?.setAttribute("data-lucide", "phone-call");
    document.getElementById("call-state-text").textContent = "Ready";
    document.getElementById("ai-speaking-status").textContent = "Ready to start sales call";
    statusRole.textContent = "LiveKit • Ready";
    avatarBadge?.classList.remove("live");

    this.stopTimer();
    if (window.lucide) window.lucide.createIcons();

    // Auto-switch to Post-Call Intelligence and load AI summary & status
    setTimeout(async () => {
      document.getElementById("btn-view-analysis")?.click();
      await CallHistory.load();
      if (window.AppState.currentCallId) {
        await CallHistory.showDetails(window.AppState.currentCallId);
      }
    }, 1800);
  },

  runSimulationMode(productName, language, customerName) {
    document.getElementById("btn-view-chat")?.click();
    LiveChat.removeConnecting();

    const btn = document.getElementById("btn-call-toggle");
    const label = document.getElementById("call-toggle-label");
    const statusRole = document.getElementById("bot-role-status");
    const avatarBadge = document.getElementById("avatar-live-indicator");
    const pitchKpi = document.getElementById("kpi-pitch-text");
    const listenKpi = document.getElementById("kpi-listen-text");

    btn.disabled = false;
    btn.classList.remove("start-mode");
    label.textContent = "End Call";
    document.getElementById("call-toggle-icon")?.setAttribute("data-lucide", "phone-off");
    document.getElementById("call-state-text").textContent = "Live Call";
    document.getElementById("ai-speaking-status").textContent = "AI Agent is speaking...";
    window.AppState.isCallActive = true;
    this.startTimer();
    statusRole.textContent = "Alex • Pitching";
    avatarBadge?.classList.add("live");
    if (window.lucide) window.lucide.createIcons();

    const discloseConsent = document.getElementById("consent-check")?.checked;
    const consentText = discloseConsent
      ? "Please note this sales call is recorded for quality assurance. "
      : "";

    LiveChat.appendMessage("bot", `Hello ${customerName}! Thanks for connecting. ${consentText}I'm Alex from ${productName}. How can I assist your business growth today?`);

    const dialogue = [
      { delay: 3500, speaker: "customer", text: "Hi Alex! We need an automated CRM pipeline that eliminates manual rep data entry.", pitchRatio: "2.1%", listenRatio: "1.9%" },
      { delay: 7500, speaker: "bot", text: `${productName} automatically transcribes meetings, predicts deal closure at 92% accuracy, and saves 10 hours per rep each week.`, pitchRatio: "3.4%", listenRatio: "1.5%" },
      { delay: 12000, speaker: "customer", text: "That fits our roadmap! What's the annual pricing and can you book a demo?", pitchRatio: "2.8%", listenRatio: "2.4%" },
      { delay: 16000, speaker: "bot", text: "At $39/month billed annually you lock in a 20% discount. I can book a 15-minute live walkthrough for your team this Thursday!", pitchRatio: "4.2%", listenRatio: "1.8%" },
      { delay: 20000, speaker: "customer", text: "Thursday afternoon works great! Lock in that discount and send over the calendar invite.", pitchRatio: "3.8%", listenRatio: "2.7%" }
    ];

    dialogue.forEach(item => {
      setTimeout(() => {
        if (window.AppState.isCallActive) {
          LiveChat.appendMessage(item.speaker, item.text);
          statusRole.textContent = item.speaker === "bot" ? "Alex • Speaking" : "Customer • Speaking";
          if (pitchKpi) pitchKpi.textContent = item.pitchRatio;
          if (listenKpi) listenKpi.textContent = item.listenRatio;
        }
      }, item.delay);
    });
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.App.init();
});
