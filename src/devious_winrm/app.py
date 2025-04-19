"""Devious WinRM."""

import psrp
import typer
from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print_ft
from psrp import WSManInfo

from devious_winrm.util.commands import commands, run_command


class Terminal:
    """Terminal class to handle the connection and command execution."""

    def __init__(self, conn: WSManInfo, ps: psrp.SyncPowerShell) -> None:
        """Initialize the terminal with a connection object."""
        self.session = PromptSession()
        self.conn = conn
        self.ps = ps
        self.error_count: int = 0

    def run(self) -> None:
        """Run the terminal and handle user input."""
        while True:
            current_dir = self.ps.add_script("pwd").invoke()
            user_input: str = self.session.prompt(str(current_dir[0]) + "> ")
            self.process_command(user_input)

    def process_command(self, user_input: str) -> None:
        """Run a command in the terminal and print_ft the output."""
        command: str = user_input.split(" ")[0]
        if command in commands:
            run_command(self, user_input)
            return
        try:
            self.ps.add_script(user_input)
            self.ps.add_command("Out-String")
            out: str = self.ps.invoke()[0]

            # The pipeline only keeps track of total erros, not per command
            # So we need to check if the error stream has changed
            had_error: bool = len(self.ps.streams.error) > self.error_count
            if had_error:
                print_ft(str(self.ps.streams.error[-1]).strip())
                self.error_count = len(self.ps.streams.error)

            if out:
                print_ft(out.strip())
        except Exception as e:
            print_ft(e)
            return
        finally:
            print_ft()
            # Clear the commands in the pipeline
            self.ps._pipeline.metadata.commands = []  # noqa: SLF001



def main(conn: WSManInfo) -> None:
    """Run the terminal application."""
    with psrp.SyncRunspacePool(conn) as rp:
        ps = psrp.SyncPowerShell(rp)
        terminal = Terminal(conn, ps)
        terminal.run()

if __name__ == "__main__":
    typer.run(main)
