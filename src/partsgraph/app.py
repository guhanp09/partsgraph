import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .io import ROOT, require, theme
from .pipeline import load


def main():
    theme("PartsGraph", "Component dependency paths, constrained production, and disruption scenarios")
    require(ROOT / "data/processed/bom.csv", "partsgraph run")
    st.info(
        "BOM-derived engineering scenario. Suppliers, inventory, compatibility specifications, demand and economics are simulated."
    )
    model = load()
    supplier = st.sidebar.selectbox("Supplier outage", ["None"] + sorted(model.orders.supplier.unique()))
    horizon = st.sidebar.slider("Planning horizon (days)", 1, 60, 28)
    lead = st.sidebar.slider("Delivery delay (days)", 0, 30, 0)
    rejected = st.sidebar.slider("Rejected fraction of receipts", 0.0, 1.0, 0.0, 0.05)
    substitution = st.sidebar.checkbox("Use approved compatible spare inventory")
    r = model.scenario(None if supplier == "None" else supplier, horizon, lead, rejected, substitution)
    cols = st.columns(3)
    cols[0].metric("Buildable units", int(r["allocation"].buildable.sum()))
    cols[1].metric("Unfilled demand", r["unfilled_units"])
    cols[2].metric("Lost scenario contribution", f"₹{r['lost_contribution_inr']:,.0f}")
    tabs = st.tabs(["Production", "Dependency graph", "Actions and evidence"])
    with tabs[0]:
        st.dataframe(r["allocation"], hide_index=True)
        st.dataframe(r["paths"], hide_index=True)
    with tabs[1]:
        g = model.graph()
        selected = st.selectbox("Trace product", list(model.products["product"]))
        sub = g.subgraph({selected} | nx.descendants(g, selected))
        pos = nx.spring_layout(sub, seed=26)
        fig = go.Figure()
        for a, b in sub.edges:
            fig.add_trace(
                go.Scatter(
                    x=[pos[a][0], pos[b][0]],
                    y=[pos[a][1], pos[b][1]],
                    mode="lines",
                    line=dict(color="#b5c5d5"),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        fig.add_trace(
            go.Scatter(
                x=[pos[n][0] for n in sub],
                y=[pos[n][1] for n in sub],
                text=list(sub),
                mode="markers+text",
                textposition="top center",
                marker=dict(size=14, color="#168b8b"),
            )
        )
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with tabs[2]:
        checks = model.alternatives.copy()
        checks["compatible"] = [model.compatibility(r.original, r.alternate) for r in checks.itertuples()]
        st.dataframe(checks, hide_index=True)
        st.write("Spare transfers", r["transfers"])
        st.dataframe(pd.read_csv(ROOT / "reports/actions.csv"), hide_index=True)
        st.download_button(
            "Download scenario workbook",
            (ROOT / "reports/scenario_review.xlsx").read_bytes(),
            "scenario_review.xlsx",
        )
