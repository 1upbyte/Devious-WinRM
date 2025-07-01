"""Entry point for the CLI application."""
import argparse

from psrp import SyncRunspacePool, WSManInfo

from devious_winrm.app import Terminal
from devious_winrm.util.kerberos import prepare_kerberos

LM_HASH: str = "aad3b435b51404eeaad3b435b51404ee"

def cli() -> None:
    """Manage CLI arguments."""
    print("""
-- Devious WinRM CLI --
    """)
    parser = argparse.ArgumentParser(description="Devious WinRM CLI")
    parser.add_argument("host", help="Target host")
    parser.add_argument("-u", "--username", help="Username", default=None)
    parser.add_argument("-p", "--password", help="Password", default=None)
    parser.add_argument("-P", "--port", type=int, help="Port", default=5985)
    parser.add_argument("-a", "--auth", help="Authentication method", default="ntlm",
                        choices=["basic", "certificate", "credssp", "kerberos", "negotiate", "ntlm"])
    parser.add_argument("-H", "--hash", dest="nt_hash", help="NTLM hash", default=None)
    parser.add_argument("--dc", "--domain-controller", dest="dc", help="Domain controller (FQDN)", default=None)

    args = parser.parse_args()

    host = args.host
    username = args.username
    password = args.password
    port = args.port
    auth = args.auth
    nt_hash = args.nt_hash
    dc = args.dc

    if nt_hash is not None:
        if ":" in nt_hash:  # In case user provides lm_hash:nt_hash
            nt_hash = nt_hash.split(":")[1]
        if len(nt_hash) != 32:
            parser.error("NTLM hash must be 32 characters long.")
        if password is not None:
            parser.error("Password and NTLM hash cannot be used together.")
        if auth != "kerberos":
            password = f"{LM_HASH}:{nt_hash}"

    if dc is not None and dc.count(".") < 2:
        parser.error("Please specify the FQDN of the domain controller (dc.example.com).")

    if auth == "kerberos":
        if not dc:
            parser.error("Domain controller must be specified when using Kerberos.")
        prepare_kerberos(dc, username, password, nt_hash)

    conn = WSManInfo(
        server=host,
        username=username,
        password=password,
        port=port,
        auth=auth,
    )

    try:
        terminal = Terminal(conn)
        with SyncRunspacePool(conn) as rp:
            terminal.run(rp)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Exiting the application...")
        parser.exit(1)

if __name__ == "__main__":
    cli()
