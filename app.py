"""
Formula 1 World Championship Dashboard (1950-2024)
====================================================
Framework : Streamlit
Charts    : Plotly Express / Graph Objects
Data      : f1_race_results_complete.csv
            f1_standings_history.csv
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# -- Page Configuration --------------------------------------------------------
st.set_page_config(
    page_title="F1 Championship Dashboard",
    page_icon="F1",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .stApp { background-color: #f5f6fa; }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #C0392B;
        text-align: center;
        letter-spacing: 0.5px;
        margin-bottom: 0;
    }
    [data-testid="stMetricValue"] { color: #C0392B; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

CHART_TEMPLATE = "plotly_white"
COLOR_SEQ      = px.colors.qualitative.D3


# -- Data Loading --------------------------------------------------------------
@st.cache_data
def load_data():
    results   = pd.read_csv("f1_race_results_complete.csv")
    standings = pd.read_csv("f1_standings_history.csv")

    for col in ["position", "positionOrder", "grid", "points", "laps", "fastest_lap_speed"]:
        if col in results.columns:
            results[col] = pd.to_numeric(results[col], errors="coerce")

    standings["points"] = pd.to_numeric(standings["points"], errors="coerce")
    standings["wins"]   = pd.to_numeric(standings["wins"],   errors="coerce")

    return results, standings

results_df, standings_df = load_data()
ALL_YEARS = sorted(results_df["year"].dropna().unique().astype(int))


# ==============================================================================
# HEADER
# ==============================================================================
st.markdown('<div class="main-title">Formula 1 World Championship Dashboard</div>',
            unsafe_allow_html=True)

st.divider()

# ==============================================================================
# GLOBAL CONTROL — Year Range
# ==============================================================================
st.markdown("**Global Filter — Season Range** &nbsp;&nbsp; *(updates all charts simultaneously)*")
global_year = st.slider(
    label="Season Range",
    min_value=int(ALL_YEARS[0]),
    max_value=int(ALL_YEARS[-1]),
    value=(2000, int(ALL_YEARS[-1])),
    label_visibility="collapsed",
)

base_r = results_df[
    (results_df["year"] >= global_year[0]) &
    (results_df["year"] <= global_year[1])
].copy()

base_s = standings_df[
    (standings_df["year"] >= global_year[0]) &
    (standings_df["year"] <= global_year[1])
].copy()

# KPI row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Races",         base_r[["year", "round"]].drop_duplicates().shape[0])
k2.metric("Drivers",       base_r["driver_name"].nunique())
k3.metric("Constructors",  base_r["constructor_name"].nunique())
k4.metric("Host Countries",base_r["circuit_country"].nunique())

st.divider()


# ==============================================================================
# ROW 1 — Chart 1 (Line) | Chart 2 (Bar) | Chart 5 (Donut)
# ==============================================================================
col1, col2, col5 = st.columns(3, gap="medium")

# ── Chart 1: Line Chart ────────────────────────────────────────────────────────
with col1:
    st.subheader("Points Progression")

    c1a, c1b = st.columns(2)
    c1_focus = c1a.radio("Focus", ["Driver", "Constructor"], key="c1_focus", horizontal=True)
    c1_topn  = c1b.slider("Top N", 3, 15, 8, key="c1_topn")

    filt_s1 = base_s[base_s["type"] == c1_focus.lower()]
    end_season1 = (
        filt_s1.sort_values(["year", "round"])
        .groupby(["year", "entity_name"], as_index=False)
        .last()[["year", "entity_name", "points"]]
    )
    top1 = (
        end_season1.groupby("entity_name")["points"]
        .sum().nlargest(c1_topn).index.tolist()
    )
    line_data = end_season1[end_season1["entity_name"].isin(top1)]

    fig_line = px.line(
        line_data,
        x="year", y="points", color="entity_name",
        markers=True,
        template=CHART_TEMPLATE,
        labels={"year": "Season", "points": "Points", "entity_name": c1_focus},
        color_discrete_sequence=COLOR_SEQ,
    )
    fig_line.update_layout(
        height=310,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(dtick=5),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#f5f6fa",
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ── Chart 2: Horizontal Bar Chart ─────────────────────────────────────────────
with col2:
    st.subheader("Race Wins Ranking")

    c2a, c2b = st.columns(2)
    c2_focus = c2a.radio("Focus", ["Driver", "Constructor"], key="c2_focus", horizontal=True)
    c2_topn  = c2b.slider("Top N", 3, 20, 10, key="c2_topn")

    name_col2 = "driver_name" if c2_focus == "Driver" else "constructor_name"
    wins_data = (
        base_r[base_r["positionOrder"] == 1]
        .groupby(name_col2).size()
        .reset_index(name="wins")
        .nlargest(c2_topn, "wins")
        .sort_values("wins")
    )
    fig_bar = px.bar(
        wins_data, x="wins", y=name_col2, orientation="h",
        color="wins", color_continuous_scale="Reds",
        template=CHART_TEMPLATE,
        labels={"wins": "Race Wins", name_col2: c2_focus},
    )
    fig_bar.update_layout(
        height=310,
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#f5f6fa",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ── Chart 5: Donut Chart ───────────────────────────────────────────────────────
with col5:
    st.subheader("DNF Reasons")
    st.caption("Genuine retirements only.")

    c5_top = st.slider("Top N", 5, 15, 8, key="c5_top")

    finished_labels = {"Finished"} | {f"+{i} Lap{'s' if i>1 else ''}" for i in range(1, 15)}
    dnf_df     = base_r[~base_r["dnf_reason"].isin(finished_labels)]
    dnf_counts = dnf_df["dnf_reason"].value_counts().head(c5_top).reset_index()
    dnf_counts.columns = ["reason", "count"]

    fig_donut = px.pie(
        dnf_counts, names="reason", values="count",
        hole=0.45,
        template=CHART_TEMPLATE,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_donut.update_traces(
        textposition="inside",
        textinfo="percent+label",
        insidetextfont=dict(size=8),
    )
    fig_donut.update_layout(
        height=310, showlegend=False,
        paper_bgcolor="#f5f6fa",
        margin=dict(l=5, r=5, t=10, b=10),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

st.divider()


# ==============================================================================
# ROW 2 — Chart 3 (Heatmap) | Chart 6 (Treemap)
# ==============================================================================
col3, col6 = st.columns([3, 2], gap="large")

# ── Chart 3: Performance Heatmap ──────────────────────────────────────────────
with col3:
    st.subheader("Season-by-Season Performance Heatmap")
    st.caption("Darker red = stronger performance. Empty = did not compete.")

    h1, h2, h3 = st.columns(3)
    c3_focus  = h1.radio("Focus", ["Driver", "Constructor"], key="c3_focus", horizontal=True)
    c3_topn   = h2.slider("Top N", 5, 25, 12, key="c3_topn")
    c3_metric = h3.radio("Metric", ["Points", "Wins"], key="c3_metric", horizontal=True)

    name_col3 = "driver_name" if c3_focus == "Driver" else "constructor_name"

    if c3_metric == "Points":
        heatmap_agg = base_r.groupby(["year", name_col3])["points"].sum().reset_index()
        heat_val_col, heat_label = "points", "Total Points"
    else:
        heatmap_agg = (
            base_r[base_r["positionOrder"] == 1]
            .groupby(["year", name_col3]).size().reset_index(name="wins")
        )
        heat_val_col, heat_label = "wins", "Race Wins"

    top_entities3 = (
        heatmap_agg.groupby(name_col3)[heat_val_col]
        .sum().nlargest(c3_topn).index.tolist()
    )
    heatmap_agg = heatmap_agg[heatmap_agg[name_col3].isin(top_entities3)]

    pivot = (
        heatmap_agg.pivot_table(
            index=name_col3, columns="year",
            values=heat_val_col, aggfunc="sum"
        ).fillna(0)
    )
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=True).index]

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.astype(str).tolist(),
        y=pivot.index.tolist(),
        colorscale="Reds",
        hoverongaps=False,
        hovertemplate=(
            "<b>%{y}</b><br>Season: %{x}<br>"
            f"{heat_label}: %{{z:.0f}}<extra></extra>"
        ),
        colorbar=dict(title=heat_label, thickness=10),
    ))
    fig_heat.update_layout(
        height=max(260, c3_topn * 20),
        template=CHART_TEMPLATE,
        xaxis=dict(
            title="Season",
            dtick=5 if (global_year[1] - global_year[0]) > 10 else 1,
        ),
        yaxis=dict(title=""),
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#f5f6fa",
        plot_bgcolor="#ffffff",
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ── Chart 6: Treemap ───────────────────────────────────────────────────────────
with col6:
    st.subheader("Points by Nationality")
    st.caption("Total points earned by drivers or constructors from each country.")

    c6_focus = st.radio("Focus", ["Driver", "Constructor"], key="c6_focus", horizontal=True)

    nat_col6 = "driver_nationality" if c6_focus == "Driver" else "constructor_nationality"
    nat_data = (
        base_r.groupby(nat_col6)["points"]
        .sum().reset_index().nlargest(20, "points")
    )
    fig_tree = px.treemap(
        nat_data,
        path=[nat_col6], values="points",
        color="points", color_continuous_scale="OrRd",
        template=CHART_TEMPLATE,
        labels={"points": "Total Points", nat_col6: "Nationality"},
    )
    fig_tree.update_layout(
        height=max(260, c3_topn * 20),
        paper_bgcolor="#f5f6fa",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig_tree, use_container_width=True)
