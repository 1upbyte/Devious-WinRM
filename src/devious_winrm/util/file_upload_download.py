# ruff: noqa: S324
"""File upload/download utilities.

Credit to @jborean93 for original code. This is a modification to add progress bars and\
an option to copy a file to a variable instead of to disk.
"""
import hashlib
import shutil
import tempfile
import typing as t
from pathlib import Path

from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit.shortcuts.progress_bar import formatters
from psrp import PSRPError, SyncPowerShell, SyncPSDataCollection, SyncRunspacePool

from devious_winrm.util.get_command_output import get_command_output
from devious_winrm.util.misc import get_pwsh_script

pb_format = [
    formatters.Percentage(),
    formatters.Text(" "),
    formatters.Bar(sym_a="#", sym_b="#", sym_c="."),
    formatters.Text("  "),
]

def copy_file(
    rp: SyncRunspacePool,
    src: Path,
    dest: str,
    *_: t.Never,
    overwrite: bool = False,
) -> str:
    """Copy a file to the remote connection.

    Copies a local file to the remote PowerShell connection. The file transfer
    will not be as fast as a transfer over SMB or SSH due to the extra overhead
    that the PSRP layer adds but it will work on whatever connection type is
    used.

    Args:
        rp: An opened Runspace Pool. A connection info object will open a new
            pool and close once the copy has completed whereas a Runspace Pool
            object will use what has already been opened and share the same
            state.
        src: The local path to copy from.
        dest: The destination path to copy the file to. This must be a string
            and relative paths are resolved from the current location of the
            connection which is based on the connection type.
        overwrite: Overwrite the destination file.

    Returns:
        str: The absolute path to the remote destination that the local file
        was copied to.

    """
    src_path = Path.expanduser(src)

    def read_buffer(path: Path, buffer_size: int) -> t.Iterator[bytes]:
        sha1 = hashlib.sha1()

        with path.open(mode="rb") as fd, ProgressBar(formatters=pb_format) as pb:
            file_size = path.stat().st_size
            progress = pb(total=file_size, remove_when_done=True)
            for data in iter((lambda: fd.read(buffer_size)), b""):
                sha1.update(data)
                progress.items_completed += len(data)
                yield data
            progress.done = True
        yield sha1.hexdigest().encode("utf-8")

    ps = SyncPowerShell(rp)
    if dest.startswith("$"):
        ps.add_script(get_pwsh_script("UploadTo-Memory.ps1"))
        ps.add_parameter("variableName", dest[1:])
    else:
        ps.add_script(get_pwsh_script("copy.ps1"))
        ps.add_parameter("Path", dest)
        ps.add_parameter("Overwrite", overwrite)

    output = ps.invoke(
        input_data=read_buffer(src_path, rp.max_payload_size),
        buffer_input=False,
    )

    return t.cast("str", output[0])


def fetch_file(
    rp: SyncRunspacePool,
    src: str,
    dest: Path,
) -> Path:
    """Fetch a file from the remote connection.

    Fetches a file from the remote PowerShell connection and copies it to the
    local path specified. The file transfer will not be as fast as a transfer
    over SMB or SSH due to the extra overhead that the PSRP layer adds but it
    will work on whatever connection type is used.

    Args:
        rp: An opened Runspace Pool.
        src: The remote path to copy from.
        dest: The destination path to copy the file to.

    Returns:
        Path: The absolute path to the local destination
        that the remote file was fetched to.

    """
    dest_path = dest

    with tempfile.TemporaryDirectory() as temp_dir:
        ps = SyncPowerShell(rp)
        ps.add_script(get_pwsh_script("fetch.ps1"))
        ps.add_parameters(
            Path=src,
            BufferSize=rp.max_payload_size,
        )

        file = get_command_output(rp, f"Get-Item {src} | Out-String")
        if not file or not file[0]:
            ps.invoke() # An invalid file will raise an error
        file_size = get_command_output(rp, f"(Get-Item {src}).Length | Out-String")[0]
        file_size = int(file_size)

        out = SyncPSDataCollection[t.Any]()
        temp_file = Path(temp_dir, "psrp-fetch-temp")
        with temp_file.open(mode="wb") as temp_fd,\
            ProgressBar(formatters=pb_format) as pb:

            progress = pb(total=file_size, remove_when_done=True)

            sha1 = hashlib.sha1()

            def on_data(data: bytes | str) -> None:
                if isinstance(data, bytes):
                    sha1.update(data)  # type: ignore[has-type] # Nested func is problematic
                    temp_fd.write(data)  # type: ignore[has-type] # Ditto above
                    progress.items_completed += len(data)


            out.data_added += on_data
            ps.invoke(output_stream=out)
            progress.done = True
        expected_file_hash = out[-1]
        actual_file_hash = sha1.hexdigest()
        if actual_file_hash != expected_file_hash:
            error = f"Invalid hash of retrieved file -\
                 {actual_file_hash} != {expected_file_hash}"
            raise PSRPError(error)

        shutil.move(temp_file, dest_path)

    dest_path = dest_path.absolute()
    if isinstance(dest, Path):
        return dest_path

    str_dest = str(dest_path)
    if isinstance(dest, bytes):
        return str_dest.encode("utf-8", errors="surrogatepass")

    return str_dest
