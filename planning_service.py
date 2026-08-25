"""Shared application service used by the dashboard and API."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pandas as pd

from ai_optimization_layer import AIPriorityEngine, Recommendation, RecommendationEngine, SyntheticDataAdapter
from cp_sat_optimizer import CPSATOptimizer
from workflow import PlanWorkflow


@dataclass
class ScenarioResult:
    scenario: str
    solver_status: str
    recommendations: List[Recommendation]
    total_tasks: int
    scheduled_tasks: int
    total_delay_minutes: float
    block_utilization: float
    downtime_hours: float
    downtime_reduction: float
    deadline_alerts: int
    unmet_task_ids: List[str]
    resource_violations: List[str]

    def to_dict(self):
        result = asdict(self)
        result["recommendations"] = [asdict(item) for item in self.recommendations]
        return result


class PlanningService:
    """Orchestrates data, scoring, optimization, scenarios and workflow."""

    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.adapter = SyntheticDataAdapter(self.data_dir)
        self.recommender = RecommendationEngine()
        self.optimizer = CPSATOptimizer()
        self.workflow = PlanWorkflow(str(self.data_dir / "output" / "plan_workflow.json"))

    def load(self):
        data = self.adapter.load()
        resources_path = self.data_dir / "resource_capacity.csv"
        geo_path = self.data_dir / "geo_reference.csv"
        data["resources"] = pd.read_csv(resources_path) if resources_path.exists() else pd.DataFrame()
        data["geo"] = pd.read_csv(geo_path) if geo_path.exists() else pd.DataFrame()
        return data

    def score_tasks(self, data):
        return AIPriorityEngine.score_tasks(data["tasks"], data.get("history"))

    def run(self, scenario: str = "Normal traffic", traffic_level: str = "NORMAL", maintenance_level: str = "ALL", horizon_days: int = 7, max_blocks: int = None) -> ScenarioResult:
        data = self.load()
        today = pd.Timestamp.now().normalize()
        tasks = self.score_tasks(data)
        tasks = tasks[tasks["deadline"] <= today + pd.Timedelta(days=horizon_days)].copy()
        blocks = data["blocks"][data["blocks"]["start"] <= today + pd.Timedelta(days=horizon_days)].copy()
        selected_blocks, solver_status = self.optimizer.select(tasks, blocks, data.get("forecast"), max_blocks)
        if solver_status == "INFEASIBLE":
            selected_blocks = blocks.iloc[0:0]
        scenario_data = dict(data)
        scenario_data["tasks"] = tasks
        scenario_data["blocks"] = selected_blocks
        recommendations = self.recommender.recommend(
            scenario_data, traffic_level=traffic_level, maintenance_level=maintenance_level
        )
        scheduled_ids = {task_id for item in recommendations for task_id in item.task_ids}
        total_effort = float(tasks["estimated_duration"].sum()) if not tasks.empty else 0.0
        downtime = sum((item.end - item.start).total_seconds() / 3600 for item in recommendations)
        utilization = sum(item.utilization for item in recommendations) / len(recommendations) if recommendations else 0.0
        alerts = int(((tasks["deadline"] - today).dt.days <= 7).sum()) if not tasks.empty else 0
        resource_violations = self._resource_violations(recommendations, data["resources"])
        return ScenarioResult(
            scenario=scenario,
            solver_status=solver_status,
            recommendations=recommendations,
            total_tasks=len(tasks),
            scheduled_tasks=len(scheduled_ids),
            total_delay_minutes=sum(item.train_delay_minutes for item in recommendations),
            block_utilization=utilization,
            downtime_hours=downtime,
            downtime_reduction=max(0.0, (total_effort - downtime) / total_effort) if total_effort else 0.0,
            deadline_alerts=alerts,
            unmet_task_ids=sorted(set(tasks["task_id"]) - scheduled_ids),
            resource_violations=resource_violations,
        )

    @staticmethod
    def _resource_violations(recommendations, resources):
        if resources.empty:
            return []
        violations = []
        for recommendation in recommendations:
            for department in recommendation.departments:
                match = resources[
                    (resources["department"] == department)
                    & (resources["section"] == recommendation.section)
                ]
                if not match.empty and recommendation.end - recommendation.start > timedelta(hours=float(match.iloc[0]["available_team_hours"])):
                    violations.append(f"{department} capacity exceeded in {recommendation.section}")
        return violations

    def horizons(self, traffic_level: str = "NORMAL", maintenance_level: str = "ALL") -> Dict[str, ScenarioResult]:
        return {
            "daily": self.run("Daily plan", traffic_level, maintenance_level, 1),
            "weekly": self.run("Weekly plan", traffic_level, maintenance_level, 7),
            "monthly": self.run("Monthly plan", traffic_level, maintenance_level, 30),
        }

    def create_plan(self, result: ScenarioResult, user: str = "AI Optimization Engine"):
        return self.workflow.create(f"PLAN-{datetime.now():%Y%m%d%H%M%S}", user)
