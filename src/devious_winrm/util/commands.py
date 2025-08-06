"""File to define commands."""
from __future__ import annotations

from typing import TYPE_CHECKING

import psrp

from devious_winrm.util.bypass_amsi import bypass_amsi as bypass_amsi_func
from devious_winrm.util.file_upload_download import copy_file, fetch_file
from devious_winrm.util.get_command_output import get_command_output
from devious_winrm.util.invoke_in_memory import invoke_in_memory
from devious_winrm.util.printers import print_error, print_info

if TYPE_CHECKING:
    from collections.abc import Callable

    from devious_winrm.app import Terminal
import argparse
from pathlib import Path

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
    # Implemented in app.py

@command
def help(_self: Terminal, _args: str) -> None:  # noqa: A001
    """Show help information."""
    print_info("Available commands:")
    for cmd, details in commands.items():
        print_info(f"{cmd}: {details['description']}")

@command
def upload(self: Terminal, args: list[str]) -> None | bool:
    """Upload a file. Use --help for usage."""
    epilog = "Large files may struggle to transfer."
    parser = argparse.ArgumentParser("upload", exit_on_error=False, epilog=epilog)
    parser.add_argument("local_path", type=str)
    parser.add_argument(
        "-o", "--overwrite",
        action="store_true",
        help="overwrite the existing file if it exists (Default: False).",
    )
    parser.add_argument(dest="destination", type=str, nargs="?", default=".",
                        help="prepend with a $ to store the file"
                        " in a variable instead of on disk")
    try:
            parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return None
    except SystemExit: # --help raises SystemExit
        return None
    try:
        local_path: Path = Path(parsed_args.local_path)
        destination: str = parsed_args.destination
        overwrite: bool = parsed_args.overwrite
        final_dest = copy_file(self.rp, local_path, destination, overwrite=overwrite)
        print_info(f"Uploaded {local_path} to {final_dest}")
    except FileNotFoundError:
        print_error(f"No such file or directory: {local_path}")
    except (psrp.PSRPError, OSError) as e:
        print_error(f"Failed to upload file: {e}")
    else:
        return True

@command
def download(self: Terminal, args: list[str]) -> None:
    """Download a file. Use --help for usage."""
    epilog = "Large files may struggle to transfer."
    parser = argparse.ArgumentParser("download", exit_on_error=False, epilog=epilog)
    parser.add_argument(
        "-o", "--overwrite",
        action="store_true",
        help="overwrite the existing file if it exists (Default: False).",
    )
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
        remote_path: str = parsed_args.remote_path
        local_path: Path = Path(parsed_args.local_path or remote_path.split("\\")[-1])
        overwrite: bool = parsed_args.overwrite
        final_path = fetch_file(self.rp, remote_path, local_path, overwrite=overwrite)
        print_info(f"Downloaded {remote_path} to {final_path}")
    except FileNotFoundError:
        print_error(f"No such file or directory: {local_path}")
    except (psrp.PSRPError, OSError) as e:
        print_error(f"Failed to download file: {e}")

@command
def invoke(self: Terminal, args: list[str]) -> None:
    """Invoke a .NET binary in memory. Use --help for usage."""
    epilog = "Large files may have issues uploading."
    parser = argparse.ArgumentParser("invoke", exit_on_error=False, epilog=epilog)
    parser.add_argument("local_path", type=str)
    parser.add_argument(
        "-c", "--no_cache",
        action="store_true",
        help="re-upload the binary instead of using the cached copy (Default: False).",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER,
                        help="comma separated arguments to pass to the binary.")
    try:
            parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return
    except SystemExit: # --help raises SystemExit
        return

    var_name = Path(parsed_args.local_path).name

    cached = get_command_output(self.rp, f"Get-Variable {var_name}")

    if cached and cached[0] and not parsed_args.no_cache:
        print_info("Using cached binary.")
    else:
        success = upload(self, [parsed_args.local_path, f"${var_name}"])
        if not success:
            return # Errors will be printed by upload()

    invoke_in_memory(self.rp, var_name, parsed_args.args)

@command
def bypass_amsi(self: Terminal, _args: list[str]) -> None:
    """Bypass the Antimalware Scan Interface (AMSI)."""
    bypass_amsi_func(self.rp)
