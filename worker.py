"""Two phases run as separate OS processes so S2 (cross-session persistence) is a real restart."""
import argparse, json, os, random, zlib
from .memory import BeliefStore
from .state import GameState
from .trace import TraceLog, new_corr_id
from .scenarios import BY_ID, PLAYER, ROLES
from .proposers import PROPOSERS
from .adapter import Adapter
from .actions import tell, present_writ


def paths(d):
    return os.path.join(d, "memory.db"), os.path.join(d, "state.db"), os.path.join(d, "trace.db")


def observe(d, sid):
    sc = BY_ID[sid]
    mem, st, tr = (BeliefStore(paths(d)[0]), GameState(paths(d)[1]), TraceLog(paths(d)[2]))
    try:
        if sc.truth_has_writ:
            st.seed_verified_writ(PLAYER, "CROWN-017")
        tick = 0
        for step in sc.steps:
            tick += 1
            if step["op"] == "say":
                tell(mem, tr, step["npc"], PLAYER, step["text"], tick, step["value"], step["confidence"], step["source_type"])
            elif step["op"] == "present":
                present_writ(st, tr, PLAYER, step["writ"])
            elif step["op"] == "gossip":
                for nb in mem.gossip(step["teller"], step["listener"], tick, keep_origin=step["keep_origin"]):
                    tr.record(nb.corr_id, "propagation", {"from": step["teller"], "to": step["listener"],
                                                          "belief_id": nb.id, "origin": nb.origin})
        return {"ok": True}
    finally:
        for store in (mem, st, tr):
            store.db.close()


def adjudicate(d, sid, condition, proposer, seed):
    sc = BY_ID[sid]
    mem, st, tr = (BeliefStore(paths(d)[0]), GameState(paths(d)[1]), TraceLog(paths(d)[2]))
    try:
        retrieved = [b.__dict__ for b in mem.all()]  # post-restart view, for S2
        ad = Adapter(mem, st, tr, PROPOSERS[proposer](), condition, ROLES, seed)
        chain, dec = ad.adjudicate(sc.ask["npc"], PLAYER, sc.ask["intent"])
        return {"chain": chain, "decision": dec.__dict__, "retrieved_after_restart": retrieved}
    finally:
        for store in (mem, st, tr):
            store.db.close()



if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["observe", "adjudicate"])
    p.add_argument("--dir", required=True); p.add_argument("--scenario", required=True)
    p.add_argument("--condition", default="N0"); p.add_argument("--proposer", default="credulous")
    p.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    out = observe(a.dir, a.scenario) if a.phase == "observe" else adjudicate(a.dir, a.scenario, a.condition, a.proposer, a.seed)
    print(json.dumps(out, default=str))
