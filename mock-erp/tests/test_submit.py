from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_submit_claim_success():
    """Test successful claim submission."""
    claim_data = {
        "employee_id": "priya@kharcha.test",
        "amount_paise": 100000,
        "expense_date": "2026-10-09",
        "vendor": "Test Vendor",
        "description": "Test expense"
    }
    
    response = client.post("/erp/submit", json=claim_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "submitted"
    assert "erp_ref" in data
    assert data["erp_ref"].startswith("ERP-")
    assert "claim_id" in data


def test_submit_claim_missing_fields():
    """Test claim submission with missing required fields."""
    claim_data = {
        "employee_id": "priya@kharcha.test"
        # Missing amount_paise
    }
    
    response = client.post("/erp/submit", json=claim_data)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data


def test_submit_claim_invalid_employee():
    """Test claim submission with invalid employee."""
    claim_data = {
        "employee_id": "invalid@kharcha.test",
        "amount_paise": 100000
    }
    
    response = client.post("/erp/submit", json=claim_data)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Employee not found" in data["detail"]
