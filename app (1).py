import json
import math
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==============================================================================
# NUR-2 CAREER VENTURE LAB — STAGE 1 STREAMLIT APPLICATION
# Team: Healthcare | Pathway: NUR-2 | Course: Precalculus | Level: Advanced
# ==============================================================================

st.set_page_config(
    page_title="NUR-2 Health Education Studio | Career Venture Lab",
    page_icon="🩺",
    layout="wide",
)

def money(val) -> Decimal:
    """Exact two-decimal money rounding using Decimal."""
    return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def default_state() -> dict:
    """Initialize Team Healthcare NUR-2 baseline state from Student Handbook."""
    return {
        "team_id": "Healthcare",
        "course": "Precalculus",
        "pathway_id": "NUR-2",
        "selected_level": "Advanced",
        "snapshot_id": "SNAP-NUR2-001",
        "state_version": 1,
        "simulation_date": "2027-01-01",
        "base_period": "Monthly",
        "working_days": 20,
        "currency": "USD",
        "disclaimer": "Fictional general health education simulation only. No diagnosis, clinical treatment, or real patient data.",
        "startup": {
            "owner_contribution": 6000.00,
            "equipment_assets": 1500.00,
            "pre_opening_expense": 500.00,
            "opening_inventory": 0.00,
            "opening_cash": 4000.00,
            "retained_earnings": -500.00,
            "loan_principal": 0.00,
        },
        "params": {
            "base_price": 25.00,
            "D0": 80,
            "staff_hours": 30.0,
            "hours_per_unit": 0.5,
            "venue_seats": 60,
            "no_show_rate": 0.0,
            "satisfaction_mean": 4.0,
            "var_educator": 2.00,
            "var_materials": 2.00,
            "var_cleaning": 1.00,
            "fix_venue": 250.00,
            "fix_software": 100.00,
            "fix_accessibility": 200.00,
            "fix_admin_ins": 150.00,
            "interest": 0.00,
            "additional_capex": 0.00,
            "refund_amount": 0.00,
        },
        "current_cash": 4000.00,
        "current_debt": 0.00,
        "current_equipment": 1500.00,
        "ledger": [],
        "processed_run_ids": [],
        "processed_campaign_ids": [],
        "pending_recommendations": [],
        "decisions": [],
    }

if "sim_state" not in st.session_state:
    st.session_state.sim_state = default_state()

state = st.session_state.sim_state

# ------------------------------------------------------------------------------
# DETERMINISTIC NUR-2 SIMULATION ENGINE
# ------------------------------------------------------------------------------
def compute_capacity(staff_hours: float, hours_per_unit: float, venue_seats: int) -> int:
    if hours_per_unit <= 0:
        return 0
    staff_cap = math.floor(staff_hours / hours_per_unit)
    return max(0, min(staff_cap, int(venue_seats)))

def run_simulation_step(
    current_state: dict,
    sim_date: str,
    requested: int,
    ad_cost: float,
    run_id: str,
    campaign_id: str = "",
    capacity_override: int | None = None,
    mode_label: str = "Normal Mode",
) -> tuple[bool, str]:
    """Advance simulation once with duplicate-run protection and exact Decimal math."""
    if run_id in current_state["processed_run_ids"]:
        return False, f"Rejected duplicate run_id '{run_id}'. No duplicate transactions created."

    p = current_state["params"]
    price = money(p["base_price"])
    var_per_unit = money(p["var_educator"] + p["var_materials"] + p["var_cleaning"])
    fixed_cost = money(p["fix_venue"] + p["fix_software"] + p["fix_accessibility"] + p["fix_admin_ins"])
    marketing = money(ad_cost)
    interest = money(p["interest"])
    capex = money(p["additional_capex"])
    refunds = money(p["refund_amount"])

    # Campaign duplicate protection
    if marketing > Decimal("0.00") and campaign_id:
        if campaign_id in current_state["processed_campaign_ids"]:
            return False, f"Rejected duplicate campaign_id '{campaign_id}'. Campaign cost cannot be charged twice."

    if capacity_override is not None:
        eff_cap = max(0, int(capacity_override))
    else:
        eff_cap = compute_capacity(p["staff_hours"], p["hours_per_unit"], p["venue_seats"])

    req = max(0, int(requested))
    booked = min(req, eff_cap)
    attended = math.floor(booked * (1.0 - float(p["no_show_rate"])))
    sold = attended
    unserved = max(0, req - booked)

    gross_revenue = money(price * Decimal(sold))
    net_revenue = money(gross_revenue - refunds)
    variable_expense = money(var_per_unit * Decimal(sold))
    total_operating_expense = money(variable_expense + fixed_cost + marketing)
    operating_profit = money(net_revenue - total_operating_expense)
    net_profit = money(operating_profit - interest)

    open_cash = money(current_state["current_cash"])
    close_cash = money(open_cash + net_revenue - variable_expense - fixed_cost - marketing - interest - capex)

    new_version = current_state["state_version"] + 1
    tx_entry = {
        "transaction_id": f"TX-{new_version:04d}",
        "run_id": run_id,
        "date": sim_date,
        "mode": mode_label,
        "state_version": new_version,
        "requested": req,
        "effective_capacity": eff_cap,
        "booked": booked,
        "attended_sold": sold,
        "unserved_demand": unserved,
        "unit_price": float(price),
        "revenue": float(net_revenue),
        "variable_expense": float(variable_expense),
        "fixed_expense": float(fixed_cost),
        "marketing_expense": float(marketing),
        "total_expense": float(total_operating_expense),
        "operating_profit": float(operating_profit),
        "net_profit": float(net_profit),
        "opening_cash": float(open_cash),
        "closing_cash": float(close_cash),
        "campaign_id": campaign_id if marketing > 0 else "",
    }

    current_state["ledger"].append(tx_entry)
    current_state["processed_run_ids"].append(run_id)
    if marketing > Decimal("0.00") and campaign_id:
        current_state["processed_campaign_ids"].append(campaign_id)

    current_state["current_cash"] = float(close_cash)
    current_state["current_equipment"] = float(money(current_state["current_equipment"]) + capex)
    current_state["state_version"] = new_version
    current_state["simulation_date"] = sim_date
    current_state["snapshot_id"] = f"SNAP-NUR2-{new_version:03d}"
    return True, f"Recorded {tx_entry['transaction_id']} (v{new_version}): Sold {sold} seats, Profit ${net_profit}, Closing Cash ${close_cash}."

# ------------------------------------------------------------------------------
# SIDEBAR: PERSISTENT SNAPSHOT & SAVE/LOAD JSON
# ------------------------------------------------------------------------------
with st.sidebar:
    st.header("🩺 NUR-2 Control & Persistence")
    st.caption(state["disclaimer"])
    st.markdown(f"**Team ID:** `{state['team_id']}`")
    st.markdown(f"**Pathway:** `{state['pathway_id']}` ({state['course']})")
    st.markdown(f"**State Version:** `v{state['state_version']}` | `{state['snapshot_id']}`")
    st.metric("Current Spendable Cash", f"${state['current_cash']:,.2f}")

    st.divider()
    st.subheader("Save / Restore State (JSON)")
    snapshot_json = json.dumps(state, indent=2)
    st.download_button(
        label="⬇️ Export Snapshot JSON",
        data=snapshot_json,
        file_name=f"{state['team_id']}_{state['pathway_id']}_v{state['state_version']}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded_file = st.file_uploader("⬆️ Restore Snapshot JSON", type=["json"])
    if uploaded_file is not None:
        if st.button("Load Uploaded Snapshot", use_container_width=True):
            try:
                loaded = json.load(uploaded_file)
                if loaded.get("team_id") != state["team_id"]:
                    st.error(f"Rejected: Team ID mismatch ('{loaded.get('team_id')}' != '{state['team_id']}').")
                elif loaded.get("pathway_id") != state["pathway_id"]:
                    st.error(f"Rejected: Pathway mismatch ('{loaded.get('pathway_id')}' != '{state['pathway_id']}').")
                else:
                    st.session_state.sim_state = loaded
                    st.success(f"Restored snapshot {loaded.get('snapshot_id')} (v{loaded.get('state_version')}).")
                    st.rerun()
            except Exception as exc:
                st.error(f"Invalid JSON file: {exc}")

    st.divider()
    if st.button("🔄 Reset to Post-Startup Baseline", use_container_width=True):
        st.session_state.sim_state = default_state()
        st.rerun()

# ------------------------------------------------------------------------------
# MAIN HEADER & TABS (STAGE 1 + PLACEHOLDERS FOR STAGE 2/3)
# ------------------------------------------------------------------------------
st.title("NUR-2: Nurse-Led Health Education Simulation")
st.info(
    "**Stage 1 Build Active:** Deterministic Ledger, Startup Funding & Editable Cost Lines, Precalculus Math Skills & Levels Panel, Save/Restore JSON, and Acceptance Fixture Tests. "
    "*(Stage 2 Report Center/Marketing Studio & Stage 3 Assessments are clearly marked for upcoming phases.)*"
)

tabs = st.tabs([
    "1. Overview & Inputs",
    "2. Precalculus Math Panel",
    "3. Operations & Ledger",
    "4. Fixture & Acceptance Tests",
    "5. AI Handoff & Stage 2/3 Roadmap",
])

# ==============================================================================
# TAB 1: OVERVIEW & INPUTS
# ==============================================================================
with tabs[0]:
    st.subheader("Startup Financing & Opening Balance Sheet (Fictional Defaults)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Owner Contribution", f"${state['startup']['owner_contribution']:,.2f}")
    c2.metric("Equipment & Access Assets", f"${state['startup']['equipment_assets']:,.2f}")
    c3.metric("Pre-Opening Expense", f"${state['startup']['pre_opening_expense']:,.2f}")
    c4.metric("Post-Startup Opening Cash", f"${state['startup']['opening_cash']:,.2f}")
    st.caption("Accounting rule: Equipment ($1,500) and pre-opening setup ($500) are accounted for at startup; retained earnings begin at -$500.00.")

    st.divider()
    col_left, col_right = st.columns(2)
    p = state["params"]

    with col_left:
        st.subheader("Pricing, Demand & Capacity Parameters")
        p["base_price"] = st.number_input("Workshop Seat Price ($ USD)", min_value=1.0, max_value=200.0, value=float(p["base_price"]), step=1.0)
        p["D0"] = st.number_input("Baseline Monthly Demand D0 (seats)", min_value=0, max_value=500, value=int(p["D0"]), step=5)
        p["staff_hours"] = st.number_input("Educator Staff Hours / Month", min_value=0.0, max_value=500.0, value=float(p["staff_hours"]), step=1.0)
        p["hours_per_unit"] = st.number_input("Educator Hours per Seat", min_value=0.1, max_value=10.0, value=float(p["hours_per_unit"]), step=0.1)
        p["venue_seats"] = st.number_input("Venue Seat Capacity / Month", min_value=0, max_value=500, value=int(p["venue_seats"]), step=5)
        p["no_show_rate"] = st.slider("No-Show Rate (0.00 to 1.00)", min_value=0.0, max_value=1.0, value=float(p["no_show_rate"]), step=0.05)

        derived_cap = compute_capacity(p["staff_hours"], p["hours_per_unit"], p["venue_seats"])
        st.success(f"**Derived Monthly Capacity:** `{derived_cap}` seats/month (`min(floor({p['staff_hours']}/{p['hours_per_unit']}), {p['venue_seats']})`)")

    with col_right:
        st.subheader("Editable Variable & Fixed Cost Lines")
        st.markdown("**Variable Cost per Attended Seat:**")
        vc1, vc2, vc3 = st.columns(3)
        p["var_educator"] = vc1.number_input("Educator Delivery ($)", min_value=0.0, value=float(p["var_educator"]), step=0.5)
        p["var_materials"] = vc2.number_input("Workshop Materials ($)", min_value=0.0, value=float(p["var_materials"]), step=0.5)
        p["var_cleaning"] = vc3.number_input("Cleaning Consumables ($)", min_value=0.0, value=float(p["var_cleaning"]), step=0.5)
        tot_var = p["var_educator"] + p["var_materials"] + p["var_cleaning"]
        st.info(f"**Total Variable Cost per Attended Seat:** `${tot_var:,.2f}`")

        st.markdown("**Monthly Fixed Expenses:**")
        fc1, fc2 = st.columns(2)
        p["fix_venue"] = fc1.number_input("Venue Rental ($/mo)", min_value=0.0, value=float(p["fix_venue"]), step=10.0)
        p["fix_software"] = fc2.number_input("Scheduling Software ($/mo)", min_value=0.0, value=float(p["fix_software"]), step=10.0)
        fc3, fc4 = st.columns(2)
        p["fix_accessibility"] = fc3.number_input("Accessibility Support ($/mo)", min_value=0.0, value=float(p["fix_accessibility"]), step=10.0)
        p["fix_admin_ins"] = fc4.number_input("Admin & Insurance ($/mo)", min_value=0.0, value=float(p["fix_admin_ins"]), step=10.0)
        tot_fix = p["fix_venue"] + p["fix_software"] + p["fix_accessibility"] + p["fix_admin_ins"]
        st.info(f"**Total Monthly Fixed Cost:** `${tot_fix:,.2f}`")

# ==============================================================================
# TAB 2: PRECALCULUS MATH SKILLS & CHALLENGE LEVEL PANEL
# ==============================================================================
with tabs[1]:
    st.subheader("Persistent Math Skills & Challenge Level Panel (Precalculus)")
    level = st.selectbox(
        "Select Challenge Level (Teacher-Approved Mode):",
        ["Foundation", "Applied", "Advanced"],
        index=["Foundation", "Applied", "Advanced"].index(state["selected_level"]),
    )
    state["selected_level"] = level

    F = p["fix_venue"] + p["fix_software"] + p["fix_accessibility"] + p["fix_admin_ins"]
    v = p["var_educator"] + p["var_materials"] + p["var_cleaning"]
    p0 = p["base_price"]
    D0 = p["D0"]
    cap = compute_capacity(p["staff_hours"], p["hours_per_unit"], p["venue_seats"])

    if level == "Foundation":
        st.markdown("### Foundation Mode: Rational Average Cost Function $A(s)$")
        st.latex(r"C(s) = F + v \cdot s, \quad A(s) = rac{C(s)}{s} = rac{F}{s} + v \quad 	ext{for } 0 < s \le 	ext{capacity}")
        st.markdown(
            f"- **Current Parameters:** $F = \${F:,.2f}$, $v = \${v:,.2f}/\text{{seat}}$, Domain: $0 < s \le {cap}$ seats.
"
            f"- **Asymptotes:** Vertical asymptote at $s = 0$ ($A(0)$ is undefined); horizontal asymptote at $y = {v:.2f}$ ($/seat).
"
            f"- **At Full Capacity ($s = {cap}$):** $A({cap}) = \${(F/cap + v) if cap > 0 else 0:,.2f}$ per seat."
        )
        s_vals = np.linspace(1, max(1, cap), 60)
        a_vals = F / s_vals + v
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s_vals, y=a_vals, mode="lines+markers", name="Average Cost A(s) ($/seat)"))
        fig.add_hline(y=v, line_dash="dash", annotation_text=f"Horizontal Asymptote y = ${v:.2f}")
        fig.update_layout(title="Average Cost per Attended Seat A(s) vs. Volume s", xaxis_title="Attended Seats (s)", yaxis_title="Average Cost ($/seat)")
        st.plotly_chart(fig, use_container_width=True)

        df_math = pd.DataFrame({"Seats (s)": [1, 5, 10, 20, 30, 45, cap], "Total Cost C(s) ($)": [round(F + v*x, 2) for x in [1, 5, 10, 20, 30, 45, cap]], "Average Cost A(s) ($/seat)": [round(F/x + v, 2) if x > 0 else None for x in [1, 5, 10, 20, 30, 45, cap]]})
        st.dataframe(df_math, use_container_width=True)
        st.info("**Interpretation Prompt:** Why is $s = 0$ excluded from the practical domain, and what happens to average fixed cost $F/s$ as attendance approaches capacity?")

    elif level == "Applied":
        st.markdown("### Applied Mode: Composed Price-Demand-Profit Functions")
        slope = D0 / p0 if p0 > 0 else 3.2
        intercept = 2 * D0
        breakpoint_p = p0 * (2 - cap / D0) if D0 > 0 else 0.0
        st.latex(r"q(p) = \max(0, 2D_0 - 	frac{D_0}{p_0}p), \quad s(p) = \min(	ext{capacity}, q(p)), \quad P(p) = p \cdot s(p) - (F + v \cdot s(p))")
        st.markdown(
            f"- **Current Composed Rules:** $q(p) = \max(0, {intercept:.1f} - {slope:.2f}p)$ on $0 \le p \le {2*p0:.2f}$, capped at $s \le {cap}$.
"
            f"- **Capacity Breakpoint Price:** $p = \${breakpoint_p:,.2f}$ (below this price, demand exceeds {cap} seats and sales are capped).
"
            f"- **Continuous vs. Integer Rule:** Graphs show continuous curves; actual ledger transactions floor $s(p)$ to whole seats."
        )
        p_grid = np.linspace(0, max(10.0, 2 * p0), 101)
        q_grid = np.maximum(0.0, intercept - slope * p_grid)
        s_grid = np.minimum(float(cap), q_grid)
        rev_grid = p_grid * s_grid
        cost_grid = F + v * s_grid
        prof_grid = rev_grid - cost_grid

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=p_grid, y=rev_grid, name="Revenue R(p) ($)"), secondary_y=False)
        fig.add_trace(go.Scatter(x=p_grid, y=cost_grid, name="Total Cost C(s(p)) ($)"), secondary_y=False)
        fig.add_trace(go.Scatter(x=p_grid, y=prof_grid, name="Profit P(p) ($)", line=dict(width=3)), secondary_y=False)
        fig.add_trace(go.Scatter(x=p_grid, y=s_grid, name="Completed Seats s(p)", line=dict(dash="dot")), secondary_y=True)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", secondary_y=False)
        fig.add_vline(x=breakpoint_p, line_dash="dash", annotation_text=f"Cap Breakpoint ${breakpoint_p:.2f}")
        fig.update_layout(title="Composed Revenue, Cost, Profit & Capped Seats vs. Price p", xaxis_title="Workshop Seat Price p ($)")
        fig.update_yaxes(title_text="Dollars ($)", secondary_y=False)
        fig.update_yaxes(title_text="Seats (units)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        test_prices = [20.0, 25.0, 31.25, 35.0, 40.0]
        rows = []
        for tp in test_prices:
            q_val = max(0.0, intercept - slope * tp)
            s_cont = min(float(cap), q_val)
            s_int = math.floor(s_cont)
            rows.append({
                "Price ($)": tp,
                "Unconstrained Demand q(p)": round(q_val, 2),
                "Continuous Seats s(p)": round(s_cont, 2),
                "Ledger Integer Seats": s_int,
                "Continuous Profit ($)": round(tp * s_cont - (F + v * s_cont), 2),
                "Integer Ledger Profit ($)": round(tp * s_int - (F + v * s_int), 2),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.info("**Interpretation Prompt:** Why does lowering the price below $31.25 reduce profit when venue/educator capacity is capped at 60 seats?")

    else:  # Advanced
        st.markdown("### Advanced Mode: Seasonal Trigonometric Demand Model $D(t)$ + Capacity Clipping")
        st.latex(r"D(t) = D_0 \left(1 + 0.20 \sin\left(rac{2\pi(t - 1)}{12}ight)ight), \quad s(t) = \min\left(	ext{capacity}, \lfloor D(t) flooright)")
        st.markdown(
            f"- **Assumed Seasonality:** Period = 12 months; Peak at month $t = 4$ ($1.20 D_0 = {1.2*D0:.0f}$ seats); Minimum at month $t = 10$ ($0.80 D_0 = {0.8*D0:.0f}$ seats).
"
            f"- **Capacity Clipping:** Realized sales $s(t)$ cannot exceed capacity (`{cap}` seats), creating unserved demand during peak months.
"
            f"- **Model Limitation:** Trigonometric seasonality is an illustrative assumption, not an empirical guarantee."
        )
        months = np.arange(1, 13)
        d_t = D0 * (1.0 + 0.20 * np.sin(2 * np.pi * (months - 1) / 12.0))
        s_t = np.minimum(cap, np.floor(d_t))
        unserved_t = np.maximum(0, np.floor(d_t) - s_t)
        prof_t = p0 * s_t - (F + v * s_t)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=months, y=d_t, mode="lines+markers", name="Seasonal Demand D(t) (continuous)"))
        fig.add_trace(go.Bar(x=months, y=s_t, name="Realized Sales s(t) (capped integer)", opacity=0.7))
        fig.add_hline(y=cap, line_dash="dash", annotation_text=f"Capacity Limit ({cap} seats)")
        fig.update_layout(title="12-Month Seasonal Demand D(t) vs. Capacity-Capped Sales s(t)", xaxis_title="Month Index (t = 1..12)", yaxis_title="Workshop Seats")
        st.plotly_chart(fig, use_container_width=True)

        df_adv = pd.DataFrame({
            "Month (t)": months,
            "Modeled Demand D(t)": np.round(d_t, 2),
            "Floored Demand": np.floor(d_t).astype(int),
            "Capacity Limit": cap,
            "Realized Sales s(t)": s_t.astype(int),
            "Unserved Demand": unserved_t.astype(int),
            "Projected Operating Profit ($)": np.round(prof_t, 2),
        })
        st.dataframe(df_adv, use_container_width=True)
        st.info("**Interpretation Prompt:** Even though demand fluctuates between 64 and 96 seats across the year, why does realized monthly profit stay flat when capacity is 60?")

# ==============================================================================
# TAB 3: OPERATIONS & LEDGER (NORMAL SIMULATION STEP)
# ==============================================================================
with tabs[2]:
    st.subheader("Execute Single Simulation Period (Normal Mode)")
    st.markdown("Run one period at a time with a unique `run_id`. Re-submitting an existing `run_id` is automatically blocked.")

    c_sim1, c_sim2, c_sim3, c_sim4 = st.columns(4)
    sim_date_in = c_sim1.text_input("Simulation Date (YYYY-MM-DD)", value="2027-01-31")
    req_in = c_sim2.number_input("Requested Workshop Seats", min_value=0, max_value=1000, value=int(p["D0"]), step=1)
    ad_cost_in = c_sim3.number_input("Approved Marketing Expense ($)", min_value=0.0, value=0.0, step=25.0)
    run_id_in = c_sim4.text_input("Unique Run ID", value=f"RUN-NUR2-{state['state_version']:03d}")
    camp_id_in = st.text_input("Campaign ID (required if Marketing > $0)", value="")

    if st.button("✅ Approve & Advance Simulation One Period", type="primary"):
        ok, msg = run_simulation_step(
            current_state=state,
            sim_date=sim_date_in,
            requested=req_in,
            ad_cost=ad_cost_in,
            run_id=run_id_in,
            campaign_id=camp_id_in,
            capacity_override=None,
            mode_label="Normal Mode",
        )
        if ok:
            st.success(msg)
        else:
            st.error(msg)

    st.divider()
    st.subheader("Dated Event Ledger (Actual Simulated Transactions)")
    if state["ledger"]:
        df_ledger = pd.DataFrame(state["ledger"])
        st.dataframe(df_ledger, use_container_width=True)
        st.download_button(
            label="⬇️ Export Ledger as CSV",
            data=df_ledger.to_csv(index=False),
            file_name=f"{state['team_id']}_NUR2_ledger_v{state['state_version']}.csv",
            mime="text/csv",
        )
    else:
        st.caption("No transactions recorded yet. Advance a simulation step above or run the NUR fixture tests in Tab 4.")

# ==============================================================================
# TAB 4: FIXTURE & ACCEPTANCE TESTS
# ==============================================================================
with tabs[3]:
    st.subheader("NUR Package Acceptance & Fixture Verification")
    st.warning(
        "**Fixture Mode Notice:** Replaying `monthly_fixture.csv` deliberately uses `capacity_override` to verify ledger math against the Student Handbook (page 85). "
        "Always reset to post-startup baseline before running fixture tests."
    )

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### Test A: 3-Month Handbook Fixture (`monthly_fixture.csv`)")
        st.markdown(
            "Expected Handbook Results:
"
            "- **2027-01:** Sold `60`, Rev `$1,500`, Exp `$1,000`, Profit `$500`, Cash `$4,500`
"
            "- **2027-02:** Sold `60`, Rev `$1,500`, Exp `$1,100` (+$100 ad), Profit `$400`, Cash `$4,900`
"
            "- **2027-03:** Sold `45`, Rev `$1,125`, Exp `$925`, Profit `$200`, Cash `$5,100`"
        )
        if st.button("▶️ Reset & Run 3-Month NUR Fixture"):
            st.session_state.sim_state = default_state()
            s = st.session_state.sim_state
            fixture_rows = [
                ("2027-01-31", 80, 60, 0.0, "FIX-2027-01", ""),
                ("2027-02-28", 88, 60, 100.0, "FIX-2027-02", "CAMP-FEB-01"),
                ("2027-03-31", 72, 45, 0.0, "FIX-2027-03", ""),
            ]
            for dt, rq, cap_ov, ad, rid, cid in fixture_rows:
                run_simulation_step(s, dt, rq, ad, rid, cid, capacity_override=cap_ov, mode_label="Fixture Override")
            st.success("3-Month NUR Fixture executed! Check the Ledger tab or table below to verify exact match.")
            st.rerun()

    with col_t2:
        st.markdown("#### Test B: NUR Business-Specific No-Show Test (`no_show_rate = 0.20`)")
        st.markdown(
            "Expected Handbook Result (page 85):
"
            "- Reset baseline, set `no_show_rate = 0.20`, `requested = 80`:
"
            "- `booked = 60`, `attended = 48`, `revenue = $1,200`, `variable = $240`, `profit = $260`."
        )
        if st.button("▶️ Reset & Run 20% No-Show Test"):
            st.session_state.sim_state = default_state()
            s = st.session_state.sim_state
            s["params"]["no_show_rate"] = 0.20
            ok, msg = run_simulation_step(s, "2027-01-31", 80, 0.0, "TEST-NOSHOW-20", mode_label="No-Show Test")
            st.success(msg)
            st.rerun()

    if state["ledger"]:
        st.markdown("#### Current Ledger Verification Table")
        st.dataframe(pd.DataFrame(state["ledger"]), use_container_width=True)

# ==============================================================================
# TAB 5: AI HANDOFF & STAGE 2/3 ROADMAP
# ==============================================================================
with tabs[4]:
    st.subheader("Manual AI Specialist Handoff & Upcoming Build Stages")
    st.markdown(
        "**Manual Integration Workflow (Handbook p. 58):**
"
        "1. Export your current snapshot JSON from the sidebar (`SNAP-NUR2-...`).
"
        "2. Attach the snapshot to your **Finance**, **Operations**, **Market & Marketing**, or **Independent Reviewer** assistant.
"
        "3. Paste and review the returned `proposed_changes` below before approving any adjustment."
    )
    st.text_area("Paste Structured Assistant Recommendation (for Student Review Log)", height=140, placeholder='{"role": "Finance", "snapshot_id": "SNAP-NUR2-001", "approval_status": "pending", ...}')
    st.markdown(
        "#### Roadmap Status
"
        "- **Stage 1 (Active):** Inputs, startup balances, Precalculus math modes, deterministic ledger, Save/Load JSON, fixture tests.
"
        "- **Stage 2 (Next):** Full 8-report Report Center (PDF/CSV), Costed Marketing Studio (`campaign_id` A/B testing), and Two-Report Decision Memo builder.
"
        "- **Stage 3 (Planned):** Cross-Course Connections panel & Frozen-Snapshot Assessment generator."
    )
