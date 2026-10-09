from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_scenario():
    """Test getting current scenario configuration."""
    response = client.get("/admin/scenario")
    assert response.status_code == 200
    
    data = response.json()
    assert "in_review_delay" in data
    assert "approved_delay" in data
    assert "paid_delay" in data
    assert isinstance(data["in_review_delay"], int)
    assert isinstance(data["approved_delay"], int)
    assert isinstance(data["paid_delay"], int)


def test_configure_scenario():
    """Test configuring scenario timings."""
    config_data = {
        "in_review_delay": 5,
        "approved_delay": 10,
        "paid_delay": 15
    }
    
    response = client.post("/admin/scenario", json=config_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "scenario_updated"
    assert "in_review_delay" in data["updated_fields"]
    assert "approved_delay" in data["updated_fields"]
    assert "paid_delay" in data["updated_fields"]
    
    # Verify the values were updated
    response = client.get("/admin/scenario")
    assert response.status_code == 200
    data = response.json()
    assert data["in_review_delay"] == 5
    assert data["approved_delay"] == 10
    assert data["paid_delay"] == 15


def test_configure_scenario_partial():
    """Test configuring only some scenario timings."""
    # First set known values
    client.post("/admin/scenario", json={
        "in_review_delay": 10,
        "approved_delay": 20,
        "paid_delay": 30
    })
    
    # Now update only one field
    config_data = {
        "in_review_delay": 5
    }
    
    response = client.post("/admin/scenario", json=config_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "scenario_updated"
    assert "in_review_delay" in data["updated_fields"]
    assert "approved_delay" not in data["updated_fields"]
    assert "paid_delay" not in data["updated_fields"]
    
    # Verify the values
    response = client.get("/admin/scenario")
    assert response.status_code == 200
    data = response.json()
    assert data["in_review_delay"] == 5
    assert data["approved_delay"] == 20  # Unchanged
    assert data["paid_delay"] == 30      # Unchanged
