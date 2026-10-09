import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum


class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PAID = "paid"


class Claim:
    def __init__(self, claim_data: Dict[str, Any]):
        self.id = str(uuid.uuid7())
        self.employee_id = claim_data.get("employee_id")
        self.submitted_at = datetime.utcnow()
        self.status = ClaimStatus.SUBMITTED
        self.amount_paise = claim_data.get("amount_paise", 0)
        self.expense_date = claim_data.get("expense_date")
        self.vendor = claim_data.get("vendor", "")
        self.description = claim_data.get("description", "")
        self.erp_ref = f"ERP-{datetime.utcnow().strftime('%Y%m')}-{str(self.id)[:8].upper()}"
        
        # Status transition times (configurable)
        self.in_review_delay = 10  # seconds
        self.approved_delay = 20   # seconds after in_review
        self.paid_delay = 30       # seconds after approved
        
        # Calculate transition timestamps
        self.submitted_ts = self.submitted_at
        self.in_review_ts = self.submitted_at + timedelta(seconds=self.in_review_delay)
        self.approved_ts = self.in_review_ts + timedelta(seconds=self.approved_delay)
        self.paid_ts = self.approved_ts + timedelta(seconds=self.paid_delay)
    
    def get_current_status(self) -> ClaimStatus:
        """Get the current status based on elapsed time."""
        now = datetime.utcnow()
        
        if now >= self.paid_ts:
            return ClaimStatus.PAID
        elif now >= self.approved_ts:
            return ClaimStatus.APPROVED
        elif now >= self.in_review_ts:
            return ClaimStatus.IN_REVIEW
        else:
            return ClaimStatus.SUBMITTED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "amount_paise": self.amount_paise,
            "expense_date": self.expense_date,
            "vendor": self.vendor,
            "description": self.description,
            "erp_ref": self.erp_ref,
            "status": self.get_current_status(),
            "submitted_at": self.submitted_at.isoformat(),
            "timestamps": {
                "submitted": self.submitted_ts.isoformat(),
                "in_review": self.in_review_ts.isoformat(),
                "approved": self.approved_ts.isoformat(),
                "paid": self.paid_ts.isoformat()
            }
        }


class ERPStorage:
    def __init__(self, employees_file: str = "data/seed/employees.json"):
        self.employees_file = employees_file
        self.employees: Dict[str, Dict] = {}
        self.claims: Dict[str, Claim] = {}
        self._lock = threading.RLock()
        self.load_employees()
        
        # Start background thread to update claim statuses
        self._start_background_updater()
    
    def load_employees(self):
        """Load employees from the seed data file."""
        try:
            # Try to load from the specified path
            if os.path.isabs(self.employees_file):
                file_path = self.employees_file
            else:
                # Relative to the current working directory or mock-erp directory
                file_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", self.employees_file)
                file_path = os.path.normpath(file_path)
            
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Index employees by email for easy lookup
            for emp in data.get("employees", []):
                self.employees[emp["email"]] = emp
                
            print(f"Loaded {len(self.employees)} employees from {file_path}")
        except Exception as e:
            print(f"Warning: Could not load employees from {self.employees_file}: {e}")
            # Load some default employees for testing
            self.employees = {
                "priya@kharcha.test": {
                    "id": "0192f000-0000-7000-8000-000000000001",
                    "email": "priya@kharcha.test",
                    "name": "Priya Sharma",
                    "entitlements": [{"category": "broadband", "limit_paise": 1500000, "paid_paise": 1200000}]
                },
                "arjun@kharcha.test": {
                    "id": "0192f000-0000-7000-8000-000000000002",
                    "email": "arjun@kharcha.test",
                    "name": "Arjun Singh",
                    "entitlements": [{"category": "broadband", "limit_paise": 1500000, "paid_paise": 1490000}]  # Nearly exhausted
                }
            }
    
    def get_employee_by_email(self, email: str) -> Optional[Dict]:
        """Get employee by email."""
        with self._lock:
            return self.employees.get(email)
    
    def submit_claim(self, claim_data: Dict[str, Any]) -> Claim:
        """Submit a new reimbursement claim."""
        with self._lock:
            claim = Claim(claim_data)
            self.claims[claim.id] = claim
            return claim
    
    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get a claim by ID."""
        with self._lock:
            return self.claims.get(claim_id)
    
    def get_claims_by_employee(self, employee_id: str) -> List[Claim]:
        """Get all claims for an employee."""
        with self._lock:
            return [claim for claim in self.claims.values() if claim.employee_id == employee_id]
    
    def _update_claim_statuses(self):
        """Background task to update claim statuses (though status is computed on demand)."""
        # This is a placeholder - status is computed dynamically in get_current_status()
        # But we could use this for cleanup or notifications if needed
        pass
    
    def _start_background_updater(self):
        """Start background thread for periodic updates."""
        def update_loop():
            while True:
                time.sleep(5)  # Update every 5 seconds
                self._update_claim_statuses()
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()


# Global storage instance
storage = ERPStorage()
