import httpx

from src.models import Trip, TripStatus


class _FakeMPResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


def _fake_async_client(payment_payload: dict):
    """Reemplaza httpx.AsyncClient para simular la respuesta de la API de MercadoPago
    sin salir a la red. El .post() de _notify() no se implementa a propósito: esa
    llamada está protegida por try/except en payments.py y no debe afectar el test."""
    class _Client:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, headers=None):
            return _FakeMPResponse(payment_payload)
    return _Client


def _create_trip(db_session, **overrides) -> Trip:
    defaults = dict(
        customer_phone="+521111111111",
        fare=120.0,
        status=TripStatus.REQUESTED,
        payment_status="pending_payment",
    )
    defaults.update(overrides)
    trip = Trip(**defaults)
    db_session.add(trip)
    db_session.commit()
    db_session.refresh(trip)
    return trip


def test_webhook_ignores_non_payment_topics(client):
    resp = client.post("/api/v1/payments/webhook/mercadopago?topic=merchant_order&id=999")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_confirms_trip_on_approved_payment(client, db_session, monkeypatch):
    trip = _create_trip(db_session)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client({
        "status": "approved", "external_reference": trip.trip_id,
    }))

    resp = client.post("/api/v1/payments/webhook/mercadopago?topic=payment&id=123")
    assert resp.status_code == 200

    db_session.refresh(trip)
    assert trip.payment_status == "paid"
    assert trip.status == TripStatus.CONFIRMED


def test_webhook_cancels_trip_on_rejected_payment(client, db_session, monkeypatch):
    trip = _create_trip(db_session)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client({
        "status": "rejected", "external_reference": trip.trip_id,
    }))

    resp = client.post("/api/v1/payments/webhook/mercadopago?topic=payment&id=456")
    assert resp.status_code == 200

    db_session.refresh(trip)
    assert trip.payment_status == "failed"
    assert trip.status == TripStatus.CANCELLED


def test_webhook_is_idempotent_for_already_paid_trip(client, db_session, monkeypatch):
    """Un segundo webhook 'approved' para un viaje ya pagado no debe reenviar la notificación
    ni romper nada — sólo confirma que el estado se mantiene consistente."""
    trip = _create_trip(db_session, payment_status="paid", status=TripStatus.CONFIRMED)
    monkeypatch.setattr(httpx, "AsyncClient", _fake_async_client({
        "status": "approved", "external_reference": trip.trip_id,
    }))

    resp = client.post("/api/v1/payments/webhook/mercadopago?topic=payment&id=789")
    assert resp.status_code == 200

    db_session.refresh(trip)
    assert trip.payment_status == "paid"
    assert trip.status == TripStatus.CONFIRMED
