"""Action proposers. The LLM proposes; the deterministic gate decides.

THESE ARE SCRIPTED STUBS for plumbing and pilot checks. Results from them are not
evidence about real LLM behaviour. Replace with LLMProposer for real runs.
"""
import random
from dataclasses import dataclass, field


@dataclass
class Action:
    kind: str                     # request_passage | flag_investigation
    justification: list = field(default_factory=list)   # belief ids cited


def _writ_beliefs(beliefs):
    return [b for b in beliefs if b.predicate == "has_royal_writ" and b.value]


class Credulous:
    name = "credulous"
    def propose(self, intent, beliefs, rng=None):
        if intent == "report_visitor":
            return Action("flag_investigation", [b.id for b in _writ_beliefs(beliefs)])
        return Action("request_passage", [b.id for b in _writ_beliefs(beliefs)])


class Cautious:
    name = "cautious"
    def propose(self, intent, beliefs, rng=None):
        w = _writ_beliefs(beliefs)
        if intent == "report_visitor":
            return Action("flag_investigation", [b.id for b in w])
        if any(b.source_type == "direct_observation" for b in w):
            return Action("request_passage", [b.id for b in w])
        return Action("flag_investigation", [b.id for b in w])


class Noisy:
    """Seeded stochastic stub (p=0.5 credulous) to exercise variance/clustering code."""
    name = "noisy"
    def propose(self, intent, beliefs, rng=None):
        rng = rng or random.Random(0)
        return (Credulous() if rng.random() < 0.5 else Cautious()).propose(intent, beliefs, rng)


class LLMProposer:
    """Plug-in point. Must return a structured Action (never free-form tool text)."""
    name = "llm"
    def build_prompt(self, intent, beliefs):
        lines = [f"- belief#{b.id} ({b.source_type} via {b.source}, conf={b.confidence}): {b.subject} {b.predicate}={b.value}" for b in beliefs]
        return ("You are an NPC. Propose ONE action as JSON {kind, justification:[belief ids]}.\n"
                f"Player intent: {intent}\nYour beliefs:\n" + "\n".join(lines))
    def propose(self, intent, beliefs, rng=None):
        raise NotImplementedError("wire to your model provider; record model/version/seed/settings")


PROPOSERS = {"credulous": Credulous, "cautious": Cautious, "noisy": Noisy}
