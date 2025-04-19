"""Devious WinRM."""

import asyncio
from typing import Optional

import psrp
import typer
from prompt_toolkit import PromptSession
from prompt_toolkit import print_formatted_text as print_ft
from psrp import WSManInfo

from devious_winrm.util.commands import commands, run_command


class Terminal:
    """Async Terminal for handling connection and command execution."""

    def __init__(self, conn: WSManInfo, ps: psrp.AsyncPowerShell) -> None:
        self.session = PromptSession()
        self.conn = conn
        self.ps = ps
        self.error_count: int = 0

    async def run(self) -> None:
        """Run the terminal event loop asynchronously."""
        while True:
            current_dir = await self.ps.add_script("pwd").invoke()
            user_input: str = await self.session.prompt_async(str(current_dir[0]) + "> ")
            await self.process_command(user_input)

    async def process_command(self, user_input: str) -> None:
        """Execute a command or run a registered action."""
        command = user_input.split(" ")[0]
        if command in commands:
            await run_command(self, user_input)
            return
        try:
            self.ps.add_script(user_input)
            self.ps.add_command("Out-String")
            out_list = await self.ps.invoke()

            had_error = len(self.ps.streams.error) > self.error_count
            if had_error:
                print_ft(str(self.ps.streams.error[-1]).strip())
                self.error_count = len(self.ps.streams.error)

            out = out_list[0] if out_list else ""
            if out:
                print_ft(out.strip())
        except Exception as e:
            print_ft(e)
        finally:
            print_ft()
            # Clear pipeline commands
            self.ps._pipeline.metadata.commands = []  # noqa: SLF001


async def _async_main(conn: WSManInfo) -> None:
    """Async entrypoint to initialize the pool and run the terminal."""
    async with psrp.AsyncRunspacePool(conn) as rp:
        ps = psrp.AsyncPowerShell(rp)
        terminal = Terminal(conn, ps)
        await terminal.run()


def main(conn: WSManInfo) -> None:
    """Sync wrapper to run the async main via asyncio."""
    asyncio.run(_async_main(conn))


if __name__ == "__main__":
    typer.run(main)
