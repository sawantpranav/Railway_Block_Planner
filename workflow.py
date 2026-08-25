"""Lightweight approval and audit workflow for generated recommendations."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import Any, Dict, List


@dataclass
class PlanRecord:
    plan_id: str
    status: str = "DRAFT"
    created_by: str = "AI Optimization Engine"
    approver: str = ""
    comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    approved_at: str = ""


class PlanWorkflow:
    """Persist plan state transitions and audit events in a local JSON file."""

    def __init__(self, path: str = "output/plan_workflow.json"):
        self.path = Path(path)
        self.path.parent.mkdir(exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"plans": {}, "audit": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def create(self, plan_id: str, user: str = "AI Optimization Engine") -> PlanRecord:
        data = self._read()
        record = PlanRecord(plan_id=plan_id, created_by=user)
        data["plans"][plan_id] = asdict(record)
        data["audit"].append({"event": "PLAN_CREATED", "plan_id": plan_id, "at": record.created_at, "user": user})
        self._write(data)
        return record

    def transition(self, plan_id: str, status: str, user: str, comment: str = "") -> PlanRecord:
        data = self._read()
        if plan_id not in data["plans"]:
            raise KeyError(f"Unknown plan: {plan_id}")
        record = data["plans"][plan_id]
        allowed = {"DRAFT": {"SUBMITTED", "CANCELLED"}, "SUBMITTED": {"APPROVED", "REJECTED"}, "REJECTED": {"DRAFT"}, "APPROVED": set(), "CANCELLED": set()}
        if status not in allowed.get(record["status"], set()):
            raise ValueError(f"Cannot transition {record['status']} to {status}")
        record["status"] = status
        record["approver"] = user if status in {"APPROVED", "REJECTED"} else record.get("approver", "")
        record["comment"] = comment
        if status == "APPROVED":
            record["approved_at"] = datetime.now().isoformat(timespec="seconds")
        data["audit"].append({"event": f"PLAN_{status}", "plan_id": plan_id, "at": datetime.now().isoformat(timespec="seconds"), "user": user, "comment": comment})
        self._write(data)
        return PlanRecord(**record)

    def get(self, plan_id: str) -> PlanRecord:
        record = self._read()["plans"].get(plan_id)
        if not record:
            raise KeyError(f"Unknown plan: {plan_id}")
        return PlanRecord(**record)

    def audit(self) -> List[Dict[str, Any]]:
        return self._read()["audit"]
