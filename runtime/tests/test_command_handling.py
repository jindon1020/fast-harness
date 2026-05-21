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

    def test_ui_contains_slash_command_suggestion_contract(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn('id="commandMenu"', html)
        self.assertIn("function renderCommandSuggestions", html)
        self.assertIn("function applyCommandSuggestion", html)
        self.assertIn('promptInput.addEventListener("input", updateCommandSuggestions)', html)

    def test_ui_nests_sessions_under_workspaces_and_uses_dialog_branch_select(self):
        html = Path(__file__).resolve().parents[1].joinpath("ui", "index.html").read_text()

        self.assertIn("function showSessionDialog", html)
        self.assertIn("function deleteWorkspace", html)
        self.assertIn("sessionsForWorkspace", html)
        self.assertIn("/default-repo/branches", html)
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


if __name__ == "__main__":
    unittest.main()
