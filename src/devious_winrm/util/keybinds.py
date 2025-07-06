"""Store keybinds for the terminal."""
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

@kb.add("tab")
def _(event) -> None:  # noqa: ANN001
    """When Tab is pressed, handle completion.

    1. If a completion session is active, cycle to the next completion.
    2. If not, start a completion session and select the first option.
    """
    b = event.app.current_buffer
    if b.complete_state:
        b.complete_next()
        # Skip over the original text (only show completions)
        if (b.text == b.complete_state.original_document.text
            and b.complete_state.completions):
                b.complete_next(count=1)
    else:
        b.start_completion(select_first=True)
