"""Adapter: memory -> proposer -> deterministic gate -> state commit, fully traced.

chain_id = corr_id of the originating utterance (first retrieved belief). If other
beliefs with different corr_ids were consulted they are listed in `also_consulted`.
With no belief, a fresh request id is used.
"""
import random
from .trace import new_corr_id
from .gates import decide


class Adapter:
    def __init__(self, memory, state, trace, proposer, condition, roles, seed=0, link=None):
        self.memory, self.state, self.trace = memory, state, trace
        self.proposer, self.condition, self.roles = proposer, condition, roles
        self.rng = random.Random(seed)
        self.link = link          # optional FrameworkLink (real Thespis/DnA mirror)

    def adjudicate(self, npc, player, intent):
        beliefs = self.memory.for_npc(npc, "has_royal_writ", player)
        chain = beliefs[0].corr_id if beliefs else new_corr_id()
        decision_id = new_corr_id()
        self.trace.record(chain, "belief_retrieve", {
            "npc": npc, "belief_ids": [b.id for b in beliefs],
            "source_types": [b.source_type for b in beliefs],
            "also_consulted": sorted({b.corr_id for b in beliefs} - {chain})})
        self.trace.record(chain, "adapter_handoff", {
            "intent": intent, "condition": self.condition,
            "belief_fields": [{"id": b.id, "source_type": b.source_type, "confidence": b.confidence,
                               "story": b.story, "event_id": b.event_id} for b in beliefs]})
        action = self.proposer.propose(intent, beliefs, self.rng)
        if action.metadata:
            self.trace.record(chain, "model_proposal", action.metadata)
        d = decide(self.condition, action, beliefs, self.state, player, self.roles, chain, decision_id)
        self.trace.record(chain, "adjudication", {
            "decision_id": decision_id, "action": action.kind, "justification": action.justification,
            "allowed": d.allowed, "protected": d.protected, "satisfied_by": d.satisfied_by,
            "promoted": d.promoted, "provisional": d.provisional, "reason": d.reason,
            "promotion_records": d.promotion_records})

        seqs = []
        if d.allowed:
            if d.satisfied_by == "belief_materialized":
                seqs.append(self.state.commit("entitlement_set", player,
                            {"name": "has_royal_writ", "set_by": f"adapter.{self.condition}"}, chain))
            if d.protected:
                seqs.append(self.state.commit("location_changed", player, {"to": "twisting_tunnel"}, chain))
            elif d.provisional:
                seqs.append(self.state.commit("annotation_added", player,
                            {"kind": "investigation_flag", "note": "provisional"}, chain))
        if seqs:
            self.trace.record(chain, "tool_exec", {"action": action.kind, "decision_id": decision_id})
            self.trace.record(chain, "state_mutation", {"seqs": seqs})
            if self.link and d.protected:
                self.link.mirror_move(chain)
        return chain, d
