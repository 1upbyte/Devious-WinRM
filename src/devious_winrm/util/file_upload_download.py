"""Handle uploading and downloading files using HTTP."""

import errno
import http.server
import socket
from functools import partial
from pathlib import Path
from random import randint
from socketserver import TCPServer
from threading import Event, Thread

LOWER_PORT_BOUND = 1024
UPPER_PORT_BOUND = 65535
MAX_ATTEMPTS = 3
"""Number of attempts to try uploading before failing."""

class SingleFileGETHandler(http.server.SimpleHTTPRequestHandler):
    """Serve a single file."""

    def __init__(self, file: bytes, file_size: int,
                 request: socket.socket,
                 client_address: tuple,
                 server: TCPServer) -> None:
        """Set the file to be served."""
        self.file = file
        self.file_size = str(file_size)
        super().__init__(request, client_address, server)

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests by serving the predefined HTML_CONTENT."""
        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("Content-Length", self.file_size)
        self.end_headers()

        self.wfile.write(self.file)

class MaxAttemptsExceededError(Exception):
    """Exception for too many attempts."""

def run_server(file_path: Path, server_active: Event) -> None:
    """Run the HTTP server.

    The server will stop after handling the first GET request.
    """
    port = randint(LOWER_PORT_BOUND, UPPER_PORT_BOUND)  # noqa: S311

    with file_path.open(mode="rb") as file:
        file_contents = file.read()
        file_size = file.tell()

        GETHandler = partial(SingleFileGETHandler, file_contents, file_size)  # noqa: N806
        with TCPServer(("", port),
                        RequestHandlerClass=GETHandler,
                        bind_and_activate=False) as tcp_socket:
            tcp_socket.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_socket.server_bind()
            tcp_socket.server_activate()
            print(f"Running on http://localhost:{port}")
            server_active.set()
            tcp_socket.handle_request()




def upload_file(file_path: Path) -> None:
    """Upload a file to the remote server via HTTP.

    Returns:
        str: Path on the remote host where the file was uploaded.

    """
    attempts = 0
    while attempts < MAX_ATTEMPTS:
        file_path = file_path.expanduser().resolve()
        try:
            server_active = Event()
            http_server = Thread(target=run_server,
                                 args=(file_path, server_active),
                                 name="http-server")
            http_server.start()
            server_active.wait()
            http_server.join()
        except OSError as e:
            # In case port is already being used, try again
            if e.errno == errno.EADDRINUSE:
                attempts += 1
                continue
            raise
        break

    error = f"Too many attempts failed when uploading {file_path}"
    raise MaxAttemptsExceededError(error)

if __name__ == "__main__":
    upload_file(Path("~/test/test.txt"))
