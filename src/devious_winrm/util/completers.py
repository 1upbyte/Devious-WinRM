"""Auto suggester remote paths.

Thank you to @adityatelange for much of this code.
Check out his project at https://github.com/adityatelange/evil-winrm-py/
"""
import pathlib
import re
from collections.abc import Iterator

import psrp
from prompt_toolkit.completion import (
    CompleteEvent,
    Completion,
    PathCompleter,
)
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

from devious_winrm.util.get_command_output import get_command_output


class RemotePathAutoCompleter(PathCompleter):
    """Auto complter for remote paths."""

    def __init__(self, rp: psrp.SyncRunspacePool) -> None:
        """Initialize the remote path completer."""
        self.rp = rp


    def get_completions(self, document: Document, _: CompleteEvent) -> Iterator[Completion]:  # noqa: E501
        """Return the available paths."""
        path = document.get_word_before_cursor(WORD=True).replace("\\", "/")

        # Parse the path. Folders need to be in the 'directory' variable, hence the code
        ended_with_slash = False
        if path.endswith(("\\", "/")):
            ended_with_slash = True
        path = pathlib.PureWindowsPath(path)
        directory = str(path.parent)
        prefix = str(path.name)
        if ended_with_slash:
            directory += "\\" + prefix
            prefix = ""
        # Accounts PureWindowsPath(C:) not putting a \ in front of itself
        drive_letter_path = False
        if re.match(r"^[A-Za-z]:$", directory): # Matches C:, D:, etc
            directory += "\\"
            drive_letter_path = True

        attrs = ""
        doc_text = document.text_before_cursor
        if doc_text and doc_text.split()[0] == "cd":
            attrs = "-Attributes Directory"

        cmd = f"gci -LiteralPath '{directory}' -Filter '{prefix}*' {attrs} -Force \
            | Select-Object @{{Name='Name'; \
            Expression={{if ($_.PSIsContainer) {{$_.Name + '\\'}} else {{$_.Name}}}}}} \
            | Select-Object -ExpandProperty Name"

        children = get_command_output(self.rp, cmd)
        for child in children:
            completion = child
            # For some reason passing 'C:\file' to -LiteralPath in the command will
            # cause it to return the same file. Powershell quirks I suppose
            if completion == directory:
                completion = ""
            completion = completion.removesuffix("\\")
            # Have the user type the \, otherwise pressing tab will cycle completions
            if " " in completion: # Quote paths with spaces
                completion = f'"{completion}"'
            if drive_letter_path:
                completion = f"\\{completion}"
            yield Completion(completion,
                             selected_style=CompleteStyle.READLINE_LIKE,
                             start_position=-len(prefix))


