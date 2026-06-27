from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from rental_service.domain import CarCategory, CarStatus, RentalStatus, Role


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=1)
    birth_date: date
    driving_license_issue_date: date
    roles: set[Role]

    @field_validator("roles")
    @classmethod
    def roles_must_not_be_empty(cls, roles: set[Role]) -> set[Role]:
        if not roles:
            raise ValueError("roles must not be empty")
        return roles


class UserRolesRequest(BaseModel):
    roles: set[Role]

    @field_validator("roles")
    @classmethod
    def roles_must_not_be_empty(cls, roles: set[Role]) -> set[Role]:
        if not roles:
            raise ValueError("roles must not be empty")
        return roles


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    birth_date: date
    driving_license_issue_date: date
    roles: frozenset[Role]


class CarCreateRequest(BaseModel):
    vin: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    category: CarCategory
    daily_rate: int = Field(gt=0)


class CarStatusRequest(BaseModel):
    status: CarStatus


class CarResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vin: str
    brand: str
    model: str
    category: CarCategory
    daily_rate: int
    status: CarStatus


class RentalCreateRequest(BaseModel):
    car_id: int = Field(gt=0)
    start_date: date
    end_date: date


class CompleteRentalRequest(BaseModel):
    return_date: date
    damaged: bool = False


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rental_id: int
    base_price: int
    penalty: int
    total_price: int
    created_at: datetime
    completed_at: datetime | None


class RentalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    car_id: int
    start_date: date
    end_date: date
    status: RentalStatus
    created_at: datetime


class RentalResultResponse(BaseModel):
    rental: RentalResponse
    contract: ContractResponse | None = None
