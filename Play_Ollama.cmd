@echo off
cd /d "%~dp0"
set OLLAMA_HOST=http://localhost:11434
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=qwen3:4b
py -3 -m eddas_writ --provider ollama %*
if errorlevel 1 pause
