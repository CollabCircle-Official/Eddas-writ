# Native framework integration — release boundary

The v6 game is a complete standalone adventure and research harness. It does not claim native Thespis or Dungeons and Agents integration.

## Audited upstream revisions

| Project | Audited revision | Observed status |
|---|---|---|
| Dungeons and Agents | `4e7f4253395e06e3f637a494631427bb53484a54` | Event store, replay, guarded headless turn tested. No tracked LICENSE/COPYING file was found in the audited checkout; redistribution permission remains unverified. |
| Thespis | `6e07facf4ec9345b35500addcb013bba1d4e41a4` | MIT license observed. Belief evidence, gossip provenance and persistence probes passed. |

## Why the native adapter is not shipped as an active backend

The previous `backends/frameworks.py` was a fixture-based mirror that imported Thespis test fixtures and used a fixed Dungeons and Agents `FunctionModel` that always called `move_to`. It was explicitly untested as a production integration. It did not replace the local stores, did not mirror gossip, and did not establish that belief evidence changed a native agent decision. It has therefore been removed from the runnable v6 package rather than exposed as a misleading feature.

## Required native integration milestone

1. Obtain and pin both upstream checkouts at the revisions above (or explicitly approve newer revisions).
2. Confirm Dungeons and Agents redistribution/use license before vendoring or packaging any code.
3. Implement the Thespis adapter against its public session/belief API, not test fixtures.
4. Implement the Dungeons and Agents adapter against its public turn/movement API, with model-driven intent and a real authorization boundary.
5. Run a paired native movement experiment: evidence-present vs evidence-withheld, same seed, same model and prompt settings.
6. Verify persisted native evidence IDs, native movement event, final location and a single correlation chain.
7. Test restart, fault injection, malformed outputs, unknown evidence IDs and rollback/partial-commit behaviour.

Until these checks pass, the SQLite stores remain the standalone game's stores and the native integration status must remain **pending**.
