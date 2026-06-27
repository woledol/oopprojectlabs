from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse

from rental_service.domain import CarCategory, CarStatus, Role, User
from rental_service.repositories import (
    CarRepository,
    ContractRepository,
    RentalRepository,
    UserRepository,
)
from rental_service.schemas import (
    CarCreateRequest,
    CarResponse,
    CarStatusRequest,
    CompleteRentalRequest,
    ContractResponse,
    RentalCreateRequest,
    RentalResponse,
    RentalResultResponse,
    UserCreateRequest,
    UserResponse,
    UserRolesRequest,
)
from rental_service.services import (
    CarService,
    RentalResult,
    RentalService,
    ServiceError,
    UserService,
)


@dataclass(frozen=True)
class AppContainer:
    users: UserService
    cars: CarService
    rentals: RentalService


def create_container(seed: bool = True) -> AppContainer:
    users = UserRepository()
    cars = CarRepository()
    rentals = RentalRepository()
    contracts = ContractRepository()
    if seed:
        users.add("admin", date(1980, 1, 1), date(2000, 1, 1), frozenset({Role.ADMIN}))
        users.add("manager", date(1985, 1, 1), date(2005, 1, 1), frozenset({Role.MANAGER}))
        users.add("client", date(1995, 1, 1), date(2015, 1, 1), frozenset({Role.CLIENT}))
        users.add(
            "client_manager",
            date(1990, 1, 1),
            date(2010, 1, 1),
            frozenset({Role.CLIENT, Role.MANAGER}),
        )
    return AppContainer(
        users=UserService(users),
        cars=CarService(cars),
        rentals=RentalService(cars, rentals, contracts),
    )


def create_app(seed: bool = True) -> FastAPI:
    app = FastAPI(title="Car Rental Lab 2")
    app.state.container = create_container(seed=seed)

    @app.exception_handler(ServiceError)
    async def handle_service_error(_request: Request, error: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.message})

    app.include_router(router)
    return app


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


ContainerDep = Annotated[AppContainer, Depends(get_container)]
UserIdHeader = Annotated[int, Header(alias="X-User-Id")]
IncludeUnavailableQuery = Annotated[bool, Query()]


def get_current_user(
    x_user_id: UserIdHeader,
    container: ContainerDep,
) -> User:
    return container.users.authenticate(x_user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/cars", response_model=list[CarResponse])
def list_cars(
    container: ContainerDep,
    status: CarStatus | None = None,
    category: CarCategory | None = None,
    brand: str | None = None,
    include_unavailable: IncludeUnavailableQuery = False,
) -> list[CarResponse]:
    cars = container.cars.list_cars(
        status=status,
        category=category,
        brand=brand,
        include_unavailable=include_unavailable,
    )
    return [CarResponse.model_validate(car) for car in cars]


@router.post("/cars", response_model=CarResponse, status_code=201)
def add_car(
    request: CarCreateRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> CarResponse:
    car = container.cars.add_car(
        actor,
        request.vin,
        request.brand,
        request.model,
        request.category,
        request.daily_rate,
    )
    return CarResponse.model_validate(car)


@router.patch("/cars/{car_id}/status", response_model=CarResponse)
def update_car_status(
    car_id: int,
    request: CarStatusRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> CarResponse:
    car = container.cars.update_status(actor, car_id, request.status)
    return CarResponse.model_validate(car)


@router.get("/users", response_model=list[UserResponse])
def list_users(
    actor: CurrentUser,
    container: ContainerDep,
) -> list[UserResponse]:
    users = container.users.list_users(actor)
    return [UserResponse.model_validate(user) for user in users]


@router.post("/users", response_model=UserResponse, status_code=201)
def add_user(
    request: UserCreateRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> UserResponse:
    user = container.users.create_user(
        actor,
        request.username,
        request.birth_date,
        request.driving_license_issue_date,
        frozenset(request.roles),
    )
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}/roles", response_model=UserResponse)
def update_user_roles(
    user_id: int,
    request: UserRolesRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> UserResponse:
    user = container.users.update_roles(actor, user_id, frozenset(request.roles))
    return UserResponse.model_validate(user)


@router.get("/rentals", response_model=list[RentalResponse])
def list_rentals(
    actor: CurrentUser,
    container: ContainerDep,
) -> list[RentalResponse]:
    rentals = container.rentals.list_rentals(actor)
    return [RentalResponse.model_validate(rental) for rental in rentals]


@router.post("/rentals", response_model=RentalResultResponse, status_code=201)
def create_rental(
    request: RentalCreateRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> RentalResultResponse:
    result = container.rentals.create_rental(
        actor,
        request.car_id,
        request.start_date,
        request.end_date,
    )
    return rental_result_response(result)


@router.patch("/rentals/{rental_id}/approve", response_model=RentalResultResponse)
def approve_rental(
    rental_id: int,
    actor: CurrentUser,
    container: ContainerDep,
) -> RentalResultResponse:
    result = container.rentals.approve_rental(actor, rental_id)
    return rental_result_response(result)


@router.patch("/rentals/{rental_id}/reject", response_model=RentalResponse)
def reject_rental(
    rental_id: int,
    actor: CurrentUser,
    container: ContainerDep,
) -> RentalResponse:
    rental = container.rentals.reject_rental(actor, rental_id)
    return RentalResponse.model_validate(rental)


@router.patch("/rentals/{rental_id}/complete", response_model=RentalResultResponse)
def complete_rental(
    rental_id: int,
    request: CompleteRentalRequest,
    actor: CurrentUser,
    container: ContainerDep,
) -> RentalResultResponse:
    result = container.rentals.complete_rental(
        actor,
        rental_id,
        request.return_date,
        request.damaged,
    )
    return rental_result_response(result)


@router.get("/contracts", response_model=list[ContractResponse])
def list_contracts(
    actor: CurrentUser,
    container: ContainerDep,
) -> list[ContractResponse]:
    contracts = container.rentals.get_contracts(actor)
    return [ContractResponse.model_validate(contract) for contract in contracts]


def rental_result_response(result: RentalResult) -> RentalResultResponse:
    return RentalResultResponse(
        rental=RentalResponse.model_validate(result.rental),
        contract=(
            ContractResponse.model_validate(result.contract)
            if result.contract is not None
            else None
        ),
    )


app = create_app()
