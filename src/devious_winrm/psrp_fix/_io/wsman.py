"""Original code by github/jborean93/pypsrp"""
import threading
import typing as t

import httpcore
import httpx
from psrp import WSManHTTPError
from psrp._io.wsman import SyncWSManHTTP, WSManConnectionData


class SyncWSManHTTPFix(SyncWSManHTTP):
    def __init__(
        self,
        connection_info: WSManConnectionData,
    ) -> None:
        self.connection_info = connection_info
        super().__init__(connection_info)

    def post(
        self,
        data: bytes,
        data_sent: t.Optional[threading.Event] = None,
    ) -> bytes:
        """POST WSMan data to the endpoint.

        The WSMan envelope is sent as a HTTP POST request to the endpoint
        specified. This method should deal with the encryption required for a
        request if it is necessary.

        Args:
            data: The WSMan envelope to send to the endpoint.
            data_sent: An event that is set once the client has sent the body.

        Returns:
            bytes: The WSMan response.
        """
        ext: t.Optional[t.Dict[str, t.Any]] = None
        if data_sent:

            def trace(event_name: str, info: t.Dict[str, t.Any]) -> None:
                if event_name == "http11.send_request_body.complete" and data_sent:
                    data_sent.set()

            ext = {"trace": trace}

        with self._conn_lock:
            content = None
            attempt = 1
            while attempt <= 5:
                try:
                    response = self._http.post(
                        self.connection_uri,
                        content=data,
                        headers={
                            "Content-Type": "application/soap+xml;charset=UTF-8",
                        },
                        extensions=ext,
                    )
                    content = response.read()
                    break
                except (httpcore.RemoteProtocolError, httpcore.ReadTimeout):
                    self.__init__(self.connection_info)
                finally:
                    attempt += 1
        # A WSManFault has more information that the WSMan state machine can
        # handle with better context so we ignore those.
        if response.status_code != 200 and (not content or b"wsmanfault" not in content):
            try:
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise WSManHTTPError(str(e), response.status_code) from e

        return content or b""
