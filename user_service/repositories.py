import json
from abc import ABC, abstractmethod
from pathlib import Path

from user_service.domain import PredictionHistoryItem, Session, User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_username(self, username: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    def find_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError


class JsonUserRepository(UserRepository):
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, user: User) -> None:
        data = self._load()
        data["users"].append(
            {
                "id": user.id,
                "username": user.username,
                "fullName": user.full_name,
                "passwordHash": user.password_hash,
                "createdAt": user.created_at,
            }
        )
        self._save(data)

    def find_by_username(self, username: str) -> User | None:
        normalized = username.lower()
        for raw_user in self._load()["users"]:
            if raw_user["username"].lower() == normalized:
                return self._to_user(raw_user)
        return None

    def find_by_id(self, user_id: str) -> User | None:
        for raw_user in self._load()["users"]:
            if raw_user["id"] == user_id:
                return self._to_user(raw_user)
        return None

    def _load(self) -> dict:
        if not self._file_path.exists():
            return {"users": []}
        with self._file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, data: dict) -> None:
        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _to_user(self, raw_user: dict) -> User:
        return User(
            id=raw_user["id"],
            username=raw_user["username"],
            full_name=raw_user["fullName"],
            password_hash=raw_user["passwordHash"],
            created_at=raw_user["createdAt"],
        )


class SessionRepository(ABC):
    @abstractmethod
    def add(self, session: Session) -> None:
        raise NotImplementedError

    @abstractmethod
    def find_by_token(self, token: str) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, token: str) -> None:
        raise NotImplementedError


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def add(self, session: Session) -> None:
        self._sessions[session.token] = session

    def find_by_token(self, token: str) -> Session | None:
        return self._sessions.get(token)

    def delete(self, token: str) -> None:
        self._sessions.pop(token, None)


class PredictionHistoryRepository(ABC):
    @abstractmethod
    def add(self, item: PredictionHistoryItem) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_by_user_id(self, user_id: str) -> list[PredictionHistoryItem]:
        raise NotImplementedError


class JsonPredictionHistoryRepository(PredictionHistoryRepository):
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, item: PredictionHistoryItem) -> None:
        data = self._load()
        data["items"].append(item.to_dict())
        self._save(data)

    def list_by_user_id(self, user_id: str) -> list[PredictionHistoryItem]:
        items = []
        for raw_item in self._load()["items"]:
            if raw_item["userId"] == user_id:
                items.append(self._to_item(raw_item))
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def _load(self) -> dict:
        if not self._file_path.exists():
            return {"items": []}
        with self._file_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save(self, data: dict) -> None:
        with self._file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _to_item(self, raw_item: dict) -> PredictionHistoryItem:
        return PredictionHistoryItem(
            id=raw_item["id"],
            user_id=raw_item["userId"],
            patronymic=raw_item["patronymic"],
            predicted_name=raw_item["predictedName"],
            confidence=float(raw_item["confidence"]),
            created_at=raw_item["createdAt"],
        )
