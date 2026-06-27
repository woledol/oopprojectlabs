import os
from http.server import ThreadingHTTPServer

from user_service.web import UserRequestHandler


def run() -> None:
    port = int(os.getenv("USER_SERVICE_PORT", "8000"))
    server = ThreadingHTTPServer(("localhost", port), UserRequestHandler)
    print(f"user-service started on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
