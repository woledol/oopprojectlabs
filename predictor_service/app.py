import os
from http.server import ThreadingHTTPServer

from predictor_service.web import PredictorRequestHandler


def run() -> None:
    port = int(os.getenv("PREDICTOR_PORT", "8001"))
    server = ThreadingHTTPServer(("localhost", port), PredictorRequestHandler)
    print(f"predictor-service started on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
