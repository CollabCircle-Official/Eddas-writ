# Edda's Writ v5 — A Lantern for the Vale

A playable, saveable, text-based fantasy adventure and an auditable research harness about memory, evidence, and authorization.

## Requirements
- Windows 10/11
- Python 3.10+ (3.12 recommended)
- Optional: Ollama and `qwen3:4b`

## Play
Extract the folder. Double-click `Play.cmd`, or run:

```powershell
py -3 -m eddas_writ
```

Choose a role and policy with command-line options:

```powershell
py -3 -m eddas_writ --role courier --policy strict --save saves/courier
py -3 -m eddas_writ --role traveler --policy strict --save saves/traveler
py -3 -m eddas_writ --role impostor --policy evidence --save saves/impostor
```

Use a new save directory for each run. Saves are stored in SQLite.

## Optional local model
Start Ollama and pull the model:

```powershell
ollama pull qwen3:4b
```

Then:

```powershell
py -3 -m eddas_writ --provider ollama --model qwen3:4b --role traveler --policy strict --save saves/ollama-traveler
```

The model is an untrusted proposer. Its JSON proposal never grants passage. The deterministic gate independently checks evidence IDs and verified registry evidence. If Ollama is unavailable or returns invalid data, the game fails closed.

## Policies
- `strict`: only a registry-verified royal writ authorizes passage.
- `evidence`: testimony may prompt investigation but never authorizes movement.
- `naive_demo`: deliberately unsafe research comparison. It can trust remembered claims and must never be used as a production policy.

## Game controls
Commands are displayed for each scene. At the gate:
- `talk <message>` records testimony and attributed hearsay.
- `ledger` checks the authoritative registry.
- `show` presents the traveler's document.
- `pass` asks the proposer and then the deterministic gate.
- `switch` changes between Edda and Hild.
- `journal` shows evidence, memories, decisions, and event counts.

## Tests
```powershell
py -3 -m unittest discover -s tests -v
```

## Scope and integration status
This v5 package is a self-contained playable implementation with a deterministic authorization boundary, SQLite persistence, optional Ollama proposals, and unit tests. It is **not yet a verified native integration** with Thespis or Dungeons and Agents. Their pinned checkouts, API contracts, and runtime tests must be available before that integration can honestly be marked complete. Do not present this local SQLite implementation as native-framework evidence.

## Research integrity
- A proposer action is not an authorization decision.
- Testimony and hearsay are not registry evidence.
- Evidence identifiers must exist in the local evidence store.
- `naive_demo` is explicitly unsafe and is only for controlled comparisons.
- Smoke tests and pilot plumbing checks are not empirical evidence.
- Keep raw experimental runs out of Git commits; archive them separately with protocol and environment metadata.
