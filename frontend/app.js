/* NexusBridge workspace SPA — talks to the FastAPI backend (/api/*). */
"use strict";

const api = (path, opts) =>
  fetch(path, opts).then(async (res) => {
    const body = res.status === 204 ? null : await res.json().catch(() => null);
    if (!res.ok) throw new Error((body && body.detail) || res.statusText);
    return body;
  });

const el = (id) => document.getElementById(id);
const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

const badge = (ok, good = "success", bad = "failure") =>
  `<span class="badge ${ok ? good : bad}">${ok ? good : bad}</span>`;

function setRow(tbody, cells) {
  const tr = document.createElement("tr");
  cells.forEach((c) => { const td = document.createElement("td"); td.innerHTML = c; tr.appendChild(td); });
  tbody.appendChild(tr);
}

async function checkHealth() {
  try {
    const h = await api("/api/health");
    el("health").textContent = `${h.service} v${h.version} · ${h.status}`;
    el("health").className = "health ok";
  } catch (e) {
    el("health").textContent = "offline";
    el("health").className = "health bad";
  }
}

async function loadDashboard() {
  const d = await api("/api/dashboard");
  el("dashboard-stats").innerHTML = [
    ["Total jobs", d.total_jobs], ["Active", d.active_jobs], ["Paused", d.paused_jobs],
    ["Total runs", d.total_runs], ["Rows in", d.total_rows_in], ["Rows out", d.total_rows_out],
    ["Error rate", `${(d.overall_error_rate * 100).toFixed(1)}%`],
  ].map(([l, n]) => `<div class="stat"><div class="label">${l}</div><div class="num">${n}</div></div>`).join("");

  const jb = el("dashboard-jobs").querySelector("tbody");
  jb.innerHTML = "";
  d.jobs.forEach((j) => setRow(jb, [
    esc(j.name), badge(j.status === "active", "active", "paused"), j.total_runs,
    j.success_runs, j.failure_runs, `${(j.error_rate * 100).toFixed(1)}%`,
    esc(j.last_run_at || "—"),
  ]));

  const rb = el("dashboard-runs").querySelector("tbody");
  rb.innerHTML = "";
  d.recent_runs.forEach((r) => setRow(rb, [
    r.id, esc(r.job_id), badge(r.status === "success"), r.rows_in, r.rows_out,
    esc(r.error || "—"), esc(r.started_at),
  ]));
}

async function loadConnectors() {
  const rows = await api("/api/connectors");
  const tb = el("connectors").querySelector("tbody");
  tb.innerHTML = "";
  rows.forEach((c) => setRow(tb, [
    c.id, esc(c.name), esc(c.type), esc(c.base_url || "—"),
    esc(c.auth_type), esc(c.notes || "—"), esc(c.created_at),
  ]));
}

async function loadMappings() {
  const rows = await api("/api/mappings");
  const tb = el("mappings").querySelector("tbody");
  tb.innerHTML = "";
  rows.forEach((m) => setRow(tb, [
    m.id, esc(m.name), `${m.source_connector_id} → ${m.target_connector_id}`,
    esc(m.fields.map((f) => `${f.source_field}→${f.target_field}(${f.transform})`).join(", ")),
    esc(m.notes || "—"),
  ]));
}

async function loadJobs() {
  const rows = await api("/api/jobs");
  const tb = el("jobs").querySelector("tbody");
  tb.innerHTML = "";
  for (const j of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${j.id}</td><td>${esc(j.name)}</td>
      <td>${j.source_connector_id}</td><td>${j.target_connector_id}</td>
      <td>${j.mapping_id}</td><td>${esc(j.schedule_note || "—")}</td>
      <td>${badge(j.status === "active", "active", "paused")}</td>
      <td><button class="action" data-run="${j.id}">Run</button></td>`;
    tb.appendChild(tr);
  }
  tb.querySelectorAll("button[data-run]").forEach((btn) => {
    btn.addEventListener("click", () => runJob(btn.dataset.run, btn));
  });
}

async function runJob(jobId, btn) {
  btn.disabled = true;
  const out = el("run-output");
  try {
    const r = await api(`/api/jobs/${jobId}/run`, { method: "POST" });
    out.classList.remove("hidden");
    out.textContent = JSON.stringify({
      status: r.status, rows_in: r.rows_in, rows_out: r.rows_out,
      error: r.error || null, output: r.output,
    }, null, 2);
    await loadDashboard();
  } catch (e) {
    out.classList.remove("hidden");
    out.textContent = `Run failed: ${e.message}`;
  } finally {
    btn.disabled = false;
  }
}

async function loadWebhooks() {
  const rows = await api("/api/webhooks");
  const tb = el("webhooks").querySelector("tbody");
  tb.innerHTML = "";
  rows.forEach((w) => setRow(tb, [
    w.id, esc(w.path), esc(w.method), esc(w.job_id),
    badge(Boolean(w.active), "active", "inactive"),
  ]));
}

const loaders = {
  dashboard: loadDashboard, connectors: loadConnectors,
  mappings: loadMappings, jobs: loadJobs, webhooks: loadWebhooks,
};

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("hidden", p.id !== `pane-${tab}`));
  if (loaders[tab]) loaders[tab].then(() => {}).catch((e) => {
    el(`pane-${tab}`).insertAdjacentHTML("beforeend", `<p class="hint">Load error: ${esc(e.message)}</p>`);
  });
}

document.querySelectorAll(".tab").forEach((t) =>
  t.addEventListener("click", () => switchTab(t.dataset.tab))
);

checkHealth();
switchTab("dashboard");