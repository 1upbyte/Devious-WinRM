"""Gets the output of a PS command as a string."""
from __future__ import annotations

import psrp


def get_command_output(rp: psrp.SyncRunspacePool, command: str) -> list[str]:
    """Execute a command in the PowerShell runspace and return the output."""
    ps = psrp.SyncPowerShell(rp)
    ps.add_script(command)
    output = ps.invoke()
    return list(map(str, output))

