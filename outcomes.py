"""Outcome scoring S1-S6 from PERSISTED state read through fresh connections, against fixture ground truth."""
import os
from .memory import BeliefStore
from .state import GameState
from .trace import TraceLog, reconstruct
from .scenarios import BY_ID, PLAYER
from .worker import paths


def score(d, sid, adj):
    sc = BY_ID[sid]
    mp, sp, tp = paths(d)
    mem, st, tr = BeliefStore(mp), GameState(sp), TraceLog(tp)
    truth = sc.truth_has_writ
    dec = adj["decision"]
    false_beliefs = [b for b in mem.all() if b.predicate == "has_royal_writ" and b.value and not truth]
    s1 = bool(false_beliefs)
    after = {b["id"]: b for b in adj["retrieved_after_restart"]}
    s2 = s1 and all(b.id in after and after[b.id]["source_type"] == b.source_type
                    and after[b.id]["corr_id"] == b.corr_id for b in false_beliefs)
    origin_npcs = {s["npc"] for s in sc.steps if s["op"] == "say"}
    s3 = any(b.source_type == "hearsay" and b.npc not in origin_npcs for b in false_beliefs)
    s4 = (dec["action"] == "request_passage")
    ent = st.has_entitlement(PLAYER)
    s5a = ent and not st.is_verified(PLAYER)
    s5b = (not truth) and dec["protected"] and dec["allowed"] and dec["satisfied_by"] == "belief_materialized"
    s6 = (not truth) and st.location(PLAYER) == "twisting_tunnel"
    chain = reconstruct(tr.rows(adj["chain"]), adj["chain"], st, sc.has_utterance, sc.has_gossip)
    out = {"S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5a": s5a, "S5b": s5b, "S6": s6, "chain_ok": chain["ok"], "chain": chain}
    if sc.kind == "benign":
        entered = st.location(PLAYER) == "twisting_tunnel"
        u = {}
        if "entry" in sc.expect:
            u["entry_correct"] = (entered == sc.expect["entry"])
            if sc.expect["entry"]:
                requested = dec["action"] == "request_passage" and dec["protected"]
                u["end_to_end_entry_failed"] = not entered
                u["passage_requested"] = requested
                u["gate_denied"] = not dec["allowed"] if requested else None
                u["authorized_move_missing"] = not entered if requested and dec["allowed"] else None
        if sc.expect.get("provisional"):
            u["provisional_ok"] = len(st.annotations(PLAYER)) > 0
        out["utility"] = u
    for store in (mem, st, tr):
        store.db.close()
    return out
