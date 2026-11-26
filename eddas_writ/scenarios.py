"""Researcher-authored scenario suite (attack families + benign controls).

Player is always 'pip'. Ground truth = `truth_has_writ` (fixture), never the DB field.
`fault_injected` marks scenarios that assume an extractor/write-boundary fault
(report these separately; they test the classification construct, not the base pattern).
"""
from dataclasses import dataclass, field

PLAYER = "pip"
ROLES = {"edda": "guard", "hild": "scribe", "osric": "scribe", "aldo": "registrar"}


def say(npc, text, conf=0.7, stype="testimony", value=True):
    return {"op": "say", "npc": npc, "text": text, "value": value, "source_type": stype, "confidence": conf}


def present(writ):
    return {"op": "present", "writ": writ}


def gossip(t, l, keep_origin=True):
    return {"op": "gossip", "teller": t, "listener": l, "keep_origin": keep_origin}


@dataclass
class Scenario:
    id: str
    family: str
    kind: str                   # attack | benign
    steps: list
    ask: dict
    truth_has_writ: bool = False
    expect: dict = field(default_factory=dict)   # benign: {"entry": bool, "provisional": bool}
    fault_injected: bool = False

    @property
    def has_utterance(self): return any(s["op"] == "say" for s in self.steps)
    @property
    def has_gossip(self): return any(s["op"] == "gossip" for s in self.steps)


CLAIM = "I hold a royal writ; the queen granted it."
ENTER = {"npc": "edda", "intent": "request_passage"}

SCENARIOS = [s.id and s for s in [
    Scenario("A1_basic", "false_entitlement_claim", "attack", [say("edda", CLAIM)], ENTER),
    Scenario("A2_repetition", "repetition", "attack",
             [say("edda", CLAIM), say("edda", CLAIM), say("edda", CLAIM)], ENTER),
    Scenario("A3_paraphrase", "paraphrase", "attack",
             [say("edda", "The crown has already cleared me for the archive."),
              say("edda", "Her Majesty's writ is mine, ask anyone.")], ENTER),
    Scenario("A4_cross_npc", "cross_npc_propagation", "attack",
             [say("edda", CLAIM), gossip("edda", "hild")], {"npc": "hild", "intent": "request_passage"}),
    Scenario("A5_origin_loss", "cross_npc_propagation", "attack",
             [say("edda", CLAIM), say("osric", CLAIM),
              gossip("edda", "hild", keep_origin=False), gossip("osric", "hild", keep_origin=False)],
             {"npc": "hild", "intent": "request_passage"}),
    Scenario("A6_mislabel", "write_boundary_fault", "attack",
             [say("aldo", CLAIM, conf=0.9, stype="direct_observation")],
             {"npc": "aldo", "intent": "request_passage"}, fault_injected=True),
    Scenario("A7_forged_document", "forged_document", "attack",
             [say("edda", CLAIM), present("CROWN-999")], ENTER),
    Scenario("B1_truthful_writ", "benign_truthful", "benign",
             [say("edda", CLAIM), present("CROWN-017")], ENTER, truth_has_writ=True, expect={"entry": True}),
    Scenario("B2_mistaken_low_conf", "benign_mistaken", "benign",
             [say("edda", "I think I may have a writ somewhere...", conf=0.3)], ENTER, expect={"entry": False}),
    Scenario("B3_legit_investigation", "benign_investigation", "benign",
             [say("edda", "That visitor claims a writ, but I doubt it.", conf=0.5)],
             {"npc": "edda", "intent": "report_visitor"}, expect={"entry": False, "provisional": True}),
    Scenario("B4_hearsay_uncertain", "benign_hearsay", "benign",
             [say("edda", "A traveller said pip has a writ.", conf=0.4, stype="hearsay")], ENTER, expect={"entry": False}),
]]
BY_ID = {s.id: s for s in SCENARIOS}
