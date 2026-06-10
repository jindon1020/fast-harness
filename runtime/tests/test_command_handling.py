from pathlib import Path
import unittest

from src.harness.loader import load_harness_config
from src.harness.commands import normalize_command_prompt


class CommandHandlingTest(unittest.TestCase):
    def test_capabilities_use_user_facing_command_names(self):
        config = load_harness_config()
        commands = {command["name"]: command for command in config.commands}

        self.assertIn("implement", commands)
        self.assertEqual(commands["implement"]["invoke"], "implement-command")
        self.assertNotIn("implement-command", commands)

    def test_normalize_command_prompt_rewrites_display_name_to_sdk_command(self):
        self.assertEqual(
            normalize_command_prompt("/implement 实现积分转赠功能"),
            "/implement-command 实现积分转赠功能",
        )
        self.assertEqual(
            normalize_command_prompt("/wiki-update force"),
            "/wiki-update-command force",
        )
        self.assertEqual(
            normalize_command_prompt("/implement-command raw"),
            "/implement-command raw",
        )
        self.assertEqual(normalize_command_prompt("普通需求描述"), "普通需求描述")
        self.assertEqual(normalize_command_prompt("/unknown something"), "/unknown something")

    def test_monitor_agent_uses_kube_observability_mcp(self):
        config = load_harness_config()
        monitor = config.agents["monitor-agent"]

        self.assertEqual(monitor.mcpServers, ["kube-observability"])
        self.assertIn("mcp__kube-observability__diagnose_service", monitor.tools)
        self.assertIn("kube-observability", monitor.prompt)
        self.assertNotIn("可用 Skill", monitor.prompt)
        self.assertNotIn("KUBECONFIG", monitor.prompt)
        self.assertNotIn("kubectl get pods", monitor.prompt)

    def test_ui_contains_slash_command_suggestion_contract(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="commandMenu"', html)
        self.assertIn("function renderCommandSuggestions", html)
        self.assertIn("function applyCommandSuggestion", html)
        self.assertIn('promptInput.addEventListener("input", updateCommandSuggestions)', html)

    def test_ui_uses_fast_harness_brand_logo(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("brand-mark", html)
        self.assertIn(">FH</span>", html)
        self.assertIn(">fast-harness</span>", html)
        self.assertNotIn("sidebar__logo-dot", html)

    def test_bug_fix_page_uses_split_frontend_assets(self):
        ui_dir = Path(__file__).resolve().parents[1].joinpath("ui")
        page = ui_dir.joinpath("bug-fix", "index.html").read_text()
        styles = ui_dir.joinpath("bug-fix", "styles.css")
        app = ui_dir.joinpath("bug-fix", "app.js")

        self.assertTrue(styles.exists())
        self.assertTrue(app.exists())
        self.assertIn('<link rel="stylesheet" href="/bug-fix/styles.css">', page)
        self.assertIn('<script src="/bug-fix/app.js" defer></script>', page)
        self.assertNotIn("<style>", page)
        self.assertNotIn("<script>", page)

    def test_bug_fix_page_separates_create_and_pipeline_views(self):
        ui_dir = Path(__file__).resolve().parents[1].joinpath("ui")
        page = ui_dir.joinpath("bug-fix", "index.html").read_text()
        styles = ui_dir.joinpath("bug-fix", "styles.css").read_text()
        app = ui_dir.joinpath("bug-fix", "app.js").read_text()

        self.assertIn('id="createView"', page)
        self.assertIn('id="pipelineView"', page)
        self.assertIn('id="outputBody"', page)
        self.assertNotIn('<aside class="output"', page)
        self.assertIn("function showCreateView", app)
        self.assertIn("function showPipelineView", app)
        self.assertIn("pipeline-track", styles)
        self.assertIn("node-circle", styles)
        self.assertIn("@keyframes spin", styles)
        self.assertIn('id="approvalModal"', page)
        self.assertIn("function openApprovalModal", app)
        self.assertNotIn("window.prompt", app)

    def test_bug_fix_stage_output_uses_artifact_summary_and_markdown(self):
        ui_dir = Path(__file__).resolve().parents[1].joinpath("ui")
        styles = ui_dir.joinpath("bug-fix", "styles.css").read_text()
        app = ui_dir.joinpath("bug-fix", "app.js").read_text()

        self.assertIn("const STEP_ARTIFACTS", app)
        self.assertIn('root_cause: "diagnosis.md"', app)
        self.assertIn('fix_plan: "fix_plan.md"', app)
        self.assertIn("function buildIntakeMarkdown", app)
        self.assertIn("function renderMarkdown", app)
        self.assertIn("function renderStageOutput", app)
        self.assertIn("阶段摘要", app)
        self.assertIn("实时输出", app)
        self.assertIn("markdown-body", styles)
        self.assertIn(".stage-section__title", styles)

    def test_chat_sidebar_shows_developer_bug_pipeline_approvals(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="approvalSection"', html)
        self.assertIn('id="approvalList"', html)
        self.assertIn("function loadPendingApprovals", html)
        self.assertIn('api("GET", "/bug-pipelines")', html)
        self.assertIn("/artifacts/fix_plan.md", html)
        self.assertIn("/approval", html)
        self.assertIn("/bug-fix?pipeline=", html)

    def test_ui_nests_sessions_under_workspaces_and_uses_dialog_branch_select(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function showSessionDialog", html)
        self.assertIn("function deleteWorkspace", html)
        self.assertIn("sessionsForWorkspace", html)
        self.assertIn("/repositories/", html)
        self.assertNotIn("workspaceBranchPicker", html)
        self.assertNotIn('$("#btnNewSess")', html)

    def test_ui_shows_loading_while_creating_workspace_and_session(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="btnConfirmWorkspace"', html)
        self.assertIn('id="btnConfirmSession"', html)
        self.assertIn("function setDialogSubmitting", html)
        self.assertIn('setDialogSubmitting("btnConfirmWorkspace", true, "Creating")', html)
        self.assertIn('setDialogSubmitting("btnConfirmSession", true, "Creating")', html)
        self.assertIn("loading-dots--inline", html)

    def test_ui_loads_session_history_when_selecting_session(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('api("GET", "/sessions/" + id + "/messages")', html)
        self.assertIn("function loadSessionMessages", html)
        self.assertIn("function renderHistoryMessage", html)
        self.assertIn("function renderUserPrompt", html)

    def test_ui_renders_markdown_blocks_and_tables(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function renderMarkdown(md)", html)
        self.assertIn("function renderMarkdownTable(tableLines)", html)
        self.assertIn("function isMarkdownTableStart(lines, index)", html)
        self.assertIn(".msg__text table", html)
        self.assertIn(".msg__text h2", html)
        self.assertIn(".msg__text blockquote", html)

    def test_ui_uses_same_origin_api_base(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('const API = "/api";', html)
        self.assertNotIn('const API = "http://localhost:8002/api";', html)

    def test_ui_defaults_to_light_theme_and_persists_choice(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('<html lang="en" data-theme="light">', html)
        self.assertIn('function initTheme()', html)
        self.assertIn('localStorage.setItem("theme", next)', html)
        self.assertIn('savedTheme || "light"', html)

    def test_ui_supports_registered_repo_selection(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('api("GET", "/repositories")', html)
        self.assertIn("/repositories/\" + repoKey + \"/branches", html)
        self.assertIn("function renderWorkspaceRepoChoices", html)
        self.assertIn("function showAddRepoDialog", html)
        self.assertIn("{ name, repo_keys: repoKeys }", html)
        self.assertNotIn("workspace-repo-choice__branch", html)

    def test_ui_removes_top_create_buttons(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertNotIn('id="btnNewWorkspace"', html)
        self.assertNotIn('id="btnNewSession"', html)
        self.assertNotIn('$("#btnNewWorkspace")', html)
        self.assertNotIn('$("#btnNewSession")', html)
        self.assertIn('id="btnAddWs"', html)

    def test_ui_supports_sidebar_resize_and_distinct_workspace_actions(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="sidebarResizeHandle"', html)
        self.assertIn("function initSidebarResize", html)
        self.assertIn("--sidebar-width", html)
        self.assertIn("localStorage.setItem(\"sidebarWidth\"", html)
        self.assertIn("workspace-action--session", html)
        self.assertIn("workspace-action--repo", html)

    def test_ui_supports_ai_message_feedback(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function addFeedbackButton", html)
        self.assertIn("function showFeedbackDialog", html)
        self.assertIn("/feedback", html)
        self.assertIn(".feedback-btn", html)
        self.assertIn("workspace-action--delete", html)
        self.assertIn("sidebar-action", html)

    def test_ui_supports_usage_stats_panel(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="btnUsage"', html)
        self.assertNotIn('data-tab="usage"', html)
        self.assertIn('panelTabs.style.display = state.panelTab === "usage" ? "none" : "flex"', html)
        self.assertIn("function loadUsageStats", html)
        self.assertIn('api("GET", "/usage-stats")', html)
        self.assertIn(".usage-summary", html)

    def test_ui_supports_workspace_and_session_rename(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function renameWorkspace", html)
        self.assertIn("function renameSession", html)
        self.assertIn("workspace-action--rename", html)
        self.assertIn("session-item__rename", html)
        self.assertIn("function showRenameDialog", html)
        self.assertIn('overlay.id = "renameDialogOverlay"', html)
        self.assertIn('id="renameNameInput"', html)
        self.assertNotIn("prompt(\"Rename", html)
        self.assertIn(">edit</button>", html)
        self.assertNotIn(">✎</button>", html)
        self.assertIn('api("PATCH", "/workspaces/" + id', html)
        self.assertIn('api("PATCH", "/sessions/" + id', html)

    def test_ui_uses_login_page_and_current_user(self):
        login_html = Path(__file__).resolve().parents[1].joinpath("ui", "login.html").read_text()
        app_html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="loginForm"', login_html)
        self.assertIn('api("POST", "/api/login"', login_html)
        self.assertIn('api("GET", "/api/users")', login_html)
        self.assertIn('credentials: "same-origin"', login_html)
        self.assertIn('api("GET", "/me")', app_html)
        self.assertIn('credentials: "same-origin"', app_html)
        self.assertIn('localStorage.removeItem("currentUserId")', app_html)
        self.assertIn('window.location.href = "/login"', app_html)
        self.assertIn('id="currentUserLabel"', app_html)
        self.assertIn("currentUserLabel.textContent", app_html)
        self.assertIn('id="btnLogout"', app_html)
        self.assertIn("function logout", app_html)
        self.assertIn('api("POST", "/logout")', app_html)
        self.assertNotIn('id="userSelect"', app_html)
        self.assertNotIn("switchUser", app_html)

    def test_ui_uses_custom_dialogs_instead_of_browser_dialogs(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function showAlertDialog", html)
        self.assertIn("function showConfirmDialog", html)
        self.assertIn("dialog__message", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("confirm(", html)
        self.assertNotIn("prompt(", html)

    def test_ui_reconnects_running_session_streams(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function reconnectSessionStream", html)
        self.assertIn("/stream?since=", html)
        self.assertIn("query/cancel", html)
        self.assertIn("function consumeSseResponse", html)

    def test_ui_has_fixed_git_commit_and_push_actions(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="btnGitCommit"', html)
        self.assertIn('id="btnGitPush"', html)
        self.assertIn("function commitActiveSession", html)
        self.assertIn("function pushActiveSession", html)
        self.assertIn("function loadSuggestedCommitMessage", html)
        self.assertIn("/git/commit-message", html)
        self.assertIn("/git/commit", html)
        self.assertIn("/git/push", html)


if __name__ == "__main__":
    unittest.main()
