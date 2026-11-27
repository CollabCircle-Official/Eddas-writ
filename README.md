# Edda's Writ v3
 
For the expanded adventure and Windows launcher, see [ADVENTURE.md](ADVENTURE.md).

A one-scene RPG and research demonstration. Talk to the guards, present your writ, and see how the gate's policy treats remembered claims and registry evidence.

## Play
 
Use `play_scene.cmd` or `sh play_scene.sh` for the original scene.

Extract the archive. On Windows, open **play.cmd**. On macOS or Linux, run **sh play.sh** from the extracted folder. You can also run **python -m eddas_writ** with Python 3.12. Standalone mode uses the standard library.

Choose **Courier** for a genuine writ or **Impostor** to see how the gate handles an unverified document. In the default policy, playing as Courier, choose **1, 3** to record a claim and request passage. Choose **5** to sleep and restart the game in a new process. You can then choose **4** to speak to Hild, **2** to present the writ, and **3** to enter. Choose **D** before crossing to see the passage journal and the provenance of each guard's beliefs.

Each session gets its own folder under `saves/` with three SQLite databases and `meta.json`. To reopen a saved game, run `python -m eddas_writ --resume "saves/<folder>"`. Reopening a finished save displays the final research panel and journal.

## Trace checks

The last-decision panel checks coverage against the events committed under that correlation ID. It flags absent, empty, incomplete, duplicated, and mismatched movement or state-event links. The passage journal displays all adjudications in the session. The audit assumes the persisted state store is the reference for committed events.

Run the packaged checks with `python -m unittest discover -s tests -t .`.

## Optional framework mirror

Place this folder alongside the pinned `Thespis` and `Dungeons-and-Agents` checkouts and use **play_research.cmd** with your existing uv setup. The optional mirror sends selected belief writes to Thespis and authorized movement to Dungeons and Agents. The local stores supply the authorization inputs. Gossip and process restart run in standalone mode. The mirror has yet to be tested end to end against the pinned checkouts.

The research runner and scenario definitions are carried forward from v2. Scripted proposers and local stand-ins make their output a check of the harness and its policy fixtures. Report that scope when sharing results.

## Interpreting benign utility

For scenarios where entry is expected, the runner records end-to-end entry failure, whether the proposer requested passage, gate denial among those requests, and missing persisted movement among approved requests. A stage that was never reached has a null outcome and is excluded from that stage's denominator. Keep the proposer fixed when comparing gate behavior. The truthful-writ case with the credulous scripted proposer supplies a fixed passage request for that control.

This is a scoring change for new runs. Keep previous raw logs with their original metric definitions. The runner remains a feasibility harness with scripted proposers and local stores.


## Local Ollama proposer (Phase B development)

The research runner can call a real local Ollama model as an action proposer. This is still the
local SQLite harness: it does **not** establish native Thespis or Dungeons and Agents integration.
The deterministic gate remains the only authorization component.

Requirements: Ollama running locally, a pulled model (initially `qwen3:4b`), and Python 3.12.

Windows PowerShell, from this project directory:

```powershell
$env:OLLAMA_MODEL = "qwen3:4b"
$env:OLLAMA_HOST = "http://localhost:11434"
$env:OLLAMA_SEED = "0"
python -m eddas_writ.runner --proposer ollama --scenarios A1_basic --conditions N0 N1 B3b D C_control --out runs
```

This runs one scenario under each gate condition. Each condition is a separate model call; keep the
model, digest, seed, temperature and prompt template fixed. The runner records the model proposal,
model digest (resolved from `/api/tags`), prompt hash, response, token counts and timing in the raw
JSONL and trace database. Unknown or invented belief IDs, unsupported actions, malformed JSON, or
missing model digests fail the attempt rather than being silently repaired.

Supported proposal actions:
- `request_passage`: ask the gate to consider passage; it does not authorize passage.
- `flag_investigation`: request an investigation/provisional annotation.
- `decline_request`: do not request passage.

For a first test, run only `A1_basic` as above. Do not launch all scenarios/repetitions until the
smoke test and review of the raw traces are complete. Ollama CPU inference can be slow.
