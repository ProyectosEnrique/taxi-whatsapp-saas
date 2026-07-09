from datetime import datetime, timezone

from src import fare_service
from src.models import FareConfig


def _cfg(**overrides) -> FareConfig:
    defaults = dict(
        base_fare=50.0,
        per_km_rate=8.0,
        minimum_fare=70.0,
        surge_enabled=False,
        surge_peak_multiplier=1.3,
        surge_night_multiplier=1.5,
        surge_weekend_multiplier=1.2,
    )
    defaults.update(overrides)
    return FareConfig(**defaults)


class _FixedDatetime(datetime):
    """datetime.now() congelado para probar las franjas de surge sin depender del reloj real."""
    _frozen = datetime(2026, 1, 1, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        return cls._frozen.replace(tzinfo=tz) if tz else cls._frozen


def test_calculate_fare_base_plus_distance():
    fare = fare_service.calculate_fare(_cfg(), distance_km=5)
    assert fare == 90.0  # 50 + 5*8


def test_calculate_fare_enforces_minimum():
    fare = fare_service.calculate_fare(_cfg(), distance_km=1)
    assert fare == 70.0  # 50 + 1*8 = 58 < mínimo 70


def test_calculate_fare_ignores_surge_when_disabled():
    fare = fare_service.calculate_fare(_cfg(surge_enabled=False), distance_km=10)
    assert fare == 130.0  # 50 + 10*8, sin recargo


def test_calculate_fare_applies_peak_surge(monkeypatch):
    # 2026-07-08 08:00 UTC = miércoles, hora pico (7-9am)
    _FixedDatetime._frozen = datetime(2026, 7, 8, 8, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(fare_service, "datetime", _FixedDatetime)

    fare = fare_service.calculate_fare(_cfg(surge_enabled=True), distance_km=10)
    assert fare == round((50 + 10 * 8) * 1.3, 2)


def test_calculate_fare_applies_night_surge(monkeypatch):
    # 2026-07-08 02:00 UTC = madrugada
    _FixedDatetime._frozen = datetime(2026, 7, 8, 2, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(fare_service, "datetime", _FixedDatetime)

    fare = fare_service.calculate_fare(_cfg(surge_enabled=True), distance_km=10)
    assert fare == round((50 + 10 * 8) * 1.5, 2)


def test_calculate_fare_applies_weekend_surge(monkeypatch):
    # 2026-07-11 12:00 UTC = sábado, fuera de horas pico/madrugada
    _FixedDatetime._frozen = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(fare_service, "datetime", _FixedDatetime)

    fare = fare_service.calculate_fare(_cfg(surge_enabled=True), distance_km=10)
    assert fare == round((50 + 10 * 8) * 1.2, 2)
