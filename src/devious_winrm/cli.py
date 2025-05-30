"""Entry point for the CLI application."""
from typing import Annotated, Optional

import typer
from psrp import WSManInfo

from devious_winrm.app import main
from devious_winrm.util.kerberos import prepare_kerberos

LM_HASH: str = "aad3b435b51404eeaad3b435b51404ee"

def cli(host: Annotated[str, typer.Argument()],  # noqa: PLR0913
        username: Annotated[str, typer.Option("-u", "--username")] = None,
        password: Annotated[str, typer.Option("-p", "--password")] = None,
        port: Annotated[int, typer.Option("-P", "--port")] = 5985,
        auth: Annotated[str, typer.Option("-a", "--auth")] = "ntlm",
        nt_hash: Annotated[str, typer.Option("-H", "--hash")] = None,
        dc: Annotated[Optional[str], typer.Option("--dc", "--domain-controller")]=None,
) -> None:
    """Parse command line arguments and forward them to the terminal."""
    if auth not in ["basic", "certificate", "credssp", "kerberos", "negotiate", "ntlm"]:
        error = ("Invalid authentication method. Choose from: basic, certificate, "
        "credssp, kerberos, negotiate, ntlm.")
        raise typer.BadParameter(error)

    if nt_hash is not None:
        if ":" in nt_hash: # In case user provides lm_hash:nt_hash
            nt_hash = nt_hash.split(":")[1]
        if len(nt_hash) != 32:
            error = "NTLM hash must be 32 characters long."
            raise typer.BadParameter(error)
        if password is not None:
            error = "Password and NTLM hash cannot be used together."
            raise ValueError(error)
        if auth != "kerberos":
            password = f"{LM_HASH}:{nt_hash}"

    if dc is not None and dc.count(".") < 2:
        error = "Please specify the FQDN of the domain controller (dc.example.com)."
        raise typer.BadParameter(error)

    if auth == "kerberos":
        if not dc:
            error = "Domain controller must be specified when using Kerberos."
            raise typer.BadParameter(error)
        prepare_kerberos(dc, username, password, nt_hash)

    """ Main function to run the terminal """
    conn = WSManInfo(
        server=host,
        username=username,
        password=password,
        port=port,
        auth=auth,
    )
    main(conn)

app = typer.Typer()
app.command()(cli)

if __name__ == "__main__":
    app()
