"""Utility functions for Kerberos authentication."""
import os
import re
import subprocess
import tempfile
from datetime import datetime
from textwrap import dedent
from typing import List

from impacket.krb5 import constants
from impacket.krb5.ccache import CCache
from impacket.krb5.kerberosv5 import getKerberosTGT
from impacket.krb5.types import Principal

from devious_winrm.app import Terminal
from devious_winrm.util.printers import print_info

LM_HASH = "aad3b435b51404eeaad3b435b51404ee"

def has_cached_credential(realm: str) -> bool:
    """Check if a (valid) Kerberos TGT is already cached."""
    if os.name == "nt":
        parse_klist = parse_nt_klist
        cmd = "C:/Windows/System32/klist.exe"
    else:
        parse_klist = parse_mit_klist
        cmd = "klist"

    try:
        output = subprocess.run([cmd], capture_output=True, text=True, check=True)  # noqa: S603
        output: str = output.stdout
    except subprocess.CalledProcessError as err:
        error = "Running 'klist' failed! Is Kerberos installed?"
        raise OSError(error) from err

    tickets = parse_klist(output)
    date_format = "%m/%d/%Y %H:%M:%S"
    for ticket in tickets:
        server_valid = False
        expired = True

        if ticket["expiration_time"] is None or ticket["server"] is None:
            continue

        if f"krbtgt/{realm}" in ticket["server"]:
            server_valid = True
        if ticket["expiration_time"] is not None:
            # Windows prints the expiration time in the local timezone.
            ticket_time = datetime.strptime(ticket["expiration_time"], date_format)  # noqa: DTZ007
            if datetime.now() < ticket_time:  # noqa: DTZ005
                expired = False
        if server_valid and not expired:
            return True
    return False

def prepare_kerberos(
        dc: str,
        username: str = None,
        password: str = None,
        nt_hash: str = None) -> None:
    """Prepare the Kerberos configuration."""
    dc: str = dc.upper()
    fqdn_array: list[str] = dc.split(".")
    if len(fqdn_array) < 3:
        error = "Domain controller must be fully-qualified-domain name (dc.example.com)!"  # noqa: E501
        raise ValueError(error)
    realm: str = fqdn_array[-2] + "." + fqdn_array[-1]

    is_cred_cached = has_cached_credential(realm)
    print_info("Using Kerberos!")
    if os.name == "nt":
        if is_cred_cached:
            return
        error = "No cached Kerberos tickets. Rerun Devious-WinRM using 'runas /netonly'."
        raise OSError(error)

    configure_krb(realm, dc)

    if not is_cred_cached:
        tgt, _, old_session_key, session_key = _get_tgt(
            username=username, password=password, nt_hash=nt_hash, domain=realm)

        ccache = CCache()
        ccache.fromTGT(tgt, old_session_key, session_key)

        with tempfile.NamedTemporaryFile(mode="wb+", delete=False) as f:
            f.write(ccache.getData())
            f.flush()
            os.environ["KRB5CCNAME"] = f.name

def _get_tgt(
        username: str = None,
        password: str = None,
        nt_hash: str = None,
        domain: str = None) -> None:
    """Get a TGT (Ticket Granting Ticket) for Kerberos authentication."""
    if username is None:
        error = "No cached Kerberos ticket. A username is required."
        raise ValueError(error)
    if password is None and nt_hash is None:
        error = "No cached Kerberos ticket. A password, NTLM hash or AES key is required."  # noqa: E501
        raise ValueError(error)

    if nt_hash is not None:
        lm_hash: str = LM_HASH

    user = Principal(username, type=constants.PrincipalNameType.NT_PRINCIPAL.value)



    return getKerberosTGT(
        clientName=user,
        password=password,
        lmhash=lm_hash,
        nthash=nt_hash,
        domain=domain)

def parse_nt_klist(output: str) -> list[dict[str, str]]:
    """Parse the output of 'klist' on Windows.

    Returns:
        List: An array of dicts (one per ticket) with a server & expiration_time field.

    """
    tickets = []
    # Split the output into individual ticket blocks
    ticket_blocks = re.split(r"#\d+>", output)[1:]

    for block in ticket_blocks:
        ticket_info = {}
        lines = block.strip().split("\n")

        found_server = False
        found_end_time = False

        for _line in lines:
            line = _line.strip()
            if line: # Ensure the line is not empty
                if line.startswith("Server:"):
                    ticket_info["server"] = line.split("Server: ")[1].strip()
                    found_server = True
                elif line.startswith("End Time:"):
                    # Extract the End Time and remove "(local)"
                    end_time_raw = line.split("End Time: ")[1].strip()
                    ticket_info["expiration_time"] = end_time_raw.replace(" (local)", "")
                    found_end_time = True

            if found_server and found_end_time:
                break # Exit the inner loop for this block

        if (ticket_info["server"] is not None 
            and ticket_info["expiration_time"] is not None):
            tickets.append(ticket_info)

    return tickets
def parse_mit_klist(output: str) -> list[dict[str, str]]:
    """Parse the output of 'klist' of MIT Kerberos (non-Windows).

    Returns:
        List: An array of dicts (one per ticket) with a server & expiration_time field.

    """
    error = "TODO"
    raise NotImplementedError(error)
def configure_krb(realm, dc):
    """Set the Kerberos config file for non-Windows systems."""
    krb5_conf_data: str = dedent(f"""
    [libdefaults]
        default_realm = {realm}

    [realms]
        {realm} = {{
            kdc = {dc}
            admin_server = {dc}
        }}

    [domain_realm]
        .{realm} = {realm}
        {realm} = {realm}
    """)

    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write(krb5_conf_data)
        f.flush()
        os.environ["KRB5_CONFIG"] = f.name
