"""Eliminar chofer desde el panel: sin viajes se borra de verdad; con viajes
solo se desactiva para no perder el historial."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src.auth import hash_password
from src.config import settings
from src.database import get_db
from src.models import Customer, Driver, Trip
from src.routers import admin

H = {"x-admin-key": "clave-admin"}


@pytest.fixture
def client(monkeypatch, db_session):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "clave-admin")
    app = FastAPI()
    app.include_router(admin.router)
    app.dependency_overrides[get_db] = _override_get_db
    db_session.add(Driver(phone="+524610000001", name="Pedro", password_hash=hash_password("x"), is_active=True))
    db_session.commit()
    return TestClient(app)


def test_driver_without_trips_is_deleted(client, db_session):
    driver = db_session.query(Driver).one()
    db_session.add(Customer(phone="+524610000099", name="Ana", password_hash="x", preferred_driver_id=driver.id))
    db_session.commit()

    r = client.delete("/api/v1/admin/drivers/%2B524610000001", headers=H)
    assert r.status_code == 200 and r.json()["deleted"] is True
    db_session.expire_all()
    assert db_session.query(Driver).count() == 0
    assert db_session.query(Customer).one().preferred_driver_id is None


def test_driver_with_trips_is_only_deactivated(client, db_session):
    db_session.add(Trip(trip_id="T-1", customer_phone="+524610000099", driver_phone="+524610000001"))
    db_session.commit()

    r = client.delete("/api/v1/admin/drivers/%2B524610000001", headers=H)
    assert r.status_code == 200 and r.json()["deleted"] is False
    db_session.expire_all()
    assert db_session.query(Driver).one().is_active is False


def test_requires_admin_key(client):
    assert client.delete("/api/v1/admin/drivers/%2B524610000001", headers={"x-admin-key": "mala"}).status_code == 401
