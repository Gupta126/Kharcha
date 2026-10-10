from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ARJUN = "0192f000-0000-7000-8000-000000000002"


def test_list_employees():
    r = client.get("/employees")
    assert r.status_code == 200
    assert {e["email"] for e in r.json()} == {
        "priya@kharcha.test", "arjun@kharcha.test", "meera@kharcha.test", "vikram@kharcha.test"}


def test_get_employee_by_id_and_email():
    by_id = client.get(f"/employees/{ARJUN}")
    by_email = client.get("/employees/arjun@kharcha.test")
    assert by_id.status_code == by_email.status_code == 200
    assert by_id.json() == by_email.json()
    assert "entitlements" not in by_id.json()


def test_arjun_broadband_is_exhausted():
    r = client.get(f"/employees/{ARJUN}/entitlements")
    assert r.status_code == 200
    bb = next(e for e in r.json()["entitlements"] if e["category"] == "broadband")
    assert bb["paid_paise"] == bb["limit_paise"] == 1500000


def test_unknown_employee_is_404():
    assert client.get("/employees/nobody@kharcha.test").status_code == 404


def test_prd_route_names_exist():
    paths = app.openapi()["paths"]
    assert "/reimbursements" in paths and "/reimbursements/{ref}" in paths
