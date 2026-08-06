# Install Ascent Steel Forecast (I-beam icon)

## Why you saw the Edge logo

Dragging a site to the desktop or using Edge **Create shortcut** makes a **browser** shortcut. Windows always stamps that with the **Edge** icon — your site’s favicon is ignored.

To get the **steel I-beam** icon you need either:

1. **Windows desktop installer** (below) — creates a real `.lnk` with our `.ico`, or  
2. **Phone: Add to Home Screen** — uses the I-beam from the app manifest.

## Windows — one-click desktop icon

1. Download this folder (or the release zip), **or** run from GitHub:
2. Double-click **`Install-Ascent-Steel-Desktop.bat`**
3. A shortcut appears on your Desktop: **Ascent US Steel Forecast** with the I-beam icon.
4. Double-click it anytime to open the live forecast.

App URL: https://ascent-steel-forecast-cnz5m3zmygunxam6xrnubz.streamlit.app/

## iPhone / iPad

1. Open the app link in **Safari** (not an in-app browser).
2. Tap **Share** → **Add to Home Screen**.
3. Name it **Ascent Steel** → **Add**.
4. The steel I-beam icon appears on your home screen.

## Android

1. Open the app link in **Chrome**.
2. Tap **⋮** menu → **Add to Home screen** / **Install app**.
3. Confirm — I-beam icon is added.

## Files

| File | Purpose |
|------|---------|
| `Ascent-Steel-Forecast.ico` | Windows multi-size I-beam icon |
| `Ascent-Steel-Forecast.png` | 256×256 PNG (manual shortcut icon) |
| `Install-Ascent-Steel-Desktop.bat` | Double-click installer |
| `Install-Ascent-Steel-Desktop.ps1` | PowerShell that builds the shortcut |
| `icon-192.png` / `icon-512.png` | PWA / Android |
| `apple-touch-icon.png` | iOS home screen |

## Manual shortcut (if script is blocked)

1. Right-click Desktop → **New → Shortcut** → paste the app URL → name it.
2. Right-click the new shortcut → **Properties** → **Change Icon**.
3. Browse to `Ascent-Steel-Forecast.ico` → OK → Apply.
