from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum


class Role(StrEnum):
    CLIENT = "CLIENT"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class CarStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RENTED = "RENTED"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"


class RentalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class CarCategory(StrEnum):
    ECONOMY = "ECONOMY"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    SPORT = "SPORT"


@dataclass(frozen=True)
class User:
    id: int
    username: str
    birth_date: date
    driving_license_issue_date: date
    roles: frozenset[Role]


@dataclass(frozen=True)
class Car:
    id: int
    vin: str
    brand: str
    model: str
    category: CarCategory
    daily_rate: int
    status: CarStatus


@dataclass(frozen=True)
class Rental:
    id: int
    user_id: int
    car_id: int
    start_date: date
    end_date: date
    status: RentalStatus
    created_at: datetime


@dataclass(frozen=True)
class Contract:
    id: int
    rental_id: int
    base_price: int
    penalty: int
    total_price: int
    created_at: datetime
    completed_at: datetime | None = None


def now_utc() -> datetime:
    return datetime.now(UTC)


def full_years_between(start: date, end: date) -> int:
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


def rental_days(start: date, end: date) -> int:
    return (end - start).days + 1


def dates_intersect(left_start: date, left_end: date, right_start: date, right_end: date) -> bool:
    return left_start <= right_end and right_start <= left_end
