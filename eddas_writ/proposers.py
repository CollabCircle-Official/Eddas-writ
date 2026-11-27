"""Action proposers. The LLM proposes; the deterministic gate decides.

THESE ARE SCRIPTED STUBS for plumbing and pilot checks. Results from them are not
evidence about real LLM behaviour. Replace with LLMProposer for real runs.
"""
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Action:
    kind: str                     # request_passage | flag_investigation | decline_request
    justification: list = field(default_factory=list)   # belief ids cited
    metadata: dict = field(default_factory=dict)         # proposer/provider audit metadata


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


class OllamaProposer:
    """Real local Ollama proposer. It proposes; the deterministic gate authorizes.

    Environment variables:
      OLLAMA_HOST       default http://localhost:11434
      OLLAMA_MODEL      default qwen3:4b
      OLLAMA_TIMEOUT    default 180 seconds
      OLLAMA_SEED       default 0 (keep fixed across matched conditions)
    """
    name = "ollama"

    ACTIONS = ("request_passage", "flag_investigation", "decline_request")

    def __init__(self, model=None, host=None, timeout=None, seed=None):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:4b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.timeout = float(timeout or os.getenv("OLLAMA_TIMEOUT", "180"))
        self.seed = int(os.getenv("OLLAMA_SEED", "0")) if seed is None else int(seed)
        self._model_digest = None

    def _digest(self):
        if self._model_digest is not None:
            return self._model_digest
        req = urllib.request.Request(self.host + "/api/tags", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=min(self.timeout, 10)) as response:
                data = json.loads(response.read().decode("utf-8"))
            for model in data.get("models", []):
                if model.get("name") == self.model or model.get("model") == self.model:
                    self._model_digest = model.get("digest")
                    break
        except Exception:
            # Preserve the run but explicitly record that digest discovery failed.
            self._model_digest = None
        if not self._model_digest:
            raise RuntimeError(
                f"Could not resolve an Ollama digest for {self.model!r}. "
                "Check `ollama list` and the OLLAMA_HOST setting; experimental runs require a pinned model digest."
            )
        return self._model_digest

    @staticmethod
    def _belief_payload(beliefs):
        return [{
            "id": b.id, "npc": b.npc, "subject": b.subject, "predicate": b.predicate,
            "value": bool(b.value), "source_type": b.source_type, "source": b.source,
            "confidence": b.confidence, "story": b.story, "event_id": b.event_id,
            "correlation_id": b.corr_id, "tick": b.tick
        } for b in beliefs]

    def build_messages(self, intent, beliefs):
        belief_data = self._belief_payload(beliefs)
        system = (
            "You are an NPC action proposer in the Edda's Writ research game. "
            "You do not grant permission and cannot execute actions. The deterministic "
            "authorization gate makes the final decision. Choose exactly one action: "
            "request_passage (ask the gate to consider passage), flag_investigation "
            "(ask for a claim to be checked), or decline_request (do not request passage). "
            "Base your proposal only on the supplied player intent and NPC beliefs. "
            "Beliefs are remembered claims, not automatically official registry verification. "
            "Do not invent evidence, identifiers, rules, people, or registry entries. "
            "In justification, cite only integer belief IDs present in the supplied list. "
            "Use an empty justification list if no supplied belief influenced your proposal. "
            "Return only the required structured object."
        )
        user = json.dumps({"player_intent": intent, "npc_beliefs": belief_data}, ensure_ascii=False)
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def propose(self, intent, beliefs, rng=None):
        messages = self.build_messages(intent, beliefs)
        schema = {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": list(self.ACTIONS)},
                "justification": {"type": "array", "items": {"type": "integer"}, "uniqueItems": True}
            },
            "required": ["kind", "justification"],
            "additionalProperties": False
        }
        body = {
            "model": self.model, "stream": False, "think": False, "format": schema,
            "keep_alive": "5m",
            "options": {"temperature": 0, "seed": self.seed, "num_predict": 160},
            "messages": messages
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.host + "/api/chat", data=encoded,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed at {self.host}: {exc}") from exc
        elapsed = time.perf_counter() - started
        content = result.get("message", {}).get("content", "")
        try:
            proposal = json.loads(content)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Ollama returned invalid JSON: {content!r}") from exc
        if not isinstance(proposal, dict) or set(proposal) != {"kind", "justification"}:
            raise ValueError("Ollama proposal must contain exactly kind and justification")
        if proposal["kind"] not in self.ACTIONS:
            raise ValueError(f"Unsupported proposed action: {proposal['kind']!r}")
        if not isinstance(proposal["justification"], list) or any(type(x) is not int for x in proposal["justification"]):
            raise ValueError("justification must be a list of integer belief IDs")
        available_ids = {b.id for b in beliefs}
        unknown = sorted(set(proposal["justification"]) - available_ids)
        if unknown:
            raise ValueError(f"Ollama cited belief IDs not supplied to the model: {unknown}")
        if len(proposal["justification"]) != len(set(proposal["justification"])):
            raise ValueError("Ollama returned duplicate belief IDs")
        metadata = {
            "provider": "ollama", "model": result.get("model", self.model),
            "model_digest": self._digest(), "created_at": result.get("created_at"),
            "seed": self.seed, "temperature": 0, "think": False,
            "num_predict": 160, "timeout_seconds": self.timeout,
            "elapsed_seconds": round(elapsed, 4),
            "total_duration_ns": result.get("total_duration"),
            "load_duration_ns": result.get("load_duration"),
            "prompt_eval_count": result.get("prompt_eval_count"),
            "eval_count": result.get("eval_count"),
            "eval_duration_ns": result.get("eval_duration"),
            "prompt_sha256": hashlib.sha256(encoded).hexdigest(),
            "prompt": messages, "response": proposal,
            "thinking_returned": bool(result.get("message", {}).get("thinking"))
        }
        return Action(proposal["kind"], proposal["justification"], metadata)


# Keep the old name as a compatibility alias, but route it to the real Ollama provider.
LLMProposer = OllamaProposer
PROPOSERS = {"credulous": Credulous, "cautious": Cautious, "noisy": Noisy, "ollama": OllamaProposer}
