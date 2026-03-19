const state = {
  selectedJobId: null,
  jobs: [],
  results: [],
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function formatStatus(status) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function setBadge(element, status) {
  element.className = `badge ${status}`;
  element.textContent = formatStatus(status);
}

function renderStats(summary) {
  document.getElementById("totalJobs").textContent = summary.total_jobs;
  document.getElementById("activeJobs").textContent = summary.active_jobs;
  document.getElementById("successRate").textContent = `${summary.success_rate}%`;
  document.getElementById("recordsScraped").textContent = summary.records_scraped;
  document.getElementById("liveLabel").textContent =
    summary.active_jobs > 0 ? "Scraping in Progress..." : "Standing by";
}

function populateRules(rules) {
  const select = document.getElementById("ruleId");
  const currentValue = select.value;
  select.innerHTML = "";
  for (const rule of rules) {
    const option = document.createElement("option");
    option.value = rule.rule_id;
    option.textContent = `${rule.site_name} | ${rule.rule_id}`;
    select.appendChild(option);
  }
  if (currentValue) {
    select.value = currentValue;
  }
}

function renderChart(jobs) {
  const chart = document.getElementById("chartBars");
  chart.innerHTML = "";
  const chartJobs = jobs.slice(0, 6).reverse();
  const maxValue = Math.max(...chartJobs.map((job) => job.total_records), 1);
  for (const job of chartJobs) {
    const bar = document.createElement("div");
    bar.className = "chart-bar";
    bar.style.height = `${Math.max((job.total_records / maxValue) * 100, 12)}px`;
    bar.title = `${job.job_id}: ${job.total_records} records`;
    const label = document.createElement("span");
    label.textContent = job.total_records;
    bar.appendChild(label);
    chart.appendChild(bar);
  }
}

function renderJobStatus(job) {
  document.getElementById("selectedJobId").textContent = job ? job.job_id : "None";
  const badge = document.getElementById("selectedJobStatus");
  const progress = job ? job.progress : 0;
  if (job) {
    setBadge(badge, job.status);
  } else {
    badge.className = "badge";
    badge.textContent = "Idle";
  }
  document.getElementById("selectedJobProgress").textContent = `${progress}%`;
  document.getElementById("progressBar").style.width = `${progress}%`;
  document.getElementById("exportCsvBtn").href = job ? job.exports.csv : "#";
  document.getElementById("exportJsonBtn").href = job ? job.exports.json : "#";
}

function inferStatus(row) {
  return row.availability && row.availability.toLowerCase().includes("out")
    ? "Inventory Alert"
    : "Success";
}

function renderResults(rows) {
  state.results = rows;
  const filter = document.getElementById("tableSearch").value.trim().toLowerCase();
  const tbody = document.getElementById("resultsTableBody");
  tbody.innerHTML = "";
  const filtered = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(filter));
  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No rows match the current view.</td></tr>`;
    return;
  }
  for (const row of filtered) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.title ?? "-")}</td>
      <td>${escapeHtml(row.price ?? "-")}</td>
      <td>${escapeHtml(row.availability ?? "-")}</td>
      <td><a class="result-link" href="${escapeAttribute(row.product_link ?? "#")}" target="_blank">View</a></td>
      <td>${escapeHtml(inferStatus(row))}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderLogs(logs) {
  const container = document.getElementById("logsContainer");
  container.innerHTML = "";
  if (!logs.length) {
    container.innerHTML = `<div class="log-line">No logs for this job yet.</div>`;
    return;
  }
  for (const log of logs) {
    const line = document.createElement("div");
    line.className = "log-line";
    line.textContent = `[${new Date(log.timestamp).toLocaleTimeString()}] ${log.event_type}: ${log.message}`;
    container.appendChild(line);
  }
}

async function loadJobDetails(jobId) {
  if (!jobId) {
    renderResults([]);
    renderLogs([]);
    renderJobStatus(null);
    return;
  }
  const [results, logs] = await Promise.all([
    fetchJson(`/jobs/results/${jobId}`),
    fetchJson(`/jobs/logs/${jobId}`),
  ]);
  const rows = results.map((item) => item.extracted_json);
  renderResults(rows);
  renderLogs(logs);
}

async function refreshDashboard() {
  try {
    const data = await fetchJson("/dashboard/summary");
    document.getElementById("apiStatus").textContent = "Connected";
    renderStats(data.summary);
    populateRules(data.rules);
    state.jobs = data.jobs;
    renderChart(data.jobs);

    const selectedJob =
      data.jobs.find((job) => job.job_id === state.selectedJobId) ||
      data.jobs[0] ||
      null;

    state.selectedJobId = selectedJob ? selectedJob.job_id : null;
    renderJobStatus(selectedJob);
    await loadJobDetails(state.selectedJobId);
  } catch (error) {
    document.getElementById("apiStatus").textContent = "Offline";
    console.error(error);
  }
}

async function createJob(event) {
  event.preventDefault();
  const payload = {
    rule_id: document.getElementById("ruleId").value,
    mode: document.getElementById("mode").value,
    pages: Number(document.getElementById("pages").value),
    output_formats: ["csv", "json", "xlsx"],
  };
  const response = await fetchJson("/jobs/launch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  state.selectedJobId = response.job_id;
  await refreshDashboard();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

document.getElementById("jobForm").addEventListener("submit", createJob);
document.getElementById("refreshBtn").addEventListener("click", refreshDashboard);
document.getElementById("clearBtn").addEventListener("click", () => renderResults([]));
document.getElementById("tableSearch").addEventListener("input", () => renderResults(state.results));

refreshDashboard();
setInterval(refreshDashboard, 5000);
