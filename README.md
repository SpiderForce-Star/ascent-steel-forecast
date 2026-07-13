# Ascent Building Systems — US Steel Cost 2-Year Forecast Dashboard

Executive-ready **Streamlit** dashboard for PEMB / MBMA industry leaders.  
Visualizes **Base vs Risk-Adjusted** 24-month steel cost forecasts ($/ton) with tariff, China dumping, geo risk premium (8–11%), and social/demand volatility controls.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B)
![Plotly](https://img.shields.io/badge/Plotly-interactive-3F4F75)

---

## Features

| Area | Capability |
|------|------------|
| **Categories** | Overall, Hot Rolled Plates, HR I-Beams/Channels, Sub Framing, Sheet/Trim Painted, HSS Round Pipes, HSS Square/Rect Tubes, TNFAB, TNFAB2nd |
| **Data** | Pre-loaded 24-month sample (±0.4–0.5% MoM, GeoRisk 8–11%) |
| **Upload** | Excel models in December 2025, 5-1-2026, and 2-11-2026 layouts |
| **Charts** | Interactive Plotly Base vs Adjusted lines, multi-category paths, MoM bars, tornado / sensitivity |
| **Risk engine** | Tariff pass-through, dumping pressure/premium, geo premium, demand volatility oscillation |
| **Tabs** | Dashboard Overview · Category Deep Dive · Sensitivity Analysis · Export Report |
| **Export** | Excel workbook, PDF executive brief, CSV |
| **Theme** | Dark / light toggle with Ascent branding placeholder |

---

## Quick start (one command after install)

### 1. Install (once)

```powershell
cd C:\Users\chris.woodmore\ascent-steel-forecast-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Run (one command)

```powershell
streamlit run app.py
```

Or double-click / run:

```powershell
.\run.bat
```

The app opens in your browser (default `http://localhost:8501`).

Without activating a venv:

```powershell
python -m streamlit run app.py
```

---

## Using the dashboard

1. **Category** — pick a material category in the sidebar.  
2. **Upload** (optional) — drop a forecasting Excel file, click **Load upload**.  
3. **Risk sliders** — Tariff Change, China Dumping Risk, Geo Risk Premium (8–11%), Social/Demand Volatility.  
4. **Apply** — click **Apply adjustments & regenerate forecast** to rebuild the 2-year path.  
5. **Tabs** — review overview charts/table, deep dive, sensitivity, then export Excel/PDF.  
6. **Reset sample** — restores the bundled 5-1-2026-pattern sample data and baseline risks.

### Compatible Excel layouts

The parser auto-detects side-by-side blocks:

```text
Month | Overall | MoM % |  Month | Hot Rolled Plates | MoM % |  ...
```

Also supports:

- `Month-Year` headers (5-1-2026 style)
- `GeoRiskPremium` columns (`8-10%`, `9-11%`, or numeric)
- Standalone **TNFAB** tables (lower section of 5-1 model)
- Derives **TNFAB2nd** from TNFAB (~+2.3%) when the secondary series is missing

Example source files on this machine:

- `Desktop\Forecasting\December 2025 US Steel Forecasting Models.xlsx`
- `Desktop\Forecasting\5-1-2026 US Steel Forecasting.xlsx`
- `Desktop\Forecasting\US Steel Cost Forecasting 2-11-2026.xlsx`

---

## Project layout

```text
ascent-steel-forecast-app/
├── app.py                 # Streamlit entry point
├── requirements.txt
├── README.md
├── assets/
│   └── style.css          # Executive UI polish + Ascent branding styles
├── data/
│   └── sample_forecast.csv
├── exports/               # Optional local export folder
└── src/
    ├── data_loader.py     # Sample load + Excel parser
    ├── forecast_engine.py # Hybrid risk-adjusted forecast
    ├── charts.py          # Plotly figures
    └── export.py          # Excel / PDF builders
```

---

## Methodology (executive summary)

- **Base path**: refined seasonal MoM (±0.4–0.5%), aligned with Fast Markets–informed hybrid trains; July/January flats; spring rise / late-year ease.  
- **Tariffs**: partial pass-through to $/ton, stronger on plates & HSS.  
- **China dumping**: mild spot pressure + risk premium (import-sensitive categories).  
- **Geo risk premium**: 8–11% band, applied as differential vs embedded model geo.  
- **Social/demand volatility**: mean premium + seasonal oscillation.  
- Direct mill list prices (Nucor / U.S. Steel / SDI) are **not** used as primary sources, per model evaluation notes.

---

## Branding placeholder

Header shows **ASCENT BUILDING SYSTEMS · BRANDING PLACEHOLDER** and an **ABS** monogram.  
Replace logo assets under `assets/` and adjust the hero block in `app.py` when official brand files are available.

---

## Requirements

- Python 3.10+
- Windows / macOS / Linux
- Packages: see `requirements.txt` (streamlit, pandas, numpy, plotly, openpyxl, xlsxwriter, reportlab)

---

## Support

Internal tool for Ascent Building Systems leadership review.  
For model updates, re-export Excel in the same Month | Price | MoM block format and upload via the sidebar.
