"""BDMS/COA-compatible AI recommendation layer for the SIH prototype.

This module consumes synthetic extracts shaped like TMS, SMMS, TDMS and COA
feeds. It recommends coordinated work windows without replacing BDMS or COA.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError:
    RandomForestClassifier = None


PRIORITY_WEIGHTS = {
    "safety_criticality": 0.30,
    "severity": 0.25,
    "urgency": 0.20,
    "asset_criticality": 0.15,
    "traffic_impact": 0.10,
}


@dataclass
class Recommendation:
    block_id: str
    section: str
    task_ids: List[str]
    departments: List[str]
    start: datetime
    end: datetime
    priority_score: float
    priority_class: str
    train_delay_minutes: float
    utilization: float
    reasons: List[str]


class SyntheticDataAdapter:
    """Standardize synthetic source extracts into planner-ready tables."""

    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)

    def load(self) -> Dict[str, pd.DataFrame]:
        tasks = pd.read_csv(self.data_dir / "maintenance_tasks.csv")
        trains = pd.read_csv(self.data_dir / "train_schedule.csv")
        blocks = pd.read_csv(self.data_dir / "block_windows.csv")
        forecast = pd.read_csv(self.data_dir / "goods_train_forecast.csv")
        history = pd.read_csv(self.data_dir / "maintenance_history.csv")
        return {
            "tasks": self._clean_tasks(tasks),
            "trains": self._clean_trains(trains),
            "blocks": self._clean_blocks(blocks),
            "forecast": self._clean_forecast(forecast),
            "history": history,
        }

    @staticmethod
    def _clean_tasks(tasks: pd.DataFrame) -> pd.DataFrame:
        tasks = tasks.copy()
        tasks.columns = [column.strip().lower() for column in tasks.columns]
        numeric_columns = [
            "severity", "safety_criticality", "overdue_days",
            "estimated_duration", "failure_history", "asset_criticality",
        ]
        for column in numeric_columns:
            tasks[column] = pd.to_numeric(tasks[column], errors="coerce").fillna(0)
        tasks["deadline"] = pd.to_datetime(tasks["deadline"], errors="coerce")
        return tasks.dropna(subset=["task_id", "department", "location", "deadline"])

    @staticmethod
    def _clean_trains(trains: pd.DataFrame) -> pd.DataFrame:
        trains = trains.copy()
        trains["arrival_time"] = pd.to_datetime(trains["arrival_time"])
        trains["departure_time"] = pd.to_datetime(trains["departure_time"])
        trains["traffic_density"] = pd.to_numeric(
            trains["traffic_density"], errors="coerce"
        ).fillna(0.5)
        return trains

    @staticmethod
    def _clean_blocks(blocks: pd.DataFrame) -> pd.DataFrame:
        blocks = blocks.copy()
        blocks["start"] = pd.to_datetime(
            blocks["date"] + " " + blocks["start_time"]
        )
        blocks["end"] = pd.to_datetime(
            blocks["date"] + " " + blocks["end_time"]
        )
        blocks["available_duration"] = pd.to_numeric(
            blocks["available_duration"], errors="coerce"
        ).fillna(0)
        return blocks

    @staticmethod
    def _clean_forecast(forecast: pd.DataFrame) -> pd.DataFrame:
        forecast = forecast.copy()
        forecast["forecast_date"] = pd.to_datetime(forecast["forecast_date"])
        forecast["expected_traffic_intensity"] = pd.to_numeric(
            forecast["expected_traffic_intensity"], errors="coerce"
        ).fillna(0.5)
        return forecast


class AIPriorityEngine:
    """Rule-based explainable priority model with an ML-ready interface."""

    @staticmethod
    def score_tasks(tasks: pd.DataFrame, history: pd.DataFrame = None) -> pd.DataFrame:
        scored = tasks.copy()
        scored["urgency"] = (scored["overdue_days"] / 14 * 10).clip(0, 10)
        scored["traffic_impact"] = (
            scored["asset_criticality"] * 0.6 + scored["severity"] * 0.4
        ).clip(0, 10)
        scored["priority_score"] = sum(
            scored[column] * weight for column, weight in PRIORITY_WEIGHTS.items()
        )
        scored["predicted_risk"] = AIPriorityEngine._predict_risk(scored, history)
        scored["priority_score"] = (
            scored["priority_score"] * 0.8 + scored["predicted_risk"] * 0.2
        ).clip(0, 10)
        scored["priority_class"] = pd.cut(
            scored["priority_score"],
            bins=[-1, 3.9, 5.9, 7.9, 10],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        ).astype(str)
        return scored.sort_values("priority_score", ascending=False)

    @staticmethod
    def _predict_risk(tasks: pd.DataFrame, history: pd.DataFrame = None) -> pd.Series:
        features = ["severity", "safety_criticality", "overdue_days", "failure_history", "asset_criticality"]
        if tasks.empty:
            return pd.Series(index=tasks.index, dtype=float)

        task_matrix = tasks[features]
        if task_matrix.empty:
            return pd.Series(index=tasks.index, dtype=float)

        fallback = (task_matrix.mean(axis=1) / 10 * 10).clip(0, 10)
        if RandomForestClassifier is None or history is None or history.empty:
            return fallback

        history = history.copy()
        if "asset_criticality" not in history.columns:
            history["asset_criticality"] = history["safety_criticality"]
        for feature in features:
            history[feature] = pd.to_numeric(history[feature], errors="coerce")
        available = history.dropna(subset=features + ["completion_status"])
        if available.empty or available["completion_status"].nunique() < 2 or len(available) < 8:
            return fallback

        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
        labels = (available["completion_status"].astype(str).str.upper() != "COMPLETED").astype(int)
        try:
            model.fit(available[features], labels)
        except ValueError:
            return fallback

        if getattr(model, "classes_", None) is None or len(model.classes_) < 2:
            return fallback

        risk_index = list(model.classes_).index(1) if 1 in model.classes_ else 0
        if task_matrix.empty:
            return fallback
        return pd.Series(model.predict_proba(task_matrix)[:, risk_index] * 10, index=tasks.index)


class RecommendationEngine:
    """Combine compatible departmental work and select low-impact windows."""

    def recommend(
        self,
        data: Dict[str, pd.DataFrame],
        traffic_level: str = "NORMAL",
        maintenance_level: str = "ALL",
    ) -> List[Recommendation]:
        tasks = AIPriorityEngine.score_tasks(data["tasks"], data.get("history"))
        blocks = data["blocks"].copy()
        trains = data["trains"]
        forecast = data.get("forecast", pd.DataFrame())
        traffic_multiplier = {"LOW": 0.6, "NORMAL": 1.0, "HIGH": 1.35}[traffic_level]
        recommendations = []

        for section, section_tasks in tasks.groupby("location", sort=False):
            if maintenance_level == "CRITICAL":
                section_tasks = section_tasks[
                    section_tasks["priority_score"] >= 6.0
                ]
            if section_tasks.empty:
                continue

            compatible = blocks[blocks["section"] == section].copy()
            # Coordinated teams share the window; the block must cover the
            # longest activity rather than adding parallel work durations.
            coordinated_duration = section_tasks["estimated_duration"].max()
            compatible = compatible[
                compatible["available_duration"] >= coordinated_duration
            ]
            if compatible.empty:
                continue

            compatible["train_delay"] = compatible.apply(
                lambda block: self._train_delay(
                    block, trains, forecast, traffic_multiplier
                ),
                axis=1,
            )
            selected = compatible.sort_values(
                ["train_delay", "start"]
            ).iloc[0]
            departments = sorted(section_tasks["department"].unique().tolist())
            score = float(section_tasks["priority_score"].max())
            reasons = self._explain(section_tasks, selected, coordinated_duration)
            recommendations.append(
                Recommendation(
                    block_id=selected["block_id"],
                    section=section,
                    task_ids=section_tasks["task_id"].tolist(),
                    departments=departments,
                    start=selected["start"].to_pydatetime(),
                    end=(selected["start"] + timedelta(hours=coordinated_duration)).to_pydatetime(),
                    priority_score=score,
                    priority_class=str(section_tasks.iloc[0]["priority_class"]),
                    train_delay_minutes=float(selected["train_delay"]),
                    utilization=float(coordinated_duration / selected["available_duration"]),
                    reasons=reasons,
                )
            )
        return recommendations

    @staticmethod
    def _train_delay(
        block: pd.Series,
        trains: pd.DataFrame,
        forecast: pd.DataFrame,
        multiplier: float,
    ) -> float:
        overlaps = trains[
            (trains["departure_time"] <= block["end"])
            & (trains["arrival_time"] >= block["start"])
        ]
        forecast_row = forecast[forecast["section"] == block["section"]]
        forecast_impact = (
            float(forecast_row["expected_traffic_intensity"].iloc[0])
            if not forecast_row.empty else 0.0
        )
        return float((overlaps["traffic_density"].sum() * 12 + forecast_impact * 8) * multiplier)

    @staticmethod
    def _explain(tasks: pd.DataFrame, block: pd.Series, duration: float) -> List[str]:
        reasons = [
            f"{len(tasks)} compatible department activities share section {block['section']}",
            f"shared work fits in the {duration:.1f}-hour window",
            f"block utilization is {duration / block['available_duration']:.0%}",
        ]
        if block["traffic_level"] == "LOW":
            reasons.append("COA window has LOW traffic")
        if tasks["priority_score"].max() >= 8:
            reasons.append("highest-priority task is safety-critical")
        return reasons


def run_what_if(data_dir: str = ".") -> Dict[str, List[Recommendation]]:
    """Compare normal and high-traffic recommendations for the dashboard."""
    data = SyntheticDataAdapter(data_dir).load()
    engine = RecommendationEngine()
    return {
        "normal_traffic": engine.recommend(data, traffic_level="NORMAL"),
        "high_goods_traffic": engine.recommend(data, traffic_level="HIGH"),
    }
