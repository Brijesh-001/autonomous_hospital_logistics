"""Streamlit UI for Autonomous Hospital Logistics Simulation."""

import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from simulation import HospitalSimulation
from config import STATUS_COLORS

st.set_page_config(
    page_title="Autonomous Hospital Logistics",
    page_icon="🤖",
    layout="wide",
)

if "sim" not in st.session_state:
    st.session_state.sim = HospitalSimulation()

sim: HospitalSimulation = st.session_state.sim

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
.metric-card {padding: 10px; border-radius: 10px; border: 1px solid #ddd;}
.small {font-size: 0.85rem; color: #666;}
</style>
""", unsafe_allow_html=True)

st.title("🤖 Autonomous Hospital Logistics")
st.caption("Real-time simulation of autonomous task planning, safe navigation, human interaction and emergency delivery.")

# Sidebar controls
with st.sidebar:
    st.header("🎛️ Simulation Control")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("▶ Start", use_container_width=True):
            sim.running = True
    with c2:
        if st.button("⏸ Pause", use_container_width=True):
            sim.running = False

    if st.button("↻ Reset", use_container_width=True):
        sim.reset()
        st.rerun()

    speed = st.select_slider(
        "Simulation speed",
        options=[1, 2, 5, 10],
        value=2,
        help="Higher values update the simulation faster.",
    )

    st.divider()
    st.header("🎯 Scenarios")
    scenario = st.selectbox(
        "Choose scenario",
        [
            "Normal Hospital Operations",
            "Emergency Medicine Delivery",
            "High Human Traffic",
            "Blocked Corridor",
            "Low Battery",
            "Multiple Critical Deliveries",
            "Robot Failure",
        ],
    )
    if st.button("Load Scenario", use_container_width=True):
        sim.apply_scenario(scenario)
        st.rerun()

    st.divider()
    st.header("➕ Manual Events")

    if st.button("🚨 Add Emergency", use_container_width=True):
        sim.add_emergency()
        st.rerun()

    if st.button("👤 Add Human", use_container_width=True):
        sim.add_human()
        st.rerun()

    if st.button("⚠️ Add Obstacle", use_container_width=True):
        sim.add_obstacle()
        st.rerun()

    if st.button("🚧 Block Sample Corridor", use_container_width=True):
        sim.map.scenario_blocked_corridor()
        sim.log(f"{sim.now:04d}s - Sample corridor blocked manually")
        st.rerun()

    if st.button("Clear Blocked Corridors", use_container_width=True):
        sim.map.clear_blocks()
        sim.log(f"{sim.now:04d}s - All blocked corridors cleared")
        st.rerun()

    st.divider()
    st.info(f"Scenario: {sim.scenario}\n\nSimulation clock: {sim.now}s")

# Dynamic simulation fragment
@st.fragment(run_every=f"{max(0.15, 1.0 / speed):.2f}s")
def live_dashboard():
    sim.tick()
    metrics = sim.metrics()

    # Metrics
    cols = st.columns(6)
    cards = [
        ("🤖 Active Robots", metrics["active"]),
        ("📦 Pending Tasks", metrics["pending"]),
        ("✅ Completed", metrics["completed"]),
        ("🚨 Critical", metrics["critical"]),
        ("⚠️ Delayed", metrics["delayed"]),
        ("⏱ Avg Delivery", f"{metrics['avg_delivery']:.0f}s"),
    ]
    for col, (label, value) in zip(cols, cards):
        col.metric(label, value)

    st.subheader("🏥 Live Hospital Map")

    left, right = st.columns([2.2, 1])

    with left:
        fig = go.Figure()

        # Grid
        for x in range(sim.map.width):
            fig.add_trace(go.Scatter(
                x=[x, x], y=[0, sim.map.height - 1],
                mode="lines", line=dict(color="#eeeeee", width=1),
                hoverinfo="skip", showlegend=False
            ))
        for y in range(sim.map.height):
            fig.add_trace(go.Scatter(
                x=[0, sim.map.width - 1], y=[y, y],
                mode="lines", line=dict(color="#eeeeee", width=1),
                hoverinfo="skip", showlegend=False
            ))

        # Restricted areas
        if sim.map.restricted:
            rx, ry = zip(*sim.map.restricted)
            fig.add_trace(go.Scatter(
                x=rx, y=ry, mode="markers",
                marker=dict(size=20, symbol="square", color="red", opacity=0.45),
                name="Restricted"
            ))

        # High traffic
        if sim.map.high_traffic:
            hx, hy = zip(*sim.map.high_traffic)
            fig.add_trace(go.Scatter(
                x=hx, y=hy, mode="markers",
                marker=dict(size=17, symbol="square", color="gold", opacity=0.30),
                name="High Traffic"
            ))

        # Blocked
        if sim.map.blocked:
            bx, by = zip(*sim.map.blocked)
            fig.add_trace(go.Scatter(
                x=bx, y=by, mode="markers",
                marker=dict(size=21, symbol="x", color="black"),
                name="Blocked"
            ))

        # Locations
        lx, ly, labels = [], [], []
        for name, point in sim.map.locations.items():
            lx.append(point[0]); ly.append(point[1]); labels.append(name)
        fig.add_trace(go.Scatter(
            x=lx, y=ly, mode="markers+text",
            text=labels, textposition="top center",
            marker=dict(size=18, symbol="square", color="lightblue",
                        line=dict(width=1, color="black")),
            name="Hospital Areas",
            hovertemplate="%{text}<extra></extra>"
        ))

        # Humans
        if sim.humans:
            ux, uy = zip(*sim.humans)
            fig.add_trace(go.Scatter(
                x=ux, y=uy, mode="markers",
                marker=dict(size=15, symbol="circle", color="orange"),
                name="Humans",
                hovertemplate="Human<extra></extra>"
            ))

        # Robots and routes
        for robot in sim.robots:
            # Route line from current position onward
            route = robot.route[robot.route_index:] if robot.route else []
            if len(route) >= 2:
                xs = [p[0] for p in route]
                ys = [p[1] for p in route]
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines",
                    line=dict(width=4, dash="dash"),
                    name=f"{robot.robot_id} planned route",
                    hovertemplate=f"{robot.robot_id} route<extra></extra>"
                ))

            fig.add_trace(go.Scatter(
                x=[robot.position[0]], y=[robot.position[1]],
                mode="markers+text",
                text=[robot.robot_id],
                textposition="bottom center",
                marker=dict(
                    size=22,
                    symbol="circle",
                    color=STATUS_COLORS.get(robot.status, "blue"),
                    line=dict(width=2, color="white"),
                ),
                name=robot.robot_id,
                hovertemplate=(
                    f"<b>{robot.robot_id}</b><br>"
                    f"Status: {robot.status}<br>"
                    f"Battery: {robot.battery:.0f}%<br>"
                    f"Task: {robot.current_task or 'None'}<br>"
                    f"Safety: {robot.safety}<extra></extra>"
                ),
            ))

        fig.update_layout(
            height=570,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(range=[-1, sim.map.width], showgrid=False, zeroline=False),
            yaxis=dict(range=[-1, sim.map.height], showgrid=False, zeroline=False, scaleanchor="x"),
            legend=dict(orientation="h", y=-0.08),
            clickmode="event+select",
        )
        st.plotly_chart(fig, use_container_width=True, key="hospital_map")

    with right:
        st.subheader("🤖 Robot Status")
        selected = st.selectbox(
            "Select robot",
            [r.robot_id for r in sim.robots],
            key="selected_robot",
        )
        robot = next(r for r in sim.robots if r.robot_id == selected)

        task = sim.manager.tasks.get(robot.current_task) if robot.current_task else None

        st.markdown(f"### {robot.robot_id}")
        st.write(f"**Status:** `{robot.status}`")
        st.progress(min(max(robot.battery / 100, 0), 1), text=f"Battery: {robot.battery:.0f}%")
        st.write(f"**Current Task:** {robot.current_task or 'None'}")

        if task:
            st.write(f"**From:** {task.pickup}")
            st.write(f"**To:** {task.destination}")
            st.write(f"**Priority:** {task.priority_label(sim.now)}")
            st.write(f"**ETA:** {robot.eta_seconds()} sec")
            st.write(f"**Route Safety:** `{robot.safety}`")

            reasons = getattr(task, "_assignment_reasons", [])
            if reasons:
                with st.expander("🧠 Why was this robot selected?", expanded=True):
                    st.write(f"**{task.task_id} assigned to {robot.robot_id} because:**")
                    for reason in reasons:
                        st.write(f"• {reason}")
        else:
            st.write("**ETA:** —")
            st.write(f"**Route Safety:** `{robot.safety}`")

        st.write(f"**Position:** {robot.position}")
        st.write(f"**Distance Travelled:** {robot.distance_travelled:.0f}")
        st.write(f"**Safety Stops:** {robot.safety_stops}")

    st.subheader("📋 Task Queue")

    rows = []
    for task in sim.manager.tasks.values():
        rows.append({
            "Task ID": task.task_id,
            "Item": task.item,
            "From": task.pickup,
            "To": task.destination,
            "Priority": task.priority_label(sim.now),
            "Deadline": f"{max(0, task.deadline_seconds - (sim.now-task.created_at))}s",
            "Assigned Robot": task.assigned_robot or "—",
            "Status": task.status,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("📊 Performance")
        perf = pd.DataFrame({
            "Metric": [
                "Robot Utilization",
                "Battery Used",
                "Average Route",
                "Safety Stops",
                "Route Recalculations",
                "Deadline Success",
            ],
            "Value": [
                f"{metrics['utilization']:.0f}%",
                f"{metrics['battery_used']:.1f}",
                f"{metrics['avg_route']:.1f} cells",
                metrics["safety_stops"],
                metrics["replans"],
                f"{metrics['deadline_success']:.0f}%",
            ],
        })
        st.dataframe(perf, use_container_width=True, hide_index=True)

    with c2:
        st.subheader("🛡️ Safety & Event Log")
        if sim.event_log:
            for event in sim.event_log[:12]:
                st.write(event)
        else:
            st.write("No events yet.")

live_dashboard()

st.caption(
    "All values are generated from the live simulation state. "
    "Robot routes, battery, status, ETA, task assignments and safety state are dynamic."
)
