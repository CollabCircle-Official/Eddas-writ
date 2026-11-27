# Changelog

## 6.0.0 — Final standalone game release candidate
- Made the adventure the default `python -m eddas_writ` entry point.
- Added optional Ollama-powered natural dialogue with distinct Edda and Hild personalities.
- Connected the structured Ollama action proposer to the adventure gate.
- Kept dialogue generation and action proposals separate.
- Added `talk <message>`, `ask` and `inspect` commands.
- Persisted provider/model selection with each save and across process restarts.
- Added fail-closed handling for action-proposer errors in the game loop.
- Added Windows UTF-8 launchers and complete setup/game/research documentation.
- Preserved the separate research runner and scenario/test suite.
- Documented native Thespis/Dungeons and Agents integration as unverified.
