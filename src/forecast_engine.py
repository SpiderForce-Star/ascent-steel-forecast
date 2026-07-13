"""
Hybrid steel cost forecast adjustment engine.

Mirrors the refined Ascent methodology:
  Fast Markets + Bayesian / hybrid patterns for tariffs, China dumping,
  geo risk premium (8–11%), and social/demand volatility.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class RiskFactors:
    """Sidebar risk controls (percent units unless noted)."""

    tariff_change_pct: float = 0.0  # -20 to +40
    china_dumping_risk_pct: float = 25.0  # 0–100
    geo_risk_premium_pct: float = 9.5  # 8–11
    social_demand_vol_pct: float = 10.0  # 0–50

    def to_dict(self) -> dict:
        return asdict(self)


# Baseline assumptions baked into sample models (neutral adjustment ≈ 1.0)
BASELINE = RiskFactors(
    tariff_change_pct=0.0,
    china_dumping_risk_pct=25.0,
    geo_risk_premium_pct=9.5,
    social_demand_vol_pct=10.0,
)

# Pass-through / sensitivity coefficients (refined high-accuracy patterns)
TARIFF_PASSTHROUGH = 0.38  # fraction of tariff change that hits mill $/ton
DUMPING_PRICE_PRESSURE = -0.12  # dumping risk tends to pressure spot prices down
DUMPING_VOL_PREMIUM = 0.08  # but adds risk premium / volatility cost
GEO_BASELINE = 9.5
GEO_SENSITIVITY = 0.55  # share of geo premium delta applied to price
VOL_MEAN_PREMIUM = 0.10  # social/demand vol mean uplift coefficient
VOL_OSC_AMPLITUDE = 0.06  # seasonal oscillation amplitude from vol
DEFAULT_GEO_IN_BASE = 9.0  # geo already partially in base path


def _month_phase(dates: pd.Series) -> np.ndarray:
    """Seasonal phase 0–1 for hybrid oscillation (spring rise / fall decline)."""
    months = pd.to_datetime(dates).dt.month.values
    # Peak mid-year (June), trough December — smooth sine
    return np.sin(2 * np.pi * (months - 3) / 12.0)


def compute_adjustment_multipliers(
    df: pd.DataFrame,
    risks: RiskFactors,
) -> pd.DataFrame:
    """
    Compute Base vs Adjusted 24-month prices for all categories.

    Adjusted path:
      1. Structural uplift from tariff delta vs baseline
      2. China dumping: mild downward spot pressure + risk premium
      3. Geo risk premium differential vs baseline 9.5%
      4. Social/demand volatility: mean premium + seasonal oscillation
      5. Hybrid blend with mild mean-reversion toward category trend
    """
    out = df.copy()
    n = len(out)
    if n == 0:
        out["Adjusted_Price_per_Ton"] = []
        out["Adjustment_Factor"] = []
        out["Risk_Uplift_Pct"] = []
        return out

    # Category-specific sensitivity (plates more tariff-sensitive; HSS more dump/import)
    cat_tariff = {
        "Overall": 1.0,
        "Hot Rolled Plates": 1.15,
        "HR I-Beams/Channels": 1.05,
        "Sub Framing": 0.95,
        "Sheet/Trim Painted": 0.90,
        "HSS Round Pipes": 1.10,
        "HSS Square/Rect Tubes": 1.10,
        "TNFAB": 1.00,
        "TNFAB2nd": 1.05,
    }
    cat_dump = {
        "Overall": 1.0,
        "Hot Rolled Plates": 1.20,
        "HR I-Beams/Channels": 0.90,
        "Sub Framing": 1.10,
        "Sheet/Trim Painted": 1.15,
        "HSS Round Pipes": 1.25,
        "HSS Square/Rect Tubes": 1.25,
        "TNFAB": 1.00,
        "TNFAB2nd": 1.10,
    }

    tariff_delta = risks.tariff_change_pct - BASELINE.tariff_change_pct
    dump_delta = risks.china_dumping_risk_pct - BASELINE.china_dumping_risk_pct
    geo_delta = risks.geo_risk_premium_pct - BASELINE.geo_risk_premium_pct
    vol_delta = risks.social_demand_vol_pct - BASELINE.social_demand_vol_pct

    phases = _month_phase(out["Date"])
    # Progressive risk accrual: early months less fully priced-in than far horizon
    horizon = out.groupby("Category").cumcount().values.astype(float)
    max_h = max(out.groupby("Category").size().max() - 1, 1)
    horizon_w = 0.65 + 0.35 * (horizon / max_h)

    t_sens = out["Category"].map(lambda c: cat_tariff.get(c, 1.0)).values
    d_sens = out["Category"].map(lambda c: cat_dump.get(c, 1.0)).values

    # Component impacts (as decimal factors, small)
    tariff_imp = (tariff_delta / 100.0) * TARIFF_PASSTHROUGH * t_sens * horizon_w
    dump_imp = (
        (dump_delta / 100.0) * DUMPING_PRICE_PRESSURE * d_sens
        + (risks.china_dumping_risk_pct / 100.0) * DUMPING_VOL_PREMIUM * 0.15 * d_sens
    ) * horizon_w
    # Absolute geo: apply premium relative to what's already in base geo column
    base_geo = out["GeoRiskPremium_Pct"].fillna(DEFAULT_GEO_IN_BASE).values
    geo_imp = (
        (risks.geo_risk_premium_pct - base_geo) / 100.0
    ) * GEO_SENSITIVITY + (geo_delta / 100.0) * 0.25

    vol_mean = (risks.social_demand_vol_pct / 100.0) * VOL_MEAN_PREMIUM * 0.5
    vol_mean += (vol_delta / 100.0) * VOL_MEAN_PREMIUM
    vol_osc = (
        (risks.social_demand_vol_pct / 100.0)
        * VOL_OSC_AMPLITUDE
        * phases
        * horizon_w
    )

    total_imp = tariff_imp + dump_imp + geo_imp + vol_mean + vol_osc
    # Soft clamp for executive-stable paths
    total_imp = np.clip(total_imp, -0.18, 0.28)
    factor = 1.0 + total_imp

    out["Adjustment_Factor"] = np.round(factor, 5)
    out["Risk_Uplift_Pct"] = np.round(total_imp * 100.0, 3)
    out["Adjusted_Price_per_Ton"] = np.round(
        out["Base_Price_per_Ton"].values * factor, 2
    )
    out["Applied_GeoRisk_Pct"] = risks.geo_risk_premium_pct
    out["Applied_Tariff_Pct"] = risks.tariff_change_pct
    out["Applied_Dumping_Pct"] = risks.china_dumping_risk_pct
    out["Applied_Volatility_Pct"] = risks.social_demand_vol_pct

    # Recompute MoM on adjusted path for display
    out = out.sort_values(["Category", "Date"]).reset_index(drop=True)
    out["Adj_MoM_Pct"] = (
        out.groupby("Category")["Adjusted_Price_per_Ton"].pct_change() * 100.0
    ).round(3)
    out["Adj_MoM_Pct"] = out["Adj_MoM_Pct"].fillna(0.0)

    return out


def regenerate_forecast(
    base_df: pd.DataFrame,
    risks: RiskFactors,
    extend_to_24: bool = True,
) -> pd.DataFrame:
    """
    Apply risk factors and optionally extend short series to 24 months
    using the refined ±0.4–0.5% MoM seasonal pattern.
    """
    df = base_df.copy()
    if extend_to_24:
        df = _ensure_24_months(df)
    return compute_adjustment_multipliers(df, risks)


def _calendar_mom(month: int, beam_like: bool = False) -> float:
    """Return MoM as decimal matching refined model patterns."""
    table = {
        1: 0.0,
        2: 0.005,
        3: 0.005,
        4: 0.005,
        5: 0.005,
        6: 0.005,
        7: 0.0,
        8: -0.005,
        9: -0.005,
        10: -0.005,
        11: -0.005,
        12: -0.005,
    }
    rate = table.get(month, 0.0)
    if beam_like:
        rate = round(rate * 0.8, 5)  # ~0.4%
    return rate


def _ensure_24_months(df: pd.DataFrame) -> pd.DataFrame:
    """Extend each category forward to 24 months if needed."""
    pieces = []
    beam_like = {
        "HR I-Beams/Channels",
        "HSS Round Pipes",
        "HSS Square/Rect Tubes",
        "Sheet/Trim Painted",
    }
    for cat, sub in df.groupby("Category", sort=False):
        sub = sub.sort_values("Date").copy()
        if len(sub) >= 24:
            pieces.append(sub.iloc[:24])
            continue
        rows = [sub.iloc[i].to_dict() for i in range(len(sub))]
        last = rows[-1]
        price = float(last["Base_Price_per_Ton"])
        dt = pd.Timestamp(last["Date"])
        geo = float(last.get("GeoRiskPremium_Pct", 9.0))
        while len(rows) < 24:
            dt = (dt + pd.offsets.MonthBegin(1)) if dt.day == 1 else (
                dt + pd.DateOffset(months=1)
            ).replace(day=1)
            rate = _calendar_mom(dt.month, beam_like=cat in beam_like)
            price = round(price * (1 + rate), 2)
            # mild geo drift toward 8–11 band
            if dt.month <= 6:
                geo = min(11.0, max(8.0, geo + 0.1))
            else:
                geo = min(11.0, max(8.0, geo - 0.05))
            rows.append(
                {
                    "Month": dt.strftime("%Y-%m"),
                    "Date": dt,
                    "Category": cat,
                    "Base_Price_per_Ton": price,
                    "MoM_Pct": round(rate * 100, 2),
                    "GeoRiskPremium_Pct": round(geo, 2),
                    "Model_Source": str(last.get("Model_Source", "Extended"))
                    + " + hybrid extend",
                }
            )
        pieces.append(pd.DataFrame(rows))
    return pd.concat(pieces, ignore_index=True)


def sensitivity_grid(
    base_df: pd.DataFrame,
    category: str,
    base_risks: RiskFactors,
    factor_name: str,
    values: list[float],
) -> pd.DataFrame:
    """
    One-way sensitivity: average adjusted price vs a single risk factor.
    """
    sub = base_df[base_df["Category"] == category]
    if sub.empty:
        sub = base_df[base_df["Category"] == "Overall"]
    results = []
    for v in values:
        r = RiskFactors(**base_risks.to_dict())
        setattr(r, factor_name, v)
        adj = compute_adjustment_multipliers(sub, r)
        results.append(
            {
                "Factor_Value": v,
                "Avg_Adjusted_Price": float(adj["Adjusted_Price_per_Ton"].mean()),
                "End_Adjusted_Price": float(adj["Adjusted_Price_per_Ton"].iloc[-1]),
                "Avg_Uplift_Pct": float(adj["Risk_Uplift_Pct"].mean()),
            }
        )
    return pd.DataFrame(results)


def tornado_impacts(
    base_df: pd.DataFrame,
    category: str,
    base_risks: RiskFactors,
) -> pd.DataFrame:
    """Low/high swings for each risk factor around current settings."""
    specs = [
        ("tariff_change_pct", "Tariff Change (%)", -10.0, 25.0),
        ("china_dumping_risk_pct", "China Dumping Risk (%)", 0.0, 80.0),
        ("geo_risk_premium_pct", "Geo Risk Premium (%)", 8.0, 11.0),
        ("social_demand_vol_pct", "Social/Demand Volatility (%)", 0.0, 40.0),
    ]
    sub = base_df[base_df["Category"] == category]
    if sub.empty:
        sub = base_df[base_df["Category"] == "Overall"]
    base_adj = compute_adjustment_multipliers(sub, base_risks)
    base_avg = float(base_adj["Adjusted_Price_per_Ton"].mean())

    rows = []
    for attr, label, lo, hi in specs:
        r_lo = RiskFactors(**base_risks.to_dict())
        r_hi = RiskFactors(**base_risks.to_dict())
        setattr(r_lo, attr, lo)
        setattr(r_hi, attr, hi)
        avg_lo = float(compute_adjustment_multipliers(sub, r_lo)["Adjusted_Price_per_Ton"].mean())
        avg_hi = float(compute_adjustment_multipliers(sub, r_hi)["Adjusted_Price_per_Ton"].mean())
        rows.append(
            {
                "Factor": label,
                "Low": avg_lo,
                "High": avg_hi,
                "Base": base_avg,
                "Downside": avg_lo - base_avg,
                "Upside": avg_hi - base_avg,
                "Range": abs(avg_hi - avg_lo),
            }
        )
    return pd.DataFrame(rows).sort_values("Range", ascending=True)
