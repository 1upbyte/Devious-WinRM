"""Gets the output of a PS command as a string."""
from __future__ import annotations

import psrp

from devious_winrm.util.printers import print_error


def get_command_output(rp: psrp.SyncRunspacePool, command: str) -> list[str]:
    """Execute a command in the PowerShell runspace and return the output.

    Args:
        rp (psrp.SyncRunspacePool): The runspace pool on which to execute the command.
        command (str): The command to run.

    Returns:
        list[str]: List of output objects as strings.
        For example, running "GetChild-Item" would return one item per file.

    """
    ps = psrp.SyncPowerShell(rp)
    ps.add_script(command)
    try:
        output = ps.invoke()
    except psrp.PSRPError as e:
        print_error(e)
        return [""]
    return list(map(str, output))

