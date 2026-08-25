"""Streamlit dashboard for the BDMS/COA AI optimization-layer prototype."""

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from ai_optimization_layer import AIPriorityEngine, RecommendationEngine, SyntheticDataAdapter
from planning_service import PlanningService


DATA_DIR = Path(__file__).parent

st.set_page_config(
    page_title="AI Railway Block Planning",
    page_icon="🚆",
    layout="wide",
)


@st.cache_data
def load_data():
    return SyntheticDataAdapter(DATA_DIR).load()


def recommendation_frame(recommendations):
    rows = []
    for item in recommendations:
        rows.append({
            "Block ID": item.block_id,
            "Day": item.start.strftime("%A"),
            "Corridor": item.section,
            "Time": f"{item.start:%H:%M} - {item.end:%H:%M}",
            "Departments": " + ".join(item.departments),
            "Tasks": ", ".join(item.task_ids),
            "Priority": item.priority_class,
            "Score": round(item.priority_score, 1),
            "Utilization": f"{item.utilization:.0%}",
            "Train delay (min)": round(item.train_delay_minutes, 1),
        })
    return pd.DataFrame(rows)


def write_plan_csv(recommendations):
    output_dir = DATA_DIR / "output"
    output_dir.mkdir(exist_ok=True)
    frame = recommendation_frame(recommendations)
    frame.to_csv(output_dir / "optimized_block_plan.csv", index=False)
    return frame


def traffic_analysis(trains):
    periods = pd.date_range("2026-08-23", periods=24, freq="h")
    rows = []
    for period in periods:
        hour = period.hour
        count = int(((trains["departure_time"].dt.hour - hour) % 24 <= 1).sum())
        if count >= 4:
            level = "HIGH"
        elif count >= 2:
            level = "MEDIUM"
        else:
            level = "LOW"
        rows.append({"Hour": f"{hour:02d}:00", "Trains": count, "Traffic": level})
    return pd.DataFrame(rows)


def render_recommendation_details(recommendations):
    if not recommendations:
        st.info("No compatible block window was found for the selected scenario.")
        return
    selected_id = st.selectbox("Explain recommendation", [item.block_id for item in recommendations])
    selected = next(item for item in recommendations if item.block_id == selected_id)
    st.subheader(f"Why did AI select {selected.block_id}?")
    for reason in selected.reasons:
        st.markdown(f"✓ {reason}")


def scenario_summary(recommendations, tasks):
    scheduled_ids = {task_id for item in recommendations for task_id in item.task_ids}
    critical = tasks[tasks["priority_class"] == "CRITICAL"]
    unscheduled_critical = critical[~critical["task_id"].isin(scheduled_ids)]
    return {
        "blocks": len(recommendations),
        "scheduled": len(scheduled_ids),
        "delay": sum(item.train_delay_minutes for item in recommendations),
        "utilization": (
            sum(item.utilization for item in recommendations) / len(recommendations)
            if recommendations else 0
        ),
        "unscheduled_critical": unscheduled_critical["task_id"].tolist(),
    }


def main():
    service = PlanningService(DATA_DIR)
    data = service.load()
    uploaded_tasks = st.sidebar.file_uploader("Upload maintenance_tasks.csv", type="csv")
    uploaded_trains = st.sidebar.file_uploader("Upload train_schedule.csv", type="csv")
    uploaded_blocks = st.sidebar.file_uploader("Upload block_windows.csv", type="csv")
    if uploaded_tasks and uploaded_trains and uploaded_blocks:
        data["tasks"] = SyntheticDataAdapter._clean_tasks(pd.read_csv(uploaded_tasks))
        data["trains"] = SyntheticDataAdapter._clean_trains(pd.read_csv(uploaded_trains))
        data["blocks"] = SyntheticDataAdapter._clean_blocks(pd.read_csv(uploaded_blocks))
    priority_tasks = AIPriorityEngine.score_tasks(data["tasks"], data.get("history"))
    engine = RecommendationEngine()

    st.title("AI-Powered Railway Block Planning System")
    st.caption("Decision-support layer over existing BDMS, COA, TMS, SMMS and TDMS systems")
    st.info("This prototype recommends coordinated blocks. BDMS and COA remain the operational systems of record.")

    traffic_level = st.sidebar.selectbox("Train traffic scenario", ["NORMAL", "HIGH", "LOW"])
    maintenance_level = st.sidebar.selectbox("Maintenance scope", ["ALL", "CRITICAL"])
    recommendations = engine.recommend(
        data, traffic_level=traffic_level, maintenance_level=maintenance_level
    )
    current_summary = scenario_summary(recommendations, priority_tasks)

    critical_count = int((priority_tasks["priority_class"] == "CRITICAL").sum())
    overdue_count = int((data["tasks"]["overdue_days"] > 0).sum())
    source_count = int(data["tasks"]["source_system"].nunique())
    total_effort = float(data["tasks"]["estimated_duration"].sum())
    coordinated_effort = sum((item.end - item.start).total_seconds() / 3600 for item in recommendations)
    time_saved = max(0.0, total_effort - coordinated_effort)
    utilization = (
        sum(item.utilization for item in recommendations) / len(recommendations)
        if recommendations else 0
    )
    downtime_reduction = time_saved / total_effort if total_effort else 0

    metrics = st.columns(7)
    metric_values = [
        ("Total tasks", len(data["tasks"])),
        ("Critical tasks", critical_count),
        ("Overdue tasks", overdue_count),
        ("Block windows", len(data["blocks"])),
        ("AI blocks", len(recommendations)),
        ("Utilization", f"{utilization:.0%}"),
        ("Downtime reduction", f"{downtime_reduction:.0%}"),
    ]
    for column, (label, value) in zip(metrics, metric_values):
        column.metric(label, value)

    st.subheader("Control-room decision brief")
    brief_columns = st.columns(3)
    brief_columns[0].metric("Safety-gate risks", len(current_summary["unscheduled_critical"]))
    brief_columns[1].metric("Estimated train delay", f"{current_summary['delay']:.1f} min")
    brief_columns[2].metric("Average block use", f"{current_summary['utilization']:.0%}")
    if current_summary["unscheduled_critical"]:
        st.error(
            "SAFETY GATE: approval requires review of unscheduled critical tasks: "
            + ", ".join(current_summary["unscheduled_critical"])
        )
    else:
        st.success("SAFETY GATE: all critical tasks are covered by the recommended plan.")

    st.divider()
    map_tab, traffic_tab, priority_tab, plan_tab, impact_tab, monthly_tab, ops_tab = st.tabs(
        ["Corridor map", "Traffic analysis", "Maintenance priority", "Optimized plan", "Before vs after", "Monthly view", "Operations"]
    )

    with traffic_tab:
        st.subheader("Train traffic analysis")
        st.caption(f"Integrated maintenance sources: {source_count} (TMS, SMMS, TDMS) + COA windows + goods forecast")
        traffic = traffic_analysis(data["trains"])
        st.bar_chart(traffic.set_index("Hour")["Trains"])
        lowest = traffic.loc[traffic["Trains"].idxmin()]
        st.success(
            f"AI analysis: lowest traffic period identified at {lowest['Hour']}. "
            "Low-traffic COA windows are preferred to minimize disruption."
        )
        st.dataframe(traffic, width="stretch", hide_index=True)

    with priority_tab:
        st.subheader("AI maintenance priority")
        if priority_tasks.empty:
            st.info("No maintenance tasks are available for prioritization.")
        else:
            display = priority_tasks[[
                "task_id", "department", "asset_type", "severity", "predicted_risk", "priority_score", "priority_class", "deadline"
            ]].rename(columns={
                "task_id": "Task ID", "department": "Department", "asset_type": "Asset",
                "severity": "Severity", "predicted_risk": "Predicted risk", "priority_score": "Priority score", "priority_class": "Status",
                "deadline": "Deadline",
            })
            st.dataframe(display, width="stretch", hide_index=True)
            top = priority_tasks.iloc[0]
            st.warning(
                f"AI recommendation: {top['task_id']} should be scheduled first because it combines "
                f"high safety criticality ({top['safety_criticality']}/10), severe condition, and deadline pressure."
            )
            st.caption("Priority combines safety criticality, severity, urgency, asset criticality, traffic impact, and a history-trained risk signal.")

    with plan_tab:
        st.subheader("Weekly AI-optimized block plan")
        plan_frame = write_plan_csv(recommendations)
        if plan_frame.empty:
            st.warning("No plan was generated for this scenario.")
        else:
            st.dataframe(plan_frame, width="stretch", hide_index=True)
            st.download_button(
                "Download optimized_block_plan.csv",
                plan_frame.to_csv(index=False),
                "optimized_block_plan.csv",
                "text/csv",
            )
        render_recommendation_details(recommendations)

    with impact_tab:
        st.subheader("AI impact analysis")
        separate_blocks = len(data["tasks"])
        optimized_blocks = len(recommendations)
        impact = pd.DataFrame({
            "Measure": ["Separate departmental blocks", "AI coordinated blocks", "Block time (hours)"],
            "Traditional": [separate_blocks, separate_blocks, round(total_effort, 1)],
            "AI": [optimized_blocks, optimized_blocks, round(coordinated_effort, 1)],
        })
        st.dataframe(impact, width="stretch", hide_index=True)
        st.success(
            f"AI combines compatible work into {optimized_blocks} blocks and saves "
            f"{time_saved:.1f} hours of repeated infrastructure downtime."
        )
        st.subheader("What-if traffic stress test")
        alternate_level = "HIGH" if traffic_level != "HIGH" else "LOW"
        alternate = engine.recommend(data, traffic_level=alternate_level, maintenance_level=maintenance_level)
        alternate_summary = scenario_summary(alternate, priority_tasks)
        comparison = pd.DataFrame({
            "Scenario": [f"Current ({traffic_level})", f"Stress test ({alternate_level})"],
            "Recommended blocks": [current_summary["blocks"], alternate_summary["blocks"]],
            "Scheduled tasks": [current_summary["scheduled"], alternate_summary["scheduled"]],
            "Estimated delay (min)": [round(current_summary["delay"], 1), round(alternate_summary["delay"], 1)],
            "Safety-gate risks": [len(current_summary["unscheduled_critical"]), len(alternate_summary["unscheduled_critical"])],
        })
        st.dataframe(comparison, width="stretch", hide_index=True)
        st.caption("The stress test recalculates the same uploaded maintenance scenario under a different traffic condition.")

    with monthly_tab:
        st.subheader("Monthly planning view")
        if recommendations:
            monthly = recommendation_frame(recommendations).copy()
            monthly["Week"] = ((pd.to_datetime([item.start for item in recommendations]).day - 1) // 7 + 1)
            st.dataframe(
                monthly[["Week", "Corridor", "Departments", "Tasks", "Priority"]],
                width="stretch",
                hide_index=True,
            )
        approaching = data["tasks"][data["tasks"]["deadline"] <= data["tasks"]["deadline"].min() + pd.Timedelta(days=14)]
        st.info(
            f"Monthly planning reserves suitable future windows. {len(approaching)} task(s) "
            "reach their deadline within the next 14-day planning window."
        )

    with map_tab:
        st.subheader("Corridor activity map")
        if not data["geo"].empty:
            geo = data["geo"].copy()
            geo["section"] = geo["section"].astype(str)

            corridor_activity = (
                priority_tasks.groupby("location", as_index=False)["task_id"].count()
                .rename(columns={"location": "section", "task_id": "active_tasks"})
            )
            corridor_priority = (
                priority_tasks.groupby("location", as_index=False)["priority_score"].max()
                .rename(columns={"location": "section", "priority_score": "max_priority_score"})
            )
            corridor_summary = geo.merge(corridor_activity, on="section", how="left").merge(
                corridor_priority, on="section", how="left"
            )
            corridor_summary["active_tasks"] = corridor_summary["active_tasks"].fillna(0).astype(int)
            corridor_summary["max_priority_score"] = corridor_summary["max_priority_score"].fillna(0).round(1)

            max_risk = float(corridor_summary["max_priority_score"].max()) if not corridor_summary.empty else 1.0
            route_data = []
            for _, row in corridor_summary.iterrows():
                risk = float(row.get("max_priority_score", 0.0))
                intensity = max(0.0, min(1.0, risk / max_risk if max_risk > 0 else 0.0))
                route_data.append({
                    "section": row["section"],
                    "start": [float(row["start_lon"]), float(row["start_lat"])],
                    "end": [float(row["end_lon"]), float(row["end_lat"])],
                    "start_station": row["start_station"],
                    "end_station": row["end_station"],
                    "active_tasks": int(row.get("active_tasks", 0)),
                    "max_priority_score": round(risk, 1),
                    "color": [255, int(210 * (1 - intensity)), 40, 245],
                    "width": 14 + int(10 * intensity),
                    "path": [
                        [float(row["start_lon"]), float(row["start_lat"])],
                        [float(row["end_lon"]), float(row["end_lat"])],
                    ],
                })

            route_frame = pd.DataFrame(route_data)
            if not route_frame.empty:
                base_points = pd.concat([
                    geo[["section", "start_lat", "start_lon"]].rename(columns={"start_lat": "lat", "start_lon": "lon"}),
                    geo[["section", "end_lat", "end_lon"]].rename(columns={"end_lat": "lat", "end_lon": "lon"}),
                ], ignore_index=True).drop_duplicates()

                avg_lat = base_points["lat"].mean()
                avg_lon = base_points["lon"].mean()

                label_data = route_frame[["section", "start_station", "end_station", "start", "end"]].copy()
                label_data["midpoint"] = label_data.apply(
                    lambda row: [
                        (float(row["start"][0]) + float(row["end"][0])) / 2,
                        (float(row["start"][1]) + float(row["end"][1])) / 2,
                    ],
                    axis=1,
                )
                station_data = pd.concat([
                    route_frame[["start_station", "start"]].rename(columns={"start_station": "station", "start": "position"}),
                    route_frame[["end_station", "end"]].rename(columns={"end_station": "station", "end": "position"}),
                ], ignore_index=True).drop_duplicates(subset=["station"])

                st.markdown(
                    "**Map key:** "
                    "<span style='color:#ff4b3e'>●</span> station &nbsp;&nbsp; "
                    "<span style='color:#56b4e9'>━</span> track &nbsp;&nbsp; "
                    "<span style='color:#f0a202'>━</span> higher-priority corridor",
                    unsafe_allow_html=True,
                )
                base_map = pdk.Deck(
                    map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
                    initial_view_state=pdk.ViewState(
                        latitude=avg_lat,
                        longitude=avg_lon,
                        zoom=3.5,
                        pitch=0,
                    ),
                    layers=[
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=base_points,
                            get_position='[lon, lat]',
                            get_radius=16000,
                            get_fill_color=[255, 75, 62, 210],
                            pickable=True,
                        ),
                        pdk.Layer(
                            "PathLayer",
                            data=route_frame,
                            get_path="path",
                            get_color="color",
                            get_width="width",
                            width_min_pixels=6,
                            pickable=True,
                            auto_highlight=True,
                        ),
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=station_data,
                            get_position="position",
                            get_radius=22000,
                            get_fill_color=[255, 75, 62, 240],
                            get_line_color=[255, 220, 210, 255],
                            get_line_width=2,
                            stroked=True,
                            pickable=True,
                        ),
                        pdk.Layer(
                            "TextLayer",
                            data=[{
                                "text": row["section"],
                                "position": row["midpoint"],
                                "color": [245, 245, 245, 255],
                                "size": 13,
                            } for _, row in label_data.iterrows()],
                            get_text="text",
                            get_position="position",
                            get_color="color",
                            get_size=13,
                            get_text_anchor="middle",
                            get_alignment_baseline="center",
                        )
                    ],
                    tooltip={
                        "html": "<b>{section}</b><br/>From {start_station} to {end_station}<br/>Tasks: {active_tasks}<br/>Priority: {max_priority_score}",
                        "style": {"color": "white"},
                    },
                )
                st.pydeck_chart(base_map)

            st.caption("Corridor-level activity and risk summary")
            st.dataframe(
                corridor_summary[["section", "start_station", "end_station", "active_tasks", "max_priority_score"]]
                .sort_values("max_priority_score", ascending=False),
                width="stretch",
                hide_index=True,
            )

            if recommendations:
                recommendation_by_section = pd.DataFrame([
                    {
                        "section": item.section,
                        "recommended_block": item.block_id,
                        "departments": ", ".join(item.departments),
                        "train_delay_min": round(item.train_delay_minutes, 1),
                    }
                    for item in recommendations
                ])
                st.caption("Recommended block allocations")
                st.dataframe(recommendation_by_section, width="stretch", hide_index=True)
        else:
            st.info("Add geo_reference.csv to display corridor coordinates.")

    with ops_tab:
        st.subheader("Planning horizons and controls")
        horizon = st.selectbox("Planning horizon", ["daily", "weekly", "monthly"])
        horizon_result = service.horizons(traffic_level, maintenance_level)[horizon]
        st.metric("Solver status", horizon_result.solver_status)
        st.metric("Deadline alerts", horizon_result.deadline_alerts)
        if horizon_result.unmet_task_ids:
            st.warning("Unmet tasks: " + ", ".join(horizon_result.unmet_task_ids))
        if horizon_result.resource_violations:
            st.error("Resource limits: " + "; ".join(horizon_result.resource_violations))
        timeline = []
        for item in horizon_result.recommendations:
            for department in item.departments:
                timeline.append({"Department": department, "Corridor": item.section, "Start": item.start, "End": item.end})
        if timeline:
            st.subheader("Gantt timeline")
            st.dataframe(pd.DataFrame(timeline), width="stretch", hide_index=True)
        if st.button("Create draft for approval"):
            record = service.create_plan(horizon_result)
            st.success(f"Created {record.plan_id} with status {record.status}")


if __name__ == "__main__":
    main()
