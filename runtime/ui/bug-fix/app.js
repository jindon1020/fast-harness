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
const SKIPPABLE_STEPS = new Set(["code_review", "unit_test", "regression"]);
const MAX_SCREENSHOTS = 5;
const MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024;
const ALLOWED_SCREENSHOT_TYPES = new Set(["image/png", "image/jpeg", "image/webp", "image/gif"]);

let state = {
  user: null,
  users: [],
  repos: [],
  pipelines: [],
  activeId: "",
  activeStep: "",
  stream: null,
  pollTimer: null,
  repoContexts: [],
  screenshotImages: [],
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
  const chatNav = $("#chatNavLink");
  if (chatNav && data.user.role === "reporter") chatNav.hidden = true;
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
  $("#btnSidebarNewPipeline").addEventListener("click", showCreateView);
  $("#btnAddRepoContext").addEventListener("click", addRepoContext);
  $("#btnSelectScreenshots").addEventListener("click", () => $("#screenshotInput").click());
  $("#screenshotInput").addEventListener("change", event => {
    addScreenshotFiles(Array.from(event.target.files || []));
    event.target.value = "";
  });
  $("#screenshotNotes").addEventListener("paste", handleScreenshotPaste);
  bindScreenshotDropzone();
  $("#btnApprovalClose").addEventListener("click", closeApprovalModal);
  $("#btnApprovalCancel").addEventListener("click", closeApprovalModal);
  $("#btnApprovalConfirm").addEventListener("click", submitApprovalModal);
  $("#btnCommitClose").addEventListener("click", closeCommitModal);
  $("#btnCommitCancel").addEventListener("click", closeCommitModal);
  $("#btnCommitConfirm").addEventListener("click", submitCommitModal);
  $("#btnPipelineSessionClose").addEventListener("click", closePipelineSessionModal);
  $("#btnPipelineSessionCancel").addEventListener("click", closePipelineSessionModal);
  $("#btnPipelineSessionConfirm").addEventListener("click", submitPipelineSessionModal);
  $("#approvalModal").addEventListener("click", (event) => {
    if (event.target.id === "approvalModal") closeApprovalModal();
  });
  $("#commitModal").addEventListener("click", (event) => {
    if (event.target.id === "commitModal") closeCommitModal();
  });
  $("#pipelineSessionModal").addEventListener("click", (event) => {
    if (event.target.id === "pipelineSessionModal") closePipelineSessionModal();
  });
  document.addEventListener("click", event => {
    if (!event.target.closest(".pipeline-list-row")) closePipelineMenus();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !$("#approvalModal").hidden) closeApprovalModal();
    if (event.key === "Escape" && !$("#commitModal").hidden) closeCommitModal();
    if (event.key === "Escape" && !$("#pipelineSessionModal").hidden) closePipelineSessionModal();
    if (event.key === "Escape") closePipelineMenus();
  });
}

function showCreateView() {
  state.activeId = "";
  state.activeStep = "";
  closeStream();
  stopPolling();
  $("#createView").hidden = false;
  $("#pipelineView").hidden = true;
  renderScreenshotPreview();
  renderRepoContexts();
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
  renderRepoContexts();
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
    state.repoContexts = [];
    state.screenshotImages = [];
    renderScreenshotPreview();
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
    screenshot_images: state.screenshotImages.map(image => ({
      name: image.name,
      mime_type: image.mime_type,
      data: image.data,
      size: image.size,
    })),
    extra_context: $("#extraContext").value || null,
    repo_contexts: repoContextsPayload(),
  };
}

function bindScreenshotDropzone() {
  const dropzone = $("#screenshotDropzone");
  dropzone.addEventListener("paste", handleScreenshotPaste);
  dropzone.addEventListener("dragover", event => {
    event.preventDefault();
    dropzone.classList.add("drag-over");
  });
  dropzone.addEventListener("dragleave", event => {
    if (!dropzone.contains(event.relatedTarget)) dropzone.classList.remove("drag-over");
  });
  dropzone.addEventListener("drop", event => {
    event.preventDefault();
    dropzone.classList.remove("drag-over");
    addScreenshotFiles(Array.from(event.dataTransfer?.files || []));
  });
}

function handleScreenshotPaste(event) {
  const files = Array.from(event.clipboardData?.items || [])
    .filter(item => item.kind === "file" && item.type.startsWith("image/"))
    .map(item => item.getAsFile())
    .filter(Boolean);
  if (!files.length) return;
  event.preventDefault();
  addScreenshotFiles(files);
}

async function addScreenshotFiles(files) {
  const imageFiles = files.filter(file => file && file.type.startsWith("image/"));
  if (!imageFiles.length) {
    toast("请选择图片文件");
    return;
  }
  for (const file of imageFiles) {
    if (state.screenshotImages.length >= MAX_SCREENSHOTS) {
      toast(`最多上传 ${MAX_SCREENSHOTS} 张截图`);
      break;
    }
    if (!ALLOWED_SCREENSHOT_TYPES.has(file.type)) {
      toast(`不支持的图片格式：${file.type || file.name}`);
      continue;
    }
    if (file.size > MAX_SCREENSHOT_BYTES) {
      toast(`${file.name} 超过 10MB`);
      continue;
    }
    try {
      state.screenshotImages.push(await readScreenshotFile(file));
    } catch (error) {
      toast(error.message);
    }
  }
  renderScreenshotPreview();
}

function readScreenshotFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = String(reader.result || "");
      const base64 = dataUrl.includes(",") ? dataUrl.split(",", 2)[1] : dataUrl;
      resolve({
        name: file.name || "screenshot",
        mime_type: file.type,
        data: base64,
        size: file.size,
        preview_url: dataUrl,
      });
    };
    reader.onerror = () => reject(new Error(`读取截图失败：${file.name}`));
    reader.readAsDataURL(file);
  });
}

function renderScreenshotPreview() {
  const preview = $("#screenshotPreview");
  if (!preview) return;
  preview.innerHTML = state.screenshotImages.map((image, index) => `
    <article class="screenshot-card">
      <img src="${escapeHtml(image.preview_url)}" alt="${escapeHtml(image.name)}">
      <div class="screenshot-card__meta">
        <span class="screenshot-card__name" title="${escapeHtml(image.name)}">${escapeHtml(image.name)}</span>
        <button class="btn screenshot-card__remove" type="button" data-index="${index}">删除</button>
      </div>
    </article>
  `).join("");
  preview.querySelectorAll(".screenshot-card__remove").forEach(button => {
    button.addEventListener("click", () => {
      state.screenshotImages.splice(Number(button.dataset.index), 1);
      renderScreenshotPreview();
    });
  });
}

function repoContextsPayload() {
  const primary = {
    repo_key: $("#repoKey").value,
    branch: $("#targetBranch").value,
    role: "fix",
    correlation_id_name: $("#primaryCorrelationName").value || "request_id",
    correlation_id_value: $("#requestId").value || null,
  };
  const related = Array.from(document.querySelectorAll(".repo-context-row")).map(row => ({
    repo_key: row.querySelector(".repo-context-repo").value,
    branch: row.querySelector(".repo-context-branch").value || null,
    role: "observe",
    correlation_id_name: row.querySelector(".repo-context-id-name").value || null,
    correlation_id_value: row.querySelector(".repo-context-id-value").value || null,
    note: row.querySelector(".repo-context-note").value || null,
  })).filter(context => context.repo_key);
  return [primary, ...related];
}

function addRepoContext() {
  const available = state.repos.find(repo => repo.key !== $("#repoKey").value) || state.repos[0];
  state.repoContexts.push({
    repo_key: available?.key || "",
    branch: available?.default_branch || "dev",
    correlation_id_name: "task_id",
    correlation_id_value: "",
    note: "",
  });
  renderRepoContexts();
}

function renderRepoContexts() {
  const list = $("#repoContextList");
  if (!list) return;
  if (!state.repoContexts.length) {
    list.innerHTML = `<div class="empty">暂未添加关联仓库。跨服务问题可添加 algo-manager、workflow 等仓库辅助排查。</div>`;
    return;
  }
  list.innerHTML = state.repoContexts.map((context, index) => renderRepoContextRow(context, index)).join("");
  list.querySelectorAll(".repo-context-row").forEach((row, index) => {
    row.querySelector(".repo-context-remove").addEventListener("click", () => {
      state.repoContexts.splice(index, 1);
      renderRepoContexts();
    });
    row.querySelector(".repo-context-repo").addEventListener("change", event => {
      const repo = state.repos.find(item => item.key === event.target.value);
      state.repoContexts[index].repo_key = event.target.value;
      state.repoContexts[index].branch = repo?.default_branch || "dev";
      renderRepoContexts();
    });
    row.querySelector(".repo-context-branch").addEventListener("input", event => {
      state.repoContexts[index].branch = event.target.value;
    });
    row.querySelector(".repo-context-id-name").addEventListener("input", event => {
      state.repoContexts[index].correlation_id_name = event.target.value;
    });
    row.querySelector(".repo-context-id-value").addEventListener("input", event => {
      state.repoContexts[index].correlation_id_value = event.target.value;
    });
    row.querySelector(".repo-context-note").addEventListener("input", event => {
      state.repoContexts[index].note = event.target.value;
    });
  });
}

function renderRepoContextRow(context, index) {
  const repoOptions = state.repos.map(repo => `
    <option value="${escapeHtml(repo.key)}" ${repo.key === context.repo_key ? "selected" : ""}>${escapeHtml(repo.name)}</option>
  `).join("");
  return `
    <section class="repo-context-row">
      <div class="repo-context-row__head">
        <div class="repo-context-row__title">关联仓库 ${index + 1}</div>
        <button class="btn repo-context-row__remove repo-context-remove" type="button">移除</button>
      </div>
      <div class="repo-context-row__grid">
        <label class="field">
          <span>仓库</span>
          <select class="repo-context-repo">${repoOptions}</select>
        </label>
        <label class="field">
          <span>观测分支</span>
          <input class="repo-context-branch" value="${escapeHtml(context.branch || "dev")}" placeholder="dev">
        </label>
        <label class="field">
          <span>ID 类型</span>
          <input class="repo-context-id-name" value="${escapeHtml(context.correlation_id_name || "")}" placeholder="task_id">
        </label>
        <label class="field">
          <span>ID 值</span>
          <input class="repo-context-id-value" value="${escapeHtml(context.correlation_id_value || "")}" placeholder="可选">
        </label>
      </div>
      <label class="field">
        <span>说明</span>
        <input class="repo-context-note" value="${escapeHtml(context.note || "")}" placeholder="例如：下游任务状态、回调链路、异步处理服务">
      </label>
    </section>
  `;
}

function renderPipelines() {
  const list = $("#pipelineList");
  if (!state.pipelines.length) {
    list.innerHTML = `<div class="empty">暂无 pipeline</div>`;
    return;
  }
  list.innerHTML = state.pipelines.map(item => `
    <div class="pipeline-list-row">
      <button class="pipeline-item ${item.pipeline_id === state.activeId ? "active" : ""}" data-id="${escapeHtml(item.pipeline_id)}">
        <div class="pipeline-item__id">${escapeHtml(item.pipeline_id)} · ${escapeHtml(item.status)}</div>
        <div class="pipeline-item__desc">${escapeHtml(pipelineLabel(item))}</div>
      </button>
      <button class="pipeline-menu-button" aria-label="流水线会话操作" aria-expanded="false" onclick="togglePipelineMenu(event, '${escapeHtml(item.pipeline_id)}')">…</button>
      <div class="pipeline-menu" id="pipelineMenu-${escapeHtml(item.pipeline_id)}" hidden>
        <button onclick="openPipelineRenameModal(event, '${escapeHtml(item.pipeline_id)}')">重命名会话</button>
        <button class="pipeline-menu__danger" onclick="openPipelineDeleteModal(event, '${escapeHtml(item.pipeline_id)}')">删除会话</button>
      </div>
    </div>
  `).join("");
  list.querySelectorAll(".pipeline-item").forEach(button => {
    button.addEventListener("click", () => selectPipeline(button.dataset.id));
  });
}

function pipelineLabel(item) {
  return item.display_name || item.problem_description || item.pipeline_id;
}

function closePipelineMenus() {
  document.querySelectorAll(".pipeline-menu").forEach(menu => { menu.hidden = true; });
  document.querySelectorAll(".pipeline-menu-button").forEach(button => button.setAttribute("aria-expanded", "false"));
}

function togglePipelineMenu(event, pipelineId) {
  event.stopPropagation();
  const menu = document.getElementById(`pipelineMenu-${pipelineId}`);
  const willOpen = menu?.hidden;
  closePipelineMenus();
  if (!menu || !willOpen) return;
  menu.hidden = false;
  event.currentTarget.setAttribute("aria-expanded", "true");
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
        <span class="pill">contexts:${(item.repo_contexts || []).length || 1}</span>
        <span class="pill">target:${escapeHtml(item.target_branch)}</span>
        <span class="pill">push:${escapeHtml(item.target_branch)}</span>
        <span class="pill">ns:${escapeHtml(item.namespace)}</span>
      </div>
      <div class="actions">
        ${approvalButtons(item)}
        ${terminateButton(item)}
        <button class="btn" id="btnLoadDiff">查看 Diff</button>
      </div>
      ${codeReviewActions(item)}
      <div class="hint">流水线会自动推进。修复计划阶段会暂停等待审批，最终由研发直接提交并推送目标 feature 分支。</div>
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
  $("#detail").querySelectorAll(".node-skip").forEach(button => {
    button.addEventListener("click", event => {
      event.stopPropagation();
      skipPipelineStep(button.dataset.step);
    });
  });
  $("#btnApprove")?.addEventListener("click", () => openApprovalModal(true));
  $("#btnReject")?.addEventListener("click", () => openApprovalModal(false));
  $("#btnTerminatePipeline")?.addEventListener("click", openTerminateModal);
  $("#btnLoadDiff")?.addEventListener("click", loadDiff);
  $("#btnCodeApprove")?.addEventListener("click", () => openCodeApprovalModal(true));
  $("#btnCodeReject")?.addEventListener("click", () => openCodeApprovalModal(false));
  $("#btnBugCommit")?.addEventListener("click", openCommitModal);
  $("#btnBugPush")?.addEventListener("click", pushBugPipeline);
}

function renderNode(item, step, idx) {
  const info = item.steps[step];
  const active = state.activeStep === step ? "active" : "";
  return `
    <article class="pipeline-node ${active}" data-step="${escapeHtml(step)}" data-status="${escapeHtml(info.status)}">
      <div class="node-head">
        <div class="node-circle">${idx}</div>
        <div class="node-status-badge">${escapeHtml(statusLabel(info.status))}</div>
      </div>
      <div class="node-title">${escapeHtml(info.title)}</div>
      <div class="node-status">${escapeHtml(info.status)} · ${info.attempts || 0}</div>
      ${skipStepButton(item, step)}
    </article>
  `;
}

function skipStepButton(item, step) {
  const info = item.steps[step] || {};
  const canOperate = state.user && (
    state.user.id === item.user_id ||
    state.user.id === item.reviewer_id ||
    state.user.role === "admin"
  );
  if (!canOperate || !SKIPPABLE_STEPS.has(step)) return "";
  if (["passed", "skipped"].includes(info.status)) return "";
  if (item.status === "terminated") return "";
  return `<button class="btn node-skip" type="button" data-step="${escapeHtml(step)}">跳过</button>`;
}

function approvalButtons(item) {
  const waiting = item.steps.fix_plan?.status === "waiting_approval";
  const canApprove = waiting && state.user && (state.user.role === "admin" || state.user.id === item.reviewer_id);
  if (!canApprove) return "";
  return `<button class="btn btn-primary" id="btnApprove">审批通过</button><button class="btn btn-danger" id="btnReject">拒绝计划</button>`;
}

function terminateButton(item) {
  const finished = ["passed", "failed", "terminated"].includes(item.status);
  const canTerminate = !finished && state.user && (
    state.user.id === item.user_id ||
    state.user.id === item.reviewer_id ||
    state.user.role === "admin"
  );
  if (!canTerminate) return "";
  return `<button class="btn btn-danger" id="btnTerminatePipeline">终止流水线</button>`;
}

function statusLabel(status) {
  const labels = {
    pending: "待执行",
    running: "运行中",
    waiting_approval: "待审批",
    passed: "通过",
    failed: "失败",
    skipped: "跳过",
  };
  return labels[status] || status;
}

function codeReviewActions(item) {
  if (!["passed", "skipped"].includes(item.steps.regression?.status)) return "";
  const status = item.code_approval_status || "not_required";
  const canOperate = state.user && (state.user.role === "admin" || state.user.id === item.reviewer_id);
  const statusText = status === "approved" ? "已通过" : status === "rejected" ? "已拒绝" : "待审批";
  const controls = [];
  if (canOperate && status !== "approved") {
    controls.push(`<button class="btn btn-primary" id="btnCodeApprove">代码审批通过</button>`);
    controls.push(`<button class="btn btn-danger" id="btnCodeReject">拒绝代码改动</button>`);
  }
  if (canOperate && status === "approved") {
    controls.push(`<button class="btn btn-primary" id="btnBugCommit">代码提交</button>`);
    controls.push(`<button class="btn" id="btnBugPush">推送远程</button>`);
  }
  return `
    <section class="code-review-panel">
      <div>
        <div class="code-review-panel__label">研发代码改动审批</div>
        <div class="code-review-panel__status">${escapeHtml(statusText)} · push:${escapeHtml(item.target_branch)}</div>
      </div>
      <div class="actions">${controls.join("")}</div>
    </section>
  `;
}

function openApprovalModal(approved) {
  const modal = $("#approvalModal");
  modal.dataset.kind = "plan";
  modal.dataset.approved = approved ? "true" : "false";
  $("#approvalModalTitle").textContent = approved ? "审批通过" : "拒绝修复计划";
  $("#approvalCommentLabel").textContent = approved ? "审批意见（可选）" : "拒绝原因（可选）";
  $("#btnApprovalConfirm").textContent = approved ? "确认通过" : "确认拒绝";
  $("#approvalComment").value = "";
  modal.hidden = false;
  window.setTimeout(() => $("#approvalComment").focus(), 0);
}

function openCodeApprovalModal(approved) {
  const modal = $("#approvalModal");
  modal.dataset.kind = "code";
  modal.dataset.approved = approved ? "true" : "false";
  $("#approvalModalTitle").textContent = approved ? "代码改动审批通过" : "拒绝代码改动";
  $("#approvalCommentLabel").textContent = approved ? "审批意见（可选）" : "拒绝原因（可选）";
  $("#btnApprovalConfirm").textContent = approved ? "确认通过" : "确认拒绝";
  $("#approvalComment").value = "";
  modal.hidden = false;
  window.setTimeout(() => $("#approvalComment").focus(), 0);
}

function openTerminateModal() {
  const modal = $("#approvalModal");
  modal.dataset.kind = "terminate";
  modal.dataset.approved = "false";
  $("#approvalModalTitle").textContent = "终止流水线";
  $("#approvalCommentLabel").textContent = "终止原因";
  $("#btnApprovalConfirm").textContent = "确认终止";
  $("#approvalComment").value = "";
  modal.hidden = false;
  window.setTimeout(() => $("#approvalComment").focus(), 0);
}

function closeApprovalModal() {
  $("#approvalModal").hidden = true;
  $("#approvalModal").dataset.kind = "";
  $("#approvalModal").dataset.approved = "";
  $("#approvalComment").value = "";
}

async function submitApprovalModal() {
  const modal = $("#approvalModal");
  const kind = modal.dataset.kind || "plan";
  const approved = modal.dataset.approved === "true";
  const comment = $("#approvalComment").value.trim();
  $("#btnApprovalConfirm").disabled = true;
  try {
    let updated;
    if (kind === "terminate") {
      updated = await api("POST", `/bug-pipelines/${encodeURIComponent(state.activeId)}/terminate`, { reason: comment });
    } else {
      const path = kind === "code" ? "code-approval" : "approval";
      updated = await api("POST", `/bug-pipelines/${encodeURIComponent(state.activeId)}/${path}`, { approved, comment });
    }
    upsertPipeline(updated);
    state.activeStep = kind === "terminate" ? currentStep(updated) : (kind === "code" ? "regression" : (approved ? "code_generation" : "fix_plan"));
    renderPipelines();
    renderDetail(updated);
    closeApprovalModal();
    if (kind === "plan") {
      startStream();
      startPolling();
    }
    if (kind === "terminate") {
      closeStream();
      stopPolling();
      toast("Pipeline terminated");
    } else {
      toast(approved ? "Approved" : "Rejected");
    }
  } catch (error) {
    toast(error.message);
  } finally {
    $("#btnApprovalConfirm").disabled = false;
  }
}

async function openCommitModal() {
  const item = activePipeline();
  if (!item) return;
  $("#commitModal").hidden = false;
  $("#commitMessage").value = "Generating commit message...";
  $("#btnCommitConfirm").disabled = true;
  try {
    const data = await api("GET", `/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/git/commit-message`);
    $("#commitMessage").value = data.message || `Fix ${item.repo_name} bug`;
  } catch (error) {
    $("#commitMessage").value = `Fix ${item.repo_name} bug`;
    toast(error.message);
  } finally {
    $("#btnCommitConfirm").disabled = false;
    window.setTimeout(() => $("#commitMessage").focus(), 0);
  }
}

function closeCommitModal() {
  $("#commitModal").hidden = true;
  $("#commitMessage").value = "";
}

function openPipelineRenameModal(event, pipelineId) {
  event.stopPropagation();
  closePipelineMenus();
  const item = state.pipelines.find(pipeline => pipeline.pipeline_id === pipelineId);
  if (!item) return;
  const modal = $("#pipelineSessionModal");
  modal.dataset.kind = "rename";
  modal.dataset.pipelineId = pipelineId;
  $("#pipelineSessionModalTitle").textContent = "重命名会话";
  $("#pipelineSessionNameField").hidden = false;
  $("#pipelineSessionName").value = pipelineLabel(item);
  $("#pipelineSessionMessage").textContent = "只修改左侧列表展示名称，不会改动原始 Bug 描述和过程产物。";
  $("#btnPipelineSessionConfirm").textContent = "确认重命名";
  $("#btnPipelineSessionConfirm").classList.remove("btn-danger");
  modal.hidden = false;
  window.setTimeout(() => $("#pipelineSessionName").focus(), 0);
}

function openPipelineDeleteModal(event, pipelineId) {
  event.stopPropagation();
  closePipelineMenus();
  const item = state.pipelines.find(pipeline => pipeline.pipeline_id === pipelineId);
  if (!item) return;
  const modal = $("#pipelineSessionModal");
  modal.dataset.kind = "delete";
  modal.dataset.pipelineId = pipelineId;
  $("#pipelineSessionModalTitle").textContent = "删除会话";
  $("#pipelineSessionNameField").hidden = true;
  $("#pipelineSessionMessage").textContent = `确定删除「${pipelineLabel(item)}」？会删除该流水线记录和会话历史，不会删除工作区代码文件。`;
  $("#btnPipelineSessionConfirm").textContent = "确认删除";
  $("#btnPipelineSessionConfirm").classList.add("btn-danger");
  modal.hidden = false;
}

function closePipelineSessionModal() {
  const modal = $("#pipelineSessionModal");
  modal.hidden = true;
  modal.dataset.kind = "";
  modal.dataset.pipelineId = "";
  $("#pipelineSessionName").value = "";
  $("#pipelineSessionMessage").textContent = "";
  $("#pipelineSessionNameField").hidden = false;
  $("#btnPipelineSessionConfirm").classList.remove("btn-danger");
}

async function submitPipelineSessionModal() {
  const modal = $("#pipelineSessionModal");
  const pipelineId = modal.dataset.pipelineId;
  const kind = modal.dataset.kind;
  if (!pipelineId) return;
  $("#btnPipelineSessionConfirm").disabled = true;
  try {
    if (kind === "rename") {
      const name = $("#pipelineSessionName").value.trim();
      if (!name) {
        toast("请输入会话名称");
        return;
      }
      const updated = await api("PATCH", `/bug-pipelines/${encodeURIComponent(pipelineId)}`, { name });
      upsertPipeline(updated);
      renderPipelines();
      if (state.activeId === pipelineId) renderDetail(updated);
      toast("会话已重命名");
    }
    if (kind === "delete") {
      await api("DELETE", `/bug-pipelines/${encodeURIComponent(pipelineId)}`);
      state.pipelines = state.pipelines.filter(item => item.pipeline_id !== pipelineId);
      if (state.activeId === pipelineId) showCreateView();
      else renderPipelines();
      toast("会话已删除");
    }
    closePipelineSessionModal();
  } catch (error) {
    toast(error.message);
  } finally {
    $("#btnPipelineSessionConfirm").disabled = false;
  }
}

async function submitCommitModal() {
  const item = activePipeline();
  const message = $("#commitMessage").value.trim();
  if (!item || !message) {
    toast("Commit message is required");
    return;
  }
  $("#btnCommitConfirm").disabled = true;
  try {
    const result = await api("POST", `/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/git/commit`, { message });
    closeCommitModal();
    await refreshActive();
    toast(result.status === "clean" ? "No changes to commit" : "Committed");
  } catch (error) {
    toast(error.message);
  } finally {
    $("#btnCommitConfirm").disabled = false;
  }
}

async function pushBugPipeline() {
  const item = activePipeline();
  if (!item) return;
  const button = $("#btnBugPush");
  button.disabled = true;
  try {
    const result = await api("POST", `/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/git/push`);
    await refreshActive();
    toast(result.status === "pushed" ? "Pushed" : result.status);
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
  }
}

async function skipPipelineStep(step) {
  const item = activePipeline();
  if (!item) return;
  try {
    const updated = await api("POST", `/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/steps/${encodeURIComponent(step)}/skip`, { note: "人工跳过" });
    upsertPipeline(updated);
    state.activeStep = step;
    renderPipelines();
    renderDetail(updated);
    await loadOutput();
    if (pipelineIsLive(updated)) {
      startStream();
      startPolling();
    } else {
      closeStream();
      stopPolling();
    }
    toast("Step skipped");
  } catch (error) {
    toast(error.message);
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
        ${step === "intake" ? renderPersistedScreenshots(item) : ""}
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
  const contexts = item.repo_contexts || [];
  const lines = [
    "## 基本信息",
    `- Pipeline: \`${item.pipeline_id}\``,
    `- 主修复仓库: \`${item.repo_name || item.repo_key}\``,
    `- 目标修复分支: \`${item.target_branch}\``,
    `- 推送分支: \`${item.target_branch}\``,
    `- 测试环境 namespace: \`${item.namespace}\``,
    `- 审批研发: \`${item.reviewer_id}\``,
  ];
  if (contexts.length) {
    lines.push("", "## 仓库排查上下文");
    contexts.forEach(context => {
      const idName = context.correlation_id_name || "关联 ID";
      const idValue = context.correlation_id_value || "未提供";
      lines.push(`- \`${context.repo_name}\` (${context.role}): branch \`${context.branch}\`, ${idName} \`${idValue}\``);
      if (context.note) lines.push(`  - 说明: ${context.note}`);
    });
  }
  lines.push(
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
  );
  const optional = [
    ["request_id", "Request ID"],
    ["occurred_at", "发生时间范围"],
    ["affected_data", "当前登录用户ID"],
    ["regression_curl", "用例回归 curl"],
    ["screenshot_notes", "截图说明"],
    ["extra_context", "补充信息"],
  ];
  optional.forEach(([key, title]) => {
    if (item[key]) lines.push("", `## ${title}`, item[key]);
  });
  if (item.screenshot_attachments?.length) {
    lines.push("", "## 问题截图");
    item.screenshot_attachments.forEach(attachment => {
      lines.push(`- ${attachment.name || "screenshot"}: \`${attachment.path}\``);
    });
  }
  return lines.join("\n").trim();
}

function renderPersistedScreenshots(item) {
  const attachments = item.screenshot_attachments || [];
  if (!attachments.length) return "";
  return `
    <div class="stage-screenshot-gallery">
      ${attachments.map(attachment => {
        const filename = attachment.path ? attachment.path.split("/").pop() : "";
        const url = `${API}/bug-pipelines/${encodeURIComponent(item.pipeline_id)}/screenshots/${encodeURIComponent(filename)}`;
        const name = attachment.name || filename || "screenshot";
        return `
          <a class="stage-screenshot" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">
            <img src="${escapeHtml(url)}" alt="${escapeHtml(name)}">
            <div class="stage-screenshot__name">${escapeHtml(name)}</div>
          </a>
        `;
      }).join("")}
    </div>
  `;
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
