@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
chcp 65001 >nul
py -3 -m eddas_writ.runner --proposer credulous --out runs %*
if errorlevel 1 pause
