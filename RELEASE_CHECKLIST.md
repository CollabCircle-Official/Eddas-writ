# v6 release checklist

- [x] Default launcher opens the playable adventure menu.
- [x] Offline scripted dialogue works without external dependencies.
- [x] Optional Ollama NPC dialogue uses distinct Edda/Hild personalities.
- [x] Optional Ollama structured action proposer is connected to the adventure.
- [x] Dialogue and action proposal are separate calls and separate trace events.
- [x] Deterministic authorization gate remains the only protected-movement authority.
- [x] Model/proposer errors fail closed in the story game.
- [x] Role, gate, provider and model settings persist in the save.
- [x] Guard handover performs a real OS-process restart.
- [x] Research runner and matched scenario harness retained.
- [x] Windows UTF-8 launchers and setup documentation included.
- [x] Native-framework mirror removed from the runnable package pending verified integration.
- [ ] Native Thespis integration against public APIs and pinned checkout.
- [ ] Native Dungeons and Agents movement integration and license review.
- [ ] Windows 10/11 + Python 3.12 + local Ollama manual playthrough by project owner.

The checked items are supported by local automated tests. The unchecked items are intentionally not represented as complete.
