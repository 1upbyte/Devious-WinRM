"""Test terminal auto complete."""
import re
from typing import Never
from unittest import mock

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
    print("-----")
    print(f"Directory: '{directory}'")
    print(f"Prefix: '{prefix}'")
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

def _check_output(text: str, expected: list[str]) -> None:

    completer = RemotePathAutoCompleter(None)
    doc = Document(text)
    completions = completer.get_completions(doc, None)
    completions = list(completions)
    for completion, expected_text in zip(completions, expected, strict=True):
        assert completion.display_text == expected_text

@mock.patch("devious_winrm.util.completers.get_command_output", wraps=mock_completion)
def test_remote_path_completion(mocked_cmd: mock.Mock) -> None:
    """Mock util.get_command_output()."""
    #TODO: Use parameterize
    _check_output("", ["test.txt", "file.zip", "folder"])
    _check_output("te", ["test.txt"])
    _check_output("f", ["file.zip", "folder"])
    _check_output("cd f", ["folder"])
    _check_output("C:", ["\\Windows", "\\Users",
                        '\\"Program Files"', '\\"Program Files (x86)"'])
    _check_output("C:\\Users\\", ["pablo.comino", "1upbyte", "mario"])
    _check_output("C:\\Users\\\\\\\\", ["pablo.comino", "1upbyte", "mario"])
    _check_output("C:\\Users\\\\\\\\pa", ["pablo.comino"])
    _check_output("cd f", ["folder"])

'\\"Program Files"'
'\\"Program Files"\\'
if __name__ == "__main__":
    test_remote_path_completion()
