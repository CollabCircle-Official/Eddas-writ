@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
chcp 65001 >nul
where py >nul 2>nul
if errorlevel 1 (python -m eddas_writ.adventure --menu %*) else (py -3 -m eddas_writ.adventure --menu %*)
if errorlevel 1 pause
