from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from rental_service.api import create_app

ADMIN = 1
MANAGER = 2
CLIENT = 3
CLIENT_MANAGER = 4


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def headers(user_id: int) -> dict[str, str]:
    return {"X-User-Id": str(user_id)}


def add_car(
    client: TestClient,
    *,
    vin: str = "VIN-001",
    category: str = "STANDARD",
    daily_rate: int = 2_000,
) -> dict:
    response = client.post(
        "/cars",
        headers=headers(MANAGER),
        json={
            "vin": vin,
            "brand": "Toyota",
            "model": "Camry",
            "category": category,
            "daily_rate": daily_rate,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_rental(
    client: TestClient,
    *,
    user_id: int = CLIENT,
    car_id: int = 1,
    start_date: str = "2026-07-01",
    end_date: str = "2026-07-03",
) -> dict:
    response = client.post(
        "/rentals",
        headers=headers(user_id),
        json={"car_id": car_id, "start_date": start_date, "end_date": end_date},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_manages_users_and_username_is_unique(client: TestClient) -> None:
    forbidden = client.get("/users", headers=headers(MANAGER))
    assert forbidden.status_code == 403

    created = client.post(
        "/users",
        headers=headers(ADMIN),
        json={
            "username": "ivan",
            "birth_date": "1997-05-10",
            "driving_license_issue_date": "2018-05-10",
            "roles": ["CLIENT"],
        },
    )
    assert created.status_code == 201, created.text
    user = created.json()
    assert user["username"] == "ivan"
    assert set(user["roles"]) == {"CLIENT"}

    duplicate = client.post(
        "/users",
        headers=headers(ADMIN),
        json={
            "username": "ivan",
            "birth_date": "1998-05-10",
            "driving_license_issue_date": "2019-05-10",
            "roles": ["CLIENT"],
        },
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/users/{user['id']}/roles",
        headers=headers(ADMIN),
        json={"roles": ["CLIENT", "MANAGER"]},
    )
    assert updated.status_code == 200, updated.text
    assert set(updated.json()["roles"]) == {"CLIENT", "MANAGER"}


def test_manager_manages_car_catalog_and_vin_is_unique(client: TestClient) -> None:
    forbidden = client.post(
        "/cars",
        headers=headers(CLIENT),
        json={
            "vin": "VIN-CLIENT",
            "brand": "Ford",
            "model": "Focus",
            "category": "ECONOMY",
            "daily_rate": 1_500,
        },
    )
    assert forbidden.status_code == 403

    car = add_car(client)
    assert car["status"] == "AVAILABLE"

    duplicate = client.post(
        "/cars",
        headers=headers(MANAGER),
        json={
            "vin": "VIN-001",
            "brand": "Toyota",
            "model": "Corolla",
            "category": "ECONOMY",
            "daily_rate": 1_700,
        },
    )
    assert duplicate.status_code == 409

    available = client.get("/cars", params={"brand": "toyota"})
    assert available.status_code == 200
    assert [item["vin"] for item in available.json()] == ["VIN-001"]

    maintenance = client.patch(
        f"/cars/{car['id']}/status",
        headers=headers(MANAGER),
        json={"status": "UNDER_MAINTENANCE"},
    )
    assert maintenance.status_code == 200
    assert maintenance.json()["status"] == "UNDER_MAINTENANCE"

    assert client.get("/cars").json() == []
    all_cars = client.get("/cars", params={"include_unavailable": True}).json()
    assert all_cars[0]["status"] == "UNDER_MAINTENANCE"


def test_rental_lifecycle_approval_completion_and_penalty(client: TestClient) -> None:
    add_car(client, daily_rate=2_000)

    created = create_rental(client)
    assert created["rental"]["status"] == "PENDING"
    assert created["contract"] is None

    client_rentals = client.get("/rentals", headers=headers(CLIENT))
    assert client_rentals.status_code == 200
    assert len(client_rentals.json()) == 1

    approved = client.patch("/rentals/1/approve", headers=headers(MANAGER))
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["rental"]["status"] == "APPROVED"
    assert body["contract"]["base_price"] == 6_000
    assert body["contract"]["total_price"] == 6_000

    second_request = client.post(
        "/rentals",
        headers=headers(CLIENT),
        json={"car_id": 1, "start_date": "2026-07-02", "end_date": "2026-07-04"},
    )
    assert second_request.status_code == 409

    completed = client.patch(
        "/rentals/1/complete",
        headers=headers(MANAGER),
        json={"return_date": "2026-07-05", "damaged": True},
    )
    assert completed.status_code == 200, completed.text
    finished = completed.json()
    assert finished["rental"]["status"] == "COMPLETED"
    assert finished["contract"]["penalty"] == 7_000
    assert finished["contract"]["total_price"] == 13_000

    cars = client.get("/cars", params={"include_unavailable": True}).json()
    assert cars[0]["status"] == "AVAILABLE"


def test_client_manager_request_is_approved_automatically(client: TestClient) -> None:
    add_car(client, vin="VIN-AUTO", daily_rate=3_000)

    result = create_rental(client, user_id=CLIENT_MANAGER)

    assert result["rental"]["status"] == "APPROVED"
    assert result["contract"]["base_price"] == 9_000

    contracts = client.get("/contracts", headers=headers(MANAGER))
    assert contracts.status_code == 200
    assert len(contracts.json()) == 1


def test_rental_checks_age_experience_dates_and_car_state(client: TestClient) -> None:
    economy = add_car(client, vin="VIN-AGE", category="ECONOMY")
    premium = add_car(client, vin="VIN-PREMIUM", category="PREMIUM")

    young_user = client.post(
        "/users",
        headers=headers(ADMIN),
        json={
            "username": "too_young",
            "birth_date": "2010-01-01",
            "driving_license_issue_date": "2025-01-01",
            "roles": ["CLIENT"],
        },
    ).json()
    low_experience_user = client.post(
        "/users",
        headers=headers(ADMIN),
        json={
            "username": "low_experience",
            "birth_date": "2000-01-01",
            "driving_license_issue_date": "2025-01-01",
            "roles": ["CLIENT"],
        },
    ).json()

    wrong_dates = client.post(
        "/rentals",
        headers=headers(CLIENT),
        json={"car_id": economy["id"], "start_date": "2026-07-04", "end_date": "2026-07-01"},
    )
    assert wrong_dates.status_code == 400

    too_young = client.post(
        "/rentals",
        headers=headers(young_user["id"]),
        json={"car_id": economy["id"], "start_date": "2026-07-01", "end_date": "2026-07-02"},
    )
    assert too_young.status_code == 400

    low_experience = client.post(
        "/rentals",
        headers=headers(low_experience_user["id"]),
        json={"car_id": premium["id"], "start_date": "2026-07-01", "end_date": "2026-07-02"},
    )
    assert low_experience.status_code == 400

    maintenance = client.patch(
        f"/cars/{economy['id']}/status",
        headers=headers(MANAGER),
        json={"status": "UNDER_MAINTENANCE"},
    )
    assert maintenance.status_code == 200

    unavailable = client.post(
        "/rentals",
        headers=headers(CLIENT),
        json={"car_id": economy["id"], "start_date": "2026-07-01", "end_date": "2026-07-02"},
    )
    assert unavailable.status_code == 409


def test_pending_rental_can_be_rejected_only_once(client: TestClient) -> None:
    add_car(client, vin="VIN-REJECT")
    create_rental(client)

    rejected = client.patch("/rentals/1/reject", headers=headers(MANAGER))
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"

    approve_rejected = client.patch("/rentals/1/approve", headers=headers(MANAGER))
    assert approve_rejected.status_code == 409
