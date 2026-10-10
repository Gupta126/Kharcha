from pathlib import Path

import yaml

from app.main import app

# Paths defined in the OpenAPI contract but not yet implemented in FastAPI.
UNBUILT_PATHS = {
    "/v1/auth/login",
    "/v1/documents",
    "/v1/claims/draft",
    "/v1/claims/{id}",
    "/v1/claims/{id}/validate",
    "/v1/claims/{id}/submit",
    "/v1/agent/messages",
    "/v1/entitlements",
    "/v1/approvals/{id}",
}


def get_openapi_spec():
    contract_path = Path(__file__).parent.parent.parent / "contracts" / "openapi.yaml"
    with open(contract_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_contract_coverage():
    spec = get_openapi_spec()
    spec_paths = spec.get("paths", {})

    # Generate the FastAPI OpenAPI schema
    fastapi_openapi = app.openapi()
    fastapi_paths = fastapi_openapi.get("paths", {})
    fastapi_schemas = fastapi_openapi.get("components", {}).get("schemas", {})

    for path, path_item in spec_paths.items():
        if path in UNBUILT_PATHS:
            continue

        assert path in fastapi_paths, (
            f"Contract path {path} is not implemented in FastAPI and not in UNBUILT_PATHS."
        )

        for method, operation in path_item.items():
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            assert method.lower() in fastapi_paths[path], (
                f"Method {method.upper()} for path {path} is in contract but missing in FastAPI."
            )

            fastapi_operation = fastapi_paths[path][method.lower()]

            success_resp = operation.get("responses", {}).get("200")
            if success_resp and "content" in success_resp:
                json_content = success_resp["content"].get("application/json")
                if json_content and "schema" in json_content:
                    # Contract schema
                    ref = json_content["schema"].get("$ref")
                    assert ref is not None, "Contract schema must use $ref for 200 responses"
                    schema_name = ref.split("/")[-1]
                    contract_schema = spec["components"]["schemas"][schema_name]

                    # FastAPI schema
                    fastapi_success = fastapi_operation.get("responses", {}).get("200")
                    assert fastapi_success is not None, (
                        f"FastAPI missing 200 response for {method.upper()} {path}"
                    )
                    fastapi_json = fastapi_success.get("content", {}).get("application/json")
                    assert fastapi_json is not None, (
                        f"FastAPI 200 response missing application/json for {method.upper()} {path}"
                    )
                    fastapi_ref = fastapi_json.get("schema", {}).get("$ref")
                    assert fastapi_ref is not None, (
                        f"FastAPI schema missing $ref for {method.upper()} {path}"
                    )
                    fastapi_schema_name = fastapi_ref.split("/")[-1]
                    fastapi_model_schema = fastapi_schemas[fastapi_schema_name]

                    # Verify fields match
                    fastapi_fields = set(fastapi_model_schema.get("properties", {}).keys())
                    contract_fields = set(contract_schema.get("properties", {}).keys())

                    missing = contract_fields - fastapi_fields
                    extra = fastapi_fields - contract_fields
                    assert not missing, f"FastAPI model missing fields from contract: {missing}"
                    assert not extra, f"FastAPI model has extra fields not in contract: {extra}"

    # Check if FastAPI implements any /v1 paths NOT in the contract
    for path, methods in fastapi_paths.items():
        if not path.startswith("/v1/"):
            continue  # ignore internal or test routes if they don't start with /v1/
        if path.startswith("/v1/_test"):
            continue  # ignore test routes

        assert path in spec_paths, f"FastAPI implements {path} which is not in the contract"
        for method in methods.keys():
            assert method in spec_paths[path], (
                f"FastAPI implements {method.upper()} {path} which is not in the contract"
            )
