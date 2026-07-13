"""Plotly chart builders for the Ascent steel forecast dashboard."""

from __future__ import annotations

from typing import List, Optional, Sequence

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ascent-inspired palette (steel blue / copper accent)
ASCENT_BLUE = "#1B4F72"
ASCENT_STEEL = "#2E86AB"
ASCENT_COPPER = "#C4783A"
ASCENT_TEAL = "#1ABC9C"
ASCENT_SLATE = "#5D6D7E"
ASCENT_RED = "#C0392B"
ASCENT_GREEN = "#27AE60"
ASCENT_GOLD = "#D4A017"

CATEGORY_COLORS = {
    "Overall": ASCENT_BLUE,
    "Hot Rolled Plates": "#E74C3C",
    "HR I-Beams/Channels": "#8E44AD",
    "Sub Framing": "#16A085",
    "Sheet/Trim Painted": "#F39C12",
    "HSS Round Pipes": "#2980B9",
    "HSS Square/Rect Tubes": "#1ABC9C",
    "TNFAB": "#C4783A",
    "TNFAB2nd": "#7F8C8D",
}

# Short labels for narrow screens (bar charts / legends)
CATEGORY_SHORT = {
    "Overall": "Overall",
    "Hot Rolled Plates": "HR Plates",
    "HR I-Beams/Channels": "HR Beams",
    "Sub Framing": "Sub Frame",
    "Sheet/Trim Painted": "Sheet/Trim",
    "HSS Round Pipes": "HSS Round",
    "HSS Square/Rect Tubes": "HSS Sq/Rect",
    "TNFAB": "TNFAB",
    "TNFAB2nd": "TNFAB 2nd",
}


def short_category(name: str) -> str:
    return CATEGORY_SHORT.get(name, name if len(name) <= 14 else name[:12] + "…")


def _wrap_title(title: str, compact: bool) -> str:
    """Break long titles so Plotly does not clip them on narrow widths."""
    if not compact or not title:
        return title
    if " — " in title:
        left, right = title.split(" — ", 1)
        return f"{left}<br><span style='font-size:0.92em;opacity:0.9'>{right}</span>"
    if len(title) > 34:
        cut = title.rfind(" ", 0, 34)
        if cut < 12:
            cut = 34
        return title[:cut].rstrip() + "<br>" + title[cut:].lstrip()
    return title


def _layout(
    fig: go.Figure,
    title: str,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    """
    Shared chart chrome.
    compact=True: phone-friendly margins, smaller type, legend below, wrapped titles.
    """
    is_dark = theme == "dark"
    paper = "rgba(0,0,0,0)"
    plot = "rgba(0,0,0,0)"
    font_color = "#E8EEF4" if is_dark else "#1A1A2E"
    grid = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.08)"

    title_text = _wrap_title(title, compact)
    title_size = 12 if compact else 15
    body_size = 10 if compact else 12
    legend_size = 9 if compact else 11

    if compact:
        # Legend under plot so it never collides with title or traces
        legend = dict(
            orientation="h",
            yanchor="top",
            y=-0.28,
            xanchor="left",
            x=0,
            font=dict(size=legend_size),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
            tracegroupgap=4,
        )
        # Extra bottom room for legend; top room for wrapped title
        margin = dict(l=44, r=10, t=64, b=96)
    else:
        legend = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=legend_size),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
        )
        margin = dict(l=52, r=16, t=72, b=48)

    fig.update_layout(
        title=dict(
            text=title_text,
            x=0.0,
            xanchor="left",
            y=0.98,
            yanchor="top",
            font=dict(size=title_size, color=font_color),
            pad=dict(t=2, b=6, l=0, r=0),
        ),
        paper_bgcolor=paper,
        plot_bgcolor=plot,
        font=dict(
            family="Segoe UI, Inter, Arial, sans-serif",
            color=font_color,
            size=body_size,
        ),
        legend=legend,
        margin=margin,
        hovermode="x unified",
        autosize=True,
        dragmode=False,
        xaxis=dict(
            showgrid=True,
            gridcolor=grid,
            zeroline=False,
            automargin=True,
            title=dict(standoff=6 if compact else 8, font=dict(size=body_size)),
            tickfont=dict(size=9 if compact else 11),
            nticks=7 if compact else None,
            tickangle=-30 if compact else 0,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid,
            zeroline=False,
            tickprefix="$",
            ticksuffix="",
            automargin=True,
            title=dict(standoff=4 if compact else 6, font=dict(size=body_size)),
            tickfont=dict(size=9 if compact else 11),
            nticks=6 if compact else None,
        ),
    )
    return fig


def apply_compact_polish(fig: go.Figure, *, height: int | None = None) -> go.Figure:
    """
    Final pass for phone rendering: external space, no clipped axes,
    reduced marker clutter. Safe to call even if already compact-built.
    """
    updates = dict(
        autosize=True,
        dragmode=False,
        hovermode="closest",
        margin=dict(l=46, r=12, t=58, b=100),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.30,
            x=0,
            xanchor="left",
            font=dict(size=9),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
            itemwidth=30,
        ),
        title=dict(
            font=dict(size=12),
            x=0,
            xanchor="left",
            y=0.99,
            yanchor="top",
            pad=dict(t=0, b=4),
        ),
        font=dict(size=10),
    )
    if height is not None:
        updates["height"] = height
    fig.update_layout(**updates)
    fig.update_xaxes(
        automargin=True,
        tickfont=dict(size=9),
        title_font=dict(size=10),
        tickangle=-35,
        nticks=6,
        showspikes=False,
    )
    fig.update_yaxes(
        automargin=True,
        tickfont=dict(size=9),
        title_font=dict(size=10),
        nticks=5,
        showspikes=False,
    )
    # Smaller markers on all scatter traces
    for tr in fig.data:
        if getattr(tr, "type", None) == "scatter" and getattr(tr, "marker", None) is not None:
            try:
                tr.marker.size = min(float(tr.marker.size or 6), 5)
            except Exception:
                pass
    return fig


def base_vs_adjusted_line(
    df: pd.DataFrame,
    category: str,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    sub = df[df["Category"] == category].sort_values("Date")
    fig = go.Figure()
    marker_size = 4 if compact else 6
    fig.add_trace(
        go.Scatter(
            x=sub["Date"],
            y=sub["Base_Price_per_Ton"],
            name="Base" if compact else "Base Forecast",
            mode="lines+markers",
            line=dict(color=ASCENT_STEEL, width=2.2 if compact else 2.5, dash="solid"),
            marker=dict(size=marker_size),
            hovertemplate="%{x|%b %Y}<br>Base: $%{y:,.0f}/ton<extra></extra>",
        )
    )
    if "Adjusted_Price_per_Ton" in sub.columns:
        fig.add_trace(
            go.Scatter(
                x=sub["Date"],
                y=sub["Adjusted_Price_per_Ton"],
                name="Adjusted" if compact else "Risk-Adjusted Forecast",
                mode="lines+markers",
                line=dict(color=ASCENT_COPPER, width=2.2 if compact else 2.5),
                marker=dict(size=marker_size),
                hovertemplate="%{x|%b %Y}<br>Adjusted: $%{y:,.0f}/ton<extra></extra>",
            )
        )
        if not compact:
            fig.add_trace(
                go.Scatter(
                    x=list(sub["Date"]) + list(sub["Date"][::-1]),
                    y=list(sub["Adjusted_Price_per_Ton"])
                    + list(sub["Base_Price_per_Ton"][::-1]),
                    fill="toself",
                    fillcolor="rgba(196,120,58,0.12)",
                    line=dict(color="rgba(0,0,0,0)"),
                    name="Adjustment Band",
                    hoverinfo="skip",
                    showlegend=True,
                )
            )
    fig.update_yaxes(title_text="$/ton" if compact else "$ / ton")
    fig.update_xaxes(title_text="")
    cat_label = short_category(category) if compact else category
    return _layout(
        fig,
        f"{cat_label} — Base vs Adjusted" if compact else f"{category} — 24-Month Base vs Risk-Adjusted Forecast",
        theme,
        compact=compact,
    )


def multi_category_lines(
    df: pd.DataFrame,
    price_col: str = "Base_Price_per_Ton",
    theme: str = "dark",
    alert_categories: Optional[Sequence[str]] = None,
    *,
    compact: bool = False,
) -> go.Figure:
    """Multi-category price paths; alert categories drawn thicker in red."""
    alert_set = set(alert_categories or [])
    fig = go.Figure()
    for cat in df["Category"].unique():
        sub = df[df["Category"] == cat].sort_values("Date")
        is_alert = cat in alert_set
        color = ASCENT_RED if is_alert else CATEGORY_COLORS.get(cat, ASCENT_SLATE)
        display = short_category(str(cat)) if compact else str(cat)
        name = f"⚠ {display}" if is_alert else display
        fig.add_trace(
            go.Scatter(
                x=sub["Date"],
                y=sub[price_col],
                name=name,
                mode="lines",
                line=dict(color=color, width=2.8 if is_alert else (1.8 if compact else 2.2)),
                hovertemplate=f"{name}<br>%{{x|%b %Y}}: $%{{y:,.0f}}/ton<extra></extra>",
            )
        )
    label = "Base" if "Base" in price_col else "Adjusted"
    fig.update_yaxes(title_text="$/ton" if compact else "$ / ton")
    return _layout(
        fig,
        f"All categories — {label}" if compact else f"All Categories — {label} $/ton Path",
        theme,
        compact=compact,
    )


def mom_bars(
    df: pd.DataFrame,
    category: str,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    sub = df[df["Category"] == category].sort_values("Date")
    colors = [ASCENT_GREEN if v >= 0 else ASCENT_RED for v in sub["MoM_Pct"]]
    fig = go.Figure(
        go.Bar(
            x=sub["Date"],
            y=sub["MoM_Pct"],
            marker_color=colors,
            name="MoM %",
            hovertemplate="%{x|%b %Y}<br>MoM: %{y:.2f}%<extra></extra>",
        )
    )
    fig.update_yaxes(title_text="MoM %", ticksuffix="%", tickprefix="")
    cat_label = short_category(category) if compact else category
    out = _layout(
        fig,
        f"{cat_label} — MoM %" if compact else f"{category} — Month-over-Month Change (%)",
        theme,
        compact=compact,
    )
    # _layout defaults $/ton prefix — MoM is percent
    out.update_yaxes(tickprefix="", ticksuffix="%", title_text="MoM %")
    return out


def category_comparison_bar(
    df: pd.DataFrame,
    theme: str = "dark",
    alert_categories: Optional[Sequence[str]] = None,
    *,
    compact: bool = False,
) -> go.Figure:
    """Average base vs adjusted by category. Alert categories render in red."""
    alert_set = set(alert_categories or [])
    cols = ["Base_Price_per_Ton"]
    if "Adjusted_Price_per_Ton" in df.columns:
        cols.append("Adjusted_Price_per_Ton")
    agg = df.groupby("Category", as_index=False)[cols].mean()
    order = [c for c in CATEGORY_COLORS if c in set(agg["Category"])]
    if order:
        agg["_ord"] = agg["Category"].map({c: i for i, c in enumerate(order)})
        agg = agg.sort_values("_ord").drop(columns="_ord")
    else:
        agg = agg.sort_values("Category")

    cat_names: List[str] = [str(c) for c in agg["Category"].tolist()]
    if compact:
        labels = [
            (f"⚠ {short_category(c)}" if c in alert_set else short_category(c))
            for c in cat_names
        ]
    else:
        labels = [f"⚠️ {c}" if c in alert_set else c for c in cat_names]
    base_colors = [ASCENT_RED if c in alert_set else ASCENT_STEEL for c in cat_names]
    adj_colors = ["#E74C3C" if c in alert_set else ASCENT_COPPER for c in cat_names]

    fig = go.Figure()
    if compact:
        # Horizontal bars: category names fully readable on phones
        fig.add_trace(
            go.Bar(
                y=labels,
                x=agg["Base_Price_per_Ton"],
                name="Base",
                orientation="h",
                marker_color=base_colors,
                hovertemplate="%{y}<br>Base: $%{x:,.0f}<extra></extra>",
            )
        )
        if "Adjusted_Price_per_Ton" in agg.columns:
            fig.add_trace(
                go.Bar(
                    y=labels,
                    x=agg["Adjusted_Price_per_Ton"],
                    name="Adj",
                    orientation="h",
                    marker_color=adj_colors,
                    hovertemplate="%{y}<br>Adj: $%{x:,.0f}<extra></extra>",
                )
            )
        fig.update_layout(barmode="group")
        fig.update_xaxes(title_text="$/ton", tickprefix="$", automargin=True)
        fig.update_yaxes(title_text="", automargin=True, tickprefix="", ticksuffix="")
        # Clear default $ prefix from shared y layout for category names
        out = _layout(fig, "Avg price by category", theme, compact=compact)
        out.update_yaxes(tickprefix="", ticksuffix="", automargin=True)
        out.update_xaxes(tickprefix="$", automargin=True)
        # More height-friendly bottom margin; legend still below
        out.update_layout(margin=dict(l=8, r=12, t=52, b=72))
        return out

    fig.add_trace(
        go.Bar(
            x=labels,
            y=agg["Base_Price_per_Ton"],
            name="Avg Base",
            marker_color=base_colors,
        )
    )
    if "Adjusted_Price_per_Ton" in agg.columns:
        fig.add_trace(
            go.Bar(
                x=labels,
                y=agg["Adjusted_Price_per_Ton"],
                name="Avg Adjusted",
                marker_color=adj_colors,
            )
        )
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="$ / ton")
    fig.update_xaxes(tickangle=-32, automargin=True)
    return _layout(fig, "Category Average Price — Base vs Adjusted", theme, compact=compact)


def sensitivity_line(
    sens_df: pd.DataFrame,
    factor_label: str,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sens_df["Factor_Value"],
            y=sens_df["Avg_Adjusted_Price"],
            mode="lines+markers",
            line=dict(color=ASCENT_STEEL, width=2.5 if compact else 3),
            marker=dict(size=6 if compact else 8, color=ASCENT_COPPER),
            name="Avg Adj $/ton" if compact else "Avg Adjusted $/ton",
            hovertemplate=f"{factor_label}: %{{x}}<br>Avg Price: $%{{y:,.0f}}/ton<extra></extra>",
        )
    )
    fig.update_xaxes(title_text=factor_label if not compact else "")
    fig.update_yaxes(title_text="$/ton" if compact else "Avg Adjusted $ / ton")
    short_factor = factor_label.replace(" (%)", "")
    return _layout(
        fig,
        f"Sensitivity — {short_factor}" if compact else f"Sensitivity — {factor_label}",
        theme,
        compact=compact,
    )


def tornado_chart(
    tornado_df: pd.DataFrame,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    fig = go.Figure()
    # Short factor names on phones
    factors = tornado_df["Factor"].tolist()
    if compact:
        factors = [
            str(f)
            .replace(" Change (%)", "")
            .replace(" Risk (%)", "")
            .replace(" Premium (%)", "")
            .replace(" Volatility (%)", " Vol")
            .replace("China Dumping", "Dumping")
            .replace("Social/Demand", "Demand")
            for f in factors
        ]
    fig.add_trace(
        go.Bar(
            y=factors,
            x=tornado_df["Downside"],
            name="Down",
            orientation="h",
            marker_color=ASCENT_STEEL,
            hovertemplate="%{y}<br>Downside: $%{x:,.1f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=factors,
            x=tornado_df["Upside"],
            name="Up",
            orientation="h",
            marker_color=ASCENT_COPPER,
            hovertemplate="%{y}<br>Upside: $%{x:,.1f}<extra></extra>",
        )
    )
    fig.update_layout(barmode="relative")
    fig.update_xaxes(
        title_text="Impact ($/ton)" if compact else "Impact on Avg Adjusted Price ($/ton)",
        tickprefix="$",
        automargin=True,
    )
    fig.update_yaxes(automargin=True, tickprefix="", ticksuffix="")
    out = _layout(
        fig,
        "Tornado — risk impact" if compact else "Tornado — Risk Factor Impact Range",
        theme,
        compact=compact,
    )
    out.update_yaxes(tickprefix="", ticksuffix="")
    return out


def geo_risk_timeline(
    df: pd.DataFrame,
    category: str,
    theme: str = "dark",
    *,
    compact: bool = False,
) -> go.Figure:
    sub = df[df["Category"] == category].sort_values("Date")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    price_col = (
        "Adjusted_Price_per_Ton"
        if "Adjusted_Price_per_Ton" in sub.columns
        else "Base_Price_per_Ton"
    )
    fig.add_trace(
        go.Scatter(
            x=sub["Date"],
            y=sub[price_col],
            name="Price" if compact else "Price $/ton",
            line=dict(color=ASCENT_STEEL, width=2.2 if compact else 2.5),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=sub["Date"],
            y=sub["GeoRiskPremium_Pct"],
            name="Geo %" if compact else "Geo Risk % (in base)",
            line=dict(color=ASCENT_GOLD, width=2, dash="dot"),
        ),
        secondary_y=True,
    )
    fig.update_yaxes(
        title_text="$/ton" if compact else "$ / ton",
        secondary_y=False,
        tickprefix="$",
        automargin=True,
    )
    fig.update_yaxes(
        title_text="Geo %" if compact else "Geo Risk Premium %",
        secondary_y=True,
        ticksuffix="%",
        automargin=True,
        showgrid=False,
    )
    cat_label = short_category(category) if compact else category
    out = _layout(
        fig,
        f"{cat_label} — Price vs geo" if compact else f"{category} — Price vs Embedded Geo Risk",
        theme,
        compact=compact,
    )
    out.update_yaxes(
        title_text="$/ton" if compact else "$ / ton",
        secondary_y=False,
        tickprefix="$",
        automargin=True,
    )
    out.update_yaxes(
        title_text="Geo %" if compact else "Geo Risk Premium %",
        secondary_y=True,
        tickprefix="",
        ticksuffix="%",
        automargin=True,
        showgrid=False,
    )
    return out
