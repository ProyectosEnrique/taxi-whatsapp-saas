"""Regalo de FarmaCerca a los choferes: $30 al alta + $5 por cada uno de sus primeros 10 viajes, 14 días, un viaje
por pasajero (services/farmacerca_driver_gift.py)."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.config import settings
from src.models import Trip, TripStatus
from src.services import farmacerca_driver_gift as g


class _Resp:
    def __init__(self, status, data):
        self.status_code, self._data, self.text = status, data, str(data)

    def json(self):
        return self._data


@pytest.fixture
def fc(monkeypatch):
    """FarmaCerca simulado: abona una vez por referencia, como el de verdad ($30 TAXICHOFER, $5 TAXIVIAJE)."""
    seen, calls, sent = set(), [], []

    class _Client:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json, headers):
            calls.append((url, json, headers))
            if json["ref"] in seen:
                return _Resp(200, {"credited": 0.0, "already": True, "balance": 35.0})
            seen.add(json["ref"])
            amount = 30.0 if json["ally_code"] == "TAXICHOFER" else 5.0
            return _Resp(200, {"credited": amount, "balance": 30.0 + 5.0 * (len(seen) - 1),
                               "expires_label": "13 de febrero"})

    async def _send(chat_id, text):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr(g.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(g, "send_message", _send)
    monkeypatch.setattr(settings, "FARMACERCA_DRIVER_SECRET", "s3creto")
    return calls, sent


def test_alta_and_trips_pay_once_each(fc):
    calls, sent = fc
    assert asyncio.run(g.give("alta", "+524611112222", "Carlos Pérez", "99"))
    assert not asyncio.run(g.give("alta", "+524611112222", "Carlos Pérez", "99"))   # volvió a ligar Telegram
    assert asyncio.run(g.give("viaje", "+524611112222", "Carlos Pérez", "99", 1))
    assert not asyncio.run(g.give("viaje", "+524611112222", "Carlos Pérez", "99", 11))   # pasado el tope
    assert [(c[1]["ally_code"], c[1]["ref"]) for c in calls] == [
        ("TAXICHOFER", "AL4611112222"), ("TAXICHOFER", "AL4611112222"), ("TAXIVIAJE", "V014611112222")]
    assert all(c[2]["X-Ally-Secret"] == "s3creto" and len(c[1]["ref"]) <= 14 for c in calls)
    assert calls[0][0] == "https://farmacia.nexoai.lat/api/v1/allies/partner-credit"
    assert len(sent) == 2
    assert "Bienvenido a TaxiCerca, Carlos" in sent[0][1] and "$30" in sent[0][1] and "10 viajes" in sent[0][1]
    assert "Viaje 1 de 10" in sent[1][1] and "$5" in sent[1][1] and "Ya tienes <b>$35</b>" in sent[1][1]


def test_off_without_secret(fc, monkeypatch):
    calls, sent = fc
    monkeypatch.setattr(settings, "FARMACERCA_DRIVER_SECRET", "")
    assert not asyncio.run(g.give("alta", "+524611112222", "Carlos", "99"))
    assert not calls and not sent


def test_farmacerca_down_does_not_raise(monkeypatch):
    class _Boom:
        def __init__(self, *a, **kw):
            raise RuntimeError("sin red")

    monkeypatch.setattr(g.httpx, "AsyncClient", _Boom)
    monkeypatch.setattr(settings, "FARMACERCA_DRIVER_SECRET", "s3creto")
    assert not asyncio.run(g.give("viaje", "+524611112222", "Carlos", "99", 1))


_T0 = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _trip(db, n, customer, days=0.0, status=TripStatus.COMPLETED):
    t = Trip(trip_id=f"T{n}", customer_phone=customer, driver_phone="+524611112222", status=status,
             origin_address="A", destination_address="B", fare=50, created_at=_T0,
             completed_at=_T0 + timedelta(days=days) if status == TripStatus.COMPLETED else None)
    db.add(t)
    db.commit()
    return t


def _n(db, t):
    return g.trip_gift_number(db, "+524611112222", t)


def test_one_gift_per_passenger(db_session):
    _trip(db_session, 0, "+524619990000", status=TripStatus.CANCELLED)
    assert _n(db_session, _trip(db_session, 1, "+524619990001")) == 1
    assert _n(db_session, _trip(db_session, 2, "+524619990001", 0.1)) is None   # mismo pasajero
    assert _n(db_session, _trip(db_session, 3, "4619990002", 0.2)) == 2


def test_cap_of_ten_trips(db_session):
    nums = [_n(db_session, _trip(db_session, i, f"+5246199900{i:02d}", i * 0.1)) for i in range(12)]
    assert nums == list(range(1, 11)) + [None, None]


def test_window_of_fourteen_days_from_first_trip(db_session):
    assert _n(db_session, _trip(db_session, 1, "+524619990001")) == 1
    assert _n(db_session, _trip(db_session, 2, "+524619990002", 13.9)) == 2
    assert _n(db_session, _trip(db_session, 3, "+524619990003", 14.5)) is None
