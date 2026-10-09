import base64


def test_health_check_remains_public_when_authentication_is_enabled(client, monkeypatch):
    monkeypatch.setenv("CAMPUSFLOW_PASSWORD", "strong-test-password")
    assert client.get("/api/health").status_code == 200


def test_protected_routes_require_valid_basic_auth(client, monkeypatch):
    monkeypatch.setenv("CAMPUSFLOW_PASSWORD", "strong-test-password")
    monkeypatch.setenv("CAMPUSFLOW_USERNAME", "campus-admin")

    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/dashboard", auth=("campus-admin", "wrong")).status_code == 401
    response = client.get("/api/dashboard", auth=("campus-admin", "strong-test-password"))
    assert response.status_code == 200


def test_malformed_auth_header_is_rejected(client, monkeypatch):
    monkeypatch.setenv("CAMPUSFLOW_PASSWORD", "strong-test-password")
    invalid_header = base64.b64encode(b"missing-separator").decode("ascii")
    response = client.get("/api/dashboard", headers={"Authorization": f"Basic {invalid_header}"})
    assert response.status_code == 401
