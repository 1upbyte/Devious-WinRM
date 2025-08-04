"""Invoke the binary in $bin."""

import importlib.resources
from xml.etree.ElementTree import ParseError

import psrp

from devious_winrm.util.printers import print_error, print_ft, print_info


def _get_pwsh_script(
    name: str,
) -> str:
    """Get the contents of a known PowerShell script.

    Get the contents of a PowerShell script inside the 'devious_winrm.util.ps1' package.
    Will also strip out any empty lines and comments to reduce the data we send
    across as much as possible.

    Args:
        name: The script filename inside `devious_winrm.util.ps1' to get.

    Returns:
        The scripts contents.

    """
    script = importlib.resources.read_text("devious_winrm.util.scripts", name)
    block_comment = False
    new_lines = []
    for line in script.splitlines():

        trimmed_line = line.strip()
        if block_comment:
            block_comment = not trimmed_line.endswith("#>")
        elif trimmed_line.startswith("<#"):
            block_comment = True
        elif trimmed_line and not trimmed_line.startswith("#"):
            new_lines.append(trimmed_line)

    return "\n".join(new_lines)

script = _get_pwsh_script("Invoke-In-Memory.ps1")

def invoke_in_memory(rp: psrp.SyncRunspacePool, args: list[str]) -> None:
    """Invoke a .NET binary in memory."""
    ps = psrp.SyncPowerShell(rp)
    ps.add_script(script)
    print_info("Invoking binary in memory...")
    if args:
        ps.add_parameter("Arguments", " ".join(args))
    ps.add_command("Out-String").add_parameter("Stream", value=True)

    output = psrp.SyncPSDataCollection()
    output.data_added = print_ft
    ps.streams.error.data_added = print_error
    ps.streams.information.data_added = print_ft
    try:
        ps.invoke(output_stream=output)
    except (psrp.PipelineStopped, psrp.PipelineFailed) as e:
        print_error(e)
    except ParseError:
        print_error("Command failed: Invalid character in command.")
