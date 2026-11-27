# Windows UTF-8 summary fix

The runner now writes `summary.md` explicitly as UTF-8. The Windows launcher also enables
Python UTF-8 mode and switches the console code page to 65001.

This fixes the `UnicodeEncodeError` for Greek symbols such as Δ when Python otherwise
defaults to cp1252. It does not change model prompts, model outputs, gates, scenario logic,
or scoring.

If a prior run reached summary generation and failed there, inspect that run's `raw.jsonl`
before rerunning. The failed summary write does not imply that Ollama failed.
