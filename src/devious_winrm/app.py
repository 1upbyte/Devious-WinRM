"""Main file for the Devious-WinRM."""
from __future__ import annotations

import contextlib
import datetime
import shutil
import sys
import threading
import time

import psrp
from prompt_toolkit import HTML, PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.shortcuts import CompleteStyle
from psrp import WSManInfo
from psrpcore.types import PSInvocationState
from pygments.lexers.shell import PowerShellLexer

from devious_winrm.util.commands import commands, run_command
from devious_winrm.util.completers import RemotePathAutoCompleter
from devious_winrm.util.get_command_output import get_command_output
from devious_winrm.util.keybinds import kb
from devious_winrm.util.printers import print_error, print_ft, print_info


class Terminal:
    """Terminal for handling connection and command execution."""

    def __init__(self, conn: WSManInfo) -> None:
        """Initialize the terminal with connection and runspace pool."""
        self.conn = conn
        self.rp = None
        self.ps = None
        self.username = None
        self.session = PromptSession(
            lexer=PygmentsLexer(PowerShellLexer),
            bottom_toolbar=self.bottom_toolbar,
            refresh_interval=1,
            key_bindings=kb,
            complete_while_typing=False,
            complete_style=CompleteStyle.READLINE_LIKE,
        )

    def run(self, rp: psrp.SyncRunspacePool) -> None:
        """Run the terminal session."""
        self.rp = rp
        self.session.completer=RemotePathAutoCompleter(rp=self.rp)
        self.username = get_command_output(self.rp, "whoami")[0].strip()
        threading.Thread(target=self.keepalive, daemon=True).start()
        while True:
            try:
                user_input = self.prompt().strip()
                self.process_input(user_input)
            except (SystemExit, EOFError):
                print_info("Exiting the application...")
                sys.exit(0)
            except KeyboardInterrupt:
                if self.ps.state == PSInvocationState.Running:
                    print_info("Aborting command.")
                    self.ps.stop()
            except Exception:
                raise

    def bottom_toolbar(self) -> HTML:
        """Generate the bottom toolbar for the terminal."""
        columns, _ = shutil.get_terminal_size()
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # noqa: DTZ005
        preamble = "😈 Devious-WinRM"
        user = f"User: {self.username}"
        text = f"{preamble} | {user}(PADDING){time_str}"
        padding = columns - len(text) + len("(PADDING)") - len("> ")
        # All this is done so the padding changes based on the terminal size
        # and the clock is always aligned to the right.
        final_text = text.replace("(PADDING)", " " * padding)

        return HTML(f"<style fg='ansiblue' bg='ansiwhite'>{final_text}</style>")


    def process_input(self, user_input: str) -> None:
        """Execute a command or run a registered action."""
        if user_input in commands:
            run_command(self, user_input)
            return

        def _process_input_logic() -> None:
            """Logic to process user input and execute commands."""
            self.ps = psrp.SyncPowerShell(self.rp)
            self.ps.add_script(user_input)
            self.ps.add_command("Out-String").add_parameter("Stream", value=True)

            output = psrp.SyncPSDataCollection()
            output.data_added = print_ft
            self.ps.streams.error.data_added = print_error
            with contextlib.suppress(psrp.PipelineStopped):
                    self.ps.invoke(output_stream=output)
        thread = threading.Thread(target=_process_input_logic, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.5)

    def prompt(self) -> str:
        """Prompt the user for input.

        Returns the user input as a string.
        """
        self.ps = psrp.SyncPowerShell(self.rp)
        cwd: str = get_command_output(self.rp, "pwd")[0].strip()
        prefix = f"{cwd}> "
        return self.session.prompt(HTML(f"{prefix}"))

    def keepalive(self) -> None:
        """Keep the connection alive by sending a repeat no-op command."""
        while True:
            ps = psrp.SyncPowerShell(self.rp)
            ps.add_script("").invoke()
            time.sleep(60)
