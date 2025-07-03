"""Gets the output of a PS command as a string."""
import psrp


def get_command_output(rp: psrp.SyncRunspacePool, command: str) -> str:
    """Execute a command in the PowerShell runspace and return the output."""
    ps = psrp.SyncPowerShell(rp)
    ps.add_script(command)
    output = ps.invoke()[0]
    output = str(output)
    return output.strip()
