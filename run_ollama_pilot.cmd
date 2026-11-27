@echo off
set OLLAMA_MODEL=qwen3:4b
set OLLAMA_HOST=http://localhost:11434
set OLLAMA_SEED=0
python -m eddas_writ.runner --proposer ollama --scenarios A1_basic --conditions N0 N1 B3b D C_control --out runs
if errorlevel 1 (
  echo.
  echo Ollama pilot failed. Check that Ollama is running and qwen3:4b is installed.
  pause
  exit /b 1
)
echo.
echo Pilot complete. Inspect runs\run_*\raw.jsonl and the attempt trace databases.
pause
