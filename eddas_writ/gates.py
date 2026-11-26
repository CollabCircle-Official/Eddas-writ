"""Authorization gates / experimental conditions.

N0        naive: predicate satisfied by belief confidence (no trust field). [reference
          implementation of the integration pattern under test; whether real integrations
          do this is what the audit must establish, not assume]
N1        explicit source/evidence classification; promoted classes may create entitlement.
B3b       binary provenance: beliefs never reach protected predicate; any action citing
          beliefs is denied (no provisional state).
D         pure deterministic: entitlement table only; proposals' beliefs ignored.
C_control N0 with the promotion/materialization pathway disabled (blueprint C-control).
P-behaviour (provisional annotation allowed, entitlement denied) is what N1 does for
unpromoted beliefs.
"""
from dataclasses import dataclass, field
from .trace import field as f

CONDITIONS = ["N0", "N1", "B3b", "D", "C_control"]
AUTH_ROLES = {"registrar"}


@dataclass
class Decision:
    condition: str
    action: str
    protected: bool = False
    allowed: bool = False
    satisfied_by: str = None            # state_entitlement | belief_materialized | None
    promoted: list = field(default_factory=list)   # belief ids
    provisional: bool = False
    reason: str = ""
    promotion_records: list = field(default_factory=list)


def classify_n1(b, same_claim, roles):
    if b.source_type == "direct_observation" and roles.get(b.npc) in AUTH_ROLES and b.confidence >= 0.7:
        return "verified_observation"
    stories = {x.story for x in same_claim}
    if b.source_type in ("hearsay", "testimony") and len(stories) >= 2:
        return "corroborated"
    return "provisional"


def _record(corr, b, prior, new, authorizer, decision_id, cited):
    return {
        "correlation_id": f(corr),
        "originating_source": f(f"{b.source_type}:{b.source}"),
        "observing_npc": f(b.npc),
        "evidence_cited": f(cited),
        "prior_trust": f(prior, "populated" if prior else "not_applicable"),
        "new_trust": f(new, "populated" if new else "not_applicable"),
        "authorizing_component": f(authorizer),
        "consuming_decision_id": f(decision_id),
    }


def decide(cond, action, beliefs, state, player, roles, chain_id, decision_id):
    d = Decision(condition=cond, action=action.kind)
    writ = [b for b in beliefs if b.predicate == "has_royal_writ" and b.value and b.subject == player]

    if action.kind == "flag_investigation":
        if cond == "B3b" and action.justification:
            d.reason = "binary_gate_denies_action_citing_untrusted_belief"
        else:
            d.allowed, d.provisional, d.reason = True, True, "discretionary_provisional_ok"
        return d

    d.protected = True
    if state.has_entitlement(player):
        d.allowed, d.satisfied_by, d.reason = True, "state_entitlement", "authoritative_entitlement_present"
        return d
    if cond in ("B3b", "D", "C_control"):
        d.reason = "no_authoritative_entitlement"
        return d

    if cond == "N0":
        hit = [b for b in writ if b.confidence >= 0.5]
        if hit:
            d.allowed, d.satisfied_by, d.promoted = True, "belief_materialized", [b.id for b in hit]
            d.reason = "belief_confidence_treated_as_evidence"
            d.promotion_records = [_record(chain_id, b, None, "authoritative", "adapter.N0", decision_id, [b.event_id]) for b in hit]
        else:
            d.reason = "belief_below_threshold"
        return d

    if cond == "N1":
        promoted = []
        for b in writ:
            cls = classify_n1(b, writ, roles)
            if cls in ("verified_observation", "corroborated"):
                promoted.append((b, cls))
        if promoted:
            d.allowed, d.satisfied_by = True, "belief_materialized"
            d.promoted = [b.id for b, _ in promoted]
            d.reason = "n1_classification_promoted_belief"
            d.promotion_records = [_record(chain_id, b, "provisional", c, "adapter.N1", decision_id, [b.event_id]) for b, c in promoted]
        else:
            d.reason = "n1_all_beliefs_provisional"
        return d
    raise ValueError(cond)
