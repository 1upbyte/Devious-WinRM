"""Entry point for the CLI application."""
import importlib
from typing import Annotated

import httpcore
import psrp
import typer
from impacket.krb5.kerberosv5 import KerberosError
from psrp import SyncRunspacePool, WSManFault, WSManInfo
from spnego.exceptions import SpnegoError

from devious_winrm.app import Terminal
from devious_winrm.util.kerberos import prepare_kerberos
from devious_winrm.util.printers import print_error, print_ft, print_info

LM_HASH: str = "aad3b435b51404eeaad3b435b51404ee"

VERSION = importlib.metadata.version("devious_winrm")

print_ft("")
print_info(f"Devious-WinRM v{VERSION} by 1upbyte")


desc = {}
desc["username"] = "Username used for authentication."
desc["password"] = "Password used for authentication. Cannot be used with an NTLM hash."  # noqa: S105
desc["port"] = "Port of remote host, 5985 by default, 5986 when using SSL."
desc["kerberos"] = ("Kerberos authentication. If no username is provided,"
    " uses cached TGT. Requires specifiying a domain controller.")
desc["nt_hash"] = ("NTLM Hash. Accepts both LM:NTLM or just NTLM."
    " Cannot be used with password.")
desc["dc"] = ("FQDN for the domain controller."
    " Useful for Kerberos authentication.")

flags = {}
flags["username"] = typer.Option("-u", "--username", help=desc["username"])
flags["password"] = typer.Option("-p", "--password", help=desc["password"])
flags["port"] = typer.Option("-P", "--port", help=desc["port"])
flags["kerberos"] = typer.Option("-k", "--kerberos", help=desc["kerberos"])
flags["nt_hash"] = typer.Option("-H", "--hash", help=desc["nt_hash"])
flags["dc"] = typer.Option("--domain-controller", "--dc", help=desc["dc"])

def cli(host: Annotated[str, typer.Argument()],  # noqa: C901, PLR0912, PLR0913
    username: Annotated[str, flags["username"]] = None,
    password: Annotated[str, flags["password"]] = None,
    port: Annotated[int, flags["port"]] = 5985,
    kerberos: Annotated[bool, flags["kerberos"]] = False,  # noqa: FBT002
    nt_hash: Annotated[str, flags["nt_hash"]] = None,
    dc: Annotated[str | None, flags["dc"]]=None,
) -> None:
    """Parse command line arguments and forward them to the terminal."""
    if nt_hash is not None:
        if password is not None:
            error = "Password and NTLM hash cannot be used together."
            raise typer.BadParameter(error)
        if ":" in nt_hash: # In case user provides lm_hash:nt_hash
            nt_hash = nt_hash.split(":")[1]
        if len(nt_hash) != 32:
            error = "NTLM hash must be 32 characters long."
            raise typer.BadParameter(error)
        if not kerberos:
            password = f"{LM_HASH}:{nt_hash}"

    if dc is not None and dc.count(".") < 2:
        error = "Please specify the FQDN of the domain controller (dc.example.com)."
        raise typer.BadParameter(error)

    if kerberos and not dc and host.count(".") < 2:
            error = "Domain controller or FQDN must be specified when using Kerberos."
            raise typer.BadParameter(error)


    try:
        auth = "ntlm"
        if kerberos:
            dc_fqdn = dc if dc else host
            prepare_kerberos(dc_fqdn, username, password, nt_hash)
            auth = "kerberos"
        conn = WSManInfo(
            server=host,
            username=username,
            password=password,
            port=port,
            auth=auth,
            read_timeout=500, # A command timing out is difficult to recover.
            )
        with SyncRunspacePool(conn, max_runspaces=5) as rp:
            terminal = Terminal(conn, rp)
            terminal.run()
    except psrp.WSManAuthenticationError:
        error = "Authentication failed. Please check your credentials and try again."
        print_error(error)
    except (httpcore.ReadError, httpcore.ConnectionNotAvailable, httpcore.ReadTimeout):
        error = "Connection timed out."
        print_error(error)
    except (httpcore.ConnectError, httpcore.TimeoutException) as err:
        error = f"Connection error: {err}"
        print_error(error)
    except (OSError, FileNotFoundError, ValueError,
            NotImplementedError, KerberosError, WSManFault,
            SpnegoError) as err:
        print_error(err)
    except Exception as err:  # noqa: BLE001
        error = (f"Unexpected error occurred of type {err.__class__},"
            f" please report it! \n{err}")
        print_error(error)

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
app.command(help="")(cli)

if __name__ == "__main__":
    app()
