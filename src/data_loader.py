"""
Load and normalize US steel forecast data from Excel models and sample CSV.

Supports the column-block layouts used in:
  - December 2025 US Steel Forecasting Models.xlsx
  - 5-1-2026 US Steel Forecasting.xlsx
  - US Steel Cost Forecasting 2-11-2026.xlsx
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

CATEGORIES = [
    "Overall",
    "Hot Rolled Plates",
    "HR I-Beams/Channels",
    "Sub Framing",
    "Sheet/Trim Painted",
    "HSS Round Pipes",
    "HSS Square/Rect Tubes",
    "TNFAB",
    "TNFAB2nd",
]

# Map header aliases found across model versions → canonical category names
CATEGORY_ALIASES = {
    "overall": "Overall",
    "overall($/ton)": "Overall",
    "hot rolled plates": "Hot Rolled Plates",
    "hr-plates": "Hot Rolled Plates",
    "hotrolledplates($/ton)": "Hot Rolled Plates",
    "plates/bars($/ton)": "Hot Rolled Plates",
    "plates ($/ton)": "Hot Rolled Plates",
    "hr i-beams/channels": "HR I-Beams/Channels",
    "hr-beams": "HR I-Beams/Channels",
    "hri-beams/channels($/ton)": "HR I-Beams/Channels",
    "beams($/ton)": "HR I-Beams/Channels",
    "i-beams ($/ton)": "HR I-Beams/Channels",
    "sub framing": "Sub Framing",
    "subframing": "Sub Framing",
    "subframing($/ton)": "Sub Framing",
    "zee's($/ton)": "Sub Framing",
    "zees($/ton)": "Sub Framing",
    "sheet/trim painted": "Sheet/Trim Painted",
    "sheet/trim": "Sheet/Trim Painted",
    "sheet/trim($/ton)": "Sheet/Trim Painted",
    "sheet/trimpainted($/ton)": "Sheet/Trim Painted",
    "hss round pipes": "HSS Round Pipes",
    "hss pipe": "HSS Round Pipes",
    "hss pipes($/ton)": "HSS Round Pipes",
    "hssroundpipes($/ton)": "HSS Round Pipes",
    "hss square/rect tubes": "HSS Square/Rect Tubes",
    "hss tubes": "HSS Square/Rect Tubes",
    "hss tubes($/ton)": "HSS Square/Rect Tubes",
    "hsssquare/recttubes($/ton)": "HSS Square/Rect Tubes",
    "tnfab": "TNFAB",
    "tnfab2nd": "TNFAB2nd",
    "tnfab 2nd": "TNFAB2nd",
    "tnfab second": "TNFAB2nd",
    "bars ($/ton)": "Sub Framing",
}

CANONICAL_COLUMNS = [
    "Month",
    "Date",
    "Category",
    "Base_Price_per_Ton",
    "MoM_Pct",
    "GeoRiskPremium_Pct",
    "Model_Source",
]

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_CSV = ROOT / "data" / "sample_forecast.csv"


def _norm_header(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return str(val).strip().lower().replace("  ", " ")


def _resolve_category(header: str) -> Optional[str]:
    h = _norm_header(header)
    if not h:
        return None
    if h in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[h]
    # loose contains match
    for key, cat in CATEGORY_ALIASES.items():
        if key in h or h in key:
            return cat
    for cat in CATEGORIES:
        if cat.lower() == h:
            return cat
    return None


def _parse_month(val) -> Optional[pd.Timestamp]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, pd.Timestamp):
        return val.to_period("M").to_timestamp()
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        # Excel serial dates are handled by pandas when reading; skip raw ints
        return None
    try:
        ts = pd.to_datetime(val, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.to_period("M").to_timestamp()
    except Exception:
        return None


def _parse_geo_risk(val) -> float:
    """Parse GeoRiskPremium values like '8-10%', '9-11%', or numeric 9.5."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 9.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("%", "")
    if "-" in s:
        parts = s.split("-")
        try:
            lo, hi = float(parts[0]), float(parts[1])
            return round((lo + hi) / 2.0, 2)
        except ValueError:
            return 9.0
    try:
        return float(s)
    except ValueError:
        return 9.0


def _parse_mom(val) -> float:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0.0
    if isinstance(val, str):
        s = val.strip().replace("%", "")
        if s in ("-", "—", "", "n/a", "N/A"):
            return 0.0
        try:
            v = float(s)
        except ValueError:
            return 0.0
    else:
        try:
            v = float(val)
        except (TypeError, ValueError):
            return 0.0
    # Models mix decimal (0.005) and percent (0.5); normalize to percent units
    if abs(v) <= 0.05:
        return round(v * 100.0, 3)
    return round(v, 3)


def load_sample_data() -> pd.DataFrame:
    """Load pre-bundled 24-month sample forecast (5-1-2026 pattern)."""
    if not SAMPLE_CSV.exists():
        raise FileNotFoundError(f"Sample data not found: {SAMPLE_CSV}")
    df = pd.read_csv(SAMPLE_CSV, parse_dates=["Date"])
    df["Month"] = df["Month"].astype(str)
    df["Category"] = df["Category"].astype(str)
    return df[CANONICAL_COLUMNS].copy()


def parse_excel_model(file_obj, source_name: str = "Uploaded Model") -> pd.DataFrame:
    """
    Parse an Ascent steel forecasting Excel workbook into long-form data.

    Detects side-by-side category blocks: Month | Price | MoM | [blank] | Month | ...
    Also captures GeoRiskPremium columns and standalone TNFAB tables.
    """
    xl = pd.ExcelFile(file_obj)
    frames: list[pd.DataFrame] = []

    for sheet in xl.sheet_names:
        raw = pd.read_excel(xl, sheet_name=sheet, header=None)
        if raw.empty or raw.dropna(how="all").empty:
            continue
        frames.append(_parse_sheet_blocks(raw, source_name=f"{source_name} / {sheet}"))
        frames.append(_parse_tnfab_blocks(raw, source_name=f"{source_name} / {sheet}"))

    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        raise ValueError(
            "Could not find forecast tables in the workbook. "
            "Expected Month | Category | MoM column blocks (December / 5-1 / 2-11 formats)."
        )

    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=["Date", "Base_Price_per_Ton"])
    df = df[df["Base_Price_per_Ton"] > 0]
    # Prefer later duplicate (more complete sheet) for same Month+Category
    df = df.sort_values(["Date", "Category"]).drop_duplicates(
        subset=["Month", "Category"], keep="last"
    )
    df = df.reset_index(drop=True)

    # If TNFAB2nd missing, derive from TNFAB (+~2.3% secondary source)
    cats = set(df["Category"].unique())
    if "TNFAB" in cats and "TNFAB2nd" not in cats:
        t2 = df[df["Category"] == "TNFAB"].copy()
        t2["Category"] = "TNFAB2nd"
        t2["Base_Price_per_Ton"] = (t2["Base_Price_per_Ton"] * 1.023).round(2)
        t2["Model_Source"] = t2["Model_Source"] + " (TNFAB2nd derived)"
        df = pd.concat([df, t2], ignore_index=True)

    return df[CANONICAL_COLUMNS]


def _find_header_row(raw: pd.DataFrame) -> Optional[int]:
    """Locate the first row that looks like a forecast header (contains Month + category)."""
    for i in range(min(len(raw), 80)):
        row = raw.iloc[i]
        texts = [_norm_header(v) for v in row.values]
        has_month = any(t in ("month", "month-year", "month/year") for t in texts)
        has_cat = any(_resolve_category(t) for t in texts if t not in ("month", "month-year", "mom%", "mo/mo %", "mom %"))
        if has_month and has_cat:
            return i
    return None


def _parse_sheet_blocks(raw: pd.DataFrame, source_name: str) -> pd.DataFrame:
    header_idx = _find_header_row(raw)
    if header_idx is None:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    header = raw.iloc[header_idx]
    # Identify blocks: column j is Month label, j+1 is category price, j+2 is MoM, optional geo at j+1 if labeled GeoRisk
    blocks = []
    geo_col = None
    ncols = raw.shape[1]
    j = 0
    while j < ncols:
        cell = _norm_header(header.iloc[j] if j < len(header) else None)
        if cell in ("month", "month-year", "month/year"):
            cat_header = header.iloc[j + 1] if j + 1 < ncols else None
            cat = _resolve_category(cat_header)
            if cat:
                mom_col = j + 2 if j + 2 < ncols else None
                blocks.append({"month_col": j, "price_col": j + 1, "mom_col": mom_col, "category": cat})
                j += 3
                continue
            # GeoRiskPremium only column pair
            if cat_header and "georisk" in _norm_header(cat_header):
                geo_col = j + 1
                j += 2
                continue
        if cell and "georisk" in cell:
            geo_col = j
        j += 1

    if not blocks:
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    rows = []
    for i in range(header_idx + 1, len(raw)):
        # Use first block's month column as primary date
        month_val = raw.iloc[i, blocks[0]["month_col"]]
        dt = _parse_month(month_val)
        if dt is None:
            # try any block month col
            for b in blocks:
                dt = _parse_month(raw.iloc[i, b["month_col"]])
                if dt is not None:
                    break
        if dt is None:
            continue

        geo = 9.0
        if geo_col is not None:
            geo = _parse_geo_risk(raw.iloc[i, geo_col])

        for b in blocks:
            price_raw = raw.iloc[i, b["price_col"]]
            try:
                price = float(price_raw)
            except (TypeError, ValueError):
                continue
            if np.isnan(price) or price <= 0:
                continue
            mom = 0.0
            if b["mom_col"] is not None:
                mom = _parse_mom(raw.iloc[i, b["mom_col"]])
            rows.append(
                {
                    "Month": dt.strftime("%Y-%m"),
                    "Date": dt,
                    "Category": b["category"],
                    "Base_Price_per_Ton": round(price, 2),
                    "MoM_Pct": mom,
                    "GeoRiskPremium_Pct": geo,
                    "Model_Source": source_name,
                }
            )

    return pd.DataFrame(rows)


def _parse_tnfab_blocks(raw: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """Parse standalone TNFAB / TNFAB2nd mini-tables (e.g. lower section of 5-1 model)."""
    rows = []
    for i in range(min(len(raw), 100)):
        for j in range(raw.shape[1]):
            val = raw.iloc[i, j]
            cat = _resolve_category(val)
            if cat not in ("TNFAB", "TNFAB2nd"):
                continue
            # Header row: Month-Year | TNFAB | MoM%  OR Month | TNFAB
            # Find month col nearby
            month_col = None
            for k in range(max(0, j - 2), min(raw.shape[1], j + 1)):
                if _norm_header(raw.iloc[i, k]) in ("month", "month-year", "month/year"):
                    month_col = k
                    break
            if month_col is None:
                month_col = j - 1 if j > 0 else 0
            price_col = j
            mom_col = j + 1 if j + 1 < raw.shape[1] else None

            for r in range(i + 1, len(raw)):
                dt = _parse_month(raw.iloc[r, month_col])
                if dt is None:
                    # stop after consecutive empty
                    if r > i + 2 and all(
                        pd.isna(raw.iloc[r, c]) if c < raw.shape[1] else True
                        for c in (month_col, price_col)
                    ):
                        break
                    continue
                try:
                    price = float(raw.iloc[r, price_col])
                except (TypeError, ValueError):
                    continue
                if np.isnan(price) or price <= 0:
                    continue
                mom = _parse_mom(raw.iloc[r, mom_col]) if mom_col is not None else 0.0
                rows.append(
                    {
                        "Month": dt.strftime("%Y-%m"),
                        "Date": dt,
                        "Category": cat,
                        "Base_Price_per_Ton": round(price, 2),
                        "MoM_Pct": mom,
                        "GeoRiskPremium_Pct": 9.0,
                        "Model_Source": source_name,
                    }
                )
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=CANONICAL_COLUMNS)


def filter_category(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Return rows for one category (or all categories if Overall multi-view uses full df)."""
    if category not in df["Category"].values:
        return df.iloc[0:0].copy()
    out = df[df["Category"] == category].sort_values("Date").copy()
    return out.reset_index(drop=True)


def available_categories(df: pd.DataFrame) -> list[str]:
    present = set(df["Category"].unique())
    return [c for c in CATEGORIES if c in present] + sorted(present - set(CATEGORIES))


def summary_metrics(df: pd.DataFrame, category: str) -> dict:
    sub = filter_category(df, category)
    if sub.empty:
        return {}
    prices = sub["Base_Price_per_Ton"]
    adj = sub["Adjusted_Price_per_Ton"] if "Adjusted_Price_per_Ton" in sub.columns else prices
    return {
        "start_price": float(prices.iloc[0]),
        "end_price": float(prices.iloc[-1]),
        "avg_price": float(prices.mean()),
        "min_price": float(prices.min()),
        "max_price": float(prices.max()),
        "start_adj": float(adj.iloc[0]),
        "end_adj": float(adj.iloc[-1]),
        "avg_adj": float(adj.mean()),
        "n_months": int(len(sub)),
        "avg_mom": float(sub["MoM_Pct"].mean()),
        "avg_geo": float(sub["GeoRiskPremium_Pct"].mean()) if "GeoRiskPremium_Pct" in sub else 9.0,
    }
