"""Devious WinRM."""

import asyncio
import datetime
import os
import shutil
from functools import partial

import httpcore
import psrp
import typer
from prompt_toolkit import ANSI, HTML, PromptSession, print_formatted_text
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from psrp import WSManInfo
from pygments.lexers.shell import PowerShellLexer
from pygments.styles import get_style_by_name

from devious_winrm.util.commands import commands, run_command


class Terminal:
    """Async Terminal for handling connection and command execution."""

    def __init__(self, conn: WSManInfo, rp: psrp.AsyncRunspacePool) -> None:
        """Initialize the terminal with a connection and PowerShell session."""
        self.conn: WSManInfo = conn
        self.rp: psrp.AsyncRunspacePool = rp
        self.ps: psrp.AsyncPowerShell = None

        os.environ["PROMPT_TOOLKIT_COLOR_DEPTH"] = "ColorDepth.DEPTH_8_BIT"
        self.prompt_style = style_from_pygments_cls(get_style_by_name("monokai"))
        self.style = Style.from_dict({
            "prefix": "#F1FA88 bold",
            "error": "#CD0000",
            "devious": "#1395c4",
        })

        self.print_ft = partial(print_formatted_text, style=self.style)
        self.print_error = lambda msg: self.print_ft(HTML(f"<error>{msg}</error>"))

        self.username: str = None

        self.session = PromptSession(refresh_interval=1)

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

    async def run(self) -> None:
        """Run the terminal event loop asynchronously."""
        self.ps = psrp.AsyncPowerShell(self.rp)
        self.username = str((await self.ps.add_script("whoami").invoke())[0])
        self.session.bottom_toolbar = self.bottom_toolbar

        while True:
            self.ps = psrp.AsyncPowerShell(self.rp)
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
        self.ps = psrp.AsyncPowerShell(self.rp)
        command = user_input.split(" ")[0]
        try:
            if command in commands:
                await run_command(self, user_input)
                return

            self.ps.add_script(user_input)
            self.ps.add_command("Out-String")
            out_list = await self.ps.invoke()

            if self.ps.had_errors:
                error_message = (str(self.ps.streams.error[-1]).strip())
                self.print_error(error_message)

            out = out_list[0] if out_list else ""
            if out:
                self.print_ft(ANSI(out.strip()))
        except psrp.PipelineFailed as e:
            self.print_error(e)
        finally:
            await self.ps.close()

async def keep_alive(rp: psrp.AsyncRunspacePool) -> None:
    """Keep connection alive by sending a no-op command every 30 seconds."""
    try:
        while True:
            if rp.is_available:
                ps2 = psrp.AsyncPowerShell(rp)
                ps2.add_script("") # No-op
                done = asyncio.Event()
                await ps2.invoke_async(completed=done.set)
                await done.wait()
                await ps2.close()
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        return


async def _async_main(conn: WSManInfo) -> None:
    """Async entrypoint to initialize the pool and run the terminal."""
    try:
        async with psrp.AsyncRunspacePool(conn, max_runspaces=2) as rp:
            # Needs to be stored so it is not garbage collected
            keep_alive_task = set().add(asyncio.create_task(keep_alive(rp)))  # noqa: F841
            terminal: Terminal = Terminal(conn, rp)
            await terminal.run()

    # This error occurs on startup if the IP/host/port is unreachable
    except (httpcore.ConnectError, psrp.WSManHTTPError) as e:
        error = f"Connection error: {e}"
        terminal.print_error(error)
        raise typer.Exit(1) from e


def main(conn: WSManInfo) -> None:
    """Sync wrapper to run the async main via asyncio."""
    asyncio.run(_async_main(conn))


if __name__ == "__main__":
    typer.run(main)
