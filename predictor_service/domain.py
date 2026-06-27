from dataclasses import dataclass
from enum import Enum
from typing import List


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PatronymicRequest:
    patronymic: str


@dataclass(frozen=True)
class NameCandidate:
    name: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class PredictionResult:
    patronymic: str
    gender: Gender
    candidates: List[NameCandidate]

    @property
    def best_name(self) -> str | None:
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda candidate: candidate.confidence).name

    @property
    def confidence(self) -> float:
        if not self.candidates:
            return 0.0
        return max(candidate.confidence for candidate in self.candidates)

    def to_dict(self) -> dict:
        return {
            "patronymic": self.patronymic,
            "gender": self.gender.value,
            "bestName": self.best_name,
            "confidence": self.confidence,
            "candidates": [
                {
                    "name": candidate.name,
                    "confidence": candidate.confidence,
                    "reason": candidate.reason,
                }
                for candidate in self.candidates
            ],
        }
