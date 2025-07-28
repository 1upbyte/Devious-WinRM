"""Provide fixtures for tests."""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from psrp import SyncPowerShell, SyncRunspacePool, WSManInfo

load_dotenv()

WINRM_HTTP_PORT = 5985
DEFAULT_AUTH = "NTLM"

HOST = os.getenv("HOST")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
PORT = os.getenv("PORT", WINRM_HTTP_PORT)
AUTH = os.getenv("AUTH", DEFAULT_AUTH)

@pytest.fixture(scope="session")
def connection() -> WSManInfo:
    """Set up a testing environment on the server.

    The script in scripts/setup.ps1 will be executed.
    """
    conn = WSManInfo(
        server=HOST,
        username=USERNAME,
        password=PASSWORD,
        port=PORT,
        auth=AUTH)

    rel_script_path = Path("./scripts/setup.ps1")
    setup_script: str = (Path(__file__).parent / rel_script_path).read_text()

    # Remove comments
    # Credit to @jborean93's pypsrp for this small parser
    multi_line_comment = False
    new_lines = []
    for line in setup_script.splitlines():
        trimmed_line = line.strip()
        if multi_line_comment:
            multi_line_comment = not trimmed_line.endswith("#>")
        elif trimmed_line.startswith("<#"):
            multi_line_comment = True
        elif trimmed_line and not trimmed_line.startswith("#"):
            new_lines.append(trimmed_line)

    setup_script = "\n".join(new_lines)

    with SyncRunspacePool(conn) as rp:
        ps = SyncPowerShell(rp)
        ps.add_script(setup_script)
        output = ps.invoke()
        if ps.had_errors:
            error = f"Error occured when running test setup: {output}"
            raise RuntimeError(error)

    return conn



