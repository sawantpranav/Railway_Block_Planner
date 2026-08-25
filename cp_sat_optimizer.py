"""Optional OR-Tools CP-SAT block-window selector."""

from typing import Dict, List, Tuple

try:
    from ortools.sat.python import cp_model
except ImportError:
    cp_model = None


class CPSATOptimizer:
    """Select at most one feasible low-impact window per corridor section."""

    def select(self, tasks, blocks, forecast=None, max_blocks=None) -> Tuple[object, str]:
        if cp_model is None or blocks.empty:
            return blocks, "FALLBACK"
        sections = list(tasks["location"].unique())
        candidates = []
        for section in sections:
            section_tasks = tasks[tasks["location"] == section]
            required = float(section_tasks["estimated_duration"].max())
            for index, block in blocks[blocks["section"] == section].iterrows():
                if block["available_duration"] >= required and block["start"] <= section_tasks["deadline"].min():
                    traffic = float(block.get("traffic_level", "MEDIUM") == "HIGH")
                    candidates.append((section, index, int(round(1000 * traffic + block["start"].timestamp() / 10**6))))
        if not candidates:
            return blocks.iloc[0:0], "INFEASIBLE"
        model = cp_model.CpModel()
        variables = [model.NewBoolVar(f"window_{i}") for i in range(len(candidates))]
        for section in sections:
            indexes = [i for i, item in enumerate(candidates) if item[0] == section]
            if indexes:
                model.Add(sum(variables[i] for i in indexes) == 1)
        if max_blocks:
            model.Add(sum(variables) <= max_blocks)
        model.Minimize(sum(candidates[i][2] * variables[i] for i in range(len(candidates))))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 3
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return blocks.iloc[0:0], "INFEASIBLE"
        selected = [candidates[i][1] for i, variable in enumerate(variables) if solver.Value(variable)]
        return blocks.loc[selected], "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
