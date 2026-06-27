import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import uuid4

from user_service.domain import PredictionHistoryItem, Session, User
from user_service.repositories import (
    PredictionHistoryRepository,
    SessionRepository,
    UserRepository,
)


class ValidationError(ValueError):
    pass


class ConflictError(ValueError):
    pass


class AuthError(ValueError):
    pass


class ExternalServiceError(RuntimeError):
    pass


class PasswordHasher:
    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 150_000)
        return (
            base64.b64encode(salt).decode("ascii")
            + "$"
            + base64.b64encode(digest).decode("ascii")
        )

    def verify(self, password: str, stored_hash: str) -> bool:
        salt_value, digest_value = stored_hash.split("$", 1)
        salt = base64.b64decode(salt_value.encode("ascii"))
        expected_digest = base64.b64decode(digest_value.encode("ascii"))
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            150_000,
        )
        return hmac.compare_digest(actual_digest, expected_digest)


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._password_hasher = password_hasher

    def register(self, username: str, password: str, full_name: str) -> dict:
        username = self._normalize_username(username)
        full_name = full_name.strip()
        self._validate_password(password)
        if not full_name:
            raise ValidationError("Имя пользователя не должно быть пустым.")
        if self._user_repository.find_by_username(username):
            raise ConflictError("Пользователь с таким логином уже есть.")

        user = User(
            id=str(uuid4()),
            username=username,
            full_name=full_name,
            password_hash=self._password_hasher.hash(password),
            created_at=utc_now(),
        )
        self._user_repository.add(user)
        token = self._open_session(user.id)
        return {"token": token, "user": self._public_user(user)}

    def login(self, username: str, password: str) -> dict:
        username = self._normalize_username(username)
        user = self._user_repository.find_by_username(username)
        if not user or not self._password_hasher.verify(password, user.password_hash):
            raise AuthError("Неверный логин или пароль.")
        token = self._open_session(user.id)
        return {"token": token, "user": self._public_user(user)}

    def authenticate(self, token: str) -> User:
        if not token:
            raise AuthError("Нужна авторизация.")
        session = self._session_repository.find_by_token(token)
        if not session:
            raise AuthError("Сессия не найдена.")
        user = self._user_repository.find_by_id(session.user_id)
        if not user:
            raise AuthError("Пользователь не найден.")
        return user

    def logout(self, token: str) -> None:
        self._session_repository.delete(token)

    def _open_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._session_repository.add(
            Session(token=token, user_id=user_id, created_at=utc_now())
        )
        return token

    def _normalize_username(self, username: str) -> str:
        value = username.strip().lower()
        if len(value) < 3:
            raise ValidationError("Логин должен быть не короче 3 символов.")
        if not all(ch.isalnum() or ch in ("_", "-") for ch in value):
            raise ValidationError("Логин может содержать буквы, цифры, _ и -.")
        return value

    def _validate_password(self, password: str) -> None:
        if len(password) < 6:
            raise ValidationError("Пароль должен быть не короче 6 символов.")

    def _public_user(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "fullName": user.full_name,
            "createdAt": user.created_at,
        }


class PredictionClient(ABC):
    @abstractmethod
    def predict(self, patronymic: str) -> dict:
        raise NotImplementedError


class HttpPredictionClient(PredictionClient):
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def predict(self, patronymic: str) -> dict:
        payload = json.dumps({"patronymic": patronymic}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url}/api/predict",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            try:
                payload = json.loads(body)
                payload["_status"] = error.code
                return payload
            except json.JSONDecodeError as exc:
                raise ExternalServiceError("Сервис определения имени вернул ошибку.") from exc
        except urllib.error.URLError as exc:
            raise ExternalServiceError("Сервис определения имени недоступен.") from exc


class PredictionApplicationService:
    def __init__(
        self,
        prediction_client: PredictionClient,
        history_repository: PredictionHistoryRepository,
    ) -> None:
        self._prediction_client = prediction_client
        self._history_repository = history_repository

    def predict_for_user(self, user: User, patronymic: str) -> dict:
        result = self._prediction_client.predict(patronymic)
        if result.get("error"):
            return result
        item = PredictionHistoryItem(
            id=str(uuid4()),
            user_id=user.id,
            patronymic=result.get("patronymic") or patronymic,
            predicted_name=result.get("bestName"),
            confidence=float(result.get("confidence", 0)),
            created_at=utc_now(),
        )
        self._history_repository.add(item)
        result["historyItem"] = item.to_dict()
        return result

    def list_history(self, user: User) -> list[dict]:
        return [item.to_dict() for item in self._history_repository.list_by_user_id(user.id)]


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
