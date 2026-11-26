@echo off
REM Real Thespis + Dungeons and Agents mirror. Folder layout: <parent>\Thespis, <parent>\Dungeons-and-Agents, <parent>\Eddas_Writ_v2
set "PYTHONPATH=%~dp0"
cd /d "%~dp0..\Thespis" || goto failed
uv run --extra serve --with pytest --with httpx --with-editable "..\Dungeons-and-Agents" python -m eddas_writ --backend frameworks %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo See README.md for the required folder layout and THESPIS_DIR / DND_AGENTS_DIR.
pause
exit /b 1
