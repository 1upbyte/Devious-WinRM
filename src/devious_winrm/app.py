"""Main file for the Devious-WinRM."""
from __future__ import annotations

import contextlib
import datetime
import random
import re
import shutil
import sys
import threading
import time

import psrp
from prompt_toolkit import ANSI, HTML, PromptSession, print_formatted_text
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from psrp import WSManInfo
from psrpcore.types import ErrorRecord, PSInvocationState, PSString
from pygments.lexers.shell import PowerShellLexer
from pygments.styles import get_style_by_name

from devious_winrm.util.commands import commands, run_command
from devious_winrm.util.get_command_output import get_command_output

ANSI_RED = "\033[31m"
ANSI_BLUE = "\033[34m"
ANSI_RESET = "\033[0m"


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
            style=style_from_pygments_cls(get_style_by_name("monokai")),
            bottom_toolbar=self.bottom_toolbar,
            refresh_interval=1,
        )

    def run(self, rp: psrp.SyncRunspacePool) -> None:
        """Run the terminal session."""
        self.rp = rp
        self.username = get_command_output(self.rp, "whoami")
        threading.Thread(target=self.keepalive, daemon=True).start()
        while True:
            try:
                user_input = self.prompt().strip()
                self.process_input(user_input)
            except (SystemExit, EOFError):
                self.print_info("Exiting the application...")
                sys.exit(0)
            except KeyboardInterrupt:
                if self.ps.state == PSInvocationState.Running:
                    self.print_info("Aborting command.")
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
            output.data_added = self.print_ft
            self.ps.streams.error.data_added = self.print_error
            with contextlib.suppress(psrp.PipelineStopped):
                    self.ps.invoke(output_stream=output)
        thread = threading.Thread(target=_process_input_logic, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.5)

    def print_ft(self, message: str | PSString) -> None:
        """Print formatted text to the terminal."""
        print_formatted_text(ANSI(message))

    def print_error(self, message: ErrorRecord) -> None:
        """Print an error message to the terminal."""
        message = str(message)
        # Check if the message already contains ANSI color codes
        if not re.search(r"\x1b\[[0-9;]*m", message):
            message = f"{ANSI_RED}{message}{ANSI_RESET}"
        self.print_ft(message)

    def print_info(self, message: str) -> None:
        """Print an informational message to the terminal."""
        self.print_ft(f"{ANSI_BLUE}[+] {message}{ANSI_RESET}")

    def prompt(self) -> str:
        """Prompt the user for input.

        Returns the user input as a string.
        """
        self.ps = psrp.SyncPowerShell(self.rp)
        cwd: str = get_command_output(self.rp, "pwd")
        prefix = f"{cwd}> "
        return self.session.prompt(HTML(f"{prefix}"))

    def keepalive(self) -> None:
        """Keep the connection alive by sending a repeat no-op command."""
        while True:
            ps = psrp.SyncPowerShell(self.rp)
            ps.add_script("").invoke()
            time.sleep(60)
