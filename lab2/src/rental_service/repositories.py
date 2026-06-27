from __future__ import annotations

from dataclasses import replace
from datetime import date

from rental_service.domain import (
    Car,
    CarCategory,
    CarStatus,
    Contract,
    Rental,
    RentalStatus,
    Role,
    User,
    now_utc,
)


class UserRepository:
    def __init__(self) -> None:
        self._items: dict[int, User] = {}
        self._username_index: dict[str, int] = {}
        self._next_id = 1

    def add(
        self,
        username: str,
        birth_date: date,
        driving_license_issue_date: date,
        roles: frozenset[Role],
    ) -> User:
        if username in self._username_index:
            raise ValueError("username already exists")
        user = User(
            id=self._next_id,
            username=username,
            birth_date=birth_date,
            driving_license_issue_date=driving_license_issue_date,
            roles=roles,
        )
        self._next_id += 1
        self._items[user.id] = user
        self._username_index[user.username] = user.id
        return user

    def get(self, user_id: int) -> User | None:
        return self._items.get(user_id)

    def exists_by_username(self, username: str) -> bool:
        return username in self._username_index

    def update_roles(self, user_id: int, roles: frozenset[Role]) -> User | None:
        user = self.get(user_id)
        if user is None:
            return None
        updated = replace(user, roles=roles)
        self._items[user_id] = updated
        return updated

    def list(self) -> list[User]:
        return [self._items[key] for key in sorted(self._items)]


class CarRepository:
    def __init__(self) -> None:
        self._items: dict[int, Car] = {}
        self._vin_index: dict[str, int] = {}
        self._next_id = 1

    def add(
        self,
        vin: str,
        brand: str,
        model: str,
        category: CarCategory,
        daily_rate: int,
        status: CarStatus = CarStatus.AVAILABLE,
    ) -> Car:
        if vin in self._vin_index:
            raise ValueError("vin already exists")
        car = Car(
            id=self._next_id,
            vin=vin,
            brand=brand,
            model=model,
            category=category,
            daily_rate=daily_rate,
            status=status,
        )
        self._next_id += 1
        self._items[car.id] = car
        self._vin_index[car.vin] = car.id
        return car

    def get(self, car_id: int) -> Car | None:
        return self._items.get(car_id)

    def exists_by_vin(self, vin: str) -> bool:
        return vin in self._vin_index

    def update_status(self, car_id: int, status: CarStatus) -> Car | None:
        car = self.get(car_id)
        if car is None:
            return None
        updated = replace(car, status=status)
        self._items[car_id] = updated
        return updated

    def list(self) -> list[Car]:
        return [self._items[key] for key in sorted(self._items)]


class RentalRepository:
    def __init__(self) -> None:
        self._items: dict[int, Rental] = {}
        self._next_id = 1

    def add(
        self,
        user_id: int,
        car_id: int,
        start_date: date,
        end_date: date,
        status: RentalStatus,
    ) -> Rental:
        rental = Rental(
            id=self._next_id,
            user_id=user_id,
            car_id=car_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            created_at=now_utc(),
        )
        self._next_id += 1
        self._items[rental.id] = rental
        return rental

    def get(self, rental_id: int) -> Rental | None:
        return self._items.get(rental_id)

    def update_status(self, rental_id: int, status: RentalStatus) -> Rental | None:
        rental = self.get(rental_id)
        if rental is None:
            return None
        updated = replace(rental, status=status)
        self._items[rental_id] = updated
        return updated

    def list(self) -> list[Rental]:
        return [self._items[key] for key in sorted(self._items)]


class ContractRepository:
    def __init__(self) -> None:
        self._items: dict[int, Contract] = {}
        self._by_rental: dict[int, int] = {}
        self._next_id = 1

    def add(self, rental_id: int, base_price: int) -> Contract:
        contract = Contract(
            id=self._next_id,
            rental_id=rental_id,
            base_price=base_price,
            penalty=0,
            total_price=base_price,
            created_at=now_utc(),
        )
        self._next_id += 1
        self._items[contract.id] = contract
        self._by_rental[rental_id] = contract.id
        return contract

    def get(self, contract_id: int) -> Contract | None:
        return self._items.get(contract_id)

    def get_by_rental(self, rental_id: int) -> Contract | None:
        contract_id = self._by_rental.get(rental_id)
        if contract_id is None:
            return None
        return self.get(contract_id)

    def complete(self, contract_id: int, penalty: int) -> Contract | None:
        contract = self.get(contract_id)
        if contract is None:
            return None
        updated = replace(
            contract,
            penalty=penalty,
            total_price=contract.base_price + penalty,
            completed_at=now_utc(),
        )
        self._items[contract_id] = updated
        return updated

    def list(self) -> list[Contract]:
        return [self._items[key] for key in sorted(self._items)]
