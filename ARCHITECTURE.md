# Edda's Writ v6 architecture

## Story runtime

`eddas_writ.adventure` is the player-facing game. It orchestrates a small, deterministic scene state machine:

`Ford → Crown Gate → (Protected Tunnel | Public Trail) → Shelter/Tunnel → Watchtower → Ending`

A save folder contains:
- `story.db`: scene snapshots/history, role, time, inventory, gate, provider and model settings.
- `memory.db`: attributed NPC beliefs, source type, confidence, origin and correlation ID.
- `state.db`: authoritative registry fixtures, entitlements, annotations, location and committed state events.
- `trace.db`: correlation-linked utterance, belief, dialogue, proposal, adjudication and mutation hops.

Each action writes a new story snapshot. The `rest` command closes the worker's database connections and relaunches the game in a separate OS process before continuing with the same save folder.

## Dialogue and action proposal

Dialogue and decision proposals are deliberately separate:

1. `DialogueProvider` generates a character response. It receives read-only context and has no mutation or movement API.
2. `OllamaProposer` (or deterministic `Credulous`) proposes a structured action and cites only known belief IDs.
3. `Adapter` passes the proposal and retrieved beliefs to `gates.decide`.
4. The deterministic gate checks authoritative entitlement and the selected experimental policy.
5. Only the game state layer commits a protected location transition.

Ollama cannot create a belief, register a writ, change a policy, or directly call a movement tool. In the story runtime, proposer errors are logged and the gate remains closed. In the research runner, invalid provider outputs fail the attempt instead of being silently repaired.

## Research runner

`eddas_writ.runner` executes scenario × condition × repetition combinations. Observation and adjudication can occur in separate OS processes. Each attempt receives isolated SQLite stores and a deterministic seed. The runner records raw JSONL, decision metadata, persisted state, trace coverage and benign utility metrics.

`N0` is an intentionally unsafe simulated policy. It is retained only to reproduce a belief-to-entitlement failure under controlled conditions. `D`, `B3b` and `C_control` are safe registry-only/binary controls; `N1` is a source-classification condition.

## Native framework boundary

The shipped game is a standalone implementation using SQLite. It does not claim native Thespis or Dungeons and Agents semantics. The previous fixture-driven mirror was removed from the runnable package. See `research/FRAMEWORK_INTEGRATION_STATUS.md` for exact audited revisions, license uncertainty and the tests required before native integration can be declared complete.
