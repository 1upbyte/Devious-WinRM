"""Delay the handling of a SIGINT.

All credit to @adityatelange for this code
"""
from __future__ import annotations

import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devious_winrm.app import Terminal

RED = "\033[31m"
RESET = "\033[0m"

class DelayedKeyboardInterrupt():
    """A context manager to delay the handling of a SIGINT (Ctrl+C) signal until the enclosed block of code has completed execution.

    This is useful for ensuring that critical sections of code are not
    interrupted by a keyboard interrupt, while still allowing the signal
    to be handled after the block finishes.
    """  # noqa: E501

    def __enter__(self) -> None:
        """Set up the signal handler and store the old handler."""
        from devious_winrm.cli import terminal
        t: Terminal = terminal
        self.signal_received = False
        self.old_handler = signal.getsignal(signal.SIGINT)

        def handler(sig, frame) -> None:
            """Handle the SIGINT signal by printing a message and storing the signal."""
            t.print_error("[-] Caught Ctrl+C. Stopping current command...")
            self.signal_received = (sig, frame)

        signal.signal(signal.SIGINT, handler)

    def __exit__(self, type, value, traceback) -> None:
        """Restore the old signal handler and raise the signal if it was received."""
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            # raise the signal after the task is done
            self.old_handler(*self.signal_received)