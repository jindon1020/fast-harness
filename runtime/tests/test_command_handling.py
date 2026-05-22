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

    def test_ui_supports_registered_repo_selection(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('api("GET", "/repositories")', html)
        self.assertIn("/repositories/\" + repoKey + \"/branches", html)
        self.assertIn("function renderWorkspaceRepoChoices", html)
        self.assertIn("function showAddRepoDialog", html)
        self.assertIn("repo_keys", html)

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
        self.assertIn("workspace-action--delete", html)
        self.assertIn("sidebar-action", html)

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


if __name__ == "__main__":
    unittest.main()
