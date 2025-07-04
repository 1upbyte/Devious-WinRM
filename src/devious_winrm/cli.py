"""Entry point for the CLI application."""
from typing import Annotated, Optional

import httpcore
import psrp
import typer
from impacket.krb5.kerberosv5 import KerberosError
from psrp import SyncRunspacePool, WSManInfo

from devious_winrm.app import Terminal
from devious_winrm.util.kerberos import prepare_kerberos
from devious_winrm.util.printers import print_error, print_ft, print_info

LM_HASH: str = "aad3b435b51404eeaad3b435b51404ee"

print_ft("")
print_info("Devious-WinRM by 1upbyte")

def cli(host: Annotated[str, typer.Argument()],  # noqa: C901, PLR0913
        username: Annotated[str, typer.Option("-u", "--username")] = None,
        password: Annotated[str, typer.Option("-p", "--password")] = None,
        port: Annotated[int, typer.Option("-P", "--port")] = 5985,
        kerberos: Annotated[bool, typer.Option("-k", "--kerberos")] = False,  # noqa: FBT002
        nt_hash: Annotated[str, typer.Option("-H", "--hash")] = None,
        dc: Annotated[Optional[str], typer.Option("--domain-controller", "--dc")]=None,
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
        if kerberos:
            password = f"{LM_HASH}:{nt_hash}"

    if dc is not None and dc.count(".") < 2:
        error = "Please specify the FQDN of the domain controller (dc.example.com)."
        raise typer.BadParameter(error)

    if kerberos and not dc:
            error = "Domain controller must be specified when using Kerberos."
            raise typer.BadParameter(error)


    try:
        auth = "ntlm"
        if kerberos:
            prepare_kerberos(dc, username, password, nt_hash)
            auth = "kerberos"
        conn = WSManInfo(
            server=host,
            username=username,
            password=password,
            port=port,
            auth=auth)
        terminal = Terminal(conn)
        with SyncRunspacePool(conn) as rp:
            terminal.run(rp)
    except psrp.WSManAuthenticationError:
        error = "Authentication failed. Please check your credentials and try again."
        print_error(error)
    except httpcore.ReadError:
        error = "Connection timed out."
        print_error(error)
    except (OSError, FileNotFoundError, ValueError,
            NotImplementedError, KerberosError) as err:
        print_error(err)
    except Exception as err:  # noqa: BLE001
        error = f"An unexpected error occurred: {err}"
        print_error(error)

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
app.command()(cli)

if __name__ == "__main__":
    app()
