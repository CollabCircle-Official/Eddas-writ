"""Player-facing actions shared by the game and the scenario runner (single code path)."""
from .trace import new_corr_id


def tell(mem, tr, npc, player, text, tick, value=True, conf=0.7, stype="testimony"):
    """Player says something to an NPC. The corr_id is born HERE, at the utterance."""
    corr = new_corr_id()
    tr.record(corr, "utterance", {"player": player, "npc": npc, "text": text})
    b = mem.observe(npc, player, "has_royal_writ", value, stype, player, conf, corr, tick)
    tr.record(corr, "belief_write", {"belief_id": b.id, "source_type": b.source_type, "source": b.source,
                                     "confidence": b.confidence, "event_id": b.event_id})
    return corr, b


def present_writ(st, tr, player, writ_id):
    """The one legitimate promotion path: a document checked against the Crown's registry
    (deterministic, authoritative), never a remembered claim."""
    corr = new_corr_id()
    tr.record(corr, "document_presented", {"player": player, "writ_id": writ_id})
    ok = st.registry_check(player, writ_id)
    if ok:
        seq = st.commit("entitlement_set", player, {"name": "has_royal_writ", "set_by": "registry_verification"}, corr)
    else:
        seq = st.commit("annotation_added", player, {"kind": "forged_writ_presented", "note": writ_id}, corr)
    tr.record(corr, "tool_exec", {"action": "verify_writ", "registry_ok": ok})
    tr.record(corr, "state_mutation", {"seqs": [seq]})
    return corr, ok
