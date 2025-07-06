"""Auto suggester remote paths.

Thank you to @adityatelange for much of this code.
Check out his project at https://github.com/adityatelange/evil-winrm-py/
"""
from collections.abc import Iterator
from pathlib import Path

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
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        attrs = ""
        if word_before_cursor and document.text_before_cursor.split()[0] == "cd":
            attrs = "-Attributes Directory"
        path = Path(word_before_cursor)
        directory = str(path.parent)
        prefix = str(path.name)
        if prefix == "..":
            directory += f"\\{prefix}"
            prefix = ""
        cmd = f"gci -LiteralPath '{directory}' -Filter '{prefix}*' {attrs} -Fo | select -Exp Name"  # noqa: E501
        children = get_command_output(self.rp, cmd)
        for child in children:
            completion = child
            if " " in child: # Quote paths with spaces
                completion = f'"{completion}"'
            completion = completion[len(prefix) :]
            yield Completion(completion, selected_style=CompleteStyle.READLINE_LIKE)



