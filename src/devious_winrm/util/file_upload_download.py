"""Handle uploading and downloading files using HTTP (asyncio version)."""

import asyncio
import errno
from pathlib import Path
from random import randint
from typing import TYPE_CHECKING
from psrp import ASyncRunspacePool, AsyncPowerShell

import aiofiles
from aiohttp import web

if TYPE_CHECKING:
    from devious_winrm.app import Terminal

import importlib.resources


LOWER_PORT_BOUND = 1024
UPPER_PORT_BOUND = 65535
MAX_ATTEMPTS = 3
"""Number of attempts to try uploading before failing."""

class MaxAttemptsExceededError(Exception):
    """Exception for too many attempts."""

async def file_handler(request: web.Request) -> web.Response:
    """Serve the requested file."""
    file_bytes = request.app["file_bytes"]
    file_size = request.app["file_size"]
    headers = {
        "Content-Type": "application/octet-stream",
        "Content-Length": str(file_size),
    }
    # Send the response prematurely to set the response_sent event
    resp = web.Response(body=file_bytes, headers=headers)
    await resp.prepare(request)
    await resp.write_eof()

    request.app["response_sent"].set()
    return resp


async def run_server(file_path: Path, port: int) -> int:
    """Run the HTTP server asynchronously.

    Returns the port used.
    """
    file_path = file_path.expanduser().resolve()
    async with aiofiles.open(file_path, mode="rb") as f:
        file_bytes = await f.read()
        file_size = len(file_bytes)

    app = web.Application()
    app["file_bytes"] = file_bytes
    app["file_size"] = file_size
    app.router.add_get("/", file_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)

    app["response_sent"] = asyncio.Event()
    await site.start()

    print(f"Running on http://localhost:{port}")

    # Wait for a single request, then shutdown
    await app["response_sent"].wait()

async def execute_upload_command(
    terminal: "Terminal",
    destination: str,
    file_name: str,
    port: int,
) -> None:
    """Execute the upload command on the remote server."""
    script = importlib.resources.read_text("devious_winrm.util.scripts", "Upload.ps1")

    in_memory_upload = (destination == "$")
    if in_memory_upload:
        ps = AsyncPowerShell(terminal.rp)
        ps.add_script(script)
        ps.add_parameter("Path" = )
    async with ASyncRunspacePool(terminal.conn) as rp:
        ps = AsyncPowerShell(rp)

async def upload_file(terminal: "Terminal", local_path: Path, destination: str = ".") -> None:
    """Upload a file to the remote server via HTTP (asyncio).

    Raises MaxAttemptsExceededError on repeated failure.
    """
    file_name = local_path.name
    if destination.startswith("$"): # In-memory upload
        file_name = destination.removeprefix("$")
        destination = ("$")
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            port = randint(LOWER_PORT_BOUND, UPPER_PORT_BOUND)  # noqa: S311
            await run_server(local_path, port)

            await execute_upload_command(terminal, destination, file_name, port)
            break
        except OSError as e:
            # In case the port is already in use
            if e.errno == errno.EADDRINUSE:
                attempts += 1
                continue
            raise
    else:
        error = f"Too many attempts failed when uploading {local_path}"
        raise MaxAttemptsExceededError(error)

if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()
    from psrp import WSManInfo
    conn = WSManInfo(
        server=os.getenv("HOST"),
        username=os.getenv("USERNAME"),
        password=os.getenv("PASSWORD"),
        port=5985,
        auth="ntlm",
    )
    asyncio.run(upload_file(Path("~/test/test2.txt"), conn))
