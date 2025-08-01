"""Provide fixtures for tests."""
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input
from psrp import SyncPowerShell, SyncRunspacePool, WSManInfo

from devious_winrm.app import Terminal
from devious_winrm.util.keybinds import kb

if TYPE_CHECKING:
    from collections.abc import Iterator

    from prompt_toolkit.input import PipeInput

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

@pytest.fixture
def rp(connection: WSManInfo) -> "Iterator[SyncRunspacePool]":
    """Create a RunspacePool for the test."""
    with SyncRunspacePool(connection) as rp:
        yield rp

@pytest.fixture
def dummy_terminal(
    connection: WSManInfo,
    rp: SyncRunspacePool,
) -> "Iterator[tuple[Terminal, PipeInput]]":
    """Create a Terminal with dummy input and output for prompt session testing."""
    with create_pipe_input() as inp:
        session = PromptSession(
                key_bindings=kb,
                input=inp,
            )
        terminal = Terminal(connection, rp, session)
        yield terminal, inp
