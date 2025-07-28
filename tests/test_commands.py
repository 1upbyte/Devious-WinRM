"""Test various commands."""

import pytest
from psrp import SyncRunspacePool, WSManInfo

from devious_winrm.util.get_command_output import get_command_output


@pytest.mark.requires_server
def test_file(connection: WSManInfo) -> None:
    """Test reading a text file."""
    with SyncRunspacePool(connection) as rp:
        assert get_command_output(rp, "cat C:\\DWRM-TEST\\text.txt | Out-String")[0].strip() == "Test File"

