"""
Feature Flag & Remote Config Engine — Terminal Dashboard (TUI)

Run with:
    python app.py

By default it talks to the backend at http://localhost:8000.
Point it at a different server with an environment variable:
    FF_API_URL=http://192.168.1.50:8000 python app.py

Controls:
    Tab    - switch between the Flags view and the Configs view
    Space  - toggle the selected feature flag ON/OFF
    Enter  - edit the selected flag's rule (or config's value)
    Q      - quit
"""

import asyncio
import json
import os

import httpx
import websockets
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

API_URL = os.environ.get("FF_API_URL", "http://localhost:8000")
WS_URL = API_URL.replace("http", "ws", 1) + "/ws"


def describe_rollout(rollout: dict) -> str:
    """Human readable summary of a rollout rule, shown in the table."""
    if rollout["type"] == "everyone":
        return "Everyone"
    if rollout["type"] == "beta_only":
        return f"Beta Users Only ({len(rollout['beta_user_ids'])})"
    if rollout["type"] == "percentage":
        return f"{rollout['percentage']}% Rollout"
    return rollout["type"]


# ---------------------------------------------------------------------------
# Modal: edit a feature flag's targeting rule
# ---------------------------------------------------------------------------
class RolloutEditScreen(ModalScreen):
    CSS = """
    RolloutEditScreen { align: center middle; }
    #dialog {
        width: 60;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #dialog Label { margin-top: 1; }
    #buttons { margin-top: 1; align: right middle; }
    """

    def __init__(self, flag: dict):
        super().__init__()
        self.flag = flag

    def compose(self) -> ComposeResult:
        rollout = self.flag["rollout"]
        with Vertical(id="dialog"):
            yield Label(f"Editing rule for: [b]{self.flag['name']}[/b]")
            yield Label("Type — one of: everyone / beta_only / percentage")
            yield Input(value=rollout["type"], id="type_input")
            yield Label("Percentage (used when type = percentage), 0-100")
            yield Input(value=str(rollout["percentage"]), id="percentage_input")
            yield Label("Beta user IDs (used when type = beta_only), comma separated")
            yield Input(value=",".join(rollout["beta_user_ids"]), id="beta_input")
            with Vertical(id="buttons"):
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        rule_type = self.query_one("#type_input", Input).value.strip()
        if rule_type not in ("everyone", "beta_only", "percentage"):
            rule_type = "everyone"

        try:
            percentage = int(self.query_one("#percentage_input", Input).value.strip())
        except ValueError:
            percentage = 100
        percentage = max(0, min(100, percentage))

        beta_text = self.query_one("#beta_input", Input).value.strip()
        beta_ids = [b.strip() for b in beta_text.split(",") if b.strip()]

        self.dismiss({"type": rule_type, "percentage": percentage, "beta_user_ids": beta_ids})


# ---------------------------------------------------------------------------
# Modal: edit a remote config value
# ---------------------------------------------------------------------------
class ConfigEditScreen(ModalScreen):
    CSS = """
    ConfigEditScreen { align: center middle; }
    #dialog {
        width: 50;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #buttons { margin-top: 1; align: right middle; }
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Editing: [b]{self.config['key']}[/b] ({self.config['value_type']})")
            yield Input(value=str(self.config["value"]), id="value_input")
            with Vertical(id="buttons"):
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        raw = self.query_one("#value_input", Input).value.strip()
        if self.config["value_type"] == "number":
            try:
                value = float(raw)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                value = self.config["value"]
        else:
            value = raw

        self.dismiss(value)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class FeatureFlagTUI(App):
    TITLE = "Feature Flag & Config Manager"

    CSS = """
    #status {
        dock: bottom;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_flag", "Toggle Flag"),
        Binding("enter", "edit_selected", "Edit Rule / Value"),
        Binding("tab", "switch_tab", "Switch View"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.flags: list[dict] = []
        self.configs: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="flags-tab"):
            with TabPane("Flags", id="flags-tab"):
                yield DataTable(id="flags-table", zebra_stripes=True)
            with TabPane("Configs", id="configs-tab"):
                yield DataTable(id="configs-table", zebra_stripes=True)
        yield Static("Connecting...", id="status")
        yield Footer()

    async def on_mount(self) -> None:
        flags_table = self.query_one("#flags-table", DataTable)
        flags_table.add_columns("Flag", "Status", "Rule")
        flags_table.cursor_type = "row"

        configs_table = self.query_one("#configs-table", DataTable)
        configs_table.add_columns("Key", "Type", "Value")
        configs_table.cursor_type = "row"

        await self.refresh_state()
        # Run the websocket listener in the background so the UI updates
        # live whenever ANYONE changes a flag (even from another tool).
        self.run_worker(self.listen_for_updates(), exclusive=True)

    # -- data loading ------------------------------------------------------
    async def refresh_state(self) -> None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/api/state", timeout=5)
                response.raise_for_status()
                self.apply_state(response.json())
        except Exception as exc:  # noqa: BLE001 - show any error in the status bar
            self.query_one("#status", Static).update(f"Could not reach {API_URL}: {exc}")

    def apply_state(self, state: dict) -> None:
        self.flags = state["flags"]
        self.configs = state["configs"]
        self.render_flags()
        self.render_configs()
        self.query_one("#status", Static).update(
            f"Connected to {API_URL} | {len(self.flags)} flags, {len(self.configs)} configs"
        )

    def render_flags(self) -> None:
        table = self.query_one("#flags-table", DataTable)
        table.clear()
        for flag in self.flags:
            status = "ON " if flag["enabled"] else "OFF"
            table.add_row(flag["name"], status, describe_rollout(flag["rollout"]), key=flag["name"])

    def render_configs(self) -> None:
        table = self.query_one("#configs-table", DataTable)
        table.clear()
        for config in self.configs:
            table.add_row(config["key"], config["value_type"], str(config["value"]), key=config["key"])

    # -- live updates --------------------------------------------------------
    async def listen_for_updates(self) -> None:
        while True:
            try:
                async with websockets.connect(WS_URL) as ws:
                    self.query_one("#status", Static).update(f"Live | connected to {API_URL}")
                    async for message in ws:
                        self.apply_state(json.loads(message))
            except Exception:
                self.query_one("#status", Static).update(f"Reconnecting to {API_URL}...")
                await asyncio.sleep(2)

    # -- key bindings ---------------------------------------------------------
    def action_switch_tab(self) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = "configs-tab" if tabs.active == "flags-tab" else "flags-tab"

    async def action_toggle_flag(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active != "flags-tab":
            return

        table = self.query_one("#flags-table", DataTable)
        if table.cursor_row is None or not self.flags:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        async with httpx.AsyncClient() as client:
            await client.patch(f"{API_URL}/api/flags/{row_key}/toggle", timeout=5)
        # No need to manually refresh — the server broadcasts the new
        # state over the websocket and listen_for_updates() picks it up.

    async def action_edit_selected(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active == "flags-tab":
            await self._edit_flag_rule()
        else:
            await self._edit_config_value()

    async def _edit_flag_rule(self) -> None:
        table = self.query_one("#flags-table", DataTable)
        if table.cursor_row is None or not self.flags:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        flag = next((f for f in self.flags if f["name"] == row_key), None)
        if flag is None:
            return

        def handle_result(result: dict | None) -> None:
            if result is not None:
                self.run_worker(self._save_rollout(flag["name"], result))

        await self.push_screen(RolloutEditScreen(flag), handle_result)

    async def _edit_config_value(self) -> None:
        table = self.query_one("#configs-table", DataTable)
        if table.cursor_row is None or not self.configs:
            return

        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        config = next((c for c in self.configs if c["key"] == row_key), None)
        if config is None:
            return

        def handle_result(result) -> None:
            if result is not None:
                self.run_worker(self._save_config(config, result))

        await self.push_screen(ConfigEditScreen(config), handle_result)

    # -- API writes ------------------------------------------------------------
    async def _save_rollout(self, flag_name: str, rollout: dict) -> None:
        async with httpx.AsyncClient() as client:
            await client.put(f"{API_URL}/api/flags/{flag_name}/rollout", json=rollout, timeout=5)

    async def _save_config(self, config: dict, value) -> None:
        payload = {"key": config["key"], "value": value, "value_type": config["value_type"]}
        async with httpx.AsyncClient() as client:
            await client.put(f"{API_URL}/api/configs/{config['key']}", json=payload, timeout=5)


if __name__ == "__main__":
    FeatureFlagTUI().run()
