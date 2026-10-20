/**
 * static/js/history.js
 * Call history fetcher, Timeline track generator, and Monitoring Table Controller.
 */

const CallHistory = {
  activeStatusFilter: "",
  searchQuery: "",
  cachedCalls: [],

  init() {
    // Bind filter pills in Monitoring View
    const pills = document.querySelectorAll(".history-filter-pill");
    pills.forEach(pill => {
      pill.addEventListener("click", () => {
        pills.forEach(p => p.classList.remove("active"));
        pill.classList.add("active");
        this.activeStatusFilter = pill.getAttribute("data-status") || "";
        this.renderTable();
      });
    });

    // Refresh table button
    document.getElementById("btn-refresh-table")?.addEventListener("click", () => this.load());
    document.getElementById("btn-refresh-timeline")?.addEventListener("click", () => this.load());

    // Search query listener
    document.getElementById("input-search-query")?.addEventListener("input", (e) => {
      this.searchQuery = e.target.value.toLowerCase().trim();
      this.renderTable();
    });

    // Close Monitoring audio player
    document.getElementById("monitoring-player-close")?.addEventListener("click", () => {
      const monContainer = document.getElementById("monitoring-audio-container");
      const monPlayer = document.getElementById("monitoring-audio-player");
      if (monPlayer) monPlayer.pause();
      if (monContainer) monContainer.style.display = "none";
    });

    this.load();
  },

  getStatusBadgeClass(status) {
    const s = (status || "").toLowerCase().replace(/[^a-z]/g, "");
    if (s.includes("convert")) return "converted";
    if (s.includes("demo")) return "demo";
    if (s.includes("interest") && !s.includes("not")) return "interested";
    if (s.includes("follow")) return "followup";
    if (s.includes("not")) return "notinterested";
    return "noresponse";
  },

  getTimelineColor(status) {
    const s = (status || "").toLowerCase();
    if (s.includes("convert")) return "lime";
    if (s.includes("demo")) return "white";
    if (s.includes("interest") && !s.includes("not")) return "lime";
    if (s.includes("follow")) return "orange";
    return "orange";
  },

  getTimelineIcon(status) {
    const s = (status || "").toLowerCase();
    if (s.includes("convert")) return "check";
    if (s.includes("demo")) return "calendar";
    if (s.includes("follow")) return "clock";
    return "user";
  },

  formatDuration(seconds) {
    if (!seconds) return "00:45";
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  },

  async load() {
    try {
      const resp = await fetch("/api/calls?limit=50");
      const data = await resp.json();
      this.cachedCalls = data.calls || [];

      this.renderTimeline();
      this.renderTable();

      // Trigger app stats computation
      if (window.App && window.App.updateMetricsFromCalls) {
        window.App.updateMetricsFromCalls(this.cachedCalls);
      }
    } catch (e) {
      console.warn("Could not fetch calls:", e);
    }
  },

  renderTimeline() {
    const trackList = document.getElementById("timeline-track-list");
    if (!trackList) return;

    if (this.cachedCalls.length === 0) {
      trackList.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 3rem 1rem; font-size: 0.85rem;">
          No calls recorded yet. Click <strong>Start Sales Call</strong> to generate your first live record.
        </div>
      `;
      return;
    }

    trackList.innerHTML = this.cachedCalls.slice(0, 6).map((c, i) => {
      const time = c.created_at
        ? new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : `10:${30 - i * 15}`;
      const color = this.getTimelineColor(c.sales_status);
      const icon = this.getTimelineIcon(c.sales_status);
      const dur = this.formatDuration(c.duration_seconds);
      const leftPercent = 10 + (i * 14) % 45;
      const widthPx = Math.min(240, Math.max(130, 110 + (c.duration_seconds || 45) * 1.5));

      return `
        <div class="timeline-row">
          <span class="timeline-time-label">${time}</span>
          <div class="timeline-track">
            <div class="timeline-capsule-bar ${color}" style="left: ${leftPercent}%; width: ${widthPx}px;" onclick="CallHistory.showDetails('${c.id}')" title="Click to view details & audio playback">
              <div class="timeline-icon-badge">
                <i data-lucide="${icon}" style="width: 12px; height: 12px;"></i>
              </div>
              <span>${c.sales_status} &bull; ${dur}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    if (window.lucide) {
      window.lucide.createIcons();
    }
  },

  renderTable() {
    const tbody = document.getElementById("monitoring-tbody");
    if (!tbody) return;

    let filtered = this.cachedCalls;

    if (this.activeStatusFilter) {
      filtered = filtered.filter(c => (c.sales_status || "").toLowerCase() === this.activeStatusFilter.toLowerCase());
    }

    if (this.searchQuery) {
      filtered = filtered.filter(c => {
        const text = `${c.customer_name} ${c.product_name} ${c.sales_status} ${c.summary}`.toLowerCase();
        return text.includes(this.searchQuery);
      });
    }

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
            No conversations matching current filter criteria.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered.map(c => {
      const dateStr = c.created_at ? new Date(c.created_at).toLocaleString([], {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      }) : "N/A";

      const badgeClass = this.getStatusBadgeClass(c.sales_status);
      const recUrl = `/api/calls/${c.id}/recording`;

      return `
        <tr>
          <td><code style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--text-secondary);">${dateStr}</code></td>
          <td><strong>${c.customer_name || "Prospect"}</strong></td>
          <td>${c.product_name || "SaaS Solution"}</td>
          <td><span class="badge-capsule ${badgeClass}">${c.sales_status || "No Response"}</span></td>
          <td><code style="font-family: 'JetBrains Mono', monospace;">${this.formatDuration(c.duration_seconds)}</code></td>
          <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c.summary || ''}">
            ${c.summary || "Conversation concluded."}
          </td>
          <td>
            <button class="table-action-btn" onclick="CallHistory.playAudio('${recUrl}', '${(c.customer_name || 'Prospect').replace(/'/g, "\\'")} - ${c.product_name || 'Call'} (${c.sales_status || 'Call'})')" title="Play Call Audio">
              <i data-lucide="play" style="width: 12px; height: 12px;"></i> Play
            </button>
            <button class="table-action-btn" onclick="CallHistory.showDetails('${c.id}')" title="Inspect Intelligence & Transcript">
              <i data-lucide="file-text" style="width: 12px; height: 12px;"></i> Details
            </button>
          </td>
        </tr>
      `;
    }).join("");

    if (window.lucide) {
      window.lucide.createIcons();
    }
  },

  playAudio(url, title = "Call Recording") {
    // 1. Play in Monitoring view player if on Monitoring screen
    const monContainer = document.getElementById("monitoring-audio-container");
    const monPlayer = document.getElementById("monitoring-audio-player");
    const monLabel = document.getElementById("monitoring-player-label");

    if (monContainer && monPlayer) {
      monContainer.style.display = "block";
      if (monLabel) monLabel.textContent = title;
      monPlayer.src = url;
      monPlayer.load();
      monPlayer.play().catch(e => console.warn("Audio autoplay blocked by browser:", e));
    }

    // 2. Also keep Room view player synced
    const roomPlayer = document.getElementById("call-audio-player");
    if (roomPlayer) {
      roomPlayer.src = url;
    }
  },

  async showDetails(callId) {
    try {
      const resp = await fetch(`/api/calls/${callId}`);
      if (!resp.ok) return;
      const call = await resp.json();

      // Switch to dashboard room & post-call intelligence
      if (window.App && window.App.switchToRoomView) {
        window.App.switchToRoomView();
      }
      document.getElementById("btn-view-analysis")?.click();

      const statusElem = document.getElementById("analysis-status");
      if (statusElem) {
        statusElem.textContent = call.sales_status || "Completed";
        statusElem.style.color = this.getStatusBadgeClass(call.sales_status) === "converted"
          ? "var(--accent-lime)"
          : "var(--accent-orange)";
      }

      document.getElementById("analysis-summary").textContent = call.summary || "Executive summary recorded.";
      document.getElementById("analysis-req-obj").innerHTML = `
        <strong>Requirements:</strong> ${call.customer_requirements || "None stated"} &bull; 
        <strong>Objections:</strong> ${call.objections || "None raised"}
      `;
      document.getElementById("analysis-next-steps").textContent = call.next_steps || "Follow up with prospect.";

      if (call.transcripts && call.transcripts.length > 0) {
        LiveChat.clear();
        call.transcripts.forEach(t => {
          LiveChat.appendMessage(t.speaker_type, t.message_text, t.timestamp);
        });
      }

      const player = document.getElementById("call-audio-player");
      if (player) {
        player.src = `/api/calls/${call.id}/recording`;
        player.load();
        player.play().catch(() => {});
      }

    } catch (e) {
      console.error("Failed to load call details:", e);
    }
  }
};
