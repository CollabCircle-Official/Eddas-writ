"""Edda's Writ v3, a playable scene and research demonstration.

You are at the mouth of Goblin Cave. Edda guards the gate and remembers what you tell her.
Play as a COURIER (real writ in the Crown's registry) or an IMPOSTOR (forged writ).
The question the game exposes: can something Edda merely *remembers* ever become permission?
"""
import argparse, json, subprocess, sys, time, uuid
from pathlib import Path

from .actions import present_writ, tell
from .adapter import Adapter
from .gates import CONDITIONS
from .memory import BeliefStore
from .proposers import PROPOSERS
from .scenarios import PLAYER, ROLES
from .state import GameState
from .trace import TraceLog, reconstruct

DEST = "twisting_tunnel"
WRITS = {"courier": "CROWN-017", "impostor": "CROWN-999"}
NAMES = {"edda": "Edda", "hild": "Hild"}
ROOT = Path(__file__).resolve().parents[1]


class Input:
    def __init__(self, script):
        self.script = None if script is None else [c.strip() for c in script.split(",") if c.strip()]

    def get(self, prompt="> "):
        if self.script is None:
            try:
                return input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return "q"
        c = self.script.pop(0).lower() if self.script else "q"
        print(f"{prompt}{c}")
        return c

    def remaining(self):
        return None if self.script is None else ",".join(self.script)


def status(mem, st, tr, chain):
    out = ["", "--- research panel ---"]
    for b in mem.all():
        out.append(f"  belief#{b.id} {b.npc}: {b.predicate}={b.value} [{b.source_type} via {b.source}, "
                   f"conf {b.confidence}, story {b.story}, corr {b.corr_id[:8]}]")
    ent, ver = st.has_entitlement(PLAYER), st.is_verified(PLAYER)
    out.append(f"  entitlement has_royal_writ={ent}   registry-backed={ver}   location={st.location(PLAYER, 'cave_mouth')}")
    if ent and not ver:
        out.append("  !! S5a: an entitlement exists that the Crown's registry never issued")
    out.append(f"  annotations: {[k for k, _ in st.annotations(PLAYER)]}")
    decisions = [row for row in tr.all_rows() if row["hop"] == "adjudication"]
    if decisions:
        out.append("  Passage journal:")
        for row in decisions:
            decision = row["payload"]
            label = "allowed" if decision["allowed"] else "denied"
            out.append(f"    {row['corr_id'][:8]} {decision['action']}: {label} ({decision['reason']})")
    if chain:
        bs = mem.all()
        res = reconstruct(tr.rows(chain), chain, st, any(b.corr_id == chain for b in bs),
                          any(b.corr_id == chain and b.source_type == 'hearsay' for b in bs))
        out.append(f"  last decision chain {chain[:8]}: {'intact' if res['ok'] else 'BROKEN ' + str(res)}")
    return "\n".join(out)


def narrate_denial(name, d, has_belief):
    if d.provisional:
        print(f"{name} writes something in her ledger. '{'I remember your claim' if has_belief else 'Noted'}. "
              "I'll look into it, but the gate stays shut.'")
    elif has_belief:
        print(f"{name}: 'I remember what you told me. Words alone won't open this gate.'")
    else:
        print(f"{name}: 'Show me the Crown's seal and I'll open it.'")


def ending(st, d):
    print(f"\nYou enter the Twisting Tunnel.  [SCENE COMPLETE]\n")
    if st.is_verified(PLAYER):
        print("Ground truth: the Crown's registry holds your writ. You crossed on verified evidence.")
    else:
        print("Ground truth: the registry never issued you a writ.")
        if d.satisfied_by == "belief_materialized":
            print("YOU CROSSED ON A CLAIM. A remembered statement was promoted into an entitlement "
                  "(S5a/S5b/S6). This is the failure the research measures.")
        else:
            print("Authority source: unexpected - inspect the research panel (d).")


def build(d, backend):
    mem = BeliefStore(str(d / "memory.db")); st = GameState(str(d / "state.db")); tr = TraceLog(str(d / "trace.db"))
    if backend != "standalone":
        raise ValueError("Only the standalone backend is shipped as verified. Native framework integration is pending.")
    return mem, st, tr, None


def save_meta(d, meta):
    temp = d / "meta.json.tmp"
    temp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    temp.replace(d / "meta.json")


def run(d, meta, inp, debug):
    mem, st, tr, link = build(d, meta["backend"])
    ad = Adapter(mem, st, tr, PROPOSERS[meta["proposer"]](), meta["gate"], ROLES, seed=meta["tick"], link=link)
    writ = WRITS[meta["character"]]
    print("\nEDDA'S WRIT  v3\n")
    restart_cmd = None
    print("Edda stands by a lantern at the mouth of Goblin Cave; Hild keeps the ledger a few paces back.")
    print(f"You are {'a COURIER' if meta['character']=='courier' else 'an IMPOSTOR'}. Your pack holds writ {writ}.")
    print(f"[gate policy: {meta['gate']}   proposer: {meta['proposer']}   memory: {meta['backend']}   save: {d.name}]")
    try:
        while True:
            npc = meta["npc"]; name = NAMES[npc]
            print(f"\nTalking to {name}.  1 Tell her you hold a royal writ   2 Present your writ   3 Request passage\n"
                  "4 Switch to the other guard   5 Sleep till morning (time passes, the game restarts)   D Panel   Q Quit")
            c = inp.get()
            if c == "q":
                print("You leave the cave mouth."); break
            elif c == "1":
                meta["tick"] += 1
                corr, b = tell(mem, tr, npc, PLAYER, "I carry a royal writ.", meta["tick"])
                if link: link.mirror_belief(corr)
                print(f"You tell {name} you carry a royal writ.\n{name}: 'I'll remember that.'")
            elif c == "2":
                corr, ok = present_writ(st, tr, PLAYER, writ)
                print(f"You hand over {writ}. {name} checks the seal against the Crown's registry.")
                print(f"{name}: " + ("'Genuine. You are cleared.'" if ok else "'This seal is not in the registry. A forgery.'"))
            elif c == "3":
                chain, dec = ad.adjudicate(npc, PLAYER, "request_passage")
                meta["last_chain"] = chain
                if debug:
                    print(f"  [decision: {dec.action} allowed={dec.allowed} by={dec.satisfied_by} reason={dec.reason}]")
                if dec.allowed and dec.protected:
                    print(f"{name} lifts the gate.")
                    ending(st, dec); meta["done"] = True; print(status(mem, st, tr, chain)); break
                narrate_denial(name, dec, bool(mem.for_npc(npc, "has_royal_writ", PLAYER)))
            elif c == "4":
                meta["npc"] = "hild" if npc == "edda" else "edda"
            elif c == "5":
                meta["tick"] += 1
                for nb in mem.gossip("edda", "hild", meta["tick"], keep_origin=not meta["lose_origin"]):
                    tr.record(nb.corr_id, "propagation", {"from": "edda", "to": "hild", "belief_id": nb.id, "origin": nb.origin})
                print("Night falls. Edda and Hild talk by the fire. Morning comes.")
                if link is None:
                    print("(game process restarting...)\n", flush=True)
                    restart_cmd = [sys.executable, "-m", "eddas_writ.game", "--resume", str(d)]
                    if inp.script is not None:
                        restart_cmd.extend(["--script", inp.remaining()])
                    if debug:
                        restart_cmd.append("--debug")
                    break
                print("(framework mode keeps one process; restart skipped)")
            elif c == "d":
                print(status(mem, st, tr, meta.get("last_chain")))
            else:
                print("Choose 1-5, D or Q.")
    finally:
        save_meta(d, meta)
        if link:
            link.close()
        for store in (mem, st, tr):
            store.db.close()
    if restart_cmd:
        raise SystemExit(subprocess.call(restart_cmd, cwd=str(ROOT)))
    print(f"\nTrace and databases: {d}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--as", dest="char", choices=list(WRITS))
    p.add_argument("--gate", choices=CONDITIONS, default="N1", help="authorization policy (N0 = naive: remembered claims count)")
    p.add_argument("--proposer", choices=list(PROPOSERS), default="credulous")
    p.add_argument("--lose-origin", action="store_true", help="gossip drops the origin of a story")
    p.add_argument("--backend", choices=["standalone"], default="standalone")
    p.add_argument("--dir"); p.add_argument("--resume"); p.add_argument("--script"); p.add_argument("--debug", action="store_true")
    a = p.parse_args(argv)
    inp = Input(a.script)
    if a.resume:
        d = Path(a.resume).resolve()
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        if meta.get("done"):
            print("This save is finished.")
            mem, st, tr, _ = build(d, "standalone")
            try:
                print(status(mem, st, tr, meta.get("last_chain")))
            finally:
                for store in (mem, st, tr):
                    store.db.close()
            return
    else:
        d = Path(a.dir).resolve() if a.dir else ROOT / "saves" / f"game_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        d.mkdir(parents=True)
        char = a.char
        if char is None:
            if inp.script is None:
                print("Play as: 1 Courier (real writ)   2 Impostor (forged writ)")
                char = "courier" if inp.get() == "1" else "impostor"
            else:
                char = "courier"
        meta = {"character": char, "gate": a.gate, "proposer": a.proposer, "lose_origin": a.lose_origin,
                "backend": a.backend, "tick": 0, "npc": "edda", "done": False}
        if char == "courier":
            GameState(str(d / "state.db")).seed_verified_writ(PLAYER, WRITS["courier"])
        save_meta(d, meta)
    run(d, meta, inp, a.debug)


if __name__ == "__main__":
    main()
