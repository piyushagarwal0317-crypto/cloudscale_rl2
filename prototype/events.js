const eventIds = {
  backendUrl: "backendUrl",
  limit: "limit",
  refreshButton: "refreshButton",
  autoRefresh: "autoRefresh",
  status: "status",
  eventsList: "eventsList",
};

const runtimeBackendUrl =
  (window.APP_CONFIG && String(window.APP_CONFIG.backendUrl || "").trim()) ||
  "http://localhost:8000";

let refreshTimer = null;

function txt(id) {
  return String(document.getElementById(id).value || "").trim();
}

function toNum(id, fallback) {
  const value = Number(document.getElementById(id).value);
  return Number.isFinite(value) ? value : fallback;
}

function asDate(value) {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function setStatus(text) {
  document.getElementById(eventIds.status).textContent = text;
}

function scaleLabel(delta) {
  if (delta > 0) return `+${delta}`;
  if (delta < 0) return `${delta}`;
  return "0";
}

function renderEvents(events) {
  const root = document.getElementById(eventIds.eventsList);
  root.innerHTML = "";

  if (!events.length) {
    root.innerHTML = '<p class="placeholder">No events found yet.</p>';
    return;
  }

  for (const event of events) {
    const request = event.request || {};
    const response = event.response || {};

    const card = document.createElement("article");
    card.className = "event-card";

    const h = document.createElement("h3");
    h.textContent = `${asDate(event.created_at)} | action ${scaleLabel(Number(response.scale_delta || 0))}`;

    const badges = document.createElement("p");
    badges.className = "event-badges";
    badges.innerHTML = `
      <span class="badge">provider: ${String(response.provider || "unknown")}</span>
      <span class="badge">model: ${String(response.model || "unknown")}</span>
      <span class="badge">task: ${String(request.task_id || "unknown")}</span>
    `;

    const metrics = document.createElement("pre");
    metrics.textContent = [
      `cpu=${request.cpu_utilization ?? "?"}`,
      `latency_ms=${request.latency_ms ?? "?"}`,
      `queue=${request.queue_length ?? "?"}`,
      `pods=${request.active_pods ?? "?"}`,
      `request_rate=${request.request_rate ?? "?"}`,
    ].join(" | ");

    const rationale = document.createElement("pre");
    rationale.textContent = String(response.rationale || "No rationale saved.");

    card.appendChild(h);
    card.appendChild(badges);
    card.appendChild(metrics);
    card.appendChild(rationale);
    root.appendChild(card);
  }
}

async function fetchEvents() {
  const base = txt(eventIds.backendUrl).replace(/\/$/, "");
  const limit = Math.max(1, Math.min(100, Math.round(toNum(eventIds.limit, 20))));
  const endpoint = `${base}/ai/scale-advice/events?limit=${limit}`;

  setStatus("Loading events...");
  try {
    const res = await fetch(endpoint, { method: "GET" });
    if (!res.ok) {
      const message = await res.text();
      throw new Error(message || `HTTP ${res.status}`);
    }

    const payload = await res.json();
    const events = Array.isArray(payload.events) ? payload.events : [];
    renderEvents(events);
    setStatus(`Loaded ${events.length} events. Firestore logging enabled: ${Boolean(payload.firestore_logging_enabled)}`);
  } catch (error) {
    setStatus(`Error fetching events: ${String(error.message || error)}`);
    renderEvents([]);
  }
}

function toggleAutoRefresh() {
  const checked = Boolean(document.getElementById(eventIds.autoRefresh).checked);
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (checked) {
    refreshTimer = setInterval(fetchEvents, 10000);
  }
}

document.getElementById(eventIds.backendUrl).value = runtimeBackendUrl;
document.getElementById(eventIds.refreshButton).addEventListener("click", fetchEvents);
document.getElementById(eventIds.autoRefresh).addEventListener("change", toggleAutoRefresh);

fetchEvents();
toggleAutoRefresh();
