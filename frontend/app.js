(() => {
  // Bind dynamic API Base to current served origin for seamless single-service deployments
  const API_BASE = window.location.origin;

  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const langSelect = document.getElementById("lang-select");
  const roleSelect = document.getElementById("role-select");
  const connStatus = document.getElementById("conn-status");
  const contrastBtn = document.getElementById("contrast-toggle");
  const textBtn = document.getElementById("text-toggle");
  const micBtn = document.getElementById("mic-btn");

  let token = null;

  // --- Accessibility toggles ---
  contrastBtn.addEventListener("click", () => {
    const on = document.body.classList.toggle("high-contrast");
    contrastBtn.setAttribute("aria-pressed", String(on));
  });
  textBtn.addEventListener("click", () => {
    const on = document.body.classList.toggle("large-text");
    textBtn.setAttribute("aria-pressed", String(on));
  });

  // --- Voice input (Web Speech API, graceful no-op if unsupported) ---
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    micBtn.addEventListener("click", () => {
      micBtn.setAttribute("aria-pressed", "true");
      recognition.start();
    });
    recognition.onresult = (e) => {
      input.value = e.results[0][0].transcript;
      micBtn.setAttribute("aria-pressed", "false");
    };
    recognition.onerror = () => micBtn.setAttribute("aria-pressed", "false");
    recognition.onend = () => micBtn.setAttribute("aria-pressed", "false");
  } else {
    micBtn.disabled = true;
    micBtn.title = "Voice input not supported in this browser";
  }

  // --- Voice output ---
  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langSelect.value || "en";
    window.speechSynthesis.speak(utter);
  }

  function addMessage(role, text, meta) {
    const bubble = document.createElement("div");
    bubble.className = (role === "fan" ? "msg-fan" : "msg-copilot") +
      " rounded-2xl p-4 max-w-xl shadow-md" + (role === "fan" ? " self-end animate-slide-in-right" : " self-start animate-slide-in-left");
    
    const label = document.createElement("p");
    label.className = "text-[10px] uppercase tracking-widest font-semibold mb-1 mono";
    label.style.color = role === "fan" ? "var(--floodlight)" : "var(--pitch-light)";
    label.textContent = role === "fan" ? "You" : "Copilot" + (meta ? ` · ${meta}` : "");
    
    const body = document.createElement("p");
    body.className = "text-sm leading-relaxed";
    body.textContent = text;
    
    bubble.appendChild(label);
    bubble.appendChild(body);
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  }

  async function ensureToken() {
    if (token) return token;
    const role = roleSelect.value;
    const resp = await fetch(`${API_BASE}/api/auth/demo-token?role=${role}`, { method: "POST" });
    if (!resp.ok) throw new Error("auth failed");
    const data = await resp.json();
    token = data.access_token;
    return token;
  }

  async function checkHealth() {
    try {
      const resp = await fetch(`${API_BASE}/health`);
      if (resp.ok) {
        connStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-[var(--pitch-light)] animate-pulse inline-block"></span> connected';
        connStatus.className = "flex items-center gap-1.5 font-semibold text-[var(--pitch-light)]";
      } else {
        throw new Error("unhealthy");
      }
    } catch {
      connStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-500 animate-ping inline-block"></span> offline';
      connStatus.className = "flex items-center gap-1.5 font-semibold text-red-500";
    }
  }
  checkHealth();

  roleSelect.addEventListener("change", () => { token = null; });

  async function sendMessage(message) {
    addMessage("fan", message);
    const thinking = addMessage("copilot", "Processing request…", "routing");
    try {
      await ensureToken();
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({ message, language: langSelect.value }),
      });
      if (resp.status === 401) { token = null; throw new Error("auth expired"); }
      if (!resp.ok) throw new Error(`request failed (${resp.status})`);
      const data = await resp.json();
      thinking.remove();
      const agents = (data.agents_used || []).join(", ") || "general";
      addMessage("copilot", data.response_text, agents);
      speak(data.voice_ready_text || data.response_text);
    } catch (err) {
      thinking.remove();
      addMessage("copilot", "I couldn't reach the stadium systems just now. Please try again, or ask a nearby volunteer for help.", "error");
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    sendMessage(message);
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  document.querySelectorAll(".suggestion").forEach((btn) => {
    btn.addEventListener("click", () => sendMessage(btn.textContent));
  });

  // --- Dynamic Stadium Telemetry Live Updates ---
  function initTelemetry() {
    const lotA = document.getElementById("tel-lot-a");
    const lotB = document.getElementById("tel-lot-b");
    const shuttle = document.getElementById("tel-shuttle");
    const gateStatus = document.getElementById("tel-gate-status");
    const gateBar = document.getElementById("tel-gate-bar");

    setInterval(() => {
      // Fluctuate Lot A
      const countA = Math.floor(340 + Math.random() * 20);
      lotA.textContent = `${countA} / 500`;

      // Fluctuate Lot B
      const countB = Math.floor(475 + Math.random() * 15);
      lotB.textContent = `${countB} / 500`;

      // Fluctuate Shuttle Wait
      const times = ["4 MINS", "5 MINS", "6 MINS", "7 MINS"];
      shuttle.textContent = times[Math.floor(Math.random() * times.length)];

      // Fluctuate Gate Status slightly
      const densities = [
        { label: "Gate 1 High", width: "82%" },
        { label: "Gate 2 Moderate", width: "55%" },
        { label: "Gate 3 Low", width: "24%" },
        { label: "Gate 4 Busy", width: "70%" }
      ];
      const active = densities[Math.floor(Math.random() * densities.length)];
      if (gateStatus && gateBar) {
        gateStatus.textContent = active.label;
        gateBar.style.width = active.width;
      }
    }, 4000);
  }
  initTelemetry();

  // --- Sidebar Accordion Interaction Logic ---
  document.querySelectorAll(".accordion-trigger").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const item = trigger.closest(".accordion-item");
      const content = item.querySelector(".accordion-content");
      const isActive = item.classList.contains("active");

      // Close all accordions first (accordion behavior)
      document.querySelectorAll(".accordion-item").forEach((otherItem) => {
        otherItem.classList.remove("active");
        otherItem.querySelector(".accordion-content").style.maxHeight = null;
      });

      // Toggle current accordion
      if (!isActive) {
        item.classList.add("active");
        content.style.maxHeight = content.scrollHeight + "px";
      }
    });
  });
})();
