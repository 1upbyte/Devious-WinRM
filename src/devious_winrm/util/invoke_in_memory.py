"""Invoke the binary in $bin."""

from xml.etree.ElementTree import ParseError

import psrp

from devious_winrm.util.misc import get_pwsh_script
from devious_winrm.util.printers import print_error, print_ft, print_info

script = get_pwsh_script("Invoke-In-Memory.ps1")

def invoke_in_memory(rp: psrp.SyncRunspacePool, var_name: str, args: list[str]) -> None:
    """Invoke a .NET binary in memory."""
    ps = psrp.SyncPowerShell(rp)
    ps.add_script(script)
    ps.add_parameter("VariableName", var_name)
    if args:
        ps.add_argument(args)
    ps.add_command("Out-String").add_parameter("Stream", value=True)

    output = psrp.SyncPSDataCollection()
    output.data_added = print_ft
    ps.streams.error.data_added = print_error
    ps.streams.information.data_added = print_ft
    try:
        print_info("Invoking binary in memory...")
        ps.invoke(output_stream=output)
    except (psrp.PipelineStopped, psrp.PipelineFailed) as e:
        print_error(e)
    except ParseError:
        print_error("Command failed: Invalid character in command.")
