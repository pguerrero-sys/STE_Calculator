"""Representación geométrica: cada marcador es una posición de fase."""

import plotly.graph_objects as go

from .models import LineInput, PHASES

PHASE_COLORS = {"A": "#D45141", "B": "#087F8C", "C": "#6854B5"}


def geometry_figure(data: LineInput) -> go.Figure:
    xs = [c.x_m for c in data.conductors]
    ys = [c.y_m for c in data.conductors]
    padding = max(max(xs) - min(xs), max(ys), 1.0) * 0.15
    left, right = min(xs) - padding, max(xs) + padding
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=[left, right], y=[0, 0], mode="lines", name="Terreno de referencia: Y = 0 m",
        line={"color": "#947455", "width": 3}, hovertemplate="Terreno de referencia: Y = 0 m<extra></extra>",
    ))
    for phase in PHASES:
        conductors = [c for c in data.conductors if c.phase == phase]
        figure.add_trace(go.Scatter(
            x=[c.x_m for c in conductors], y=[c.y_m for c in conductors],
            text=[c.label for c in conductors], mode="markers+text", textposition="top center",
            name=f"Fase {phase}", marker={"size": 16, "color": PHASE_COLORS[phase], "line": {"color": "white", "width": 2}},
            hovertemplate="%{text}<br>X = %{x:.6g} m<br>Y = %{y:.6g} m<extra></extra>",
        ))
    figure.update_layout(
        template="plotly_white", height=470, margin={"l": 30, "r": 30, "t": 25, "b": 35},
        xaxis={"title": "X [m]", "range": [left, right], "zeroline": False},
        yaxis={"title": "Y [m]", "range": [-padding, max(ys) + padding], "scaleanchor": "x", "scaleratio": 1},
        legend={"orientation": "h", "y": 1.15}, dragmode="pan", paper_bgcolor="rgba(0,0,0,0)",
    )
    return figure
