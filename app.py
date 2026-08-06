"""
Ascent Building Systems — US Steel Cost 2-Year Forecast Dashboard

Executive Streamlit app for PEMB / MBMA industry leaders.
Pre-loads refined sample forecasts; accepts December 2025, 5-1-2026, and 2-11-2026 Excel models.
"""

from __future__ import annotations

import base64
import json
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.charts import (
    apply_compact_polish,
    base_vs_adjusted_line,
    category_comparison_bar,
    geo_risk_timeline,
    mom_bars,
    multi_category_lines,
    sensitivity_line,
    tornado_chart,
)
from src.data_loader import (
    CATEGORIES,
    available_categories,
    filter_category,
    load_sample_data,
    parse_excel_model,
    summary_metrics,
)
from src.export import build_excel_report, build_pdf_report, forecast_table_for_export
from src.forecast_engine import (
    BASELINE,
    RiskFactors,
    regenerate_forecast,
    sensitivity_grid,
    tornado_impacts,
)

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ICONS = ASSETS / "icons"
CSS_PATH = ASSETS / "style.css"
# Logo: prefer assets/, fall back to project root
LOGO_CANDIDATES = [
    ASSETS / "ascent-logo.png",
    ROOT / "ascent-logo.png",
]
# Video: prefer assets copy; fall back to project-root filename
VIDEO_CANDIDATES = [
    ASSETS / "intro-logo-spin.mp4",
    ROOT / "4 flat triangle logo spin.mp4",
]
ALERT_THRESHOLD = 0.03  # ±3% Base vs Adjusted

# Favicon / tab icon — Ascent logo (generated icons preferred)
def _resolve_page_icon() -> str:
    """Prefer the steel I-beam set (tab + Streamlit chrome)."""
    for p in (
        ICONS / "icon-192.png",
        ICONS / "favicon-32.png",
        ICONS / "favicon.ico",
        ICONS / "apple-touch-icon.png",
        ICONS / "favicon.png",
        *LOGO_CANDIDATES,
    ):
        if p.exists():
            return str(p)
    return "🏭"


st.set_page_config(
    page_title="Ascent | US Steel Cost 2-Year Forecast",
    page_icon=_resolve_page_icon(),
    layout="wide",
    # auto: expanded on desktop, collapsed on phones so content isn't hidden
    initial_sidebar_state="auto",
)

# Plotly: responsive, mobile-friendly (no scroll-zoom fighting page scroll)
PLOTLY_CONFIG = {
    "displayModeBar": True,
    "responsive": True,
    "displaylogo": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {
        "format": "png",
        "filename": "ascent_steel_forecast",
        "height": 720,
        "width": 1280,
        "scale": 2,
    },
}

# Phone / tablet chart heights (px)
CHART_H = {
    "desktop": {"main": 400, "side": 400, "wide": 420, "small": 340, "table": 300},
    "mobile": {"main": 320, "side": 340, "wide": 340, "small": 280, "table": 240},
}


def _file_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


@st.cache_data(show_spinner=False)
def _cached_b64(path_str: str, mtime: float) -> str:
    return _file_b64(Path(path_str))


def media_b64(path: Path) -> str:
    if not path.exists():
        return ""
    return _cached_b64(str(path.resolve()), path.stat().st_mtime)


def resolve_logo_path() -> Path | None:
    for p in LOGO_CANDIDATES:
        if p.exists():
            return p
    return None


def resolve_video_path() -> Path | None:
    for p in VIDEO_CANDIDATES:
        if p.exists():
            return p
    return None


def _chart_with_alerts(fn, *args, alert_categories=None, **kwargs):
    """Call chart helpers with optional kwargs when supported (avoids TypeError on stale modules)."""
    import inspect

    try:
        sig = inspect.signature(fn)
        params = sig.parameters
        call_kwargs = dict(kwargs)
        if "alert_categories" in params and alert_categories is not None:
            call_kwargs["alert_categories"] = alert_categories
        # Drop kwargs the target function does not accept
        call_kwargs = {k: v for k, v in call_kwargs.items() if k in params}
        return fn(*args, **call_kwargs)
    except TypeError:
        try:
            return fn(*args, **kwargs)
        except TypeError:
            return fn(*args)


def inject_css() -> None:
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _icon_b64(name: str) -> str:
    """Load a pre-generated icon under assets/icons, falling back to the logo."""
    path = ICONS / name
    if path.exists():
        return media_b64(path)
    logo = resolve_logo_path()
    return media_b64(logo) if logo else ""


def inject_pwa_and_icons() -> None:
    """
    Inject favicon, Apple touch icon, theme-color, and a web app manifest so the
    app looks branded in the browser tab and when added to an Android/iPhone home screen.

    Note: Edge/Chrome "Create shortcut" still uses the *browser* icon. For a true
    steel I-beam desktop icon on Windows, use the installer under /desktop or the
    sidebar download (see render_desktop_install).
    """
    fav16 = _icon_b64("favicon-16.png")
    fav32 = _icon_b64("favicon-32.png")
    fav48 = _icon_b64("favicon-48.png")
    apple = _icon_b64("apple-touch-icon.png")
    i192 = _icon_b64("icon-192.png")
    i256 = _icon_b64("icon-256.png") or i192
    i512 = _icon_b64("icon-512.png")
    if not fav32:
        return

    # Prefer largest I-beam for primary icon so tab + install pick the beam, not logo
    primary = i192 or fav32

    manifest = {
        "name": "Ascent | US Steel Cost Forecast",
        "short_name": "Ascent Steel",
        "description": (
            "US Steel Cost 2-Year Forecast Dashboard for PEMB / MBMA leaders — "
            "Ascent Building Systems"
        ),
        "start_url": ".",
        "scope": ".",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#0B1C2C",
        "theme_color": "#0F2C44",
        "categories": ["business", "finance", "productivity"],
        "icons": [
            {
                "src": f"data:image/png;base64,{fav48 or fav32}",
                "sizes": "48x48",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": f"data:image/png;base64,{i192}",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": f"data:image/png;base64,{i512}",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": f"data:image/png;base64,{i192}",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": f"data:image/png;base64,{i512}",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    manifest_js = json.dumps(manifest)

    # Streamlit strips <script> from markdown — inject into parent document head.
    # Remove prior Streamlit default favicons so the I-beam wins.
    components.html(
        f"""
        <script>
        (function () {{
          const doc = window.parent.document;
          function removeOldIcons() {{
            doc.querySelectorAll(
              'link[rel="icon"], link[rel="shortcut icon"], link[rel="apple-touch-icon"], link[rel="apple-touch-icon-precomposed"]'
            ).forEach(function (el) {{
              el.parentNode && el.parentNode.removeChild(el);
            }});
          }}
          function addLink(rel, href, attrs) {{
            const el = doc.createElement('link');
            el.setAttribute('rel', rel);
            el.setAttribute('href', href);
            if (attrs) {{
              Object.keys(attrs).forEach(function (k) {{
                el.setAttribute(k, attrs[k]);
              }});
            }}
            doc.head.appendChild(el);
          }}
          function upsertMeta(name, content) {{
            let el = doc.querySelector('meta[name="' + name + '"]');
            if (!el) {{
              el = doc.createElement('meta');
              el.setAttribute('name', name);
              doc.head.appendChild(el);
            }}
            el.setAttribute('content', content);
          }}
          let vp = doc.querySelector('meta[name="viewport"]');
          if (!vp) {{
            vp = doc.createElement('meta');
            vp.setAttribute('name', 'viewport');
            doc.head.appendChild(vp);
          }}
          vp.setAttribute(
            'content',
            'width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover'
          );

          removeOldIcons();

          if ('{fav16}') {{
            addLink('icon', 'data:image/png;base64,{fav16}', {{ type: 'image/png', sizes: '16x16' }});
          }}
          addLink('icon', 'data:image/png;base64,{fav32}', {{ type: 'image/png', sizes: '32x32' }});
          if ('{fav48}') {{
            addLink('icon', 'data:image/png;base64,{fav48}', {{ type: 'image/png', sizes: '48x48' }});
          }}
          addLink('icon', 'data:image/png;base64,{primary}', {{ type: 'image/png', sizes: '192x192' }});
          addLink('shortcut icon', 'data:image/png;base64,{fav32}', {{ type: 'image/png' }});
          addLink('apple-touch-icon', 'data:image/png;base64,{apple}', {{ sizes: '180x180' }});

          upsertMeta('theme-color', '#0F2C44');
          upsertMeta('msapplication-TileColor', '#0F2C44');
          if ('{i256}') {{
            upsertMeta('msapplication-TileImage', 'data:image/png;base64,{i256}');
          }}
          upsertMeta('apple-mobile-web-app-capable', 'yes');
          upsertMeta('apple-mobile-web-app-status-bar-style', 'black-translucent');
          upsertMeta('apple-mobile-web-app-title', 'Ascent Steel');
          upsertMeta('mobile-web-app-capable', 'yes');
          upsertMeta('application-name', 'Ascent Steel');

          const manifest = {manifest_js};
          const blob = new Blob([JSON.stringify(manifest)], {{ type: 'application/json' }});
          const url = URL.createObjectURL(blob);
          const oldMan = doc.querySelector('link[rel="manifest"]');
          if (oldMan) oldMan.parentNode.removeChild(oldMan);
          addLink('manifest', url);

          // Re-assert after Streamlit re-renders head (it often resets favicon)
          setTimeout(function () {{
            const hasBeam = Array.from(doc.querySelectorAll('link[rel="icon"]')).some(function (l) {{
              return (l.getAttribute('href') || '').indexOf('data:image/png') === 0;
            }});
            if (!hasBeam) {{
              removeOldIcons();
              addLink('icon', 'data:image/png;base64,{primary}', {{ type: 'image/png', sizes: '192x192' }});
              addLink('apple-touch-icon', 'data:image/png;base64,{apple}', {{ sizes: '180x180' }});
            }}
          }}, 800);
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def render_desktop_install() -> None:
    """Sidebar: download I-beam icon + Windows installer for a real desktop icon."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Install (I-beam icon)")
    st.sidebar.caption(
        "Edge **Create shortcut** always shows the Edge logo. "
        "Use these downloads for a steel I-beam icon on your desktop or phone."
    )

    ico_path = ICONS / "Ascent-Steel-Forecast.ico"
    if not ico_path.exists():
        ico_path = ICONS / "favicon.ico"
    png_path = ICONS / "icon-256.png"
    if not png_path.exists():
        png_path = ICONS / "icon-192.png"
    ps1_path = ROOT / "desktop" / "Install-Ascent-Steel-Desktop.ps1"
    bat_path = ROOT / "desktop" / "Install-Ascent-Steel-Desktop.bat"

    if ico_path.exists():
        st.sidebar.download_button(
            label="Download Windows icon (.ico)",
            data=ico_path.read_bytes(),
            file_name="Ascent-Steel-Forecast.ico",
            mime="image/x-icon",
            use_container_width=True,
            key="dl_ico",
        )
    if png_path.exists():
        st.sidebar.download_button(
            label="Download icon PNG (256px)",
            data=png_path.read_bytes(),
            file_name="Ascent-Steel-Forecast.png",
            mime="image/png",
            use_container_width=True,
            key="dl_png",
        )
    if bat_path.exists() and ps1_path.exists():
        # Zip the installer set for one-click desktop setup
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(bat_path, "Install-Ascent-Steel-Desktop.bat")
            zf.write(ps1_path, "Install-Ascent-Steel-Desktop.ps1")
            if ico_path.exists():
                zf.write(ico_path, "Ascent-Steel-Forecast.ico")
            readme = ROOT / "desktop" / "README.md"
            if readme.exists():
                zf.write(readme, "README.md")
        st.sidebar.download_button(
            label="Download desktop installer (zip)",
            data=buf.getvalue(),
            file_name="Ascent-Steel-Desktop-Installer.zip",
            mime="application/zip",
            use_container_width=True,
            key="dl_zip",
            type="primary",
        )
        st.sidebar.caption(
            "Windows: unzip → double-click **Install-Ascent-Steel-Desktop.bat**. "
            "Phone: open this site in Safari/Chrome → Share → **Add to Home Screen**."
        )
    else:
        st.sidebar.caption(
            "Phone: Share → **Add to Home Screen**. "
            "Windows: download the .ico → shortcut Properties → Change Icon."
        )


def is_mobile_layout() -> bool:
    """
    Detect phone / narrow layouts for stacking columns and compact charts.
    Priority: query param vp=m|d → session (JS) → User-Agent.
    """
    try:
        vp = st.query_params.get("vp", "")
        if isinstance(vp, list):
            vp = vp[0] if vp else ""
        vp = str(vp).lower()
        if vp in ("m", "mobile", "1"):
            st.session_state.is_mobile = True
            return True
        if vp in ("d", "desktop", "0"):
            st.session_state.is_mobile = False
            return False
    except Exception:
        pass

    if "is_mobile" in st.session_state and st.session_state.is_mobile is not None:
        return bool(st.session_state.is_mobile)

    ua = ""
    try:
        headers = getattr(st, "context", None)
        if headers is not None:
            h = headers.headers
            ua = (h.get("User-Agent") or h.get("user-agent") or "").lower()
    except Exception:
        ua = ""

    mobile = any(
        token in ua
        for token in (
            "iphone",
            "ipod",
            "ipad",
            "android",
            "mobile",
            "webos",
            "blackberry",
            "windows phone",
            "opera mini",
            "iemobile",
        )
    )
    st.session_state.is_mobile = mobile
    return mobile


def inject_viewport_sync() -> None:
    """
    Mark document with viewport mode for CSS, and one-time query-param sync for
    narrow desktop windows (phones already detected via User-Agent).
    Avoids reload loops / replaying the intro splash.
    """
    components.html(
        """
        <script>
        (function () {
          try {
            const win = window.parent;
            const doc = win.document;
            const w = win.innerWidth || doc.documentElement.clientWidth || 1200;
            const mode = w <= 768 ? 'm' : 'd';
            const label = mode === 'm' ? 'mobile' : 'desktop';
            doc.documentElement.setAttribute('data-ascent-vp', label);
            if (doc.body) doc.body.setAttribute('data-ascent-vp', label);

            const url = new URL(win.location.href);
            const cur = url.searchParams.get('vp');
            const key = 'ascent_vp_synced';
            // One soft navigation max per tab session when width disagrees with ?vp=
            if (cur !== mode && win.sessionStorage.getItem(key) !== mode) {
              win.sessionStorage.setItem(key, mode);
              url.searchParams.set('vp', mode);
              win.history.replaceState({}, '', url.toString());
              // Nudge Streamlit to re-read query params without full reload when possible
              try {
                win.dispatchEvent(new PopStateEvent('popstate'));
              } catch (e2) {}
            }
          } catch (e) { /* ignore */ }
        })();
        </script>
        """,
        height=0,
        width=0,
    )


def chart_heights() -> dict:
    return CHART_H["mobile"] if is_mobile_layout() else CHART_H["desktop"]


def _safe_key(*parts: object) -> str:
    """Build a stable Streamlit widget key from parts (alphanumeric + underscore)."""
    raw = "_".join(str(p) for p in parts if p is not None and str(p) != "")
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw).strip("_")
    return (cleaned or "chart")[:120]


def show_chart(
    fig,
    *,
    key: str,
    height: int | None = None,
    compact: bool | None = None,
) -> None:
    """
    Render a Plotly figure full-width with a unique key= (required).
    On mobile: external readable title (never clipped), compact polish, shorter height.
    """
    if not key:
        raise ValueError("show_chart requires a unique non-empty key= to avoid StreamlitDuplicateElementId")

    mobile = is_mobile_layout() if compact is None else compact
    heights = chart_heights()
    if height is None:
        height = heights["main"]

    # Pull title out of the figure on phones so it never gets cut off by SVG bounds
    raw_title = None
    try:
        raw_title = fig.layout.title.text if fig.layout.title else None
    except Exception:
        raw_title = None

    if mobile and raw_title:
        clean = re.sub(r"<[^>]+>", " ", str(raw_title))
        clean = " ".join(clean.replace("—", "–").split())
        st.markdown(
            f'<div class="chart-title-ext">{clean}</div>',
            unsafe_allow_html=True,
        )
        fig.update_layout(title=dict(text=""))
        fig = apply_compact_polish(fig, height=height)
        # Generous margins: legend below, no clipped axis labels
        fig.update_layout(
            margin=dict(l=48, r=14, t=16, b=110),
            height=height,
            autosize=True,
        )
    else:
        if height is not None:
            fig.update_layout(height=height, autosize=True)
        # Desktop: keep titles inside but with room so they do not clip
        fig.update_layout(
            margin=dict(l=56, r=20, t=78, b=52),
            title=dict(pad=dict(t=4, b=8)),
        )

    config = dict(PLOTLY_CONFIG)
    if mobile:
        # Minimal mode bar on phones — more plot area
        config = {
            **config,
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": [
                "lasso2d",
                "select2d",
                "autoScale2d",
                "zoomIn2d",
                "zoomOut2d",
                "pan2d",
            ],
        }

    st.plotly_chart(
        fig,
        use_container_width=True,
        config=config,
        key=key,
    )


def apply_theme(theme: str) -> None:
    """
    Instant full-app Dark/Light switch via CSS overrides.
    Streamlit config.toml is static; this repaints the shell + widgets on every rerun.
    """
    if theme == "light":
        css = """
        <style>
        /* ===== LIGHT THEME ===== */
        .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlockContainer"],
        section.main, .main {
          background-color: #F4F7FA !important;
          color: #1A1A2E !important;
        }
        [data-testid="stHeader"] {
          background: rgba(244, 247, 250, 0.92) !important;
        }
        [data-testid="stToolbar"] {
          background: transparent !important;
        }
        section[data-testid="stSidebar"] {
          background-color: #FFFFFF !important;
          border-right: 1px solid #D5DEE8 !important;
        }
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
          color: #1A1A2E !important;
        }
        section[data-testid="stSidebar"] [data-baseweb="select"] > div,
        section[data-testid="stSidebar"] [data-baseweb="input"] {
          background-color: #F4F7FA !important;
          color: #1A1A2E !important;
        }
        .block-container { color: #1A1A2E !important; }
        h1, h2, h3, h4, h5, h6, p, label, span, li, .stMarkdown, .stCaption {
          color: #1A1A2E !important;
        }
        .stCaption, [data-testid="stCaptionContainer"] {
          color: #5D6D7E !important;
        }
        div[data-testid="stMetric"] {
          background: #FFFFFF !important;
          border: 1px solid #D0DCE8 !important;
          color: #1A1A2E !important;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
          color: #5D6D7E !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
          color: #1B4F72 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
          color: #2E86AB !important;
        }
        .section-label { color: #5D6D7E !important; opacity: 1 !important; }
        .ascent-footer {
          color: #5D6D7E !important;
          border-top-color: #D5DEE8 !important;
        }
        div[data-testid="stDataFrame"],
        div[data-testid="stDataFrame"] * {
          color: #1A1A2E !important;
        }
        div[data-baseweb="tab-list"] button,
        button[data-baseweb="tab"] {
          color: #1A1A2E !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
          color: #1B4F72 !important;
        }
        .stRadio label, .stSelectbox label, .stSlider label {
          color: #1A1A2E !important;
        }
        [data-testid="stSlider"] [data-baseweb="slider"] div {
          color: #1A1A2E !important;
        }
        .stAlert, [data-testid="stAlert"] {
          color: #1A1A2E !important;
        }
        .category-alert-tag {
          background: rgba(192, 57, 43, 0.10) !important;
          border: 1px solid #C0392B !important;
          color: #922B21 !important;
        }
        .sidebar-alert {
          background: rgba(192, 57, 43, 0.10) !important;
          border: 1px solid #C0392B !important;
          color: #922B21 !important;
        }
        .sidebar-update-zone {
          background: linear-gradient(135deg, rgba(46, 134, 171, 0.14), rgba(27, 79, 114, 0.06)) !important;
          border: 1px solid #2E86AB !important;
          border-left: 4px solid #1B4F72 !important;
        }
        .sidebar-update-title {
          color: #1B4F72 !important;
        }
        .sidebar-update-hint {
          color: #5D6D7E !important;
        }
        .chart-title-ext {
          color: #1A1A2E !important;
        }
        .mobile-nav-tip {
          background: rgba(46, 134, 171, 0.10) !important;
          border-color: #2E86AB !important;
          color: #1A1A2E !important;
        }
        .sidebar-scroll-hint {
          color: #1A1A2E !important;
        }
        /* Keep alert banner high-contrast red */
        .alert-banner, .alert-banner * {
          color: #FFFFFF !important;
        }
        /* Hero stays branded dark-blue */
        .ascent-hero, .ascent-hero h1, .ascent-hero .subtitle,
        .ascent-hero .ascent-badge, .ascent-hero .ascent-mono,
        .ascent-hero .ascent-date {
          color: #F5F8FB !important;
        }
        .ascent-hero .subtitle { color: #D6E6F2 !important; }
        hr { border-color: #D5DEE8 !important; }
        [data-testid="stExpander"] {
          background: #FFFFFF !important;
          border-color: #D5DEE8 !important;
        }
        /* Widgets */
        .stButton > button {
          border-color: #B8C9D9 !important;
        }
        .stDownloadButton > button {
          color: inherit;
        }
        </style>
        """
    else:
        css = """
        <style>
        /* ===== DARK THEME ===== */
        .stApp, [data-testid="stAppViewContainer"],
        [data-testid="stAppViewBlockContainer"],
        section.main, .main {
          background-color: #0E1621 !important;
          color: #E8EEF4 !important;
        }
        [data-testid="stHeader"] {
          background: rgba(14, 22, 33, 0.92) !important;
        }
        section[data-testid="stSidebar"] {
          background-color: #162231 !important;
          border-right: 1px solid rgba(255,255,255,0.08) !important;
        }
        section[data-testid="stSidebar"] *,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span {
          color: #E8EEF4 !important;
        }
        .block-container { color: #E8EEF4 !important; }
        h1, h2, h3, h4, h5, h6, p, label, span, li, .stMarkdown {
          color: #E8EEF4 !important;
        }
        .stCaption, [data-testid="stCaptionContainer"] {
          color: #A8B6C5 !important;
        }
        div[data-testid="stMetric"] {
          background: rgba(46,134,171,0.10) !important;
          border: 1px solid rgba(46,134,171,0.28) !important;
          color: #E8EEF4 !important;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
          color: #A8B6C5 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
          color: #5DADE2 !important;
        }
        .section-label { color: #A8B6C5 !important; opacity: 1 !important; }
        .ascent-footer {
          color: #A8B6C5 !important;
          border-top-color: rgba(255,255,255,0.12) !important;
        }
        div[data-baseweb="tab-list"] button,
        button[data-baseweb="tab"] {
          color: #E8EEF4 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
          color: #5DADE2 !important;
        }
        .category-alert-tag {
          background: rgba(192, 57, 43, 0.18) !important;
          border: 1px solid #C0392B !important;
          color: #FFCDD2 !important;
        }
        .sidebar-alert {
          background: rgba(192, 57, 43, 0.2) !important;
          border: 1px solid #C0392B !important;
          color: #FFCDD2 !important;
        }
        .sidebar-update-zone {
          background: linear-gradient(135deg, rgba(46, 134, 171, 0.28), rgba(27, 79, 114, 0.16)) !important;
          border: 1px solid rgba(93, 173, 226, 0.55) !important;
          border-left: 4px solid #5DADE2 !important;
        }
        .sidebar-update-title {
          color: #5DADE2 !important;
        }
        .sidebar-update-hint {
          color: #A8B6C5 !important;
        }
        .chart-title-ext {
          color: #E8EEF4 !important;
        }
        .mobile-nav-tip {
          background: rgba(46, 134, 171, 0.18) !important;
          border-color: rgba(93, 173, 226, 0.45) !important;
          color: #E8EEF4 !important;
        }
        .sidebar-scroll-hint {
          color: #E8EEF4 !important;
        }
        .alert-banner, .alert-banner * {
          color: #FFFFFF !important;
        }
        .ascent-hero, .ascent-hero h1, .ascent-hero .subtitle,
        .ascent-hero .ascent-badge, .ascent-hero .ascent-mono,
        .ascent-hero .ascent-date {
          color: #F5F8FB !important;
        }
        .ascent-hero .subtitle { color: #D6E6F2 !important; }
        hr { border-color: rgba(255,255,255,0.12) !important; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


def init_state() -> None:
    if "base_df" not in st.session_state:
        st.session_state.base_df = load_sample_data()
        st.session_state.model_source = "Pre-loaded sample (5-1-2026 pattern, ±0.4–0.5% MoM)"
    if "forecast_df" not in st.session_state:
        st.session_state.forecast_df = regenerate_forecast(
            st.session_state.base_df, BASELINE
        )
    if "risks" not in st.session_state:
        st.session_state.risks = BASELINE
    if "applied" not in st.session_state:
        st.session_state.applied = True
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "dark"
    if "splash_done" not in st.session_state:
        st.session_state.splash_done = False
    if "show_file_update" not in st.session_state:
        st.session_state.show_file_update = False
    if "last_upload_id" not in st.session_state:
        st.session_state.last_upload_id = None
    if "update_flash" not in st.session_state:
        st.session_state.update_flash = None


def play_intro_splash() -> None:
    """Play the 6s logo-spin intro once per session, then fade out into the dashboard."""
    if st.session_state.get("splash_done"):
        return

    video_path = resolve_video_path()
    logo_path = resolve_logo_path()
    logo_b64 = media_b64(logo_path) if logo_path else ""

    # Full-screen splash chrome + CSS fade (Streamlit strips <script> tags)
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"], header[data-testid="stHeader"],
          [data-testid="stToolbar"], footer, #MainMenu {
            visibility: hidden !important;
          }
          .block-container {
            padding-top: 2.5rem !important;
            max-width: 920px !important;
          }
          section.main {
            background: radial-gradient(ellipse at center, #12263a 0%, #070c12 70%) !important;
          }
          section.main div[data-testid="stVideo"] {
            animation: splashFadeOut 0.9s ease-in 5.2s forwards;
          }
          section.main div[data-testid="stVideo"] video {
            border-radius: 14px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.45);
            max-height: 72vh;
          }
          @keyframes splashFadeOut {
            from { opacity: 1; }
            to { opacity: 0; visibility: hidden; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_html = (
        f'<img class="splash-logo" src="data:image/png;base64,{logo_b64}" alt="Ascent" />'
        if logo_b64
        else ""
    )
    st.markdown(
        f"""
        <div class="splash-header-bar">
          {logo_html}
          <div class="splash-caption">US Steel Cost 2-Year Forecast</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if video_path and video_path.exists():
        try:
            st.video(
                str(video_path),
                format="video/mp4",
                start_time=0,
                autoplay=True,
                muted=True,
            )
        except TypeError:
            st.video(str(video_path))
    else:
        st.markdown(
            '<div class="splash-fallback">Ascent Building Systems</div>',
            unsafe_allow_html=True,
        )

    # Hold ~6s so the intro plays fully, then fade is complete and we enter the app
    time.sleep(6.2)
    st.session_state.splash_done = True
    st.rerun()


def detect_significant_moves(
    df: pd.DataFrame, threshold: float = ALERT_THRESHOLD
) -> pd.DataFrame:
    """
    Scan all categories. Flag any where at least one month has
    |Adjusted - Base| / Base >= threshold (default 3%).
    """
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "Category",
                "Max_Abs_Pct",
                "Direction",
                "Months_Flagged",
                "Peak_Month",
            ]
        )
    if "Adjusted_Price_per_Ton" not in df.columns or "Base_Price_per_Ton" not in df.columns:
        return pd.DataFrame(
            columns=[
                "Category",
                "Max_Abs_Pct",
                "Direction",
                "Months_Flagged",
                "Peak_Month",
            ]
        )

    work = df.copy()
    work = work[work["Base_Price_per_Ton"] > 0]
    work["Delta_Pct"] = (
        (work["Adjusted_Price_per_Ton"] - work["Base_Price_per_Ton"])
        / work["Base_Price_per_Ton"]
    ) * 100.0
    work["Abs_Delta_Pct"] = work["Delta_Pct"].abs()

    rows = []
    for cat, sub in work.groupby("Category", sort=False):
        flagged = sub[sub["Abs_Delta_Pct"] >= threshold * 100.0]
        if flagged.empty:
            continue
        peak = flagged.loc[flagged["Abs_Delta_Pct"].idxmax()]
        direction = "higher" if peak["Delta_Pct"] >= 0 else "lower"
        rows.append(
            {
                "Category": cat,
                "Max_Abs_Pct": float(peak["Abs_Delta_Pct"]),
                "Direction": direction,
                "Months_Flagged": int(len(flagged)),
                "Peak_Month": str(peak.get("Month", "")),
                "Peak_Delta_Pct": float(peak["Delta_Pct"]),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "Category",
                "Max_Abs_Pct",
                "Direction",
                "Months_Flagged",
                "Peak_Month",
                "Peak_Delta_Pct",
            ]
        )

    out = pd.DataFrame(rows)
    # Preserve executive category order
    order = {c: i for i, c in enumerate(CATEGORIES)}
    out["_ord"] = out["Category"].map(lambda c: order.get(c, 99))
    out = out.sort_values(["_ord", "Max_Abs_Pct"], ascending=[True, False]).drop(
        columns="_ord"
    )
    return out.reset_index(drop=True)


def render_alert_banner(alert_df: pd.DataFrame) -> list[str]:
    """Prominent red banner when ≥3% Base vs Adjusted moves exist."""
    if alert_df is None or alert_df.empty:
        return []

    flagged = alert_df["Category"].tolist()
    n = len(flagged)
    chips = "".join(
        f'<span class="alert-chip">⚠ {row.Category} '
        f'({row.Peak_Delta_Pct:+.1f}% peak)</span>'
        for row in alert_df.itertuples()
    )
    st.markdown(
        f"""
        <div class="alert-banner" role="alert">
          <div class="alert-banner-title">
            ⚠️ ALERT: Significant 3%+ movement detected
          </div>
          <div class="alert-banner-sub">
            {n} categor{"y has" if n == 1 else "ies have"} at least one month where the
            risk-adjusted forecast is ≥3% higher or lower than base.
          </div>
          <div class="alert-chip-row">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return flagged


def hero(source: str) -> None:
    logo_path = resolve_logo_path()
    logo_b64 = media_b64(logo_path) if logo_path else ""
    logo_img = (
        f'<img class="ascent-logo" src="data:image/png;base64,{logo_b64}" '
        f'alt="Ascent Building Systems" />'
        if logo_b64
        else '<div class="ascent-logo-fallback">ABS</div>'
    )
    st.markdown(
        f"""
        <div class="ascent-hero">
          <div class="ascent-hero-row">
            <div class="ascent-hero-left">
              {logo_img}
              <div class="ascent-hero-text">
                <div class="ascent-badge">ASCENT BUILDING SYSTEMS</div>
                <h1>US Steel Cost 2-Year Forecast Dashboard</h1>
                <p class="subtitle">
                  Executive decision support for PEMB / MBMA leaders — Base vs Risk-Adjusted 24-month paths
                </p>
                <div class="meta">
                  <span class="ascent-badge">Bayesian/Gaussian/LSTM + Custom Code variance for maximum prediction modeling</span>
                  <span class="ascent-badge">Tariffs · Dumping · Geo Risk · Volatility</span>
                  <span class="ascent-badge">{source}</span>
                </div>
              </div>
            </div>
            <div class="ascent-hero-right">
              <div class="ascent-mono">Steel Cost Intelligence</div>
              <div class="ascent-date">{datetime.now().strftime("%b %d, %Y")}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _risk_sliders() -> RiskFactors:
    """Shared risk factor sliders (used in open or expandable sidebar sections)."""
    tariff = st.slider(
        "Tariff Change (%)",
        min_value=-20.0,
        max_value=40.0,
        value=float(st.session_state.risks.tariff_change_pct),
        step=0.5,
        help="Incremental tariff impact vs model baseline (pass-through ~38%).",
    )
    dumping = st.slider(
        "China Dumping Risk (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(st.session_state.risks.china_dumping_risk_pct),
        step=1.0,
        help="Higher dumping pressure can soften spot prices while adding risk premium.",
    )
    geo = st.slider(
        "Geo Risk Premium (%)",
        min_value=8.0,
        max_value=11.0,
        value=float(st.session_state.risks.geo_risk_premium_pct),
        step=0.1,
        help="Aligned with model GeoRiskPremium band (8–11%).",
    )
    vol = st.slider(
        "Social/Demand Volatility (%)",
        min_value=0.0,
        max_value=50.0,
        value=float(st.session_state.risks.social_demand_vol_pct),
        step=1.0,
        help="Civil/demand volatility premium + seasonal oscillation.",
    )
    return RiskFactors(
        tariff_change_pct=tariff,
        china_dumping_risk_pct=dumping,
        geo_risk_premium_pct=geo,
        social_demand_vol_pct=vol,
    )


def sidebar_controls(alert_categories: list[str] | None = None) -> tuple[str, RiskFactors, bool, str]:
    alert_categories = alert_categories or []
    mobile = is_mobile_layout()

    with st.sidebar:
        # Scrollable drawer chrome (CSS also enforces overflow)
        st.markdown(
            '<div class="sidebar-scroll-hint">Scroll for all controls · Close ☰ when done</div>'
            if mobile
            else "",
            unsafe_allow_html=True,
        )

        logo_path = resolve_logo_path()
        if logo_path:
            st.image(str(logo_path), width=120 if mobile else 140)
        st.markdown("### Ascent Controls")
        st.caption(
            "Tap ☰ (top-left) to open/close on phones"
            if mobile
            else "PEMB / MBMA steel cost intelligence"
        )

        theme = st.radio(
            "Theme",
            options=["dark", "light"],
            format_func=lambda x: "Dark" if x == "dark" else "Light",
            horizontal=True,
            key="theme_mode",
            help="Instantly switch the full dashboard between Dark and Light.",
        )

        st.divider()
        st.markdown("#### Category")
        present = available_categories(st.session_state.forecast_df)
        options = [c for c in CATEGORIES if c in present] or list(CATEGORIES)
        for c in CATEGORIES:
            if c not in options:
                options.append(c)

        def _label(cat: str) -> str:
            return f"⚠️ {cat}" if cat in alert_categories else cat

        category = st.selectbox(
            "Select material category",
            options=options,
            index=0,
            format_func=_label,
            help="Exact PEMB/MBMA categories from refined forecasting models. "
            "⚠️ marks ≥3% Base vs Adjusted movement.",
        )

        if alert_categories:
            st.markdown(
                f'<div class="sidebar-alert">🚨 {len(alert_categories)} categor'
                f'{"y" if len(alert_categories) == 1 else "ies"} above 3% threshold</div>',
                unsafe_allow_html=True,
            )

        # —— Update base forecast (Excel upload) —— always visible / not buried
        st.divider()
        st.markdown(
            '<div class="sidebar-update-zone">'
            '<div class="sidebar-update-title">📦 Base forecast data</div>'
            '<div class="sidebar-update-hint">Upload a new Excel model to refresh prices</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            "Update",
            type="primary",
            use_container_width=True,
            key="sidebar_update_btn",
            help="Upload a new forecasting Excel workbook and refresh the base forecast data.",
        ):
            st.session_state.show_file_update = not st.session_state.show_file_update
            if st.session_state.show_file_update:
                st.session_state.last_upload_id = None

        if st.session_state.show_file_update:
            uploaded = st.file_uploader(
                "Choose Excel forecast file",
                type=["xlsx", "xls"],
                key="base_forecast_uploader",
                help="December 2025, 5-1-2026, or 2-11-2026 style Month | Price | MoM workbooks.",
            )
            if uploaded is not None:
                file_id = f"{uploaded.name}:{uploaded.size}"
                if st.session_state.last_upload_id != file_id:
                    try:
                        with st.spinner(f"Loading {uploaded.name}…"):
                            new_base = parse_excel_model(
                                uploaded, source_name=uploaded.name
                            )
                            risks_now = st.session_state.get("risks", BASELINE)
                            st.session_state.base_df = new_base
                            st.session_state.forecast_df = regenerate_forecast(
                                new_base, risks_now
                            )
                            st.session_state.model_source = f"Uploaded: {uploaded.name}"
                            st.session_state.last_upload_id = file_id
                            st.session_state.show_file_update = False
                            st.session_state.applied = True
                            n_cats = int(new_base["Category"].nunique())
                            st.session_state.update_flash = (
                                f"Base forecast refreshed from **{uploaded.name}** "
                                f"({len(new_base):,} rows · {n_cats} categories)."
                            )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not load workbook: {exc}")
            st.caption("Supported: .xlsx / .xls with Month | Price | MoM category blocks.")

        if st.session_state.update_flash:
            st.success(st.session_state.update_flash)
            st.session_state.update_flash = None

        # Risk factors — collapsible on mobile so the drawer stays scrollable/usable
        st.divider()
        if mobile:
            with st.expander("🎚 Risk Factors", expanded=True):
                st.caption(
                    "Sliders update the forecast and 3% alarm live. Apply locks the scenario."
                )
                risks = _risk_sliders()
        else:
            st.markdown("#### Risk Factors")
            st.caption(
                "Sliders update the forecast and 3% movement alarm in real time. "
                "Use Apply to lock the current scenario."
            )
            risks = _risk_sliders()

        # Live regenerate whenever sliders move (real-time alarm + charts)
        live_df = regenerate_forecast(st.session_state.base_df, risks)
        st.session_state.forecast_df = live_df

        apply_clicked = st.button(
            "⚡ Apply adjustments & regenerate forecast",
            type="primary",
            use_container_width=True,
            key="sidebar_apply_risks_btn",
        )
        if apply_clicked:
            st.session_state.risks = risks
            st.session_state.forecast_df = live_df
            st.session_state.applied = True
            st.success("Forecast regenerated with hybrid risk path.")

        if st.button(
            "Restore baseline risks",
            use_container_width=True,
            key="sidebar_restore_baseline_btn",
        ):
            st.session_state.risks = BASELINE
            st.session_state.forecast_df = regenerate_forecast(
                st.session_state.base_df, BASELINE
            )
            st.session_state.applied = True
            st.rerun()

        st.divider()
        if mobile:
            with st.expander("Methodology", expanded=False):
                st.caption(
                    "Bayesian/Gaussian/LSTM + Custom Code variance for maximum prediction modeling. "
                    "Seasonal MoM (±0.4–0.5%), tariff pass-through, China dumping, geo premium, "
                    "and demand volatility. Mill published overvaluations (Nucor/USS/SDI direct) "
                    "removed per model notes."
                )
        else:
            st.markdown("#### Methodology")
            st.caption(
                "Bayesian/Gaussian/LSTM + Custom Code variance for maximum prediction modeling. "
                "Seasonal MoM (±0.4–0.5%), tariff pass-through, China dumping, geo premium, and demand volatility. "
                "Mill published overvaluations (Nucor/USS/SDI direct) removed per model notes."
            )

    return category, risks, apply_clicked, theme


def kpi_row(df: pd.DataFrame, category: str) -> None:
    metrics = summary_metrics(df, category)
    if not metrics:
        st.warning(
            f"No data for category **{category}**. Upload a model or choose another category."
        )
        return

    start_b, end_b = metrics["start_price"], metrics["end_price"]
    start_a, end_a = metrics["start_adj"], metrics["end_adj"]
    chg_b = ((end_b / start_b) - 1) * 100 if start_b else 0
    chg_a = ((end_a / start_a) - 1) * 100 if start_a else 0
    spread = metrics["avg_adj"] - metrics["avg_price"]

    items = [
        ("Base start", f"${start_b:,.0f}", None, "$/ton first month"),
        ("Base end (24-mo)", f"${end_b:,.0f}", f"{chg_b:+.1f}% path", None),
        ("Adj end (24-mo)", f"${end_a:,.0f}", f"{chg_a:+.1f}% path", None),
        (
            "Avg risk uplift",
            f"${spread:+,.1f}",
            f"{(spread / metrics['avg_price'] * 100):+.2f}%",
            None,
        ),
        (
            "Avg geo risk",
            f"{metrics['avg_geo']:.1f}%",
            f"{metrics['n_months']} months",
            None,
        ),
    ]

    if is_mobile_layout():
        # Full-width stack — no multi-column crush on Android/iPhone
        for label, value, delta, help_txt in items:
            kwargs = {}
            if help_txt:
                kwargs["help"] = help_txt
            if delta is not None:
                st.metric(label, value, delta, **kwargs)
            else:
                st.metric(label, value, **kwargs)
    else:
        slots = list(st.columns(5))
        for slot, (label, value, delta, help_txt) in zip(slots, items):
            kwargs = {}
            if help_txt:
                kwargs["help"] = help_txt
            if delta is not None:
                slot.metric(label, value, delta, **kwargs)
            else:
                slot.metric(label, value, **kwargs)


def _style_forecast_table(show: pd.DataFrame, alert_categories: list[str]):
    """Highlight rows ≥3% move; entire category tables when category is flagged."""
    fmt = {
        "Base_Price_per_Ton": "${:,.0f}",
        "Adjusted_Price_per_Ton": "${:,.0f}",
        "MoM_Pct": "{:.2f}%",
        "Adj_MoM_Pct": "{:.2f}%",
        "Risk_Uplift_Pct": "{:.2f}%",
        "GeoRiskPremium_Pct": "{:.1f}%",
        "Adjustment_Factor": "{:.4f}",
    }

    def _row_style(row):
        styles = [""] * len(row)
        if "Risk_Uplift_Pct" in row.index:
            try:
                if abs(float(row["Risk_Uplift_Pct"])) >= ALERT_THRESHOLD * 100:
                    styles = [
                        "background-color: rgba(192,57,43,0.22); color: #FFCDD2; font-weight: 600;"
                    ] * len(row)
            except (TypeError, ValueError):
                pass
        elif "Category" in row.index and row["Category"] in alert_categories:
            styles = ["background-color: rgba(192,57,43,0.18);"] * len(row)
        return styles

    styler = show.style.format(fmt, na_rep="—")
    if not show.empty:
        styler = styler.apply(_row_style, axis=1)
    return styler


def tab_overview(
    df: pd.DataFrame, category: str, theme: str, alert_categories: list[str]
) -> None:
    mobile = is_mobile_layout()
    compact = mobile
    h = chart_heights()
    cat_k = _safe_key(category)

    st.markdown('<div class="section-label">Dashboard Overview</div>', unsafe_allow_html=True)
    if category in alert_categories:
        st.markdown(
            f'<div class="category-alert-tag">⚠️ {category} — significant Base vs Adjusted movement</div>',
            unsafe_allow_html=True,
        )
    kpi_row(df, category)

    line_fig = (
        base_vs_adjusted_line(df, category, theme=theme, compact=compact)
        if category in df["Category"].values
        else None
    )
    bar_fig = _chart_with_alerts(
        category_comparison_bar,
        df,
        theme=theme,
        alert_categories=alert_categories,
        compact=compact,
    )
    multi_fig = _chart_with_alerts(
        multi_category_lines,
        df,
        "Adjusted_Price_per_Ton",
        theme=theme,
        alert_categories=alert_categories,
        compact=compact,
    )

    # Always stack on mobile; optional 2-col on desktop only
    if line_fig is not None:
        show_chart(
            line_fig,
            key=_safe_key("overview_base_adj", cat_k),
            height=h["main"],
            compact=compact,
        )
    else:
        st.info("Category not in current dataset.")

    n_cats = max(int(df["Category"].nunique()), 4)
    bar_h = max(h["side"], 28 * n_cats + 100) if mobile else h["side"]
    show_chart(
        bar_fig,
        key=_safe_key("overview_cat_bar", cat_k),
        height=bar_h,
        compact=compact,
    )

    show_chart(
        multi_fig,
        key=_safe_key("overview_multi_cat", cat_k),
        height=h["wide"] + (40 if mobile else 0),
        compact=compact,
    )

    st.markdown("##### Forecast data table — Base vs Adjusted")
    show = forecast_table_for_export(
        df, category if category in df["Category"].values else "Overall"
    )
    st.dataframe(
        _style_forecast_table(show, alert_categories),
        use_container_width=True,
        height=h["table"],
        key=_safe_key("overview_forecast_table", cat_k),
    )


def tab_deep_dive(
    df: pd.DataFrame, category: str, theme: str, alert_categories: list[str]
) -> None:
    mobile = is_mobile_layout()
    compact = mobile
    h = chart_heights()
    cat_k = _safe_key(category)

    st.markdown('<div class="section-label">Category Deep Dive</div>', unsafe_allow_html=True)
    if category not in df["Category"].values:
        st.warning(f"**{category}** is not present in the loaded model.")
        st.caption("TNFAB / TNFAB2nd appear in the 5-1-2026 model (TNFAB2nd may be derived).")
        return

    if category in alert_categories:
        st.markdown(
            f'<div class="category-alert-tag">⚠️ ALERT — {category} exceeds ±3% Base vs Adjusted</div>',
            unsafe_allow_html=True,
        )

    sub = filter_category(df, category)
    m = summary_metrics(df, category)

    # Metrics: single column on mobile (no jumbled multi-col grid)
    metric_items = [
        ("Min base $/ton", f"${m['min_price']:,.0f}"),
        ("Max base $/ton", f"${m['max_price']:,.0f}"),
        ("Avg MoM %", f"{m['avg_mom']:.2f}%"),
        ("Horizon", f"{m['n_months']} months"),
    ]
    if mobile:
        for label, value in metric_items:
            st.metric(label, value)
    else:
        cols = st.columns(4)
        for col, (label, value) in zip(cols, metric_items):
            col.metric(label, value)

    notes = {
        "Overall": "Blended PEMB material index — primary executive KPI.",
        "Hot Rolled Plates": "Primary structural plate; highly tariff- and dump-sensitive.",
        "HR I-Beams/Channels": "Hot-rolled sections; ~0.4% MoM amplitude in refined models.",
        "Sub Framing": "Cold-formed secondary (zees/cees) cost proxy.",
        "Sheet/Trim Painted": "Painted / finished sheet & trim (galvalume, silicone-poly, Kynar paths).",
        "HSS Round Pipes": "Hollow structural round — import/dump sensitivity elevated.",
        "HSS Square/Rect Tubes": "Square/rectangular HSS tubes for frames and secondary.",
        "TNFAB": "TNFAB plant / source path from 5-1-2026 model.",
        "TNFAB2nd": "Secondary TNFAB source path (premium vs primary when derived).",
    }

    # Charts always stacked vertically (mobile + desktop) — clean, no overlap
    show_chart(
        base_vs_adjusted_line(df, category, theme=theme, compact=compact),
        key=_safe_key("deep_base_adj", cat_k),
        height=h["main"],
        compact=compact,
    )
    show_chart(
        mom_bars(df, category, theme=theme, compact=compact),
        key=_safe_key("deep_mom", cat_k),
        height=h["small"],
        compact=compact,
    )
    show_chart(
        geo_risk_timeline(df, category, theme=theme, compact=compact),
        key=_safe_key("deep_geo", cat_k),
        height=h["main"],
        compact=compact,
    )
    st.markdown("##### Category notes")
    st.info(notes.get(category, "Material category forecast."))

    st.markdown("##### Month detail")
    cols = [
        "Month",
        "Base_Price_per_Ton",
        "Adjusted_Price_per_Ton",
        "MoM_Pct",
        "Adj_MoM_Pct",
        "GeoRiskPremium_Pct",
        "Risk_Uplift_Pct",
    ]
    cols = [c for c in cols if c in sub.columns]
    st.dataframe(
        _style_forecast_table(sub[cols], alert_categories),
        use_container_width=True,
        height=h["table"],
        key=_safe_key("deep_month_table", cat_k),
    )


def tab_sensitivity(df: pd.DataFrame, category: str, risks: RiskFactors, theme: str) -> None:
    mobile = is_mobile_layout()
    compact = mobile
    h = chart_heights()
    cat_k = _safe_key(category)

    st.markdown('<div class="section-label">Sensitivity Analysis</div>', unsafe_allow_html=True)
    st.caption(
        "One-way and tornado sensitivity around current risk settings. "
        "Uses the hybrid adjustment engine (tariff pass-through, dumping, geo, volatility)."
    )

    cat = category if category in df["Category"].values else "Overall"
    base = st.session_state.base_df

    tornado = tornado_impacts(base, cat, risks)
    factor_map = {
        "Tariff Change (%)": ("tariff_change_pct", list(range(-10, 31, 5))),
        "China Dumping Risk (%)": ("china_dumping_risk_pct", list(range(0, 101, 10))),
        "Geo Risk Premium (%)": (
            "geo_risk_premium_pct",
            [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0],
        ),
        "Social/Demand Volatility (%)": ("social_demand_vol_pct", list(range(0, 51, 5))),
    }

    show_chart(
        tornado_chart(tornado, theme=theme, compact=compact),
        key=_safe_key("sens_tornado", cat_k),
        height=h["side"] if mobile else h["main"],
        compact=compact,
    )
    st.dataframe(
        tornado[["Factor", "Low", "High", "Base", "Range"]].style.format(
            {"Low": "${:,.0f}", "High": "${:,.0f}", "Base": "${:,.0f}", "Range": "${:,.0f}"}
        ),
        use_container_width=True,
        key=_safe_key("sens_tornado_table", cat_k),
    )

    pick = st.selectbox(
        "Sensitivity factor",
        list(factor_map.keys()),
        key=_safe_key("sens_factor_pick", cat_k),
    )
    attr, values = factor_map[pick]
    sens = sensitivity_grid(base, cat, risks, attr, [float(v) for v in values])
    show_chart(
        sensitivity_line(sens, pick, theme=theme, compact=compact),
        key=_safe_key("sens_line", cat_k, pick),
        height=h["main"],
        compact=compact,
    )
    st.dataframe(
        sens.style.format(
            {
                "Factor_Value": "{:.1f}",
                "Avg_Adjusted_Price": "${:,.0f}",
                "End_Adjusted_Price": "${:,.0f}",
                "Avg_Uplift_Pct": "{:.2f}%",
            }
        ),
        use_container_width=True,
        key=_safe_key("sens_grid_table", cat_k),
    )

    st.markdown("##### Scenario presets")
    presets = {
        "Baseline": BASELINE,
        "Trade shock": RiskFactors(15.0, 40.0, 10.5, 20.0),
        "Dumping surge": RiskFactors(5.0, 75.0, 9.5, 15.0),
        "Calm markets": RiskFactors(-5.0, 10.0, 8.0, 5.0),
    }
    if mobile:
        # Stack presets 1-per-row on phones for easy taps
        for name, preset in presets.items():
            if st.button(
                name,
                use_container_width=True,
                key=_safe_key("preset_btn", name),
            ):
                st.session_state.risks = preset
                st.session_state.forecast_df = regenerate_forecast(base, preset)
                st.session_state.applied = True
                st.rerun()
            r = preset
            st.caption(
                f"T {r.tariff_change_pct:+.0f}% · D {r.china_dumping_risk_pct:.0f}% · "
                f"G {r.geo_risk_premium_pct:.1f}% · V {r.social_demand_vol_pct:.0f}%"
            )
    else:
        slots = list(st.columns(4))
        for col, (name, preset) in zip(slots, presets.items()):
            with col:
                if st.button(
                    name,
                    use_container_width=True,
                    key=_safe_key("preset_btn", name),
                ):
                    st.session_state.risks = preset
                    st.session_state.forecast_df = regenerate_forecast(base, preset)
                    st.session_state.applied = True
                    st.rerun()
                r = preset
                st.caption(
                    f"T {r.tariff_change_pct:+.0f}% · D {r.china_dumping_risk_pct:.0f}% · "
                    f"G {r.geo_risk_premium_pct:.1f}% · V {r.social_demand_vol_pct:.0f}%"
                )


def tab_export(df: pd.DataFrame, category: str, risks: RiskFactors, source: str) -> None:
    mobile = is_mobile_layout()
    h = chart_heights()

    st.markdown('<div class="section-label">Export Report</div>', unsafe_allow_html=True)
    st.write(
        "Download executive-ready workbooks and PDF summaries for leadership review. "
        "Exports reflect the **current** risk-adjusted forecast (live slider values)."
    )

    cat = category if category in df["Category"].values else "Overall"

    cat_k = _safe_key(cat)

    def _excel_block():
        st.markdown("##### Excel workbook")
        st.caption("Summary · Category · Full detail · Wide pivots")
        xlsx_bytes = build_excel_report(df, risks, cat, model_source=source)
        st.download_button(
            label="⬇️ Download Excel (.xlsx)",
            data=xlsx_bytes,
            file_name=f"Ascent_Steel_Forecast_{cat.replace('/', '-')}_{datetime.now():%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
            key=_safe_key("export_xlsx", cat_k),
        )

    def _pdf_block():
        st.markdown("##### PDF executive brief")
        st.caption("Risk settings + 24-month category table")
        pdf_bytes = build_pdf_report(df, risks, cat, model_source=source)
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name=f"Ascent_Steel_Forecast_{cat.replace('/', '-')}_{datetime.now():%Y%m%d}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=_safe_key("export_pdf", cat_k),
        )

    def _csv_block():
        st.markdown("##### CSV (category)")
        st.caption("Flat table for further analysis")
        csv = forecast_table_for_export(df, cat).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f"Ascent_Steel_Forecast_{cat.replace('/', '-')}_{datetime.now():%Y%m%d}.csv",
            mime="text/csv",
            use_container_width=True,
            key=_safe_key("export_csv", cat_k),
        )

    if mobile:
        _excel_block()
        _pdf_block()
        _csv_block()
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            _excel_block()
        with c2:
            _pdf_block()
        with c3:
            _csv_block()

    st.divider()
    st.markdown("##### Preview — export payload")
    st.dataframe(
        forecast_table_for_export(df, cat),
        use_container_width=True,
        height=h["table"],
        key=_safe_key("export_preview_table", cat_k),
    )


def main() -> None:
    init_state()
    inject_css()
    inject_pwa_and_icons()
    inject_viewport_sync()

    # Apply theme ASAP so the shell paints correctly (before/after sidebar toggle)
    current_theme = st.session_state.get("theme_mode", "dark")
    if current_theme not in ("dark", "light"):
        current_theme = "dark"
        st.session_state.theme_mode = "dark"
    apply_theme(current_theme)

    # Intro splash: once per browser session
    if not st.session_state.splash_done:
        play_intro_splash()
        return

    mobile = is_mobile_layout()

    # Pre-scan with last risks so sidebar can mark categories; then re-scan after live update
    pre_alerts = detect_significant_moves(st.session_state.forecast_df)
    pre_flagged = pre_alerts["Category"].tolist() if not pre_alerts.empty else []

    category, risks, _apply, theme = sidebar_controls(alert_categories=pre_flagged)

    # Re-apply after sidebar in case user just toggled Dark/Light this run
    if theme != current_theme:
        apply_theme(theme)

    # Sync committed risks to live slider values for export/sensitivity consistency
    st.session_state.risks = risks
    df = st.session_state.forecast_df

    # Real-time alarm at TOP of page (after load / any slider-driven regenerate)
    alert_df = detect_significant_moves(df)
    alert_categories = render_alert_banner(alert_df)

    # Logo header (always visible after splash)
    hero(st.session_state.model_source)

    if mobile:
        st.markdown(
            '<div class="mobile-nav-tip">'
            "☰ <strong>Menu</strong> (top-left) opens Category, <strong>Update</strong>, "
            "and Risk Factors — swipe/scroll the drawer, then close to view charts."
            "</div>",
            unsafe_allow_html=True,
        )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📊 Overview" if mobile else "📊 Dashboard Overview",
            "🔍 Deep Dive" if mobile else "🔍 Category Deep Dive",
            "📈 Sensitivity" if mobile else "📈 Sensitivity Analysis",
            "📤 Export" if mobile else "📤 Export Report",
        ]
    )
    with tab1:
        tab_overview(df, category, theme, alert_categories)
    with tab2:
        tab_deep_dive(df, category, theme, alert_categories)
    with tab3:
        tab_sensitivity(df, category, risks, theme)
    with tab4:
        tab_export(df, category, risks, st.session_state.model_source)

    st.markdown(
        """
        <div class="ascent-footer">
          Built by Chris Woodmore for Ascent Building Systems © 2026
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
