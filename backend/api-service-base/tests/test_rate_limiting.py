def test_login_is_rate_limited_after_threshold(client):
    """El límite es 10/minuto — el intento 11 debe rechazarse con 429."""
    payload = {"phone": "+521111111111", "password": "wrong-password"}
    for _ in range(10):
        resp = client.post("/api/v1/customer/login", json=payload)
        assert resp.status_code == 401  # credenciales incorrectas, pero no limitado aún

    resp = client.post("/api/v1/customer/login", json=payload)
    assert resp.status_code == 429


def test_register_is_rate_limited_after_threshold(client):
    """El límite es 5/minuto — el intento 6 debe rechazarse con 429 aunque
    cada registro use un teléfono distinto (el límite es por IP, no por
    teléfono — protege contra automatizar altas masivas)."""
    for i in range(5):
        resp = client.post("/api/v1/customer/register", json={
            "phone": f"+52111111{i:04d}", "password": "secret123", "name": "Test",
        })
        assert resp.status_code == 200

    resp = client.post("/api/v1/customer/register", json={
        "phone": "+521111119999", "password": "secret123", "name": "Test",
    })
    assert resp.status_code == 429
