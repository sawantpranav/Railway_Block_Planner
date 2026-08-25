"""FastAPI interface for the BDMS/COA AI optimization layer."""

from pathlib import Path
from typing import Optional

from planning_service import PlanningService

try:
    from fastapi import FastAPI, HTTPException
except ImportError:
    FastAPI = None


service = PlanningService(Path(__file__).parent)
app = FastAPI(title="Railway AI Block Planning API", version="1.0.0") if FastAPI else None


if app:
    @app.get("/health")
    def health():
        return {"status": "operational", "system": "BDMS/COA AI optimization layer"}

    @app.get("/tasks")
    def tasks():
        return service.score_tasks(service.load()).to_dict(orient="records")

    @app.get("/plans/{horizon}")
    def plan(horizon: str, traffic_level: str = "NORMAL", maintenance_level: str = "ALL"):
        if horizon not in {"daily", "weekly", "monthly"}:
            raise HTTPException(status_code=400, detail="horizon must be daily, weekly, or monthly")
        result = service.horizons(traffic_level, maintenance_level)[horizon]
        return result.to_dict()

    @app.get("/what-if")
    def what_if(traffic_level: str = "HIGH"):
        normal = service.run("Normal traffic", "NORMAL")
        scenario = service.run("What-if scenario", traffic_level)
        return {"normal": normal.to_dict(), "scenario": scenario.to_dict()}

    @app.post("/plans/{plan_id}/submit")
    def submit(plan_id: str, user: str = "operator"):
        try:
            return service.workflow.transition(plan_id, "SUBMITTED", user).__dict__
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app.post("/plans/{plan_id}/approve")
    def approve(plan_id: str, user: str = "approver", comment: str = ""):
        try:
            return service.workflow.transition(plan_id, "APPROVED", user, comment).__dict__
        except (KeyError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error))

    @app.get("/audit")
    def audit():
        return service.workflow.audit()
