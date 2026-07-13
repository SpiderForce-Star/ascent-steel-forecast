@echo off
REM Ascent Building Systems — US Steel Cost 2-Year Forecast Dashboard
cd /d "%~dp0"
python -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo If streamlit is missing, run:  pip install -r requirements.txt
  pause
)
