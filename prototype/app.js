const ids = {
  backendUrl: "backendUrl",
  taskId: "taskId",
  cpu: "cpu",
  latency: "latency",
  queue: "queue",
  pods: "pods",
  pendingUps: "pendingUps",
  pendingDowns: "pendingDowns",
  rate: "rate",
  avgLatency: "avgLatency",
  violations: "violations",
  dropped: "dropped",
  runButton: "runButton",
  result: "result",
};

const runtimeBackendUrl =
  (window.APP_CONFIG && String(window.APP_CONFIG.backendUrl || "").trim()) ||
  "http://localhost:8000";

function num(id) {
  return Number(document.getElementById(id).value);
}

function text(id) {
  return String(document.getElementById(id).value || "").trim();
}

function payload() {
  return {
    task_id: text(ids.taskId),
    time_step: 0,
    horizon: text(ids.taskId) === "easy" ? 180 : text(ids.taskId) === "hard" ? 300 : 240,
    cpu_utilization: num(ids.cpu),
    latency_ms: num(ids.latency),
    request_rate: num(ids.rate),
    queue_length: Math.max(0, Math.round(num(ids.queue))),
    active_pods: Math.max(1, Math.round(num(ids.pods))),
    pending_scale_ups: Math.max(0, Math.round(num(ids.pendingUps))),
    pending_scale_downs: Math.max(0, Math.round(num(ids.pendingDowns))),
    average_latency_ms: num(ids.avgLatency),
    total_sla_violations: Math.max(0, Math.round(num(ids.violations))),
    total_requests_dropped: Math.max(0, Math.round(num(ids.dropped))),
  };
}

function scaleLabel(delta) {
  if (delta > 0) return `Scale Up +${delta}`;
  if (delta < 0) return `Scale Down ${delta}`;
  return "Hold 0";
}

function render(data) {
  const root = document.getElementById(ids.result);
  root.innerHTML = "";

  const title = document.createElement("h3");
  title.textContent = `Recommended Action: ${scaleLabel(data.scale_delta)}`;

  const badge1 = document.createElement("span");
  badge1.className = "badge";
  badge1.textContent = `provider: ${data.provider}`;

  const badge2 = document.createElement("span");
  badge2.className = "badge";
  badge2.textContent = `model: ${data.model}`;

  const reason = document.createElement("pre");
  reason.textContent = data.rationale || "No rationale returned.";

  root.appendChild(title);
  root.appendChild(badge1);
  root.appendChild(badge2);
  root.appendChild(reason);
}

async function fetchAdvice() {
  const button = document.getElementById(ids.runButton);
  const base = text(ids.backendUrl).replace(/\/$/, "");
  const endpoint = `${base}/ai/scale-advice`;

  button.disabled = true;
  button.textContent = "Asking Gemini...";
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });

    if (!response.ok) {
      const msg = await response.text();
      throw new Error(msg || `HTTP ${response.status}`);
    }

    const data = await response.json();
    render(data);
  } catch (error) {
    const root = document.getElementById(ids.result);
    root.innerHTML = `<p class="placeholder">Error: ${String(error.message || error)}</p>`;
  } finally {
    button.disabled = false;
    button.textContent = "Get Scaling Advice";
  }
}

document.getElementById(ids.runButton).addEventListener("click", fetchAdvice);
document.getElementById(ids.backendUrl).value = runtimeBackendUrl;
