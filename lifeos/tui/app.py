import time
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, RichLog, Input, Static, Label
from textual import work
from textual.binding import Binding

from lifeos.cli import display
from lifeos.db import repository
from lifeos.scenarios import nlp_parser
from lifeos.cli.main import _ensure_setup, _run_episode

class LifeOSDashboard(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #left-panel {
        width: 70%;
        height: 100%;
        border-right: solid green;
    }
    
    #right-panel {
        width: 30%;
        height: 100%;
        padding: 1;
    }
    
    RichLog {
        height: 100%;
        width: 100%;
        border: none;
        background: black;
        color: green;
    }
    
    Input {
        dock: bottom;
        margin-top: 2;
        border: solid green;
        background: black;
        color: yellow;
    }
    
    .panel-title {
        text-align: center;
        text-style: bold;
        color: lime;
        margin-bottom: 1;
        border-bottom: solid green;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_log", "Clear Log", show=True)
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Label("SYSTEM LOGS (/var/log/lifeos.log)", classes="panel-title")
                yield RichLog(id="main-log", highlight=True, markup=True)
            
            with Vertical(id="right-panel"):
                yield Label("NLP CHAOS ENGINE", classes="panel-title")
                yield Static("Awaiting natural language input...\nType your situation below and press Enter.", id="status-text")
                yield Input(placeholder="e.g., Exam in an hour, no money...", id="chaos-input")
        
        yield Footer()

    def on_mount(self) -> None:
        _ensure_setup()
        self.main_log = self.query_one("#main-log", RichLog)
        
        # Monkey-patch display.console.print to route all CLI outputs to the TUI RichLog
        self.original_print = display.console.print
        display.console.print = self.main_log.write
        
        # Patch the spinner context manager so it doesn't break the UI
        class DummySpinner:
            def __init__(self, msg):
                self.msg = msg
            def __enter__(self):
                display.console.print(f"[yellow]{self.msg}...[/yellow]")
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
                
        display.Spinner = DummySpinner
        
        # Patch sys.stdout.write and flush for anything that still uses it
        import sys
        class DummyStdout:
            def write(self_dummy, text):
                pass
            def flush(self_dummy):
                pass
        self.original_stdout = sys.stdout
        sys.stdout = DummyStdout()

        self.main_log.write(display.BANNER)
        self.main_log.write("[bold green]System initialized.[/bold green] Ready to generate scenarios.")

    def on_unmount(self) -> None:
        # Restore everything when exiting
        display.console.print = self.original_print
        import sys
        sys.stdout = self.original_stdout

    def action_clear_log(self) -> None:
        self.main_log.clear()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chaos-input":
            user_text = event.value
            if not user_text.strip():
                return
            
            event.input.value = ""
            event.input.disabled = True
            
            self.query_one("#status-text", Static).update("[bold yellow]Generating chaos...[/bold yellow]")
            self.main_log.write(f"\n[bold yellow]> {user_text}[/bold yellow]\n")
            
            # Run the simulation in a worker thread so UI doesn't freeze
            self.run_simulation_worker(user_text)

    @work(thread=True)
    def run_simulation_worker(self, user_text: str) -> None:
        try:
            scenario_data = nlp_parser.generate_scenario_from_text(user_text)
            self.main_log.write("[bold green][OK] JSON parsed successfully. Building scenario...[/bold green]")
            
            repository.create_scenario_from_dict(scenario_data)
            scores = _run_episode("custom_chaos", "heuristic", show_score=False)
            
            payload = repository.get_episode_payload(scores["episode_id"])
            if payload:
                actions = payload.get("actions", [])
                action_types = [a["action_type"] for a in actions[:50]]
                
                self.main_log.write("[bold yellow]Generating Actionable Survival Guide...[/bold yellow]")
                report = nlp_parser.generate_actionable_report(user_text, action_types)
                
                self.main_log.write("\n[bold green][root@lifeos:~#] cat /var/log/survival_guide.txt[/bold green]")
                self.main_log.write(f"[cyan]{report}[/cyan]\n")
            
            display.show_score_card(scores)
            self.call_from_thread(self.simulation_complete)
            
        except Exception as e:
            self.main_log.write(f"[bold red]ERROR: {e}[/bold red]")
            self.call_from_thread(self.simulation_complete, error=True)

    def simulation_complete(self, error: bool = False) -> None:
        inp = self.query_one("#chaos-input", Input)
        inp.disabled = False
        inp.focus()
        
        status = self.query_one("#status-text", Static)
        if error:
            status.update("[bold red]Simulation failed.[/bold red]\nAwaiting new input.")
        else:
            status.update("[bold green]Simulation complete.[/bold green]\nAwaiting new input.")

if __name__ == "__main__":
    app = LifeOSDashboard()
    app.run()
