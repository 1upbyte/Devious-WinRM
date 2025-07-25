"""Test terminal auto complete."""
import re
from typing import Never
from unittest import mock

import pytest
from prompt_toolkit.document import Document

from devious_winrm.util.completers import RemotePathAutoCompleter


def mock_completion(_: Never, cmd: str) -> list[str]:
    """Fake the response from the server when the client asks for completions."""
    # Extract the directory, prefix, and attrs variable
    regex_directory = r"-LiteralPath\s+'(?P<directory>[^']+)'"
    regex_prefix = r"-Filter\s+'(?P<prefix>[^'*]*)\*?'"
    regex_attrs = r"-Filter\s+(?:'[^']*')\s*(?P<attrs>.*?)\s*-Force"

    directory = ""
    prefix = ""
    attrs = ""

    if match_dir := re.search(regex_directory, cmd):
        directory = match_dir.group("directory").strip()

    if match_prefix := re.search(regex_prefix, cmd):
        prefix = match_prefix.group("prefix").strip()

    if match_attrs := re.search(regex_attrs, cmd):
        attrs = match_attrs.group("attrs").strip()

    children = ["INITAL"]
    match directory:
        case ".":
            children = ["test.txt", "file.zip", "folder\\"]
        case "C:\\":
            children = ["Windows\\", "Users",
                        "Program Files\\", "Program Files (x86)\\"]
        #TODO: Fix the double backslash. It doesn't affect anything, but it's silly
        case "C:\\\\Users" | "C:\\Users":
            children = ["pablo.comino", "1upbyte", "mario"]
    if directory == ".":
        children = ["test.txt", "file.zip", "folder\\"]
    if prefix:
         children = list(filter(lambda child: child.startswith(prefix), children))
    if attrs: # If folders only
        children = list(filter(lambda child: child.endswith("\\"), children))


    return children

TEST_CASES = [
    ("", ["test.txt", "file.zip", "folder"]),
    ("te", ["test.txt"]),
    ("f", ["file.zip", "folder"]),
    ("cd f", ["folder"]),
    ("C:", ["\\Windows", "\\Users", '\\"Program Files"', '\\"Program Files (x86)"']),
    ("C:\\Users\\", ["pablo.comino", "1upbyte", "mario"]),
    ("C:\\Users\\\\\\\\", ["pablo.comino", "1upbyte", "mario"]),
    ("C:\\Users\\\\\\\\pa", ["pablo.comino"]),
    ("cd f", ["folder"]),
]

@mock.patch("devious_winrm.util.completers.get_command_output", wraps=mock_completion)
@pytest.mark.parametrize(("text_input", "expected_output"), TEST_CASES)
def test_remote_path_completion(mocked_cmd: mock.Mock,
                                text_input: str, expected_output: list[str]) -> None:
    """Test util.completers."""
    completer = RemotePathAutoCompleter(None)
    doc = Document(text_input)
    completions = completer.get_completions(doc, None)
    completions = list(completions)
    for completion, expected_text in zip(completions, expected_output, strict=True):
        assert completion.display_text == expected_text
