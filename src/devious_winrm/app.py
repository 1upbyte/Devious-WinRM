"""Devious WinRM."""

import asyncio
import os
from functools import partial

import anyio
import httpcore
import psrp
import typer
from prompt_toolkit import ANSI, HTML, PromptSession, print_formatted_text
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from psrp import WSManInfo
from psrpcore.types import PSInvocationState
from pygments.lexers.shell import PowerShellLexer
from pygments.styles import get_style_by_name

from devious_winrm.util.commands import commands, run_command


class Terminal:
    """Async Terminal for handling connection and command execution."""

    def __init__(self, conn: WSManInfo) -> None:
        """Initialize the terminal with a connection and PowerShell session."""
        self.conn: WSManInfo = conn
        self.session: PromptSession = PromptSession()
        self.ps: psrp.AsyncPowerShell = None
        self.error_count: int = 0
        self.style = Style.from_dict({
            "prefix": "#F1FA88 bold",
            "error": "#CD0000",
            "devious": "#1395c4",
        })
        os.environ["PROMPT_TOOLKIT_COLOR_DEPTH"] = "ColorDepth.DEPTH_8_BIT"
        self.print_ft = partial(print_formatted_text, style=self.style)
        self.print_error = lambda msg: self.print_ft(HTML(f"<error>{msg}</error>"))
        self.username: str = None
        self.prompt_style = style_from_pygments_cls(get_style_by_name("monokai"))

    async def run(self, ps: psrp.AsyncPowerShell) -> None:
        """Run the terminal event loop asynchronously."""
        self.ps = ps
        self.username = str((await self.ps.add_command("whoami").invoke())[0])
        while True:
            current_dir: str = str((await self.ps.add_script("pwd").invoke())[0])
            current_dir = (f"<prefix>{current_dir}</prefix>")
            prefix: str = "<ansigreen></ansigreen>"
            prompt: str = f"{prefix} {current_dir}"
            prompt: HTML = HTML(prompt)
            self.print_ft(prompt)
            user_input: str = await self.session.prompt_async(
                "PS> ", lexer=PygmentsLexer(PowerShellLexer))
            await self.process_command(user_input)

    async def process_command(self, user_input: str) -> None:
        """Execute a command or run a registered action."""
        command = user_input.split(" ")[0]
        try:
            if command in commands:
                await run_command(self, user_input)
                return

            self.ps.add_script(user_input)
            self.ps.add_command("Out-String")
            out_list = await self.ps.invoke()

            had_error = len(self.ps.streams.error) > self.error_count
            if had_error:
                error_message = (str(self.ps.streams.error[-1]).strip())
                self.print_error(error_message)
                self.error_count = len(self.ps.streams.error)

            out = out_list[0] if out_list else ""
            if out:
                self.print_ft(ANSI(out.strip()))
        except psrp.PipelineFailed as e:
            self.print_error(e)
        finally:
            # Reset pipeline state and clear commands
            # I don't know of a better way to do this than
            # modifying private attributes. - 1upbyte
            self.ps._pipeline.state = PSInvocationState.NotStarted # noqa: SLF001
            self.ps._pipeline.metadata.commands = [] # noqa: SLF001


async def _async_main(conn: WSManInfo) -> None:
    """Async entrypoint to initialize the pool and run the terminal."""
    terminal = Terminal(conn)
    try:
        async with psrp.AsyncRunspacePool(conn) as rp:
            ps = psrp.AsyncPowerShell(rp)
            await terminal.run(ps)

    # This error occurs on startup if the IP/host/port is unreachable
    except httpcore.ConnectError as e:
        error = f"Connection error: {e}"
        terminal.print_error(error)
        raise typer.Exit(1) from e
    except (
        httpcore.ConnectionNotAvailable,
        anyio.BrokenResourceError,
        httpcore.ReadError) as e:
        error = "Connection died (left alone too long)."
        terminal.print_error(error)
        raise typer.Exit(1) from e


def main(conn: WSManInfo) -> None:
    """Sync wrapper to run the async main via asyncio."""
    asyncio.run(_async_main(conn))


if __name__ == "__main__":
    typer.run(main)
