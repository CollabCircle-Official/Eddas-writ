# Edda's Writ v3

A one-scene RPG and research demonstration. Talk to the guards, present your writ, and see how the gate's policy treats remembered claims and registry evidence.

## Play

Extract the archive. On Windows, open **play.cmd**. On macOS or Linux, run **sh play.sh** from the extracted folder. You can also run **python -m eddas_writ** with Python 3.12. Standalone mode uses the standard library.

Choose **Courier** for a genuine writ or **Impostor** to see how the gate handles an unverified document. In the default policy, playing as Courier, choose **1, 3** to record a claim and request passage. Choose **5** to sleep and restart the game in a new process. You can then choose **4** to speak to Hild, **2** to present the writ, and **3** to enter. Choose **D** before crossing to see the passage journal and the provenance of each guard's beliefs.

Each session gets its own folder under `saves/` with three SQLite databases and `meta.json`. To reopen a saved game, run `python -m eddas_writ --resume "saves/<folder>"`. Reopening a finished save displays the final research panel and journal.

## Trace checks

The last-decision panel checks coverage against the events committed under that correlation ID. It flags absent, empty, incomplete, duplicated, and mismatched movement or state-event links. The passage journal displays all adjudications in the session. The audit assumes the persisted state store is the reference for committed events.

Run the packaged checks with `python -m unittest discover -s tests -t .`.

## Optional framework mirror

Place this folder alongside the pinned `Thespis` and `Dungeons-and-Agents` checkouts and use **play_research.cmd** with your existing uv setup. The optional mirror sends selected belief writes to Thespis and authorized movement to Dungeons and Agents. The local stores supply the authorization inputs. Gossip and process restart run in standalone mode. The mirror has yet to be tested end to end against the pinned checkouts.

The research runner and scenario definitions are carried forward from v2. Scripted proposers and local stand-ins make their output a check of the harness and its policy fixtures. Report that scope when sharing results.
