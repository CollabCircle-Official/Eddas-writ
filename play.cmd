@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    python -m eddas_writ %*
) else (
    py -3 -m eddas_writ %*
)
if errorlevel 1 pause
