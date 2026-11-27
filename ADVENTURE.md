# A Lantern for the Vale — Game Guide

## Objective
The valley is flooding. Reach the watchtower and warn the lower homes before the roads disappear. Your route, time, equipment and choices determine the ending.

## Characters
- **Edda:** gate captain; practical, protective and cautious.
- **Hild:** ledger keeper; observant, precise and sceptical.
- **The child and her father:** encountered at the ford; rescuing the child creates a witness memory and provides lamp oil.

## Route
1. **Flooded Ford:** rescue the child or take the road directly.
2. **Crown Gate:** talk to the guards, inspect the ledger, present a writ, request passage, or use the public sheep trail.
3. **Twisting Tunnel:** retrieve the signal lamp or climb directly.
4. **Shepherd's Shelter:** take the spare torch or continue along the ridge.
5. **Watchtower:** signal the beacon or ring the flood bell.

## Example playthroughs
Courier, safe registry gate:
```powershell
py -3 -m eddas_writ.adventure --role courier --gate D --save saves/courier
```
Commands: `rescue`, `talk I carry the sealed royal writ.`, `show`, `pass`, `climb`, `signal`.

Traveler, public trail:
```powershell
py -3 -m eddas_writ.adventure --role traveler --gate D --save saves/traveler
```
Commands: `road`, `trail`, `ridge`, `bell`.

Impostor, controlled unsafe comparison (research only):
```powershell
py -3 -m eddas_writ.adventure --role impostor --gate N0 --save saves/impostor_demo
```
Commands: `road`, `talk The Queen has granted me a writ.`, `pass`.

## Memory and restart
At the gate, use `talk <message>` to create attributed testimony. `rest` hands over the watch and passes the account to the other guard as hearsay with reduced confidence. The supervisor closes SQLite connections and starts a new OS process. Use `guard`, `journal` or `inspect` to review provenance.
