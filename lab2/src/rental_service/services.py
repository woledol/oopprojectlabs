from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from http import HTTPStatus

from rental_service.domain import (
    Car,
    CarCategory,
    CarStatus,
    Contract,
    Rental,
    RentalStatus,
    Role,
    User,
    dates_intersect,
    full_years_between,
    rental_days,
)
from rental_service.repositories import (
    CarRepository,
    ContractRepository,
    RentalRepository,
    UserRepository,
)


class ServiceError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class BadRequest(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(HTTPStatus.BAD_REQUEST, message)


class Forbidden(ServiceError):
    def __init__(self, message: str = "not enough rights") -> None:
        super().__init__(HTTPStatus.FORBIDDEN, message)


class NotFound(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(HTTPStatus.NOT_FOUND, message)


class Conflict(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(HTTPStatus.CONFLICT, message)


@dataclass(frozen=True)
class CategoryRule:
    min_age: int
    min_experience_years: int


CATEGORY_RULES: dict[CarCategory, CategoryRule] = {
    CarCategory.ECONOMY: CategoryRule(min_age=21, min_experience_years=2),
    CarCategory.STANDARD: CategoryRule(min_age=21, min_experience_years=2),
    CarCategory.PREMIUM: CategoryRule(min_age=23, min_experience_years=3),
    CarCategory.SPORT: CategoryRule(min_age=25, min_experience_years=5),
}

DAMAGE_PENALTY = 5_000
LATE_PENALTY_PER_DAY = 1_000


def require_any_role(user: User, roles: set[Role]) -> None:
    if user.roles.isdisjoint(roles):
        raise Forbidden()


def require_role(user: User, role: Role) -> None:
    require_any_role(user, {role})


class UserService:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    def authenticate(self, user_id: int) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise ServiceError(HTTPStatus.UNAUTHORIZED, "unknown user")
        return user

    def list_users(self, actor: User) -> list[User]:
        require_role(actor, Role.ADMIN)
        return self._users.list()

    def create_user(
        self,
        actor: User,
        username: str,
        birth_date: date,
        driving_license_issue_date: date,
        roles: frozenset[Role],
    ) -> User:
        require_role(actor, Role.ADMIN)
        if not username.strip():
            raise BadRequest("username must not be empty")
        if not roles:
            raise BadRequest("user must have at least one role")
        if driving_license_issue_date < birth_date:
            raise BadRequest("license issue date cannot be earlier than birth date")
        try:
            return self._users.add(username, birth_date, driving_license_issue_date, roles)
        except ValueError as error:
            raise Conflict("username must be unique") from error

    def update_roles(self, actor: User, user_id: int, roles: frozenset[Role]) -> User:
        require_role(actor, Role.ADMIN)
        if not roles:
            raise BadRequest("user must have at least one role")
        user = self._users.update_roles(user_id, roles)
        if user is None:
            raise NotFound("user not found")
        return user


class CarService:
    def __init__(self, cars: CarRepository) -> None:
        self._cars = cars

    def list_cars(
        self,
        *,
        status: CarStatus | None = None,
        category: CarCategory | None = None,
        brand: str | None = None,
        include_unavailable: bool = False,
    ) -> list[Car]:
        result = self._cars.list()
        if status is not None:
            result = [car for car in result if car.status == status]
        elif not include_unavailable:
            result = [car for car in result if car.status == CarStatus.AVAILABLE]
        if category is not None:
            result = [car for car in result if car.category == category]
        if brand:
            brand_lower = brand.lower()
            result = [car for car in result if car.brand.lower() == brand_lower]
        return result

    def add_car(
        self,
        actor: User,
        vin: str,
        brand: str,
        model: str,
        category: CarCategory,
        daily_rate: int,
    ) -> Car:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        if not vin.strip():
            raise BadRequest("vin must not be empty")
        if daily_rate <= 0:
            raise BadRequest("daily rate must be positive")
        try:
            return self._cars.add(vin, brand, model, category, daily_rate)
        except ValueError as error:
            raise Conflict("vin must be unique") from error

    def update_status(self, actor: User, car_id: int, status: CarStatus) -> Car:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        car = self._cars.update_status(car_id, status)
        if car is None:
            raise NotFound("car not found")
        return car


@dataclass(frozen=True)
class RentalResult:
    rental: Rental
    contract: Contract | None = None


class RentalService:
    def __init__(
        self,
        cars: CarRepository,
        rentals: RentalRepository,
        contracts: ContractRepository,
    ) -> None:
        self._cars = cars
        self._rentals = rentals
        self._contracts = contracts

    def list_rentals(self, actor: User) -> list[Rental]:
        if Role.ADMIN in actor.roles or Role.MANAGER in actor.roles:
            return self._rentals.list()
        require_role(actor, Role.CLIENT)
        return [rental for rental in self._rentals.list() if rental.user_id == actor.id]

    def get_contracts(self, actor: User) -> list[Contract]:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        return self._contracts.list()

    def create_rental(
        self,
        actor: User,
        car_id: int,
        start_date: date,
        end_date: date,
        today: date | None = None,
    ) -> RentalResult:
        require_role(actor, Role.CLIENT)
        self._validate_dates(start_date, end_date)
        car = self._get_car_or_raise(car_id)
        self._ensure_client_can_drive(actor, car, today or date.today())
        self._ensure_car_available(car, start_date, end_date)

        auto_approve = Role.MANAGER in actor.roles
        status = RentalStatus.APPROVED if auto_approve else RentalStatus.PENDING
        rental = self._rentals.add(actor.id, car.id, start_date, end_date, status)
        if not auto_approve:
            return RentalResult(rental=rental)

        contract = self._create_contract(rental, car)
        self._cars.update_status(car.id, CarStatus.RENTED)
        return RentalResult(rental=rental, contract=contract)

    def approve_rental(self, actor: User, rental_id: int) -> RentalResult:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        rental = self._get_rental_or_raise(rental_id)
        if rental.status != RentalStatus.PENDING:
            raise Conflict("only pending rental can be approved")
        car = self._get_car_or_raise(rental.car_id)
        self._ensure_car_available(car, rental.start_date, rental.end_date)
        rental = self._rentals.update_status(rental.id, RentalStatus.APPROVED)
        if rental is None:
            raise NotFound("rental not found")
        contract = self._create_contract(rental, car)
        self._cars.update_status(car.id, CarStatus.RENTED)
        return RentalResult(rental=rental, contract=contract)

    def reject_rental(self, actor: User, rental_id: int) -> Rental:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        rental = self._get_rental_or_raise(rental_id)
        if rental.status != RentalStatus.PENDING:
            raise Conflict("only pending rental can be rejected")
        updated = self._rentals.update_status(rental.id, RentalStatus.REJECTED)
        if updated is None:
            raise NotFound("rental not found")
        return updated

    def complete_rental(
        self,
        actor: User,
        rental_id: int,
        return_date: date,
        damaged: bool,
    ) -> RentalResult:
        require_any_role(actor, {Role.MANAGER, Role.ADMIN})
        rental = self._get_rental_or_raise(rental_id)
        if rental.status != RentalStatus.APPROVED:
            raise Conflict("only approved rental can be completed")
        contract = self._contracts.get_by_rental(rental.id)
        if contract is None:
            raise Conflict("approved rental has no contract")

        late_days = max(0, (return_date - rental.end_date).days)
        penalty = late_days * LATE_PENALTY_PER_DAY
        if damaged:
            penalty += DAMAGE_PENALTY

        completed_contract = self._contracts.complete(contract.id, penalty)
        completed_rental = self._rentals.update_status(rental.id, RentalStatus.COMPLETED)
        if completed_contract is None or completed_rental is None:
            raise NotFound("rental not found")
        self._cars.update_status(rental.car_id, CarStatus.AVAILABLE)
        return RentalResult(rental=completed_rental, contract=completed_contract)

    def _create_contract(self, rental: Rental, car: Car) -> Contract:
        base_price = car.daily_rate * rental_days(rental.start_date, rental.end_date)
        return self._contracts.add(rental.id, base_price)

    def _ensure_client_can_drive(self, user: User, car: Car, today: date) -> None:
        rule = CATEGORY_RULES[car.category]
        age = full_years_between(user.birth_date, today)
        experience = full_years_between(user.driving_license_issue_date, today)
        if age < rule.min_age:
            raise BadRequest(f"client must be at least {rule.min_age} years old")
        if experience < rule.min_experience_years:
            raise BadRequest(
                f"client must have at least {rule.min_experience_years} years of experience"
            )

    def _ensure_car_available(self, car: Car, start_date: date, end_date: date) -> None:
        if car.status == CarStatus.UNDER_MAINTENANCE:
            raise Conflict("car is under maintenance")
        if car.status == CarStatus.RENTED:
            raise Conflict("car is already rented")
        for rental in self._rentals.list():
            if rental.car_id != car.id or rental.status != RentalStatus.APPROVED:
                continue
            if dates_intersect(start_date, end_date, rental.start_date, rental.end_date):
                raise Conflict("car is not available for requested dates")

    def _validate_dates(self, start_date: date, end_date: date) -> None:
        if end_date < start_date:
            raise BadRequest("end date cannot be earlier than start date")

    def _get_car_or_raise(self, car_id: int) -> Car:
        car = self._cars.get(car_id)
        if car is None:
            raise NotFound("car not found")
        return car

    def _get_rental_or_raise(self, rental_id: int) -> Rental:
        rental = self._rentals.get(rental_id)
        if rental is None:
            raise NotFound("rental not found")
        return rental
