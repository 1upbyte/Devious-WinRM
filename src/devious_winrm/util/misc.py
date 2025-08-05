"""Miscellaneous functions."""

import importlib.resources


def get_pwsh_script(
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
