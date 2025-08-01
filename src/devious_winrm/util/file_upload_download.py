"""Handle uploading and downloading files using HTTP (asyncio version)."""

import asyncio
import errno
from pathlib import Path
from random import randint

import aiofiles
from aiohttp import web

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


async def run_server(file_path: Path) -> int:
    """Run the HTTP server asynchronously.

    Returns the port used.
    """
    port = randint(LOWER_PORT_BOUND, UPPER_PORT_BOUND)  # noqa: S311
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

async def upload_file(file_path: Path) -> None:
    """Upload a file to the remote server via HTTP (asyncio).

    Raises MaxAttemptsExceededError on repeated failure.
    """
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            await run_server(file_path)
            break
        except OSError as e:
            # In case the port is already in use
            if e.errno == errno.EADDRINUSE:
                attempts += 1
                continue
            raise
    else:
        error = f"Too many attempts failed when uploading {file_path}"
        raise MaxAttemptsExceededError(error)

if __name__ == "__main__":
    asyncio.run(upload_file(Path("~/test/test2.txt")))
