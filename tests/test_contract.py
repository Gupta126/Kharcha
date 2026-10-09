import json
from fastapi.testclient import TestClient
from app.main import app
import yaml


def load_openapi_spec():
    """Load the OpenAPI specification from contracts/openapi.yaml."""
    with open("../contracts/openapi.yaml", "r") as f:
        return yaml.safe_load(f)
def get_app_routes(client: TestClient):
    """Extract all routes from the FastAPI app, including those from included routers."""
    routes = []

    def collect_routes(route_list, prefix=""):
        for route in route_list:
            if hasattr(route, "path") and hasattr(route, "methods"):
                # Skip HEAD and OPTIONS methods that FastAPI adds automatically
                methods = [m for m in route.methods if m not in ["HEAD", "OPTIONS"]]
                if methods:
                    # Apply the prefix to the path
                    full_path = prefix + route.path
                    routes.append({
                        "path": full_path,
                        "methods": methods
                    })
            elif hasattr(route, "include_context"):  # _IncludedRouter from include_router
                # Get the prefix from the include_context
                route_prefix = prefix + route.include_context.prefix
                # Recursively collect routes from the included router
                collect_routes(route.include_context.included_router.routes, route_prefix)
            elif hasattr(route, "routes"):  # Other mounted routes
                # Get the prefix from the route path if available
                route_prefix = prefix
                if hasattr(route, "path"):
                    route_prefix = prefix + route.path
                collect_routes(route.routes, route_prefix)

    collect_routes(app.routes)
    return routes


def test_health_endpoint_in_spec():
    """Test that the health endpoint exists in the OpenAPI spec."""
    spec = load_openapi_spec()
    client = TestClient(app)
    app_routes = get_app_routes(client)

    # Find the health endpoint in our app
    health_route = None
    for route in app_routes:
        if route["path"] == "/v1/healthz" and "GET" in route["methods"]:
            health_route = route
            break

    assert health_route is not None, "Health endpoint /v1/healthz not found in app"

    # Check that it exists in the OpenAPI spec
    assert "/v1/healthz" in spec["paths"], "Health endpoint not found in OpenAPI spec"
    assert "get" in spec["paths"]["/v1/healthz"], "GET method not defined for health endpoint in spec"

    # Check that the operation ID matches
    assert spec["paths"]["/v1/healthz"]["get"]["operationId"] == "healthz"


def test_health_endpoint_response_schema():
    """Test that the health endpoint response matches the spec."""
    spec = load_openapi_spec()
    client = TestClient(app)

    response = client.get("/v1/healthz")
    assert response.status_code == 200

    # Get the expected schema from spec
    expected_schema = spec["paths"]["/v1/healthz"]["get"]["responses"]["200"]
    expected_content = expected_schema["content"]["application/json"]["schema"]

    # Validate response against expected schema (basic validation)
    data = response.json()
    assert isinstance(data, dict)
    assert "db" in data
    assert "redis" in data
    assert "llm" in data
    assert "erp" in data

    # Check that values are strings (as per spec)
    assert isinstance(data["db"], str)
    assert isinstance(data["redis"], str)
    assert isinstance(data["llm"], str)
    assert isinstance(data["erp"], str)


def test_unknown_route_return_spec_error():
    """Test that unknown routes return SPEC-compliant error JSON."""
    client = TestClient(app)
    response = client.get("/v1/unknown-route")

    # Should return 404
    assert response.status_code == 404

    # Should return error in SPEC format
    data = response.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]
    assert "details" in data["error"]

    # Code should be a string from the allowed set
    assert isinstance(data["error"]["code"], str)
    assert data["error"]["code"] in [
        "NOT_FOUND", "VALIDATION_FAILED", "ILLEGAL_TRANSITION", "NOT_ENTITLED",
        "DUPLICATE_DOCUMENT", "LLM_UNAVAILABLE", "ERP_UNAVAILABLE", "UNAUTHORIZED", "FORBIDDEN"
    ]

    # Message should be a string
    assert isinstance(data["error"]["message"], str)
    # Details should be a dict
    assert isinstance(data["error"]["details"], dict)


def test_app_has_expected_base_structure():
    """Test that the app has the basic structure expected."""
    client = TestClient(app)
    app_routes = get_app_routes(client)

    # Should have at least the health endpoint
    paths = [route["path"] for route in app_routes]
    assert "/v1/healthz" in paths

    # Should have the v1 prefix
    v1_paths = [p for p in paths if p.startswith("/v1/")]
    assert len(v1_paths) > 0, "No paths with /v1/ prefix found"