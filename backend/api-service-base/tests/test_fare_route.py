"""Tarifa por distancia de calle (no línea recta) y recargos con la hora de México."""
from datetime import datetime, timezone

from src import fare_service


class _Cfg:
    base_fare, per_km_rate, minimum_fare = 30, 8, 50
    surge_enabled = False


def test_uses_road_distance(monkeypatch):
    monkeypatch.setattr(fare_service, "_osrm_route", lambda *a: (6.2, 14.0))
    km, mins = fare_service.route_km_min(20.52, -100.81, 20.55, -100.80)
    assert (round(km, 1), mins) == (6.2, 14)
    assert fare_service.calculate_fare(_Cfg, km) == 30 + 6.2 * 8


def test_falls_back_to_straight_line_plus_30_percent():
    straight = fare_service._straight_km(20.52, -100.81, 20.55, -100.80)
    km, _ = fare_service.route_km_min(20.52, -100.81, 20.55, -100.80)
    assert abs(km - straight * 1.3) < 0.01


def test_estimate_and_create_get_the_same_price(monkeypatch):
    answers = iter([(5.0, 12.0), (9.0, 20.0)])      # OSRM cambia de opinión
    monkeypatch.setattr(fare_service, "_osrm_route", lambda *a: next(answers))
    first = fare_service.route_km_min(20.52, -100.81, 20.55, -100.80)
    second = fare_service.route_km_min(20.52, -100.81, 20.55, -100.80)
    assert first == second


def test_night_surcharge_uses_mexico_time(monkeypatch):
    class Cfg(_Cfg):
        surge_night_multiplier, surge_weekend_multiplier, surge_peak_multiplier = 1.5, 1.2, 1.3

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 10, 23, 30, tzinfo=timezone.utc)   # martes 5:30 pm en México
    monkeypatch.setattr(fare_service, "datetime", FakeDT)
    assert fare_service._surge_multiplier(Cfg) != 1.5
