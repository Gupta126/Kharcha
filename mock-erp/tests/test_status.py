from fastapi.testclient import TestClient
from app.main import app
import time

client = TestClient(app)


def test_get_claim_by_id():
    """Test getting a claim by its ID."""
    # First submit a claim
    claim_data = {
        "employee_id": "priya@kharcha.test",
        "amount_paise": 100000,
        "expense_date": "2026-10-09",
        "vendor": "Test Vendor",
        "description": "Test expense"
    }
    
    submit_response = client.post("/erp/submit", json=claim_data)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()
    claim_id = submit_data["claim_id"]
    
    # Now get the claim by ID
    response = client.get(f"/erp/claim/{claim_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == claim_id
    assert data["employee_id"] == "priya@kharcha.test"
    assert data["amount_paise"] == 100000
    assert data["status"] in ["submitted", "in_review", "approved", "paid"]


def test_get_claim_by_erp_ref():
    """Test getting a claim by its ERP reference."""
    # First submit a claim
    claim_data = {
        "employee_id": "priya@kharcha.test",
        "amount_paise": 100000,
        "expense_date": "2026-10-09",
        "vendor": "Test Vendor",
        "description": "Test expense"
    }
    
    submit_response = client.post("/erp/submit", json=claim_data)
    assert submit_response.status_code == 200
    submit_data = submit_response.json()
    erp_ref = submit_data["erp_ref"]
    
    # Now get the claim by ERP reference
    response = client.get(f"/erp/claim/{erp_ref}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["erp_ref"] == erp_ref
    assert data["id"] == submit_data["claim_id"]


def test_get_nonexistent_claim():
    """Test getting a claim that doesn't exist."""
    response = client.get("/erp/claim/nonexistent-id")
    assert response.status_code == 404
    
    data = response.json()
    assert "detail" in data


def test_get_employee_claims():
    """Test getting all claims for an employee."""
    # Submit a couple of claims
    claim_data1 = {
        "employee_id": "priya@kharcha.test",
        "amount_paise": 100000,
        "expense_date": "2026-10-09",
        "vendor": "Test Vendor 1",
        "description": "Test expense 1"
    }
    
    claim_data2 = {
        "employee_id": "priya@kharcha.test",
        "amount_paise": 200000,
        "expense_date": "2026-10-08",
        "vendor": "Test Vendor 2",
        "description": "Test expense 2"
    }
    
    client.post("/erp/submit", json=claim_data1)
    client.post("/erp/submit", json=claim_data2)
    
    # Get claims for the employee
    response = client.get("/erp/claims/priya@kharcha.test")
    assert response.status_code == 200
    
    data = response.json()
    assert "employee" in data
    assert data["employee"]["email"] == "priya@kharcha.test"
    assert "claims" in data
    assert len(data["claims"]) >= 2
