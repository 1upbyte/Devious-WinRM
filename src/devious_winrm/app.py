"""Main file for the Devious-WinRM."""
from __future__ import annotations

import datetime
import shutil
import sys
import time
from threading import Thread
from xml.etree.ElementTree import ParseError

import psrp
from prompt_toolkit import HTML, PromptSession
from psrp import WSManInfo
from psrpcore.types import PSInvocationState

from devious_winrm.util.commands import commands, run_command
from devious_winrm.util.get_command_output import get_command_output
from devious_winrm.util.printers import print_error, print_ft, print_info


class Terminal:
    """Terminal for handling connection and command execution."""

    def __init__(
        self,
        conn: WSManInfo,
        rp: psrp.SyncRunspacePool,
        session: PromptSession,
    ) -> None:
        """Initialize the terminal with connection, runspace pool, and prompt session.

        Args:
            conn (WSManInfo): The connection information.
            rp (SyncRunspacePool): The Synchronous Runspace Pool.
            session (PromptSession): The prompt session to use for user input.

        """
        self.conn = conn
        self.rp = rp
        self.ps = None
        self.username = get_command_output(self.rp, "whoami")[0].strip()
        self.pause_keepalive = False
        """
            If True, prevents the keep-alive mechanism from sending commands.
            Having the keep-alive be sent while another command is executing
            can lead to issues.
        """
        self.session = session
        self.session.bottom_toolbar = self.bottom_toolbar

    def run(self) -> None:
        """Run the terminal session."""
        Thread(target=self.keepalive, name="keep-alive", daemon=True).start()
        while True:
            try:
                self.pause_keepalive = False
                user_input = self.prompt().strip()
                self.pause_keepalive = True
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
        """Execute a command or run a registered action.

        Args:
            user_input (str): The input to parse.

        """
        cmd = ""
        if user_input:
            cmd = user_input.split()[0]

        if cmd == "exit":
            # Exit is special as it needs to be called outside of the
            # thread for it to work properly
            sys.exit()

        def _process_input_logic() -> None:
            if cmd in commands:
                run_command(self, user_input)
                return

            """Logic to process user input and execute commands."""
            self.ps = psrp.SyncPowerShell(self.rp)
            self.ps.add_script(user_input)
            self.ps.add_command("Out-String").add_parameter("Stream", value=True)

            output = psrp.SyncPSDataCollection()
            output.data_added = print_ft
            self.ps.streams.error.data_added = print_error
            try:
                self.ps.invoke(output_stream=output)
            except (psrp.PipelineStopped, psrp.PipelineFailed) as e:
                print_error(e)
            except ParseError:
                print_error("Command failed: Invalid character in command.")


        thread = Thread(target=_process_input_logic, name=user_input, daemon=True)
        thread.start()
        while thread.is_alive():
            thread.join(timeout=0.5)

    def prompt(self) -> str:
        """Prompt the user for input.

        Returns:
            str: The user's input.

        """
        self.ps = psrp.SyncPowerShell(self.rp)
        cwd: str = get_command_output(self.rp, "pwd")[0].strip()
        prefix = f"{cwd}> "
        return self.session.prompt(HTML(f"{prefix}"))

    def keepalive(self) -> None:
        """Keep the connection alive by sending a repeat no-op command."""
        while True:
            while self.pause_keepalive:
                time.sleep(1)
            ps = psrp.SyncPowerShell(self.rp)
            ps.add_script("").invoke()
            time.sleep(60)
