# v5 Architecture and Completion Plan

## Runtime pipeline

Player input → NPC memory update → proposer (rules or Ollama) → schema and evidence-ID validation → deterministic authorization gate → protected scene transition → event and decision audit.

The model cannot call movement functions, write evidence, or change the policy. The gate is the sole authority for protected passage.

## Data stores
One SQLite database per save directory:
- `game_state`: resumable scene, role, policy, time budget, inventory.
- `evidence`: evidence type, source, verification state, confidence.
- `memories`: speaker, source type, source ID and confidence.
- `decisions`: proposal, final decision, cited evidence and model metadata.
- `events`: append-only application event history.

## Current playable scope
- Three roles: courier, traveler, impostor.
- Six scenes and multiple routes.
- Two guards with attributed gossip.
- Registry verification, testimony and hearsay.
- Strict, evidence and deliberately unsafe demonstration policies.
- Rules proposer and optional local Ollama proposer.
- SQLite save/resume and audit journal.

## Required before claiming production/native integration
1. Add integration adapters against the exact pinned Thespis and Dungeons-and-Agents commits.
2. Replace SQLite stand-ins only after mapping their semantics and transaction boundaries.
3. Add end-to-end tests for gossip propagation, process restart, duplicate events and crash recovery.
4. Add adversarial tests for prompt injection, unknown IDs, stale evidence, malformed model output and proposer timeouts.
5. Add migration/versioning for save databases.
6. Add reproducible experiment manifests, fixed model digest, prompt hashes, seeds and independent scenario repetitions.
7. Verify on the user's Windows machine with the exact installed Python and Ollama versions.
