import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from predictor_service.domain import PatronymicRequest
from predictor_service.services import PatronymicAnalyzer, PatronymicValidationError


class PredictorRequestHandler(BaseHTTPRequestHandler):
    analyzer = PatronymicAnalyzer()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "predictor-service"})
            return
        self._send_json(404, {"error": "not_found", "message": "Маршрут не найден."})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/predict":
            self._send_json(404, {"error": "not_found", "message": "Маршрут не найден."})
            return

        try:
            body = self._read_json()
            patronymic = str(body.get("patronymic", ""))
            result = self.analyzer.predict(PatronymicRequest(patronymic=patronymic))
            status = 200 if result.best_name else 422
            self._send_json(status, result.to_dict())
        except PatronymicValidationError as error:
            self._send_json(400, {"error": "validation_error", "message": str(error)})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json", "message": "Некорректный JSON."})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        if not raw_body:
            return {}
        return json.loads(raw_body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"[predictor-service] {self.address_string()} - {format % args}")
