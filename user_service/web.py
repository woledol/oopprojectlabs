import json
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

from user_service.repositories import (
    InMemorySessionRepository,
    JsonPredictionHistoryRepository,
    JsonUserRepository,
)
from user_service.services import (
    AuthError,
    AuthService,
    ConflictError,
    ExternalServiceError,
    HttpPredictionClient,
    PasswordHasher,
    PredictionApplicationService,
    ValidationError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
DATA_DIR = PROJECT_ROOT / "data"


class UserRequestHandler(BaseHTTPRequestHandler):
    user_repository = JsonUserRepository(DATA_DIR / "users.json")
    session_repository = InMemorySessionRepository()
    history_repository = JsonPredictionHistoryRepository(DATA_DIR / "history.json")
    auth_service = AuthService(
        user_repository=user_repository,
        session_repository=session_repository,
        password_hasher=PasswordHasher(),
    )
    prediction_service = PredictionApplicationService(
        prediction_client=HttpPredictionClient(
            os.getenv("PREDICTOR_URL", "http://localhost:8001")
        ),
        history_repository=history_repository,
    )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "user-service"})
            return
        if path == "/api/me":
            self._handle_me()
            return
        if path == "/api/history":
            self._handle_history()
            return
        self._serve_static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/register":
            self._handle_register()
            return
        if path == "/api/login":
            self._handle_login()
            return
        if path == "/api/logout":
            self._handle_logout()
            return
        if path == "/api/predict":
            self._handle_predict()
            return
        self._send_json(404, {"error": "not_found", "message": "Маршрут не найден."})

    def _handle_register(self) -> None:
        try:
            body = self._read_json()
            result = self.auth_service.register(
                username=str(body.get("username", "")),
                password=str(body.get("password", "")),
                full_name=str(body.get("fullName", "")),
            )
            self._send_json(201, result)
        except ValidationError as error:
            self._send_json(400, {"error": "validation_error", "message": str(error)})
        except ConflictError as error:
            self._send_json(409, {"error": "conflict", "message": str(error)})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json", "message": "Некорректный JSON."})

    def _handle_login(self) -> None:
        try:
            body = self._read_json()
            result = self.auth_service.login(
                username=str(body.get("username", "")),
                password=str(body.get("password", "")),
            )
            self._send_json(200, result)
        except (ValidationError, AuthError) as error:
            self._send_json(401, {"error": "auth_error", "message": str(error)})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json", "message": "Некорректный JSON."})

    def _handle_logout(self) -> None:
        token = self._bearer_token()
        self.auth_service.logout(token)
        self._send_json(200, {"status": "ok"})

    def _handle_me(self) -> None:
        try:
            user = self.auth_service.authenticate(self._bearer_token())
            self._send_json(
                200,
                {
                    "id": user.id,
                    "username": user.username,
                    "fullName": user.full_name,
                    "createdAt": user.created_at,
                },
            )
        except AuthError as error:
            self._send_json(401, {"error": "auth_error", "message": str(error)})

    def _handle_predict(self) -> None:
        try:
            user = self.auth_service.authenticate(self._bearer_token())
            body = self._read_json()
            result = self.prediction_service.predict_for_user(
                user=user,
                patronymic=str(body.get("patronymic", "")),
            )
            status = int(result.pop("_status", 200 if result.get("bestName") else 422))
            self._send_json(status, result)
        except AuthError as error:
            self._send_json(401, {"error": "auth_error", "message": str(error)})
        except ExternalServiceError as error:
            self._send_json(503, {"error": "external_service_error", "message": str(error)})
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json", "message": "Некорректный JSON."})

    def _handle_history(self) -> None:
        try:
            user = self.auth_service.authenticate(self._bearer_token())
            self._send_json(200, {"items": self.prediction_service.list_history(user)})
        except AuthError as error:
            self._send_json(401, {"error": "auth_error", "message": str(error)})

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        if not raw_body:
            return {}
        return json.loads(raw_body)

    def _bearer_token(self) -> str:
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            return header.removeprefix("Bearer ").strip()
        return ""

    def _serve_static(self, path: str) -> None:
        if path == "/":
            target = STATIC_DIR / "index.html"
        else:
            target = STATIC_DIR / path.lstrip("/")
        resolved_static_dir = STATIC_DIR.resolve()
        resolved_target = target.resolve()
        if (
            not resolved_target.exists()
            or not resolved_target.is_file()
            or not resolved_target.is_relative_to(resolved_static_dir)
        ):
            self._send_json(404, {"error": "not_found", "message": "Файл не найден."})
            return

        content_type = "text/plain; charset=utf-8"
        if target.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        elif target.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif target.suffix == ".js":
            content_type = "text/javascript; charset=utf-8"

        body = resolved_target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"[user-service] {self.address_string()} - {format % args}")
