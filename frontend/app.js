(() => {
  const API_BASE = window.location.origin;

  // ---------- Element refs ----------
  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  const langSelect = document.getElementById("lang-select");
  const roleSelect = document.getElementById("role-select");
  const connStatus = document.getElementById("conn-status");
  const micBtn = document.getElementById("mic-btn");

  let token = null;
  let lastBotText = "";
  let notificationsOn = true;
  let voiceOutOn = true;

  // ---------- Theme ----------
  const themeSwitch = document.getElementById("theme-switch");
  function applyTheme(dark) {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    themeSwitch.setAttribute("aria-checked", String(dark));
  }
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(prefersDark);
  themeSwitch.addEventListener("click", () => {
    applyTheme(themeSwitch.getAttribute("aria-checked") !== "true");
  });

  // ---------- Settings panel ----------
  const settingsPanel = document.getElementById("settings-panel");
  const settingsScrim = document.getElementById("settings-scrim");
  function openSettings() { settingsPanel.classList.add("open"); settingsScrim.classList.add("open"); }
  function closeSettings() { settingsPanel.classList.remove("open"); settingsScrim.classList.remove("open"); }
  document.getElementById("settings-open").addEventListener("click", openSettings);
  document.getElementById("settings-open-mobile").addEventListener("click", openSettings);
  document.getElementById("settings-close").addEventListener("click", closeSettings);
  settingsScrim.addEventListener("click", closeSettings);

  document.getElementById("notif-switch").addEventListener("click", (e) => {
    notificationsOn = e.currentTarget.getAttribute("aria-checked") !== "true";
    e.currentTarget.setAttribute("aria-checked", String(notificationsOn));
  });
  document.getElementById("voice-out-switch").addEventListener("click", (e) => {
    voiceOutOn = e.currentTarget.getAttribute("aria-checked") !== "true";
    e.currentTarget.setAttribute("aria-checked", String(voiceOutOn));
  });

  // ---------- Accessibility toggles ----------
  function wireSwitch(id, onChange) {
    const el = document.getElementById(id);
    el.addEventListener("click", () => {
      const on = el.getAttribute("aria-checked") !== "true";
      el.setAttribute("aria-checked", String(on));
      onChange(on);
    });
  }
  const a11yStatus = (msg) => announce(msg);

  wireSwitch("contrast-switch", (on) => {
    document.body.classList.toggle("high-contrast", on);
    a11yStatus(on ? "High contrast mode enabled" : "High contrast mode disabled");
  });
  wireSwitch("text-switch", (on) => {
    document.body.classList.toggle("large-text", on);
    a11yStatus(on ? "Large text enabled" : "Large text disabled");
  });
  wireSwitch("wheelchair-switch", (on) => {
    document.querySelectorAll(".map-pin:not(.accessible)").forEach(p => p.style.opacity = on ? "0.35" : "1");
    a11yStatus(on ? "Wheelchair mode enabled — accessible routes highlighted" : "Wheelchair mode disabled");
  });
  wireSwitch("voice-nav-switch", (on) => {
    a11yStatus(on ? "Voice navigation enabled" : "Voice navigation disabled");
  });
  wireSwitch("screenreader-switch", (on) => {
    a11yStatus(on ? "Screen reader mode enabled — extra announcements turned on" : "Screen reader mode disabled");
  });
  wireSwitch("accessible-route-switch", (on) => {
    document.querySelectorAll(".map-pin:not(.accessible)").forEach(p => p.style.opacity = on ? "0.35" : "1");
  });

  let ariaRegion = document.createElement("span");
  ariaRegion.className = "sr-only";
  ariaRegion.setAttribute("role", "status");
  ariaRegion.setAttribute("aria-live", "polite");
  document.body.appendChild(ariaRegion);
  function announce(msg) { ariaRegion.textContent = msg; }

  // ---------- Voice input ----------
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

  function speak(text) {
    if (!voiceOutOn || !("speechSynthesis" in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = langSelect.value || "en";
    window.speechSynthesis.speak(utter);
  }

  // ---------- Toasts ----------
  const toastStack = document.getElementById("toast-stack");
  function toast(message, tone = "default") {
    if (!notificationsOn) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.innerHTML = `<span>${tone === "error" ? "⚠️" : "🔔"}</span><span>${message}</span>`;
    toastStack.appendChild(el);
    setTimeout(() => {
      el.classList.add("leaving");
      setTimeout(() => el.remove(), 260);
    }, 4200);
  }

  // ---------- Chat ----------
  function addMessage(role, text, meta) {
    const bubble = document.createElement("div");
    bubble.className = role === "fan" ? "msg msg-user" : "msg msg-bot";
    if (role !== "fan") {
      const label = document.createElement("p");
      label.className = "text-[11px] font-semibold mb-1";
      label.style.color = "var(--accent)";
      label.textContent = "Copilot" + (meta ? ` · ${meta}` : "");
      bubble.appendChild(label);
    }
    const body = document.createElement("p");
    body.textContent = text;
    bubble.appendChild(body);
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  }

  function addTypingIndicator() {
    const bubble = document.createElement("div");
    bubble.className = "msg msg-bot";
    bubble.id = "typing-indicator";
    bubble.innerHTML = `<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>`;
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
        connStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-green-500 inline-block"></span> Connected';
      } else { throw new Error("unhealthy"); }
    } catch {
      connStatus.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-500 animate-pulse inline-block"></span> Offline';
    }
  }
  checkHealth();
  roleSelect.addEventListener("change", () => { token = null; });

  async function sendMessage(message) {
    addMessage("fan", message);
    const typing = addTypingIndicator();
    try {
      await ensureToken();
      const resp = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({ message, language: langSelect.value }),
      });
      if (resp.status === 401) { token = null; throw new Error("auth expired"); }
      if (!resp.ok) throw new Error(`request failed (${resp.status})`);
      const data = await resp.json();
      typing.remove();
      const agents = (data.agents_used || []).join(", ") || "general";
      addMessage("copilot", data.response_text, agents);
      lastBotText = data.response_text || "";
      speak(data.voice_ready_text || data.response_text);
    } catch (err) {
      typing.remove();
      addMessage("copilot", "I couldn't reach the stadium systems just now. Please try again, or ask a nearby volunteer for help.", "error");
      toast("Couldn't reach the copilot backend.", "error");
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
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  document.querySelectorAll(".prompt-chip").forEach(btn => btn.addEventListener("click", () => sendMessage(btn.textContent)));
  document.querySelectorAll(".emergency-chip").forEach(btn => btn.addEventListener("click", () => {
    document.getElementById("chat").scrollIntoView({ behavior: "smooth" });
    sendMessage(btn.dataset.msg);
  }));
  document.getElementById("sos-btn").addEventListener("click", () => {
    document.getElementById("chat").scrollIntoView({ behavior: "smooth" });
    sendMessage("This is an SOS emergency — I need immediate assistance.");
  });

  document.getElementById("copy-last-btn").addEventListener("click", async () => {
    if (!lastBotText) { toast("No response to copy yet."); return; }
    try { await navigator.clipboard.writeText(lastBotText); toast("Response copied to clipboard."); }
    catch { toast("Couldn't copy — try selecting the text manually.", "error"); }
  });
  document.getElementById("clear-chat-btn").addEventListener("click", () => {
    log.innerHTML = "";
    lastBotText = "";
    toast("Conversation cleared.");
  });

  // ---------- Live telemetry (mock, same pattern as backend's mocked live data) ----------
  const GATES = ["Gate 1", "Gate 2", "Gate 3", "Gate 4", "North Concourse", "South Concourse"];
  const LEVELS = ["low", "moderate", "high"];
  let gateDensity = {};
  GATES.forEach(g => gateDensity[g] = LEVELS[Math.floor(Math.random() * 3)]);

  function timeAgoLabel(id) {
    const el = document.getElementById(id);
    if (el) el.textContent = "Updated just now";
  }

  function renderRecommendations() {
    const low = Object.entries(gateDensity).filter(([, v]) => v === "low").map(([g]) => g);
    const high = Object.entries(gateDensity).filter(([, v]) => v === "high").map(([g]) => g);
    const recs = [];
    if (low.length) recs.push(`Use ${low[0]} to avoid congestion.`);
    if (high.length) recs.push(`Heavy crowd near ${high[0]} — allow extra time.`);
    recs.push("Parking P2 has available spaces.");
    recs.push("Metro Line 1 is running with a short delay.");
    recs.push("Food Court B has shorter queues than Court A.");
    const list = document.getElementById("recommendations-list");
    if (list) list.innerHTML = recs.map(r => `<li class="flex items-start gap-2"><svg width="15" height="15" style="color:var(--accent); flex-shrink:0; margin-top:2px"><use href="#i-check"/></svg><span>${r}</span></li>`).join("");
  }

  function renderHeatmap() {
    const el = document.getElementById("heatmap-list");
    if (!el) return;
    const widthFor = { low: 30, moderate: 62, high: 90 };
    const colorFor = { low: "var(--accent)", moderate: "var(--warn)", high: "var(--danger)" };
    el.innerHTML = Object.entries(gateDensity).map(([gate, level]) => `
      <div>
        <div class="flex justify-between text-xs mb-1"><span>${gate}</span><span style="color:var(--ink-tertiary)">${level}</span></div>
        <div class="heat-bar"><div class="heat-fill" style="width:${widthFor[level]}%; background:${colorFor[level]}"></div></div>
      </div>`).join("");
  }

  function tickTelemetry() {
    GATES.forEach(g => { if (Math.random() < 0.4) gateDensity[g] = LEVELS[Math.floor(Math.random() * 3)]; });
    const topGate = Object.entries(gateDensity)[0];
    
    const sc = document.getElementById("stat-crowd");
    if (sc) sc.textContent = `${topGate[0]} · ${topGate[1][0].toUpperCase()}${topGate[1].slice(1)}`;
    const sq = document.getElementById("stat-queue");
    if (sq) sq.textContent = `${2 + Math.floor(Math.random() * 10)}–${8 + Math.floor(Math.random() * 6)} min`;
    const sp = document.getElementById("stat-parking");
    if (sp) sp.textContent = `Lot A · ${340 + Math.floor(Math.random() * 20)}/500`;
    const sw = document.getElementById("stat-weather");
    if (sw) sw.textContent = `${Math.round(22 + Math.random() * 8)}°C · ${["Clear","Cloudy","Light rain"][Math.floor(Math.random()*3)]}`;
    const st = document.getElementById("stat-transit");
    if (st) st.textContent = ["Metro L2 · On time","Metro L2 · 5 min delay","Metro L2 · 10 min delay"][Math.floor(Math.random()*3)];
    
    ["stat-crowd-time","stat-queue-time","stat-parking-time","stat-weather-time","stat-transit-time"].forEach(timeAgoLabel);
    renderRecommendations();
    renderHeatmap();
  }
  tickTelemetry();
  setInterval(tickTelemetry, 6000);

  // Ops snapshot varies slightly by role for the dashboard preview
  function renderOpsSnapshot() {
    const role = roleSelect.value;
    const base = role === "staff" ? { alerts: 1, volunteers: 42, incidents: 2, resource: 74 }
      : role === "volunteer" ? { alerts: 1, volunteers: 42, incidents: 1, resource: 68 }
      : { alerts: 0, volunteers: 42, incidents: 0, resource: 55 };
    
    const oa = document.getElementById("ops-alerts");
    if (oa) oa.textContent = base.alerts;
    const ov = document.getElementById("ops-volunteers");
    if (ov) ov.textContent = base.volunteers;
    const oi = document.getElementById("ops-incidents");
    if (oi) oi.textContent = base.incidents;
    const or = document.getElementById("ops-resource");
    if (or) or.textContent = base.resource + "%";
  }
  renderOpsSnapshot();
  roleSelect.addEventListener("change", renderOpsSnapshot);

  // Simulated periodic notifications (matches checklist's toast examples)
  const SAMPLE_NOTIFS = ["Route updated for Gate 3.", "Crowd alert: Gate 1 approaching capacity.", "Weather warning: light rain expected in 20 minutes.", "Parking now available in Lot C.", ];
  setInterval(() => {
    if (Math.random() < 0.5) toast(SAMPLE_NOTIFS[Math.floor(Math.random() * SAMPLE_NOTIFS.length)]);
  }, 15000);

  // ---------- Accordions ----------
  document.querySelectorAll(".accordion-trigger").forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const item = trigger.closest(".accordion-item");
      const content = item.querySelector(".accordion-content");
      const isActive = item.classList.contains("active");
      document.querySelectorAll(".accordion-item").forEach((other) => {
        other.classList.remove("active");
        other.querySelector(".accordion-content").style.maxHeight = null;
      });
      if (!isActive) { item.classList.add("active"); content.style.maxHeight = content.scrollHeight + "px"; }
    });
  });

  // ---------- Nav scroll behavior ----------
  const siteNav = document.getElementById("site-nav");
  if (siteNav) {
    window.addEventListener("scroll", () => siteNav.classList.toggle("scrolled", window.scrollY > 12));
  }

  const sections = ["top","chat","map","status","accessibility","emergency","dashboard"].map(id => document.getElementById(id)).filter(Boolean);
  const navLinks = document.querySelectorAll(".nav-link");
  if (sections.length && navLinks.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          navLinks.forEach(l => l.classList.toggle("active", l.dataset.section === entry.target.id));
        }
      });
    }, { rootMargin: "-40% 0px -55% 0px" });
    sections.forEach(s => io.observe(s));
  }

  // ---------- Reveal on scroll ----------
  const reveals = document.querySelectorAll(".reveal");
  if (reveals.length) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add("in-view"); revealObserver.unobserve(entry.target); } });
    }, { threshold: 0.12 });
    reveals.forEach(el => revealObserver.observe(el));
  }
})();
