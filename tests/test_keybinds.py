"""Test keybindings."""
import time
from threading import Thread
from typing import TYPE_CHECKING

from psrpcore.types import PSInvocationState

if TYPE_CHECKING:
    from prompt_toolkit.input import PipeInput

    from devious_winrm.app import Terminal

#TODO @1upbyte: Get this test to pass https://github.com/1upbyte/Devious-WinRM/issues/9
def test_ctrl_c_keybinding_interrupts(
    dummy_terminal: "tuple[Terminal, PipeInput]",
) -> None:
    """Test that pressing Ctrl-C in the terminal triggers the expected behavior."""
    terminal, inp = dummy_terminal
    session = terminal.session
    inp.send_text("sleep 35\n")

    def _run_input() -> None:
        terminal.process_input(session.prompt().strip())

    t = Thread(target=_run_input, name="input-thread")
    t.start()
    time.sleep(1)
    inp.send_bytes(b"\x03")  # Ctrl-C
    time.sleep(1)
    assert terminal.ps.state == PSInvocationState.Stopped
