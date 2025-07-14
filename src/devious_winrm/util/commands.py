"""File to define commands."""
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import psrp

from devious_winrm.util.printers import print_error, print_info
from devious_winrm.util.upload_to_memory import upload_to_memory

if TYPE_CHECKING:
    from devious_winrm.app import Terminal
import argparse
from pathlib import Path
from typing import Callable

commands = {}

def command(func: Callable) -> Callable:
    """Automatically registers a command using its docstring.

    This decorator adds the decorated function to the `commands` dictionary,
    using the function's name as the key. The value is a dictionary containing
    the function's docstring as the description and the function itself as the action.

    Args:
        func (Callable): The function to be registered as a command.

    Returns:
        Callable: The original function, unmodified.

    """
    commands[func.__name__] = {
        "description": func.__doc__,
        "action": func,
    }
    return func

def run_command(self: Terminal, user_input: str) -> None:
    """Run a command by looking it up in the dictionary and invoking its action.

    Args:
        self (Terminal): The terminal instance on which the command is executed.
        user_input (str): The command to execute.

    Raises:
        KeyError: If the specified command is not found in the commands dictionary.

    Notes:
        If the command is not found, a message is printed to inform
        the user and suggest typing 'help' for a list of available commands.

    """
    input_array: list[str] = user_input.split(" ")
    if len(input_array) == 0:
         return
    cmd: str = user_input.split(" ")[0]
    args: list[str] = input_array[1:] if len(input_array) > 1 else []
    try:
        commands[cmd]["action"](self, args)
    except KeyError:
        print_error(
            f"Command '{cmd}' not found. Type 'help' for a list of commands.",
        )


@command
def exit(_self: Terminal, _args: str) -> None:  # noqa: A001
    """Exit the application."""
    sys.exit(0)

@command
def help(_self: Terminal, _args: str) -> None:  # noqa: A001
    """Show help information."""
    print_info("Available commands:")
    for cmd, details in commands.items():
        print_info(f"{cmd}: {details['description']}")

@command
def upload(self: Terminal, args: list[str]) -> None:
    """Upload a file. Use --help for usage."""
    epilog = "Large files may struggle to transfer."
    parser = argparse.ArgumentParser("upload", exit_on_error=False, epilog=epilog)
    parser.add_argument("local_path", type=str)
    parser.add_argument(dest="destination", type=str, nargs="?",
                        help="prepend with a $ to store the file"
                        " in a variable instead of on disk")
    try:
            parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return
    except SystemExit: # --help raises SystemExit
        return
    try:
        local_path: Path = Path(parsed_args.local_path)
        destination: str = parsed_args.destination or local_path.name
        in_memory = destination.startswith("$") if destination else False
        if in_memory:
            destination = destination[1:] # Remove the $ prefix
            var_name = upload_to_memory(self.rp, local_path, destination)
            print_info(f"Uploaded {local_path} to ${var_name}")
        else:
            # Uploading a file to disk uses a secondary RunspacePool, so the keep-alive
            # from the main one won't interfere.
            self.pause_keepalive = False
            final_path = psrp.copy_file(self.conn, local_path, destination)
            print_info(f"Uploaded {local_path} to {final_path}")
    except FileNotFoundError:
        print_error(f"No such file or directory: {local_path}")
    except (psrp.PSRPError, OSError) as e:
        print_error(f"Failed to upload file: {e}")

@command
def download(self: Terminal, args: list[str]) -> None:
    """Download a file. Use --help for usage."""
    epilog = "Large files may struggle to transfer."
    parser = argparse.ArgumentParser("download", exit_on_error=False, epilog=epilog)
    parser.add_argument("remote_path", type=str)
    parser.add_argument("local_path", type=str, nargs="?")
    try:
        parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return
    except SystemExit: # --help raises SystemExit
        return

    try:
        # Downloading a file uses a secondary RunspacePool, so the keep-alive
        # from the main one won't interfere.
        self.pause_keepalive = False
        remote_path: str = parsed_args.remote_path
        local_path: str = parsed_args.local_path or remote_path.split("\\")[-1]
        final_path = psrp.fetch_file(self.conn, remote_path, local_path)
        print_info(f"Downloaded {remote_path} to {final_path}")
    except FileNotFoundError:
        print_error(f"No such file or directory: {local_path}")
    except (psrp.PSRPError, OSError) as e:
        print_error(f"Failed to download file: {e}")
