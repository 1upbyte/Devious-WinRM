"""Devious WinRM."""

from typing import Annotated

import psrp
import typer
from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print_ft
from psrp import WSManInfo

from devious_winrm.util.commands import commands, run_command
from devious_winrm.util.kerberos import prepare_kerberos


class Terminal:
    """Terminal class to handle the connection and command execution."""

    def __init__(self, conn: WSManInfo) -> None:
        """Initialize the terminal with a connection object."""
        self.session = PromptSession()
        self.conn = conn
        self.error_count: int = 0

    def run(self) -> None:
        """Run the terminal and handle user input."""
        with psrp.SyncRunspacePool(self.conn) as rp:
            self.ps = psrp.SyncPowerShell(rp)
            while True:
                try:
                    current_dir = self.ps.add_script("pwd").invoke()
                    user_input: str = self.session.prompt(str(current_dir[0]) + "> ")
                    if user_input.split(" ")[0] in commands:
                        run_command(self, user_input)
                        continue
                    try:
                        self.run_command(user_input)
                    except Exception as e:
                        print_ft(e)
                        break
                    finally:
                        print_ft()
                        # Clear the commands in the pipeline
                        self.ps._pipeline.metadata.commands = []  # noqa: SLF001
                except (KeyboardInterrupt, EOFError, SystemExit):
                    print_ft("Goodbye!")
                    self.ps.close()
                    break
                except Exception as e:
                    print_ft(e)
                    break

    def run_command(self, command: str) -> None:
        """Run a command in the terminal and print_ft the output."""
        self.ps.add_script(command)
        self.ps.add_command("Out-String")
        out = self.ps.invoke()

        had_error: bool = len(self.ps.streams.error) > self.error_count
        if had_error:
            print_ft(str(self.ps.streams.error[-1]).strip())
            self.error_count = len(self.ps.streams.error)
        if len(out[0]) > 0:
            print_ft(out[0].strip())


def main(host: Annotated[str, typer.Argument()],  # noqa: PLR0913
        username: Annotated[str, typer.Option("-u", "--username")] = None,
        password: Annotated[str, typer.Option("-p", "--password")] = None,
        port: Annotated[int, typer.Option("-P", "--port")] = 5985,
        auth: Annotated[str, typer.Option("-a", "--auth")] = "negotiate",
        nt_hash: Annotated[str, typer.Option("-H", "--hash")] = None,
        dc: Annotated[str, typer.Option("--dc", "--domain-controller")] = None) -> None:
    """Parse command line arguments and runs the terminal."""
    if nt_hash is not None:
        if len(nt_hash) != 32:
            error = "NTLM hash must be 32 characters long."
            raise ValueError(error)
        if password is not None:
            error = "Password and NTLM hash cannot be used together."
            raise ValueError(error)
        if auth != "kerberos":
            password = "aad3b435b51404eeaad3b435b51404ee:" + nt_hash
    if auth == "kerberos":
        dc = dc or host
        prepare_kerberos(host, dc, username, password, nt_hash)

    """ Main function to run the terminal """
    conn = WSManInfo(
        server=host,
        username=username,
        password=password,
        port=port,
        auth=auth,
    )
    terminal = Terminal(conn)
    try:
        terminal.run()
    except Exception as e:
        print_ft(e)
        typer.Exit()

if __name__ == "__main__":
    typer.run(main)
