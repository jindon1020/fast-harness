const API = "/api";
const STEP_ORDER = ["intake", "root_cause", "fix_plan", "code_generation", "code_review", "unit_test", "regression"];
const RUNNING_STATUSES = new Set(["running", "waiting_approval"]);
const STEP_ARTIFACTS = {
  intake: "bug_report.md",
  root_cause: "diagnosis.md",
  fix_plan: "fix_plan.md",
  code_generation: "implementation_notes.md",
  code_review: "review_feedback.md",
  unit_test: "unit_test_results.md",
  regression: "regression_results.md",
};

let state = {
  user: null,
  users: [],
  repos: [],
  pipelines: [],
  activeId: "",
  activeStep: "",
  stream: null,
  pollTimer: null,
};

const $ = (selector) => document.querySelector(selector);

function authHeaders() {
  return state.user ? { "X-User-Id": state.user.id } : {};
}

async function api(method, path, body) {
  const options = {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(API + path, options);
  if (res.status === 401 || res.status === 403) {
    window.location.href = "/login";
    return null;
  }
  if (!res.ok) throw new Error(await responseErrorMessage(res));
  return res.json();
}

async function responseErrorMessage(res) {
  const text = await res.text();
  try {
    const data = JSON.parse(text);
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map(item => item.msg || JSON.stringify(item)).join("; ");
    return data.message || text || res.statusText;
  } catch {
    return text || res.statusText;
  }
}

async function init() {
  applyTheme();
  await loadMe();
  await Promise.all([loadUsers(), loadRepos(), loadPipelines()]);
  bindEvents();
  renderFormOptions();
  renderPipelines();
  const initialPipeline = new URLSearchParams(window.location.search).get("pipeline");
  if (initialPipeline) await selectPipeline(initialPipeline);
  else showCreateView();
}

async function loadMe() {
  const data = await api("GET", "/me");
  state.user = data.user;
  $("#userLabel").textContent = `${data.user.name} · ${data.user.role}`;
}

async function loadUsers() {
  const data = await api("GET", "/users");
  state.users = data.users || [];
}

async function loadRepos() {
  const data = await api("GET", "/repositories");
  state.repos = data.repositories || [];
}

async function loadPipelines() {
  const data = await api("GET", "/bug-pipelines");
  state.pipelines = data.pipelines || [];
}

function bindEvents() {
  $("#pipelineForm").addEventListener("submit", createPipeline);
  $("#repoKey").addEventListener("change", loadBranches);
  $("#btnRefresh").addEventListener("click", refreshAll);
  $("#btnReloadOutput").addEventListener("click", loadOutput);
  $("#btnLogout").addEventListener("click", logout);
  $("#btnTheme").addEventListener("click", toggleTheme);
  $("#btnNewPipeline").addEventListener("click", showCreateView);
  $("#btnApprovalClose").addEventListener("click", closeApprovalModal);
  $("#btnApprovalCancel").addEventListener("click", closeApprovalModal);
  $("#btnApprovalConfirm").addEventListener("click", submitApprovalModal);
  $("#approvalModal").addEventListener("click", (event) => {
    if (event.target.id === "approvalModal") closeApprovalModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#approvalModal").hidden) closeApprovalModal();
  });
}

function showCreateView() {
  state.activeId = "";
  state.activeStep = "";
  closeStream();
  stopPolling();
  $("#createView").hidden = false;
  $("#pipelineView").hidden = true;
  renderPipelines();
}

function showPipelineView() {
  $("#createView").hidden = true;
  $("#pipelineView").hidden = false;
}

function renderFormOptions() {
  $("#repoKey").innerHTML = state.repos.map(repo => `<option value="${escapeHtml(repo.key)}">${escapeHtml(repo.name)}</option>`).join("");
  const developers = state.users.filter(user => user.role === "member" || user.role === "admin");
  $("#reviewerId").innerHTML = developers.map(user => `<option value="${escapeHtml(user.id)}">${escapeHtml(user.name)} (${escapeHtml(user.id)})</option>`).join("");
  loadBranches();
}

async function loadBranches() {
  const repoKey = $("#repoKey").value;
  const select = $("#targetBranch");
  select.innerHTML = `<option value="">Loading...</option>`;
  if (!repoKey) return;
  try {
    const data = await api("GET", `/repositories/${encodeURIComponent(repoKey)}/branches`);
    const branches = (data.branches || []).filter(branch => branch.startsWith("feature/"));
    select.innerHTML = branches.length
      ? `<option value="">选择 feature 分支</option>` + branches.map(branch => `<option value="${escapeHtml(branch)}">${escapeHtml(branch)}</option>`).join("")
      : `<option value="">没有可用 feature/* 远端分支</option>`;
  } catch (error) {
    select.innerHTML = `<option value="">分支加载失败</option>`;
    toast(error.message);
  }
}

async function createPipeline(event) {
  event.preventDefault();
  const button = $("#btnCreate");
  button.disabled = true;
  try {
    const created = await api("POST", "/bug-pipelines", formPayload());
    await loadPipelines();
    renderPipelines();
    $("#pipelineForm").reset();
    renderFormOptions();
    await selectPipeline(created.pipeline_id);
    toast("Pipeline created and started");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
  }
}

function formPayload() {
  return {
    repo_key: $("#repoKey").value,
    target_branch: $("#targetBranch").value,
    namespace: $("#namespace").value,
    request_id: $("#requestId").value || null,
    affected_api: $("#affectedApi").value,
    problem_description: $("#problemDescription").value,
    expected_result: $("#expectedResult").value,
    actual_result: $("#actualResult").value,
    reviewer_id: $("#reviewerId").value,
    occurred_at: $("#occurredAt").value || null,
    affected_data: $("#affectedData").value || null,
    regression_curl: $("#regressionCurl").value || null,
    screenshot_notes: $("#screenshotNotes").value || null,
    extra_context: $("#extraContext").value || null,
  };
}

function renderPipelines() {
  const list = $("#pipelineList");
  if (!state.pipelines.length) {
    list.innerHTML = `<div class="empty">暂无 pipeline</div>`;
    return;
  }
  list.innerHTML = state.pipelines.map(item => `
    <button class="pipeline-item ${item.pipeline_id === state.activeId ? "active" : ""}" data-id="${escapeHtml(item.pipeline_id)}">
      <div class="pipeline-item__id">${escapeHtml(item.pipeline_id)} · ${escapeHtml(item.status)}</div>
      <div class="pipeline-item__desc">${escapeHtml(item.problem_description)}</div>
    </button>
  `).join("");
  list.querySelectorAll(".pipeline-item").forEach(button => {
    button.addEventListener("click", () => selectPipeline(button.dataset.id));
  });
}

async function selectPipeline(id) {
  showPipelineView();
  state.activeId = id;
  const data = await api("GET", `/bug-pipelines/${encodeURIComponent(id)}`);
  upsertPipeline(data);
  if (!state.activeStep) state.activeStep = currentStep(data);
  renderPipelines();
  renderDetail(data);
  await loadOutput();
  if (pipelineIsLive(data)) {
    startStream();
    startPolling();
  } else {
    closeStream();
    stopPolling();
  }
}

function upsertPipeline(item) {
  const index = state.pipelines.findIndex(existing => existing.pipeline_id === item.pipeline_id);
  if (index >= 0) state.pipelines[index] = item;
  else state.pipelines.unshift(item);
}

function activePipeline() {
  return state.pipelines.find(item => item.pipeline_id === state.activeId);
}

function currentStep(item) {
  const running = STEP_ORDER.find(step => item.steps[step]?.status === "running");
  if (running) return running;
  const waiting = STEP_ORDER.find(step => item.steps[step]?.status === "waiting_approval");
  if (waiting) return waiting;
  const firstPending = STEP_ORDER.find(step => item.steps[step]?.status === "pending");
  if (firstPending) return firstPending;
  return "regression";
}

function pipelineIsLive(item) {
  return item && (item.status === "running" || item.status === "waiting_approval" || STEP_ORDER.some(step => RUNNING_STATUSES.has(item.steps[step]?.status)));
}

function renderDetail(item) {
  const nodes = STEP_ORDER.map((step, idx) => renderNode(item, step, idx + 1)).join("");
  $("#detail").innerHTML = `
    <section class="card summary">
      <div class="summary__title">${escapeHtml(item.pipeline_id)}</div>
      <div class="summary__desc">${escapeHtml(item.problem_description)}</div>
      <div class="meta">
        <span class="pill">${escapeHtml(item.status)}</span>
        <span class="pill">repo:${escapeHtml(item.repo_name)}</span>
        <span class="pill">target:${escapeHtml(item.target_branch)}</span>
        <span class="pill">bugfix:${escapeHtml(item.bugfix_branch)}</span>
        <span class="pill">ns:${escapeHtml(item.namespace)}</span>
      </div>
      <div class="actions">
        ${approvalButtons(item)}
        <button class="btn" id="btnLoadDiff">查看 Diff</button>
      </div>
      <div class="hint">流水线会自动推进。修复计划阶段会暂停等待审批，最终由研发人工合并 bugfix 分支到目标 feature 分支。</div>
    </section>
    <section class="pipeline-track">${nodes}</section>
  `;
  $("#detail").querySelectorAll(".pipeline-node").forEach(card => {
    card.addEventListener("click", () => {
      state.activeStep = card.dataset.step;
      renderDetail(activePipeline());
      loadOutput();
    });
  });
  $("#btnApprove")?.addEventListener("click", () => openApprovalModal(true));
  $("#btnReject")?.addEventListener("click", () => openApprovalModal(false));
  $("#btnLoadDiff")?.addEventListener("click", loadDiff);
}

function renderNode(item, step, idx) {
  const info = item.steps[step];
  const active = state.activeStep === step ? "active" : "";
  return `
    <article class="pipeline-node ${active}" data-step="${escapeHtml(step)}" data-status="${escapeHtml(info.status)}">
      <div class="node-circle">${idx}</div>
      <div class="node-title">${escapeHtml(info.title)}</div>
      <div class="node-status">${escapeHtml(info.status)} · ${info.attempts || 0}</div>
    </article>
  `;
}

function approvalButtons(item) {
  const waiting = item.steps.fix_plan?.status === "waiting_approval";
  const canApprove = waiting && state.user && (state.user.role === "admin" || state.user.id === item.reviewer_id);
  if (!canApprove) return "";
  return `<button class="btn btn-primary" id="btnApprove">审批通过</button><button class="btn btn-danger" id="btnReject">拒绝计划</button>`;
}

function openApprovalModal(approved) {
  const modal = $("#approvalModal");
  modal.dataset.approved = approved ? "true" : "false";
  $("#approvalModalTitle").textContent = approved ? "审批通过" : "拒绝修复计划";
  $("#approvalCommentLabel").textContent = approved ? "审批意见（可选）" : "拒绝原因（可选）";
  $("#btnApprovalConfirm").textContent = approved ? "确认通过" : "确认拒绝";
  $("#approvalComment").value = "";
  modal.hidden = false;
  window.setTimeout(() => $("#approvalComment").focus(), 0);
}

function closeApprovalModal() {
  $("#approvalModal").hidden = true;
  $("#approvalModal").dataset.approved = "";
  $("#approvalComment").value = "";
}

async function submitApprovalModal() {
  const modal = $("#approvalModal");
  const approved = modal.dataset.approved === "true";
  const comment = $("#approvalComment").value.trim();
  $("#btnApprovalConfirm").disabled = true;
  try {
    const updated = await api("POST", `/bug-pipelines/${encodeURIComponent(state.activeId)}/approval`, { approved, comment });
    upsertPipeline(updated);
    state.activeStep = approved ? "code_generation" : "fix_plan";
    renderPipelines();
    renderDetail(updated);
    closeApprovalModal();
    startStream();
    startPolling();
    toast(approved ? "Approved, pipeline resumed" : "Rejected");
  } catch (error) {
    toast(error.message);
  } finally {
    $("#btnApprovalConfirm").disabled = false;
  }
}

function startStream() {
  closeStream();
  state.stream = new EventSource(`${API}/bug-pipelines/${encodeURIComponent(state.activeId)}/stream?since=-1`, { withCredentials: true });
  state.stream.onmessage = () => loadOutput();
  state.stream.onerror = () => {
    closeStream();
  };
}

function closeStream() {
  if (state.stream) state.stream.close();
  state.stream = null;
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(refreshActive, 1800);
}

function stopPolling() {
  if (state.pollTimer) window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function refreshAll() {
  await loadPipelines();
  renderPipelines();
  if (state.activeId) await selectPipeline(state.activeId);
}

async function refreshActive() {
  if (!state.activeId) return;
  const data = await api("GET", `/bug-pipelines/${encodeURIComponent(state.activeId)}`);
  upsertPipeline(data);
  if (!state.activeStep || data.steps[state.activeStep]?.status === "pending") {
    state.activeStep = currentStep(data);
  }
  renderPipelines();
  renderDetail(data);
  await loadOutput();
  if (!pipelineIsLive(data)) {
    closeStream();
    stopPolling();
  }
}

async function loadOutput() {
  const item = activePipeline();
  if (!item) return;
  const step = state.activeStep || currentStep(item);
  const stepInfo = item.steps[step] || item.steps[currentStep(item)];
  $("#outputTitle").textContent = stepInfo ? `${stepInfo.title} · ${stepInfo.status}` : "阶段输出";
  try {
    const [artifact, messages] = await Promise.all([
      loadStepArtifact(item, step),
      api("GET", `/sessions/${encodeURIComponent(item.session_id)}/messages`),
    ]);
    const logs = compactMessages(messages.messages || []);
    $("#outputBody").innerHTML = renderStageOutput(item, step, artifact, logs);
  } catch (error) {
    $("#outputBody").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

async function loadStepArtifact(item, step) {
  if (step === "intake") return buildIntakeMarkdown(item);
  const artifactName = STEP_ARTIFACTS[step];
  if (!artifactName) return "";
  const data = await api("GET", `/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/artifacts/${encodeURIComponent(artifactName)}`);
  return data.content || "";
}

function renderStageOutput(item, step, artifact, logs) {
  const stepInfo = item.steps[step] || {};
  const summary = artifact || stepInfo.summary || "";
  const live = RUNNING_STATUSES.has(stepInfo.status);
  const parts = [];

  if (summary.trim()) {
    parts.push(`
      <section class="stage-section">
        <div class="stage-section__title">阶段摘要</div>
        <div class="markdown-body">${renderMarkdown(limitText(summary, 7000))}</div>
      </section>
    `);
  } else {
    parts.push(`<div class="empty">当前阶段还没有可展示的结果摘要。</div>`);
  }

  if (logs.length && (live || !summary.trim())) {
    parts.push(`
      <section class="stage-section">
        <div class="stage-section__title">实时输出</div>
        ${logs.map(renderMessage).join("")}
      </section>
    `);
  }

  return parts.join("");
}

function buildIntakeMarkdown(item) {
  const lines = [
    "## 基本信息",
    `- Pipeline: \`${item.pipeline_id}\``,
    `- 仓库: \`${item.repo_name || item.repo_key}\``,
    `- 目标修复分支: \`${item.target_branch}\``,
    `- 临时 Bugfix 分支: \`${item.bugfix_branch}\``,
    `- 测试环境 namespace: \`${item.namespace}\``,
    `- 审批研发: \`${item.reviewer_id}\``,
    "",
    "## 问题描述",
    item.problem_description || "",
    "",
    "## 涉及接口",
    item.affected_api || "",
    "",
    "## 预期结果",
    item.expected_result || "",
    "",
    "## 实际结果",
    item.actual_result || "",
  ];
  const optional = [
    ["request_id", "Request ID"],
    ["occurred_at", "发生时间"],
    ["affected_data", "影响用户或数据 ID"],
    ["regression_curl", "用例回归 curl"],
    ["screenshot_notes", "截图说明"],
    ["extra_context", "补充信息"],
  ];
  optional.forEach(([key, title]) => {
    if (item[key]) lines.push("", `## ${title}`, item[key]);
  });
  return lines.join("\n").trim();
}

async function loadDiff() {
  const item = activePipeline();
  if (!item) return;
  $("#outputTitle").textContent = "本次变更 Diff";
  try {
    const data = await api("GET", `/sessions/${encodeURIComponent(item.session_id)}/git/diff`);
    if (data.clean) {
      $("#outputBody").innerHTML = `<div class="empty">暂无代码变更。</div>`;
      return;
    }
    $("#outputBody").innerHTML = data.files.map(file => `
      <div class="log">
        <div class="log__type">${escapeHtml(file.change_type)} · ${escapeHtml(file.path)} · +${file.additions} -${file.deletions}</div>
        <pre>${escapeHtml(limitText(file.diff || "", 1600))}</pre>
      </div>
    `).join("");
  } catch (error) {
    $("#outputBody").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

function compactMessages(entries) {
  const mapped = entries
    .map(entry => entry.message || entry)
    .filter(msg => msg.type !== "user" && msg.type !== "system" && msg.type !== "status")
    .map(msg => ({ type: msg.type || "message", text: messageText(msg) }))
    .filter(item => item.text.trim());
  return mapped.slice(-4).map(item => ({ ...item, text: limitText(item.text, 1400) }));
}

function renderMessage(item) {
  return `<div class="log"><div class="log__type">${escapeHtml(item.type)}</div><div class="markdown-body markdown-body--compact">${renderMarkdown(item.text)}</div></div>`;
}

function messageText(msg) {
  if (msg.result) return msg.result;
  if (Array.isArray(msg.content)) {
    return msg.content
      .map(block => block.text || block.thinking || block.name || block.content || "")
      .filter(Boolean)
      .join("\n\n");
  }
  if (msg.message) return msg.message;
  return JSON.stringify(msg, null, 2);
}

function limitText(text, maxLength) {
  const value = String(text || "").trim();
  if (value.length <= maxLength) return value;
  return value.slice(0, maxLength).trimEnd() + "\n\n[输出已精简，完整过程保存在会话历史中]";
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let list = [];
  let listType = "ul";
  let inCode = false;
  let code = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
    paragraph = [];
  };
  const flushList = () => {
    if (!list.length) return;
    html.push(`<${listType}>${list.map(item => `<li>${inlineMarkdown(item)}</li>`).join("")}</${listType}>`);
    list = [];
    listType = "ul";
  };

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      if (inCode) {
        html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
        code = [];
        inCode = false;
      } else {
        flushParagraph();
        flushList();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      code.push(line);
      continue;
    }
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      if (list.length && listType !== "ul") flushList();
      listType = "ul";
      list.push(bullet[1]);
      continue;
    }
    const ordered = trimmed.match(/^\d+\.\s+(.+)$/);
    if (ordered) {
      flushParagraph();
      if (list.length && listType !== "ol") flushList();
      listType = "ol";
      list.push(ordered[1]);
      continue;
    }
    flushList();
    paragraph.push(trimmed);
  }
  if (inCode) html.push(`<pre><code>${escapeHtml(code.join("\n"))}</code></pre>`);
  flushParagraph();
  flushList();
  return html.join("");
}

function inlineMarkdown(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

async function logout() {
  await api("POST", "/logout", {});
  window.location.href = "/login";
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("theme", next);
  applyTheme();
}

function applyTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.dataset.theme = saved;
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { el.style.display = "none"; }, 2600);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

init().catch(error => {
  console.error(error);
  toast(error.message);
});
