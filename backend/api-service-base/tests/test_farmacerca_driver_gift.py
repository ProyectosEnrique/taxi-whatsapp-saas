"""Regalo de FarmaCerca a los choferes: $50 al alta + $50 en su primer viaje (services/farmacerca_driver_gift.py)."""
import asyncio
from datetime import datetime, timezone

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
    """FarmaCerca simulado: abona una vez por referencia, como el de verdad."""
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
                return _Resp(200, {"credited": 0.0, "already": True, "balance": 100.0})
            seen.add(json["ref"])
            return _Resp(200, {"credited": 50.0, "balance": 50.0 * len(seen), "expires_label": "11 de febrero"})

    async def _send(chat_id, text):
        sent.append((chat_id, text))
        return True

    monkeypatch.setattr(g.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(g, "send_message", _send)
    monkeypatch.setattr(settings, "FARMACERCA_DRIVER_SECRET", "s3creto")
    return calls, sent


def test_alta_and_first_trip_pay_once_each(fc):
    calls, sent = fc
    assert asyncio.run(g.give("alta", "+524611112222", "Carlos Pérez", "99"))
    assert not asyncio.run(g.give("alta", "+524611112222", "Carlos Pérez", "99"))   # volvió a ligar Telegram
    assert asyncio.run(g.give("viaje", "+524611112222", "Carlos Pérez", "99"))
    assert [c[1]["ref"] for c in calls] == ["AL4611112222", "AL4611112222", "V14611112222"]
    assert all(c[1]["ally_code"] == "TAXICHOFER" and c[2]["X-Ally-Secret"] == "s3creto" for c in calls)
    assert calls[0][0] == "https://farmacia.nexoai.lat/api/v1/allies/partner-credit"
    assert len(sent) == 2
    assert "Bienvenido a TaxiCerca, Carlos" in sent[0][1] and "$50" in sent[0][1] and "11 de febrero" in sent[0][1]
    assert "Primer viaje" in sent[1][1] and "Ya tienes <b>$100</b>" in sent[1][1]


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
    assert not asyncio.run(g.give("viaje", "+524611112222", "Carlos", "99"))


def _trip(db, n, status=TripStatus.COMPLETED):
    db.add(Trip(trip_id=f"T{n}", customer_phone="+524619990000", driver_phone="+524611112222", status=status,
                origin_address="A", destination_address="B", fare=50, created_at=datetime.now(timezone.utc)))
    db.commit()


def test_is_first_trip(db_session):
    _trip(db_session, 1, TripStatus.CANCELLED)
    assert not g.is_first_trip(db_session, "+524611112222")
    _trip(db_session, 2)
    assert g.is_first_trip(db_session, "+524611112222")
    _trip(db_session, 3)
    assert not g.is_first_trip(db_session, "+524611112222")
