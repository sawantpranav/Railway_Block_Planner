"""SIH demonstration: BDMS/COA plus AI optimization layer."""

from pathlib import Path

from ai_optimization_layer import AIPriorityEngine, RecommendationEngine, SyntheticDataAdapter, run_what_if
from planning_service import PlanningService


DATA_DIR = Path(__file__).parent


def print_recommendations(title, recommendations):
    print(f"\n{title}")
    print("=" * len(title))
    for recommendation in recommendations:
        print(
            f"{recommendation.block_id} | {recommendation.section} | "
            f"{', '.join(recommendation.departments)} | "
            f"{', '.join(recommendation.task_ids)} | "
            f"{recommendation.priority_class} {recommendation.priority_score:.1f}/10 | "
            f"delay {recommendation.train_delay_minutes:.1f} min"
        )
        for reason in recommendation.reasons:
            print(f"  - {reason}")


def main():
    data = SyntheticDataAdapter(DATA_DIR).load()
    scored_tasks = AIPriorityEngine.score_tasks(data["tasks"])

    print("BDMS / COA + AI OPTIMIZATION LAYER")
    print("Existing systems remain the system of record; this prototype recommends blocks.")
    print("\nPriority engine")
    print(scored_tasks[["task_id", "department", "priority_score", "priority_class"]].to_string(index=False))

    engine = RecommendationEngine()
    recommendations = engine.recommend(data)
    print_recommendations("Recommended coordinated block plan", recommendations)

    scenarios = run_what_if(DATA_DIR)
    for name, scenario in scenarios.items():
        total_delay = sum(item.train_delay_minutes for item in scenario)
        print(f"\nWhat-if: {name.replace('_', ' ').title()}")
        print(f"  Recommended blocks: {len(scenario)}")
        print(f"  Estimated train delay: {total_delay:.1f} minutes")

        service = PlanningService(DATA_DIR)
        horizons = service.horizons()
        print("\nPlanning horizons")
        for horizon, result in horizons.items():
            print(
                f"  {horizon.title()}: {len(result.recommendations)} blocks, "
                f"{result.scheduled_tasks}/{result.total_tasks} tasks, solver={result.solver_status}"
            )
        draft = service.create_plan(horizons["weekly"])
        print(f"\nApproval workflow: {draft.plan_id} created as {draft.status}")


if __name__ == "__main__":
    main()
