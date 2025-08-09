"""Functions for printing messages to the terminal with formatting."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from prompt_toolkit import ANSI, print_formatted_text

if TYPE_CHECKING:
    from psrpcore.types import ErrorRecord, PSString

ANSI_RED = "\033[31m"
ANSI_BLUE = "\033[34m"
ANSI_RESET = "\033[0m"

def print_ft(message: str | PSString) -> None:
    """Print formatted text to the terminal."""
    print_formatted_text(ANSI(message.strip()))

def print_error(message: ErrorRecord) -> None:
    """Print an error message to the terminal."""
    message = str(message)
    # Check if the message already contains ANSI color codes
    if not re.search(r"\x1b\[[0-9;]*m", message):
        message = f"{ANSI_RED}{message}{ANSI_RESET}"
    print_ft(message)

def print_info(message: str) -> None:
    """Print an informational message to the terminal."""
    print_ft(f"{ANSI_BLUE}[+] {message}{ANSI_RESET}")
