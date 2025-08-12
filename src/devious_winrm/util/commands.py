"""File to define commands."""
from __future__ import annotations

import importlib.resources
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
import hashlib
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
                        help="arguments to pass to the binary.")
    try:
            parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return
    except SystemExit: # --help raises SystemExit
        return

    local_path = Path(parsed_args.local_path)
    with local_path.open("rb") as f:
        file_bytes = f.read()
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    var_name = sha256_hash[:7]
    cached = get_command_output(self.rp, f"Get-Variable {var_name}", error_ok=True)

    if cached and cached[0] and not parsed_args.no_cache:
        print_info("Using cached binary.")
    else:
        success = upload(self, [str(local_path), f"${var_name}"])
        if not success:
            return # Errors will be printed by upload()
    invoke_in_memory(self.rp, var_name, parsed_args.args)

@command
def bypass_amsi(self: Terminal, _args: list[str]) -> None:
    """Bypass the Antimalware Scan Interface (AMSI)."""
    bypass_amsi_func(self.rp)

@command
def localexec(self: Terminal, args: list[str]) -> None:
    """Run a command with a local token. Use --help for usage."""
    desc = "Run a command with a local token. This is useful for commands such as\
        'Get-Service' which usually do not work via WinRM.\
        Uses RunasCs from github/antonioCoco under the hood."
    parser = argparse.ArgumentParser("localexec", exit_on_error=False, description=desc)
    parser.add_argument("command", help="the command to run. Does not need quotes\
                        even with arguments and spaces.")
    parser.add_argument("-t", "--timeout", default=120000, help="the waiting time (in\
                         ms)for the created process. This will halt RunasCs until the\
                        spawned process ends and sent the output back to the caller.\
                        If you set 0 no output will be retrieved and a background\
                        process will be created. Default: 120000 (2 minutes).")
    parser.add_argument("-n", "--no-powershell", action="store_true",
                        help="prevent commands from being wrapped with\
                            'powershell -c <command>'.")
    parser.add_argument("args", nargs=argparse.REMAINDER,
                        help=argparse.SUPPRESS) # The 'command' argument includes args.
    try:
        parsed_args = parser.parse_args(args)
    except argparse.ArgumentError as e:
        print_error(e)
        print_error("Use --help for usage details.")
        return
    except SystemExit: # --help raises SystemExit
        return

    command: str = parsed_args.command
    command_args: list[str] = parsed_args.args
    timeout: int = parsed_args.timeout
    no_powershell: bool = parsed_args.no_powershell

    invocation_args = []

    bin_path = "devious_winrm.util.binaries"
    runascs_path = str(importlib.resources.files(bin_path).joinpath("RunasCs.exe"))
    invocation_args.append(runascs_path)

    invocation_args.append("x") # Username doesn't matter for logon_type 9
    invocation_args.append("x") # Password doesn't matter for logon_type 9

    if command_args:
        command +=  " " + " ".join(parsed_args.args)
    if not no_powershell:
        command = f'powershell -c "{command}"'
    invocation_args.append(command)

    invocation_args.append("--logon-type")
    invocation_args.append("9") # Local logon type. Refer to RunasCs.exe --help
    invocation_args.append("--timeout")
    invocation_args.append(str(timeout))

    invoke(self, invocation_args)

