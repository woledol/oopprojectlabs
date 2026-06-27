from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: str
    username: str
    full_name: str
    password_hash: str
    created_at: str


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
    created_at: str


@dataclass(frozen=True)
class PredictionHistoryItem:
    id: str
    user_id: str
    patronymic: str
    predicted_name: str | None
    confidence: float
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "userId": self.user_id,
            "patronymic": self.patronymic,
            "predictedName": self.predicted_name,
            "confidence": self.confidence,
            "createdAt": self.created_at,
        }
