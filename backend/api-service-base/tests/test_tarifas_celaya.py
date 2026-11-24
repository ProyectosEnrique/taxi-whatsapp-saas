"""Tarifa de la base de la Central de Celaya (2026-11-24): fórmula $30 + $9.50/km (mínima $70),
noche = día + $10 en horario configurable, lista de precios Central ↔ lugar, y lugares locales
primero en la búsqueda del bot."""
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import _override_get_db
from src import fare_service
from src.config import settings
from src.database import get_db
from src.models import LocalPOI
from src.routers import locations, whatsapp

CENTRAL = (20.5137187, -100.8068808)
VILLAS_BAJIO = (20.5600, -100.8300)          # colonia de la lista: $140 / $150
HOTEL = (20.516555, -100.786519)             # hotel de la lista: $70 / $80


class Cfg:
    base_fare, per_km_rate, minimum_fare = 30, 9.5, 70
    surge_enabled = False
    night_surcharge, night_start_hour, night_end_hour = 10, 22, 6


def _at_mexico_hour(monkeypatch, hour):
    # México = UTC-6
    utc = datetime(2026, 11, 24, (hour + 6) % 24, 30, tzinfo=timezone.utc)

    class FakeDT(datetime):
        @classmethod
        def now(cls, tz=None):
            return utc
    monkeypatch.setattr(fare_service, "datetime", FakeDT)


@pytest.fixture
def pois(db_session):
    db_session.add_all([
        LocalPOI(name="Central de Autobuses de Celaya", lat=CENTRAL[0], lng=CENTRAL[1], kind="central"),
        LocalPOI(name="Villas del Bajío", address="Villas del Bajio I, 38016 Celaya, Gto., México",
                 lat=VILLAS_BAJIO[0], lng=VILLAS_BAJIO[1], kind="colonia",
                 central_price_day=140, central_price_night=150),
        LocalPOI(name="Hotel Soleil", address="Av. Constituyentes 125-Ote, 3 Guerras, 38080 Celaya, Gto., México",
                 lat=HOTEL[0], lng=HOTEL[1], kind="hotel", central_price_day=70, central_price_night=80),
        LocalPOI(name="Centro", address="Centro, 38000 Celaya, Gto., México", lat=20.5210, lng=-100.8150,
                 kind="colonia", central_price_day=70, central_price_night=70),
    ])
    db_session.commit()
    return db_session


@pytest.mark.parametrize("km,price", [(1.0, 70), (4.0, 70), (5.0, 80), (7.0, 95), (10.0, 125)])
def test_formula_de_dia(monkeypatch, km, price):
    _at_mexico_hour(monkeypatch, 12)
    assert fare_service.calculate_fare(Cfg, km) == price


@pytest.mark.parametrize("hour,night", [(21, False), (22, True), (2, True), (5, True), (6, False)])
def test_noche_suma_10_y_cruza_medianoche(monkeypatch, hour, night):
    _at_mexico_hour(monkeypatch, hour)
    assert fare_service.is_night(Cfg) is night
    assert fare_service.calculate_fare(Cfg, 7.0) == (105 if night else 95)


def test_sin_horario_de_noche_no_suma(monkeypatch):
    class Viejo:
        base_fare, per_km_rate, minimum_fare, surge_enabled = 30, 9.5, 70, False
    _at_mexico_hour(monkeypatch, 23)
    assert fare_service.calculate_fare(Viejo, 7.0) == 95


def test_desde_la_central_a_colonia_de_la_lista_cobra_la_lista(monkeypatch, pois):
    _at_mexico_hour(monkeypatch, 12)
    # una calle dentro de Villas del Bajío (~200 m del punto de la colonia)
    assert fare_service.trip_fare(pois, Cfg, *CENTRAL, 20.5618, -100.8300, 9.4) == 140
    _at_mexico_hour(monkeypatch, 23)
    assert fare_service.trip_fare(pois, Cfg, *CENTRAL, 20.5618, -100.8300, 9.4) == 150


def test_hacia_la_central_tambien(monkeypatch, pois):
    _at_mexico_hour(monkeypatch, 12)
    assert fare_service.trip_fare(pois, Cfg, *HOTEL, 20.5140, -100.8070, 2.0) == 70


def test_entre_otros_puntos_usa_la_formula(monkeypatch, pois):
    _at_mexico_hour(monkeypatch, 12)
    # Villas del Bajío → Hotel Soleil: ninguno es la Central
    assert fare_service.trip_fare(pois, Cfg, *VILLAS_BAJIO, *HOTEL, 7.0) == 95


def test_desde_la_central_a_un_punto_fuera_de_la_lista_usa_la_formula(monkeypatch, pois):
    _at_mexico_hour(monkeypatch, 12)
    assert fare_service.trip_fare(pois, Cfg, *CENTRAL, 20.4900, -100.7500, 8.0) == 105


# ── Búsqueda del bot ─────────────────────────────────────────────────────────

@pytest.fixture
def bot(monkeypatch, pois):
    monkeypatch.setattr(settings, "CITY_LAT", 20.5236)
    monkeypatch.setattr(settings, "CITY_LNG", -100.8147)
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "")
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", "")

    class NoNet:   # sin lugar local la búsqueda saldría a Google/Nominatim → 503 en la prueba
        def __init__(self, *a, **k):
            raise RuntimeError("sin red en pruebas")
    monkeypatch.setattr(whatsapp.httpx, "AsyncClient", NoNet)
    app = FastAPI()
    app.include_router(whatsapp.router)
    app.dependency_overrides[get_db] = _override_get_db
    c = TestClient(app)

    def search(q, near=None):
        params = {"q": q} | ({"lat": near[0], "lon": near[1]} if near else {})
        r = c.get("/api/v1/whatsapp/geocode", params=params, headers={"x-taxi-internal-key": "x"})
        return r.json()["results"] if r.status_code == 200 else r.status_code
    return search


@pytest.mark.parametrize("q", ["Villas del Bajio", "colonia villas del bajío", "voy a la colonia Villas del Bajío"])
def test_colonia_de_la_lista_sale_aproximada(bot, q):
    res = bot(q)
    assert [r["name"] for r in res] == ["Villas del Bajío"]
    assert res[0]["aproximado"] is True and res[0]["colonia"] == "Villas del Bajío"


@pytest.mark.parametrize("q", ["Hotel Soleil", "al soleil", "me llevas al hotel soleil por favor"])
def test_hotel_de_la_lista_sale_exacto(bot, q):
    res = bot(q)
    assert res[0]["name"] == "Hotel Soleil" and res[0]["aproximado"] is False
    assert res[0]["ciudad"] == "Celaya"


def test_lugar_de_la_lista_no_aplica_en_otra_ciudad(bot):
    # Pasajero en Salvatierra que pide "el centro": no es el Centro de Celaya
    assert bot("Centro", near=(20.2131, -100.8806)) == 503     # se fue a Google


def test_con_numero_es_una_direccion(bot):
    assert bot("Av. Villas del Bajío 120") == 503


# ── Panel: agregar/borrar lugares pide la clave ──────────────────────────────

def test_agregar_lugar_pide_clave(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "secreta")
    app = FastAPI()
    app.include_router(locations.router)
    app.dependency_overrides[get_db] = _override_get_db
    c = TestClient(app)
    body = {"name": "El Arco", "lat": 20.52, "lng": -100.81}
    assert c.post("/api/v1/locations/pois", json=body).status_code in (401, 422)
    r = c.post("/api/v1/locations/pois", json=body, headers={"x-admin-key": "secreta"})
    assert r.status_code == 201 and r.json()["kind"] == "lugar"
    assert c.delete(f"/api/v1/locations/pois/{r.json()['db_id']}").status_code in (401, 422)
    assert c.delete(f"/api/v1/locations/pois/{r.json()['db_id']}", headers={"x-admin-key": "secreta"}).status_code == 200


def test_una_palabra_solo_si_es_exacta(bot):
    assert [r["name"] for r in bot("colonia Centro")] == ["Centro"]
    assert bot("voy al centro comercial") == 503
