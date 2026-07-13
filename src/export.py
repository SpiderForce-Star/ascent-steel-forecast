"""Excel and PDF export for executive steel cost forecast reports."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from src.forecast_engine import RiskFactors


def forecast_table_for_export(df: pd.DataFrame, category: Optional[str] = None) -> pd.DataFrame:
    data = df.copy()
    if category and category != "ALL":
        data = data[data["Category"] == category]
    cols = [
        "Month",
        "Category",
        "Base_Price_per_Ton",
        "MoM_Pct",
        "GeoRiskPremium_Pct",
    ]
    if "Adjusted_Price_per_Ton" in data.columns:
        cols += ["Adjusted_Price_per_Ton", "Adj_MoM_Pct", "Risk_Uplift_Pct", "Adjustment_Factor"]
    cols = [c for c in cols if c in data.columns]
    out = data[cols].sort_values(["Category", "Month"]).reset_index(drop=True)
    return out


def build_excel_report(
    df: pd.DataFrame,
    risks: RiskFactors,
    category: str,
    model_source: str = "Sample / Uploaded",
) -> bytes:
    """Return .xlsx bytes with Summary, Forecast, Sensitivity-ready full data."""
    buffer = io.BytesIO()
    table = forecast_table_for_export(df)
    cat_table = forecast_table_for_export(df, category)

    summary_rows = [
        ["Ascent Building Systems", "US Steel Cost 2-Year Forecast"],
        ["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M")],
        ["Model Source", model_source],
        ["Focus Category", category],
        ["", ""],
        ["Risk Factor", "Value"],
        ["Tariff Change (%)", risks.tariff_change_pct],
        ["China Dumping Risk (%)", risks.china_dumping_risk_pct],
        ["Geo Risk Premium (%)", risks.geo_risk_premium_pct],
        ["Social/Demand Volatility (%)", risks.social_demand_vol_pct],
        ["", ""],
        ["Methodology", "Fast Markets + hybrid Bayesian / seasonal MoM (±0.4–0.5%)"],
        ["Industry Focus", "PEMB / MBMA material categories"],
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["Field", "Value"])

    # Pivot wide for executive view
    pivot_base = df.pivot_table(
        index="Month", columns="Category", values="Base_Price_per_Ton", aggfunc="mean"
    )
    pivot_adj = None
    if "Adjusted_Price_per_Ton" in df.columns:
        pivot_adj = df.pivot_table(
            index="Month",
            columns="Category",
            values="Adjusted_Price_per_Ton",
            aggfunc="mean",
        )

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)
        cat_table.to_excel(writer, sheet_name="Category Forecast", index=False)
        table.to_excel(writer, sheet_name="Full Forecast Detail", index=False)
        pivot_base.to_excel(writer, sheet_name="Base Prices Wide")
        if pivot_adj is not None:
            pivot_adj.to_excel(writer, sheet_name="Adjusted Prices Wide")

        workbook = writer.book
        header_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#1B4F72",
                "font_color": "white",
                "border": 0,
            }
        )
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            ws.set_column(0, 15, 18)

    buffer.seek(0)
    return buffer.getvalue()


def build_pdf_report(
    df: pd.DataFrame,
    risks: RiskFactors,
    category: str,
    model_source: str = "Sample / Uploaded",
) -> bytes:
    """Return a concise executive PDF summary."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleAscent",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1B4F72"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "SubAscent",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#5D6D7E"),
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    h_style = ParagraphStyle(
        "HeadAscent",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1B4F72"),
        spaceBefore=10,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    body = ParagraphStyle(
        "BodyAscent",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
    )

    story = []
    story.append(Paragraph("Ascent Building Systems", title_style))
    story.append(
        Paragraph("US Steel Cost 2-Year Forecast Dashboard — Executive Report", sub_style)
    )
    story.append(
        Paragraph(
            f"Generated {datetime.now().strftime('%B %d, %Y %H:%M')} &nbsp;|&nbsp; "
            f"Source: {model_source} &nbsp;|&nbsp; Focus: <b>{category}</b>",
            body,
        )
    )
    story.append(Spacer(1, 8))

    story.append(Paragraph("Risk Factor Settings", h_style))
    risk_data = [
        ["Factor", "Value"],
        ["Tariff Change (%)", f"{risks.tariff_change_pct:.1f}"],
        ["China Dumping Risk (%)", f"{risks.china_dumping_risk_pct:.1f}"],
        ["Geo Risk Premium (%)", f"{risks.geo_risk_premium_pct:.1f}"],
        ["Social/Demand Volatility (%)", f"{risks.social_demand_vol_pct:.1f}"],
    ]
    risk_table = Table(risk_data, colWidths=[3.2 * inch, 1.5 * inch])
    risk_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0BEC5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(risk_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph(f"Forecast Table — {category}", h_style))
    cat_df = forecast_table_for_export(df, category)
    if cat_df.empty:
        cat_df = forecast_table_for_export(df, "Overall")

    display_cols = [
        c
        for c in [
            "Month",
            "Base_Price_per_Ton",
            "MoM_Pct",
            "Adjusted_Price_per_Ton",
            "Adj_MoM_Pct",
            "Risk_Uplift_Pct",
            "GeoRiskPremium_Pct",
        ]
        if c in cat_df.columns
    ]
    headers = {
        "Month": "Month",
        "Base_Price_per_Ton": "Base $/ton",
        "MoM_Pct": "MoM %",
        "Adjusted_Price_per_Ton": "Adj $/ton",
        "Adj_MoM_Pct": "Adj MoM %",
        "Risk_Uplift_Pct": "Risk Uplift %",
        "GeoRiskPremium_Pct": "Geo Risk %",
    }
    table_data = [[headers[c] for c in display_cols]]
    for _, row in cat_df.iterrows():
        line = []
        for c in display_cols:
            val = row[c]
            if c == "Month":
                line.append(str(val))
            elif "Pct" in c:
                line.append(f"{float(val):.2f}")
            else:
                line.append(f"{float(val):,.0f}")
        table_data.append(line)

    col_w = (10.0 * inch) / max(len(display_cols), 1)
    ft = Table(table_data, colWidths=[col_w] * len(display_cols), repeatRows=1)
    ft.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B0BEC5")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F4F7FA")],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(ft)
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "<b>Methodology notes:</b> Base path follows refined high-accuracy MoM patterns "
            "(±0.4–0.5%) aligned with Fast Markets and hybrid seasonal trains. "
            "Risk-adjusted path applies tariff pass-through, China dumping pressure/premium, "
            "geo risk premium (8–11%), and social/demand volatility oscillation. "
            "Categories target PEMB/MBMA production mix (plates, beams/channels, sub-framing, "
            "sheet/trim, HSS, TNFAB).",
            body,
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "CONFIDENTIAL — For internal Ascent Building Systems leadership review. "
            "Branding placeholder: replace logo assets in /assets as needed.",
            ParagraphStyle(
                "Footer",
                parent=body,
                fontSize=8,
                textColor=colors.HexColor("#7F8C8D"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
