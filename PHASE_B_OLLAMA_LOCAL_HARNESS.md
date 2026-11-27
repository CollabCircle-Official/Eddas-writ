# Phase B: Ollama proposer integration (local harness)

## Status

Implemented a real Ollama-backed proposer in the Edda's Writ research runner.

- Provider: Ollama HTTP API (`/api/chat`)
- Initial model: `qwen3:4b`
- Structured output: JSON Schema
- Thinking: disabled
- Temperature: 0
- Seed: fixed by `OLLAMA_SEED` (default 0)
- Actions: `request_passage`, `flag_investigation`, `decline_request`
- Evidence citations: integer belief IDs; every cited ID is checked against the actual belief IDs supplied to the proposer
- Reproducibility metadata: model name, model digest from `/api/tags`, prompt hash and prompt, response, token counts, durations, seed and generation settings
- Trace: a `model_proposal` hop is written before deterministic adjudication
- Runner: supports `--proposer ollama` and `--scenarios` for staged smoke tests

## Important scope boundary

This implementation connects Ollama to the existing local Edda's Writ SQLite research harness. It does **not** yet replace the local belief store with native Thespis, and it does **not** establish native Dungeons and Agents movement. The existing `backends/frameworks.py` remains an unvalidated mirror and must not be described as a validated native integration.

The inherited Thespis fixture mapping involving `b: "mara"` is not fixed by this phase. The current Ollama proposer sees the local harness's belief objects, which use the existing `has_royal_writ` predicate and do not require the legacy `mara` argument.

## First Windows pilot

1. Start Ollama and confirm `ollama list` contains `qwen3:4b`.
2. Open this folder in PowerShell.
3. Run `run_ollama_pilot.cmd`, or run:

```powershell
$env:OLLAMA_MODEL = "qwen3:4b"
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_SEED = "0"
python -m eddas_writ.runner --proposer ollama --scenarios A1_basic --conditions N0 N1 B3b D C_control --out runs
```

This makes five model calls against one scenario, one per gate condition. The model prompt and settings are held constant; the deterministic gate condition changes. Inspect the resulting `runs/run_*/raw.jsonl` and each attempt's `trace.db`.

## Failure behaviour

The attempt fails rather than silently repairing:
- invalid JSON;
- unexpected/missing fields;
- unsupported action;
- malformed justification;
- invented or unavailable belief IDs;
- unavailable Ollama endpoint;
- missing model digest.

## Tests

The new Ollama proposer tests use a mocked HTTP response and do not call the user's Ollama server. They cover valid structured proposals, model metadata capture, invalid actions, and invented belief-ID rejection.

Passing these tests establishes provider-adapter behavior, not model quality or native framework integration.
