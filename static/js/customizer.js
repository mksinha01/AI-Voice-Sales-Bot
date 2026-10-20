/**
 * static/js/customizer.js
 * SaaS product customizer, prompt editor, and dynamic UI theme sync.
 */

const Customizer = {
  modal: null,
  activeTab: "product",

  init() {
    this.modal = document.getElementById("customizer-modal");

    // Close buttons
    document.getElementById("btn-close-modal")?.addEventListener("click", () => this.closeModal());
    
    // Close on backdrop click
    if (this.modal) {
      this.modal.addEventListener("click", (e) => {
        if (e.target === this.modal) this.closeModal();
      });
    }

    // Tab buttons
    document.getElementById("tab-btn-product")?.addEventListener("click", () => this.switchTab("product"));
    document.getElementById("tab-btn-prompt")?.addEventListener("click", () => this.switchTab("prompt"));

    // Reset & Save buttons
    document.getElementById("btn-reset-customizer")?.addEventListener("click", () => this.resetDefaults());
    document.getElementById("btn-save-customizer")?.addEventListener("click", () => this.saveConfiguration());
  },

  openModal() {
    if (this.modal) this.modal.classList.add("open");
  },

  closeModal() {
    if (this.modal) this.modal.classList.remove("open");
  },

  switchTab(tab) {
    this.activeTab = tab;
    const btnProd = document.getElementById("tab-btn-product");
    const btnPrompt = document.getElementById("tab-btn-prompt");
    const contentProd = document.getElementById("tab-content-product");
    const contentPrompt = document.getElementById("tab-content-prompt");

    if (tab === "product") {
      btnProd?.classList.add("active");
      btnPrompt?.classList.remove("active");
      if (contentProd) contentProd.style.display = "flex";
      if (contentPrompt) contentPrompt.style.display = "none";
    } else {
      btnProd?.classList.remove("active");
      btnPrompt?.classList.add("active");
      if (contentProd) contentProd.style.display = "none";
      if (contentPrompt) contentPrompt.style.display = "flex";
    }
  },

  resetDefaults() {
    document.getElementById("cust-prod-name").value = "";
    document.getElementById("cust-prod-tagline").value = "";
    document.getElementById("cust-prod-desc").value = "";
    document.getElementById("cust-prod-monthly").value = "49";
    document.getElementById("cust-prod-annual").value = "39";
    document.getElementById("cust-prod-features").value = "";
    document.getElementById("cust-system-prompt").value = "";
    
    window.AppState.customSystemPrompt = null;
    window.AppState.customProductData = null;
    alert("Studio reset to catalog defaults.");
  },

  async saveConfiguration() {
    const nameInput = document.getElementById("cust-prod-name");
    const name = nameInput ? nameInput.value.trim() : "";
    const promptInput = document.getElementById("cust-system-prompt");
    const promptText = promptInput ? promptInput.value.trim() : "";

    if (this.activeTab === "prompt" && promptText) {
      window.AppState.customSystemPrompt = promptText;
      alert("Custom system prompt set as active bot persona!");
      this.closeModal();
      return;
    }

    if (!name) {
      alert("Please provide a product name.");
      return;
    }

    const tagline = document.getElementById("cust-prod-tagline")?.value.trim() || "";
    const description = document.getElementById("cust-prod-desc")?.value.trim() || "";
    const pricing_monthly = parseFloat(document.getElementById("cust-prod-monthly")?.value) || 49;
    const pricing_annual = parseFloat(document.getElementById("cust-prod-annual")?.value) || 39;
    const featuresRaw = document.getElementById("cust-prod-features")?.value.trim() || "";
    const key_features = featuresRaw ? featuresRaw.split(",").map(s => s.trim()) : [];

    const productPayload = {
      name,
      tagline,
      description,
      pricing_monthly,
      pricing_annual,
      key_features,
      target_audience: "Businesses seeking growth",
      custom_system_prompt: promptText || null
    };

    try {
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(productPayload)
      });
      if (resp.ok) {
        window.AppState.customProductData = productPayload;
        window.AppState.customSystemPrompt = promptText || null;

        if (window.App && window.App.loadProducts) {
          await window.App.loadProducts(name);
        }
        this.closeModal();
      } else {
        alert("Failed to save product to database.");
      }
    } catch (e) {
      console.error("Save product error:", e);
      alert("Network error saving product.");
    }
  }
};
