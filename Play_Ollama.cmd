@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
chcp 65001 >nul
set OLLAMA_HOST=http://localhost:11434
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=qwen3:4b
where py >nul 2>nul
if errorlevel 1 (python -m eddas_writ.adventure --menu --provider ollama --model %OLLAMA_MODEL% %*) else (py -3 -m eddas_writ.adventure --menu --provider ollama --model %OLLAMA_MODEL% %*)
if errorlevel 1 pause
