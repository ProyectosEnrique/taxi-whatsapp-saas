"""Búsqueda de lugares para el bot: Places primero, sin resultados de nivel ciudad,
marca de aproximado, colonia/ciudad y búsqueda cerca del pasajero.
Google y Nominatim se simulan: no sale nada a la red."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.config import settings
from src.routers import whatsapp

CELAYA = (20.5236, -100.8147)
SALVATIERRA = (20.2131, -100.8806)


def _place(name, lat, lng, types, colonia="", ciudad="Celaya"):
    comps = []
    if colonia:
        comps.append({"longText": colonia, "types": ["sublocality_level_1", "sublocality", "political"]})
    if ciudad:
        comps.append({"longText": ciudad, "types": ["locality", "political"]})
    return {"displayName": {"text": name}, "formattedAddress": f"{name}, {colonia}, {ciudad}, Gto., México",
            "location": {"latitude": lat, "longitude": lng}, "types": types, "addressComponents": comps}


class _Resp:
    def __init__(self, data, status=200):
        self._data, self.status_code, self.text = data, status, str(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


@pytest.fixture
def google(monkeypatch):
    """Simula Places y Geocoding; guarda qué se pidió."""
    calls = {"places": [], "geocode": [], "nominatim": []}
    data = {"places": [], "places_status": 200, "geocode": [], "nominatim": []}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, url, json=None, headers=None):
            calls["places"].append(json)
            return _Resp({"places": data["places"]}, data["places_status"])

        async def get(self, url, params=None, headers=None):
            if "nominatim" in url:
                calls["nominatim"].append(params)
                return _Resp(data["nominatim"])
            calls["geocode"].append(params)
            return _Resp({"status": "OK" if data["geocode"] else "ZERO_RESULTS", "results": data["geocode"]})

    monkeypatch.setattr(whatsapp.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "GOOGLE_MAPS_API_KEY", "k")
    monkeypatch.setattr(settings, "CITY_LAT", CELAYA[0])
    monkeypatch.setattr(settings, "CITY_LNG", CELAYA[1])
    monkeypatch.setattr(settings, "CITY_BBOX_DEG", 0.3)
    monkeypatch.setattr(settings, "WHATSAPP_SECRET", "")
    return calls, data


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(whatsapp.router)
    return TestClient(app)


def _search(client, q, near=None):
    params = {"q": q}
    if near:
        params.update(lat=near[0], lon=near[1])
    r = client.get("/api/v1/whatsapp/geocode", params=params, headers={"x-taxi-internal-key": "x"})
    assert r.status_code == 200
    return r.json()["results"]


def test_named_place_comes_from_places_with_colonia_and_city(client, google):
    calls, data = google
    data["places"] = [_place("Hospital General de Celaya", 20.53, -100.81,
                             ["hospital", "point_of_interest", "establishment"], "Col. Centro")]
    res = _search(client, "Hospital General")
    assert res[0]["name"] == "Hospital General de Celaya"
    assert res[0]["colonia"] == "Col. Centro" and res[0]["ciudad"] == "Celaya"
    assert res[0]["aproximado"] is False
    assert calls["geocode"] == []          # Places bastó


def test_city_level_result_is_never_used(client, google):
    # Google no encontró el hospital y devolvió "Celaya" (el centro): el taxi iría al centro
    _, data = google
    data["places"] = [_place("Celaya", *CELAYA, ["locality", "political"], ciudad="Celaya")]
    data["geocode"] = [{"formatted_address": "Celaya, Gto., México",
                        "geometry": {"location": {"lat": CELAYA[0], "lng": CELAYA[1]}, "location_type": "APPROXIMATE"},
                        "types": ["locality", "political"],
                        "address_components": [{"long_name": "Celaya", "types": ["locality", "political"]}]}]
    assert _search(client, "Hospital Inventado Celaya") == []


def test_colonia_only_is_marked_approximate(client, google):
    _, data = google
    data["places"] = [_place("Las Insurgentes", 20.54, -100.80, ["neighborhood", "political"],
                             "Las Insurgentes")]
    res = _search(client, "colonia Las Insurgentes")
    assert len(res) == 1 and res[0]["aproximado"] is True


def test_exact_results_go_first(client, google):
    _, data = google
    data["places"] = [
        _place("Calle Hidalgo", 20.52, -100.81, ["route"]),
        _place("Hidalgo 45", 20.521, -100.812, ["street_address"]),
    ]
    res = _search(client, "Hidalgo 45")
    assert res[0]["name"] == "Hidalgo 45" and res[0]["aproximado"] is False
    assert res[1]["aproximado"] is True


def test_search_is_biased_near_the_passenger(client, google):
    calls, data = google
    data["places"] = [_place("Jardín Principal", 20.2135, -100.8800, ["park", "point_of_interest"],
                             "Centro", "Salvatierra")]
    res = _search(client, "Jardín Principal", near=SALVATIERRA)
    center = calls["places"][0]["locationBias"]["circle"]["center"]
    assert (center["latitude"], center["longitude"]) == SALVATIERRA
    assert res[0]["ciudad"] == "Salvatierra"


def test_far_from_everything_is_rejected(client, google):
    _, data = google
    data["places"] = [_place("Hidalgo 45", 19.43, -99.13, ["street_address"], ciudad="CDMX")]
    assert _search(client, "Hidalgo 45") == []


def test_falls_back_to_geocoding_when_places_is_not_enabled(client, google):
    calls, data = google
    data["places_status"] = 403     # Places API (New) sin habilitar
    data["geocode"] = [{"formatted_address": "Av. Juárez 120, Zona Centro, Celaya, Gto., México",
                        "geometry": {"location": {"lat": 20.522, "lng": -100.814}, "location_type": "ROOFTOP"},
                        "types": ["street_address"],
                        "address_components": [
                            {"long_name": "Zona Centro", "types": ["sublocality_level_1", "sublocality", "political"]},
                            {"long_name": "Celaya", "types": ["locality", "political"]}]}]
    res = _search(client, "Av Juárez 120")
    assert res[0]["colonia"] == "Zona Centro" and res[0]["aproximado"] is False
    assert len(calls["geocode"]) == 1


def test_nominatim_last_resort_also_drops_city_level(client, google):
    _, data = google
    data["places_status"] = 403
    data["nominatim"] = [{"display_name": "Celaya, Guanajuato, México", "lat": str(CELAYA[0]),
                          "lon": str(CELAYA[1]), "addresstype": "city", "address": {"city": "Celaya"}}]
    assert _search(client, "Calle Rara Celaya") == []
