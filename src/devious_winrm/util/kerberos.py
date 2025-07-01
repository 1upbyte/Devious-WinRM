"""Utility functions for Kerberos authentication."""
import os
import tempfile
from textwrap import dedent

from impacket.krb5 import constants
from impacket.krb5.ccache import CCache
from impacket.krb5.kerberosv5 import getKerberosTGT
from impacket.krb5.types import Principal
from prompt_toolkit import print_formatted_text as print_ft


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

    print_ft("Using Kerberos!")

    tgt, _, old_session_key, session_key = _get_tgt(
        username=username, password=password, nt_hash=nt_hash, domain=realm)

    ccache: CCache = CCache()
    ccache.fromTGT(tgt, old_session_key, session_key)

    with tempfile.NamedTemporaryFile(mode="wb+", delete=False) as f:
        f.write(ccache.getData())
        f.flush()
        os.environ["KRB5CCNAME"] = f.name

def _get_tgt(
        username: str = None,
        password: str = None,
        lm_hash: str = None,
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
        if password is not None:
            error = "Password and NTLM hash cannot be used together."
            raise ValueError(error)
        if lm_hash is None:
            lm_hash: str = "aad3b435b51404eeaad3b435b51404ee"


    user = Principal(username, type=constants.PrincipalNameType.NT_PRINCIPAL.value)



    return getKerberosTGT(
        clientName=user,
        password=password,
        lmhash=lm_hash,
        nthash=nt_hash,
        domain=domain)
