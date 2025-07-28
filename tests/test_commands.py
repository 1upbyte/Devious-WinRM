"""Test various commands.

Note: It is important to try to use commands that do not return Powershell arrays\
    wherever possible. Sending arrays through Powershell is slow and should only\
    be done when necessary.

    The two most common solutions are to:
        - Use a native binary / cmd.exe command (more vs. cat, curl.exe vs curl)
        - Append "| Out-String" to the command. This may change the output, though.\
          For example "pwd" no longer returns just the directory.
"""
from typing import TYPE_CHECKING

import pytest

from devious_winrm.util.get_command_output import get_command_output

if TYPE_CHECKING:
    from psrp import SyncRunspacePool


@pytest.mark.requires_server
def test_file(rp: "SyncRunspacePool") -> None:
    """Test reading a text file."""
    cmd = "more C:\\DWRM-TEST\\text.txt"
    assert get_command_output(rp, cmd)[0].strip() == "Test File"

