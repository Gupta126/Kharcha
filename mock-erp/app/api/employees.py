"""Employee and entitlement endpoints (PRD §22). Data comes from data/seed/employees.json."""
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["employees"])


def _seed_file() -> Path:
    candidates: list[Path] = []
    if os.environ.get("SEED_DIR"):
        candidates.append(Path(os.environ["SEED_DIR"]))
    candidates.append(Path("/data/seed"))                                   # container mount
    candidates.append(Path(__file__).resolve().parents[3] / "data" / "seed")  # repo checkout
    for folder in candidates:
        f = folder / "employees.json"
        if f.is_file():
            return f
    raise RuntimeError("employees.json not found; set SEED_DIR")


@lru_cache(maxsize=1)
def _employees() -> dict[str, dict[str, Any]]:
    data = json.loads(_seed_file().read_text(encoding="utf-8"))
    return {e["id"]: e for e in data["employees"]}


def _find(employee_id_or_email: str) -> dict[str, Any]:
    emps = _employees()
    emp = emps.get(employee_id_or_email) or next(
        (e for e in emps.values() if e["email"] == employee_id_or_email), None
    )
    if emp is None:
        raise HTTPException(status_code=404, detail="employee not found")
    return emp


def _public(emp: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in emp.items() if k != "entitlements"}


@router.get("/employees")
def list_employees() -> list[dict[str, Any]]:
    return [_public(e) for e in _employees().values()]


@router.get("/employees/{employee_id}")
def get_employee(employee_id: str) -> dict[str, Any]:
    return _public(_find(employee_id))


@router.get("/employees/{employee_id}/entitlements")
def get_entitlements(employee_id: str) -> dict[str, Any]:
    emp = _find(employee_id)
    return {"employee_id": emp["id"], "entitlements": emp["entitlements"]}
