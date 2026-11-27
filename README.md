# Edda's Writ 6.0 — A Lantern for the Vale

A saveable text adventure about a flooded valley, a royal writ, two guards with persistent memories, and the boundary between testimony and authority. It includes a reproducible research harness for studying belief propagation and authorization policies.

## Quick start (Windows)
1. Install Python 3.10+ (Python 3.12 recommended).
2. Clone or extract this repository.
3. Double-click `Play.cmd` and choose **New Journey**, a role and a gate policy.

Or run `py -3 -m eddas_writ` to open the journey menu. For a direct run, use `py -3 -m eddas_writ.adventure --role courier --gate D --save saves/courier`.

The standard-library game works offline. Each journey uses a separate save folder with SQLite databases.

## Play with Ollama
Install Ollama and pull a model:

```powershell
ollama pull qwen3:4b
```

Then double-click `Play_Ollama.cmd`, or run:

```powershell
py -3 -m eddas_writ.adventure --provider ollama --model qwen3:4b --role courier --gate D --save saves/courier_ollama
```

Ollama is used for two separate tasks: natural NPC dialogue and structured action proposals. Edda and Hild have distinct personalities. The model cannot create evidence, change policy, execute movement or authorize protected passage. The deterministic gate is the sole authority. If Ollama is unavailable, malformed or times out, the gate stays closed and the public trail remains available.

## Roles
- **Courier:** carries a genuine writ registered by the Crown.
- **Traveler:** has no writ and must use the public ridge trail.
- **Impostor:** carries a forged writ and may try to persuade the guards.

## Gate policies
| Policy | Behaviour | Use |
|---|---|---|
| `D` | Requires authoritative registry entitlement | Safe default |
| `B3b` | Beliefs cannot authorize protected movement | Safe research condition |
| `C_control` | Registry-only control condition | Safe research condition |
| `N1` | Classifies sources; uncorroborated claims remain provisional | Research condition |
| `N0` | Deliberately trusts a remembered claim | Unsafe simulation only |

Do not use `N0` for normal play. It reproduces the failure mode under controlled research conditions.

## Commands
At the gate: `talk <message>`, `ask`, `ledger`, `show`, `pass`, `guard`, `rest`, `inspect`, `journal`, `trail`. Other commands are displayed in each scene. Routes include the flooded ford, Crown gate, twisting tunnel, shepherd's shelter, ridge road and watchtower. Choices affect time, rescue status, equipment and endings.

## Saves and resume
Every completed action is persisted. Reuse the same `--save` folder to resume; role, gate, provider and model settings are retained. Use a new folder for a new playthrough.

```powershell
py -3 -m eddas_writ.adventure --role traveler --gate D --save saves/traveler_01
```

## Research harness
Run the scenario suite separately from the story game:

```powershell
py -3 -m eddas_writ.runner --proposer credulous --conditions N0 N1 B3b D C_control --out runs
```

For a local-model smoke test:

```powershell
$env:OLLAMA_MODEL = "qwen3:4b"
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_SEED = "0"
py -3 -m eddas_writ.runner --proposer ollama --scenarios A1_basic --conditions N0 N1 B3b D C_control --out runs
```

Raw JSONL, per-attempt SQLite databases, model digest, prompt hash, response, timing and scoring are stored locally. Do not commit research runs or personal save files. A smoke test or pilot is not evidence of a general model effect.

## Tests
Run the modules individually (the game and research tests launch their own child processes):

```powershell
py -3 -m unittest tests.test_game -v
py -3 -m unittest tests.test_testbed -v
py -3 -m unittest tests.test_adventure -v
py -3 -m unittest tests.test_dialogue tests.test_ollama_proposer tests.test_trace_coverage -v
```

All Ollama tests use mocked HTTP responses; no running model server is required for the test suite.

## Architecture and integration status
- Playable adventure: Python standard library.
- Memory, world state and trace: separate SQLite stores with provenance and correlation IDs.
- Ollama: local natural-language dialogue and structured action-proposal adapters.
- Authorization: deterministic and fail-closed for safe policies.
- Research runner: separate-process persistence checks, attack scenarios, benign controls and trace reconstruction.

**Native Thespis and Dungeons and Agents integration is not claimed as complete.** The prior adapter was a fixture-based, untested mirror and has been removed from the runnable build. The Dungeons and Agents license was not verified in the supplied audit. See `research/FRAMEWORK_INTEGRATION_STATUS.md` for pinned revisions and the remaining integration gates. This repository does not redistribute either upstream project or present SQLite stand-ins as native framework state.

## Research safety
- The model is a proposer, not an authority.
- Testimony and hearsay are not registry evidence.
- Unknown or invented belief IDs are rejected.
- Model errors do not open protected routes.
- `N0` is intentionally unsafe and for controlled comparison only.
- Keep raw pilot outputs and personal saves out of version control.
