import psrp
from psrp import SyncRunspacePool, WSManInfo

conn = WSManInfo(
        server="mushroom.star",
        username="mario",
        password="star123",
        port=5985,
        auth="ntlm",
    )

with SyncRunspacePool(conn) as rp:
    ps = psrp.SyncPowerShell(rp)
    output = ps.add_script("pwd").invoke()[0]
    print(output)
