from src.models import Trip, TripStatus

_REGISTER_PAYLOAD = {"phone": "+521111111111", "password": "secret123", "name": "Ana"}
_ROUTE = {
    "origin": {"address": "Casa", "lat": 20.52, "lng": -100.81},
    "destination": {"address": "Central", "lat": 20.55, "lng": -100.85},
}


def test_register_creates_customer_and_returns_token(client):
    resp = client.post("/api/v1/customer/register", json=_REGISTER_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"]
    assert body["customer"]["phone"] == _REGISTER_PAYLOAD["phone"]


def test_register_rejects_duplicate_phone(client):
    client.post("/api/v1/customer/register", json=_REGISTER_PAYLOAD)
    resp = client.post("/api/v1/customer/register", json=_REGISTER_PAYLOAD)
    assert resp.status_code == 409


def test_login_with_correct_credentials_returns_token(client):
    client.post("/api/v1/customer/register", json=_REGISTER_PAYLOAD)
    resp = client.post("/api/v1/customer/login", json={
        "phone": _REGISTER_PAYLOAD["phone"], "password": _REGISTER_PAYLOAD["password"],
    })
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_login_with_wrong_password_is_rejected(client):
    client.post("/api/v1/customer/register", json=_REGISTER_PAYLOAD)
    resp = client.post("/api/v1/customer/login", json={
        "phone": _REGISTER_PAYLOAD["phone"], "password": "wrong-password",
    })
    assert resp.status_code == 401


def test_estimate_fare_requires_auth(client):
    resp = client.post("/api/v1/customer/rides/estimate", json=_ROUTE)
    assert resp.status_code == 401


def test_estimate_fare_returns_fare_and_distance(client, customer):
    _, _, headers = customer
    resp = client.post("/api/v1/customer/rides/estimate", json=_ROUTE, headers=headers)
    assert resp.status_code == 200
    estimate = resp.json()["estimate"]
    assert estimate["fare"] >= 70.0  # tarifa mínima por defecto
    assert estimate["distance_km"] > 0


def test_request_ride_creates_trip_in_requested_status(client, customer):
    _, _, headers = customer
    resp = client.post("/api/v1/customer/rides/request", json=_ROUTE, headers=headers)
    assert resp.status_code == 200
    ride = resp.json()["ride"]
    assert ride["status"] == "requested"
    assert ride["total_fare"] >= 70.0
    assert ride["destination"]["address"] == "Central"


def test_cancel_ride_succeeds_when_requested(client, customer):
    _, _, headers = customer
    ride_id = client.post("/api/v1/customer/rides/request", json=_ROUTE, headers=headers).json()["ride"]["ride_id"]

    resp = client.post(f"/api/v1/customer/rides/{ride_id}/cancel", json={"reason": "cambio de planes"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_cancel_ride_blocked_when_in_progress(client, customer, db_session):
    _, _, headers = customer
    ride_id = client.post("/api/v1/customer/rides/request", json=_ROUTE, headers=headers).json()["ride"]["ride_id"]

    trip = db_session.query(Trip).filter(Trip.trip_id == ride_id).first()
    trip.status = TripStatus.IN_PROGRESS
    db_session.commit()

    resp = client.post(f"/api/v1/customer/rides/{ride_id}/cancel", json={"reason": "test"}, headers=headers)
    assert resp.status_code == 400
