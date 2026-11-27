# A Lantern for the Vale

Open **Play.cmd** on Windows with Python 3.12. For the role and policy menu on other systems, run `python3 -m eddas_writ.adventure --menu` from this folder. Type the commands shown in the game. Each completed action saves. At the ending, type **new** to start a fresh run and retain the previous save.

| Playthrough | Command |
|---|---|
| Courier, registry-only gate | `python -m eddas_writ.adventure --role courier --gate D --save courier_run` |
| Traveler (no writ), registry-only gate | `python -m eddas_writ.adventure --role traveler --gate D --save traveler_run` |
| Impostor, simulated naive gate | `python -m eddas_writ.adventure --role impostor --gate N0 --save impostor_demo` |

Use a different save folder to change role or policy. A save retains its original settings.

- **Courier:** `help, talk, pass, show, pass, climb, signal`. Enter each word separately.
- **Traveler:** `road, trail, ridge, bell` reaches the tower in time. `road, trail, torch, signal` gives another successful ending. The sheep trail is a public story route.
- **Memory:** At the gate, `talk` records an utterance and a belief. `rest` passes the account from Edda to Hild, saves, closes the databases and resumes in a new process. Use `guard` to speak to Hild and `journal` to inspect provenance, gate decisions and the latest passage trace.

The adventure uses v3's local stores, adapter, gates, and journal. Its passage action submits a structured request through the scripted proposer, so the player's request reaches the gate consistently. The original Phase A scene and research runner are still available as `python -m eddas_writ` and `python -m eddas_writ.runner`. See README.md for those modes.

Dialogue choices are commands with scripted responses. The adventure is offline and uses SQLite stand-ins. N0 models a deliberately permissive rule in a fictional game. The optional v3 framework mirror belongs to the original scene. This edition does not establish model behavior or native-framework authorization behavior. The story, memory, world and trace use separate databases and do not share a crash-atomic transaction.
