"""Original code by github/jborean93/pypsrp"""
import threading
import typing as t
import uuid

from psrp import SyncConnection, SyncEventCallable
from psrp._connection.wsman import (
    SyncWSManConnection,
    WSManInfo,
    _process_enumeration_response,
)
from psrp._winrs import WinRS, enumerate_winrs, receive_winrs_enumeration
from psrp._wsman import WSMan
from psrpcore import ClientRunspacePool

from devious_winrm.psrp_fix._io.wsman import SyncWSManHTTPFix as SyncWSManHTTP

if t.TYPE_CHECKING:
    from psrp._connection.connection import EnumerationRunspaceResult

PS_RESOURCE_PREFIX = "http://schemas.microsoft.com/powershell"

class WSManInfoFix(WSManInfo):
    def enumerate_sync(self) -> t.Iterator["EnumerationRunspaceResult"]:
        print("Hello from _connection!")
        connection = SyncWSManHTTP(self.connection_info)
        wsman = WSMan(self.connection_info.connection_uri)

        enumerate_winrs(wsman)
        resp = connection.post(wsman.data_to_send())
        shell_enumeration = wsman.receive_data(resp)

        shells = receive_winrs_enumeration(wsman, shell_enumeration)[0]
        for shell in shells:
            if not shell.resource_uri.startswith(f"{PS_RESOURCE_PREFIX}/"):
                continue

            enumerate_winrs(
                wsman,
                resource_uri="http://schemas.microsoft.com/wbem/wsman/1/windows/shell/Command",
                selector_filter=shell.selector_set,
            )
            resp = connection.post(wsman.data_to_send())
            yield _process_enumeration_response(self, shell, resp)
    
    def create_sync(
        self,
        pool: ClientRunspacePool,
        callback: SyncEventCallable,
    ) -> "SyncConnection":
        return SyncWSManConnectionFix(pool, callback, self, self._new_winrs_shell(pool))


class SyncWSManConnectionFix(SyncWSManConnection):
    """Sync Connection for WSMan."""

    def __init__(
        self,
        pool: ClientRunspacePool,
        callback: SyncEventCallable,
        info: WSManInfo,
        shell: WinRS,
    ) -> None:
        super(SyncWSManConnection, self).__init__(pool, callback)

        self._info = info
        self._connection = SyncWSManHTTP(self._info.connection_info)

        self._listener_tasks: t.Dict[t.Optional[uuid.UUID], threading.Thread] = {}
        self._stopped_pipelines: t.List[uuid.UUID] = []
        self._shell = shell
        self._pipeline_lookup: t.Dict[uuid.UUID, uuid.UUID] = {}


