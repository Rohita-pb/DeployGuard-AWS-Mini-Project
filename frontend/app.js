// DeployGuard Frontend Vanilla JavaScript Logic

const API_BASE = "/api";

// Global Cache for loaded applications and deployments
let state = {
  apps: [],
  deployments: [],
  incidents: [],
  checks: [],
  rollbacks: [],
  activeTab: "dashboard"
};

// Initialization on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupEventListeners();
  loadAllData();
});

// Navigation Setup
function setupNavigation() {
  const navButtons = document.querySelectorAll(".nav-btn");
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.toggle("active", content.id === `tab-${tabId}`);
  });

  // Refresh data relevant to tab
  if (tabId === "dashboard") loadDashboard();
  else if (tabId === "applications") loadApplications();
  else if (tabId === "deployments") loadDeployments();
  else if (tabId === "incidents") loadIncidents();
  else if (tabId === "checks") loadChecks();
  else if (tabId === "rollbacks") loadRollbacks();
}

function setupEventListeners() {
  document.getElementById("btn-export-csv").addEventListener("click", exportIncidentCsv);
  document.getElementById("btn-refresh-all").addEventListener("click", () => {
    showToast("Refreshing all data...", "info");
    loadAllData();
  });

  const incidentFilter = document.getElementById("filter-incident-status");
  if (incidentFilter) {
    incidentFilter.addEventListener("change", () => loadIncidents());
  }
}

// Global Data Loader
async function loadAllData() {
  await Promise.all([
    loadDashboard(),
    loadApplications(),
    loadDeployments(),
    loadIncidents(),
    loadChecks(),
    loadRollbacks()
  ]);
}

// 1. Dashboard
async function loadDashboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load dashboard data");

    const data = json.data;
    document.getElementById("stat-total-apps").textContent = data.total_applications;
    document.getElementById("stat-healthy-apps").textContent = data.healthy_applications;
    document.getElementById("stat-unhealthy-apps").textContent = data.unhealthy_applications;
    document.getElementById("stat-active-incidents").textContent = data.active_incidents;

    renderDashboardRecentDeployments(data.recent_deployments || []);
  } catch (err) {
    showToast(`Dashboard error: ${err.message}`, "error");
  }
}

function renderDashboardRecentDeployments(deployments) {
  const tbody = document.getElementById("dashboard-recent-deployments");
  if (!deployments.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No deployments recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = deployments.map(d => `
    <tr>
      <td><strong>${escapeHtml(d.application_name || "App #" + d.application_id)}</strong></td>
      <td><code>${escapeHtml(d.version)}</code></td>
      <td><span class="badge badge-${d.status.toLowerCase()}">${d.status}</span></td>
      <td>${formatDate(d.created_at)}</td>
      <td>${escapeHtml(d.notes || "-")}</td>
    </tr>
  `).join("");
}

// 2. Applications
async function loadApplications() {
  try {
    const res = await fetch(`${API_BASE}/apps`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load apps");

    state.apps = json.data;
    renderAppsTable(state.apps);
    populateAppDropdowns();
  } catch (err) {
    showToast(`Applications error: ${err.message}`, "error");
  }
}

function renderAppsTable(apps) {
  const tbody = document.getElementById("apps-table-body");
  if (!apps.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No applications registered. Click "+ Register Application" to get started.</td></tr>`;
    return;
  }

  tbody.innerHTML = apps.map(app => {
    const statusClass = (app.current_status || "UNKNOWN").toLowerCase();
    const latency = app.last_response_time_ms != null ? `${app.last_response_time_ms} ms` : "N/A";

    return `
      <tr>
        <td><strong>${escapeHtml(app.name)}</strong></td>
        <td><a href="${escapeHtml(app.base_url)}" target="_blank" rel="noopener">${escapeHtml(app.base_url)}</a></td>
        <td><code>${escapeHtml(app.health_check_url)}</code></td>
        <td><code>${app.expected_status_code}</code></td>
        <td><span class="badge badge-${statusClass}">${app.current_status || "UNKNOWN"}</span></td>
        <td>${latency}</td>
        <td>
          <button class="btn btn-sm btn-primary" onclick="runHealthCheck(${app.id}, this)">
            ⚡ Run Check
          </button>
          <button class="btn btn-sm btn-danger" onclick="confirmDeleteApp(${app.id}, '${escapeHtml(app.name)}')">
            🗑️ Delete
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function handleRegisterApp(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-submit-app");
  btn.disabled = true;
  btn.textContent = "Registering...";

  const payload = {
    name: document.getElementById("app-name").value.trim(),
    base_url: document.getElementById("app-base-url").value.trim(),
    health_check_url: document.getElementById("app-health-url").value.trim(),
    expected_status_code: parseInt(document.getElementById("app-expected-code").value, 10)
  };

  try {
    const res = await fetch(`${API_BASE}/apps`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (!json.success) {
      const errMsg = json.errors ? json.errors.join(", ") : (json.error || "Failed to register application");
      throw new Error(errMsg);
    }

    showToast("Application registered successfully!", "success");
    closeModal("modal-register-app");
    document.getElementById("form-register-app").reset();
    document.getElementById("app-expected-code").value = "200";
    await loadAllData();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Register";
  }
}

async function confirmDeleteApp(appId, appName) {
  if (!confirm(`Are you sure you want to delete application "${appName}"? This will delete all its health checks, deployments, and incidents.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/apps/${appId}`, { method: "DELETE" });
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to delete application");

    showToast(json.message || "Application deleted.", "success");
    await loadAllData();
  } catch (err) {
    showToast(`Delete failed: ${err.message}`, "error");
  }
}

// 3. Health Checks
async function runHealthCheck(appId, buttonElem) {
  if (buttonElem) {
    buttonElem.disabled = true;
    buttonElem.textContent = "Checking...";
  }

  try {
    const res = await fetch(`${API_BASE}/apps/${appId}/check`, { method: "POST" });
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Health check failed");

    const check = json.data.check;
    if (check.status === "HEALTHY") {
      showToast(`Health check passed! (${check.http_status_code} in ${check.response_time_ms}ms)`, "success");
    } else {
      const incidentNotice = json.data.incident ? ` [Incident #${json.data.incident.id} active]` : "";
      showToast(`Health check failed: ${check.error_message || "Unexpected status"}${incidentNotice}`, "error");
    }

    await loadAllData();
  } catch (err) {
    showToast(`Check failed: ${err.message}`, "error");
  } finally {
    if (buttonElem) {
      buttonElem.disabled = false;
      buttonElem.textContent = "⚡ Run Check";
    }
  }
}

async function loadChecks() {
  try {
    const res = await fetch(`${API_BASE}/checks?limit=50`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load health check history");

    state.checks = json.data;
    renderChecksTable(state.checks);
  } catch (err) {
    showToast(`Health history error: ${err.message}`, "error");
  }
}

function renderChecksTable(checks) {
  const tbody = document.getElementById("checks-table-body");
  if (!checks.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No health checks performed yet. Use "Run Check" to test an application.</td></tr>`;
    return;
  }

  tbody.innerHTML = checks.map(c => `
    <tr>
      <td>#${c.id}</td>
      <td><strong>${escapeHtml(c.application_name || "App #" + c.application_id)}</strong></td>
      <td><span class="badge badge-${c.status.toLowerCase()}">${c.status}</span></td>
      <td><code>${c.http_status_code != null ? c.http_status_code : "-"}</code></td>
      <td>${c.response_time_ms != null ? `${c.response_time_ms} ms` : "-"}</td>
      <td>${formatDate(c.checked_at)}</td>
      <td>${escapeHtml(c.error_message || "OK (Normal)")}</td>
    </tr>
  `).join("");
}

// 4. Deployments
async function loadDeployments() {
  try {
    const res = await fetch(`${API_BASE}/deployments`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load deployments");

    state.deployments = json.data;
    renderDeploymentsTable(state.deployments);
  } catch (err) {
    showToast(`Deployments error: ${err.message}`, "error");
  }
}

function renderDeploymentsTable(deployments) {
  const tbody = document.getElementById("deployments-table-body");
  if (!deployments.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No deployments recorded yet. Click "+ Record Deployment" to track a release.</td></tr>`;
    return;
  }

  tbody.innerHTML = deployments.map(d => `
    <tr>
      <td>#${d.id}</td>
      <td><strong>${escapeHtml(d.application_name || "App #" + d.application_id)}</strong></td>
      <td><code>${escapeHtml(d.version)}</code></td>
      <td><span class="badge badge-${d.status.toLowerCase()}">${d.status}</span></td>
      <td>${formatDate(d.created_at)}</td>
      <td>${escapeHtml(d.notes || "-")}</td>
      <td>
        <button class="btn btn-sm btn-outline" onclick="openRollbackForApp(${d.application_id}, ${d.id})">
          ⏪ Rollback
        </button>
      </td>
    </tr>
  `).join("");
}

async function handleRecordDeployment(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-submit-deployment");
  btn.disabled = true;
  btn.textContent = "Saving...";

  const payload = {
    application_id: parseInt(document.getElementById("deploy-app-select").value, 10),
    version: document.getElementById("deploy-version").value.trim(),
    status: document.getElementById("deploy-status").value,
    notes: document.getElementById("deploy-notes").value.trim()
  };

  try {
    const res = await fetch(`${API_BASE}/deployments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (!json.success) {
      const errMsg = json.errors ? json.errors.join(", ") : (json.error || "Failed to record deployment");
      throw new Error(errMsg);
    }

    showToast("Deployment recorded successfully!", "success");
    closeModal("modal-record-deployment");
    document.getElementById("form-record-deployment").reset();
    await loadAllData();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Save Deployment";
  }
}

// 5. Incidents
async function loadIncidents() {
  try {
    const statusFilter = document.getElementById("filter-incident-status")?.value || "";
    const url = statusFilter ? `${API_BASE}/incidents?status=${statusFilter}` : `${API_BASE}/incidents`;
    const res = await fetch(url);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load incidents");

    state.incidents = json.data;
    renderIncidentsTable(state.incidents);
  } catch (err) {
    showToast(`Incidents error: ${err.message}`, "error");
  }
}

function renderIncidentsTable(incidents) {
  const tbody = document.getElementById("incidents-table-body");
  if (!incidents.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No incidents found. All applications are operating normally.</td></tr>`;
    return;
  }

  tbody.innerHTML = incidents.map(inc => {
    const isResolved = inc.status === "RESOLVED";
    return `
      <tr>
        <td>#${inc.id}</td>
        <td><strong>${escapeHtml(inc.application_name || "App #" + inc.application_id)}</strong></td>
        <td><span class="badge badge-${inc.status.toLowerCase()}">${inc.status}</span></td>
        <td>${escapeHtml(inc.reason)}</td>
        <td>${formatDate(inc.opened_at)}</td>
        <td>${inc.resolved_at ? formatDate(inc.resolved_at) : "-"}</td>
        <td>
          ${isResolved ? `<span class="badge badge-resolved">Resolved</span>` : `
            <button class="btn btn-sm btn-primary" onclick="resolveIncident(${inc.id}, this)">
              ✅ Resolve
            </button>
          `}
        </td>
      </tr>
    `;
  }).join("");
}

async function resolveIncident(incidentId, buttonElem) {
  if (buttonElem) {
    buttonElem.disabled = true;
    buttonElem.textContent = "Resolving...";
  }

  try {
    const res = await fetch(`${API_BASE}/incidents/${incidentId}/resolve`, {
      method: "PATCH"
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to resolve incident");

    showToast(json.message || "Incident resolved.", "success");
    await loadAllData();
  } catch (err) {
    showToast(`Resolution error: ${err.message}`, "error");
  } finally {
    if (buttonElem) {
      buttonElem.disabled = false;
      buttonElem.textContent = "✅ Resolve";
    }
  }
}

// 6. Rollback Workflow
async function loadRollbacks() {
  try {
    const res = await fetch(`${API_BASE}/rollbacks`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Failed to load rollbacks");

    state.rollbacks = json.data;
    renderRollbacksTable(state.rollbacks);
  } catch (err) {
    showToast(`Rollbacks error: ${err.message}`, "error");
  }
}

function renderRollbacksTable(rollbacks) {
  const tbody = document.getElementById("rollbacks-table-body");
  if (!rollbacks.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">No rollback events recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = rollbacks.map(r => `
    <tr>
      <td>#${r.id}</td>
      <td><strong>${escapeHtml(r.application_name || "App #" + r.application_id)}</strong></td>
      <td><code>${escapeHtml(r.source_version || "N/A")}</code></td>
      <td><code>${escapeHtml(r.target_version || "N/A")}</code></td>
      <td><span class="badge badge-simulated">${r.status}</span></td>
      <td>${formatDate(r.created_at)}</td>
    </tr>
  `).join("");
}

function openRollbackForApp(appId, sourceDeployId) {
  openModal("modal-initiate-rollback");
  const appSelect = document.getElementById("rollback-app-select");
  appSelect.value = appId;
  populateRollbackDeployments(appId, sourceDeployId);
}

function populateRollbackDeployments(appId, preselectSourceId = null) {
  const sourceSelect = document.getElementById("rollback-source-select");
  const targetSelect = document.getElementById("rollback-target-select");

  sourceSelect.innerHTML = `<option value="">Select source deployment...</option>`;
  targetSelect.innerHTML = `<option value="">Select target deployment...</option>`;

  if (!appId) return;

  const appDeployments = state.deployments.filter(d => d.application_id === parseInt(appId, 10));

  if (!appDeployments.length) {
    sourceSelect.innerHTML = `<option value="">No deployments found for this application</option>`;
    targetSelect.innerHTML = `<option value="">No deployments found for this application</option>`;
    return;
  }

  appDeployments.forEach(d => {
    const optionText = `#${d.id} - ${d.version} (${d.status}) - ${formatDate(d.created_at)}`;
    sourceSelect.innerHTML += `<option value="${d.id}">${optionText}</option>`;
    targetSelect.innerHTML += `<option value="${d.id}">${optionText}</option>`;
  });

  if (preselectSourceId) {
    sourceSelect.value = preselectSourceId;
  }
}

async function handleInitiateRollback(e) {
  e.preventDefault();
  const btn = document.getElementById("btn-submit-rollback");
  btn.disabled = true;
  btn.textContent = "Executing Rollback...";

  const sourceId = document.getElementById("rollback-source-select").value;
  const targetId = document.getElementById("rollback-target-select").value;

  if (!sourceId || !targetId) {
    showToast("Please select both source and target deployments.", "error");
    btn.disabled = false;
    btn.textContent = "Execute Rollback";
    return;
  }

  if (sourceId === targetId) {
    showToast("Source and target deployments must be different.", "error");
    btn.disabled = false;
    btn.textContent = "Execute Rollback";
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/deployments/${sourceId}/rollback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_deployment_id: parseInt(targetId, 10) })
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error || "Rollback execution failed");

    showToast(`Rollback recorded! ${json.message}`, "success");
    closeModal("modal-initiate-rollback");
    document.getElementById("form-initiate-rollback").reset();
    await loadAllData();
    switchTab("rollbacks");
  } catch (err) {
    showToast(`Rollback error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Execute Rollback";
  }
}

// 7. CSV Export
function exportIncidentCsv() {
  window.location.href = `${API_BASE}/reports/incidents.csv`;
  showToast("Downloading incident CSV report...", "info");
}

// Helper: Populate Dropdowns
function populateAppDropdowns() {
  const deployAppSelect = document.getElementById("deploy-app-select");
  const rollbackAppSelect = document.getElementById("rollback-app-select");

  const options = `<option value="">Select an application...</option>` +
    state.apps.map(a => `<option value="${a.id}">${escapeHtml(a.name)} (#${a.id})</option>`).join("");

  if (deployAppSelect) deployAppSelect.innerHTML = options;
  if (rollbackAppSelect) rollbackAppSelect.innerHTML = options;
}

// Modal Helpers
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
}

// Toast Helpers
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
    <button style="background:none;border:none;color:white;cursor:pointer;font-weight:bold;">&times;</button>
  `;

  toast.querySelector("button").addEventListener("click", () => toast.remove());
  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) toast.remove();
  }, 4000);
}

// Utility: Formatting and Escaping
function formatDate(isoStr) {
  if (!isoStr) return "-";
  try {
    const d = new Date(isoStr);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
