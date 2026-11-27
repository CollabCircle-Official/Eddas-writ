import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eddas_writ.proposers import OllamaProposer, Action
from eddas_writ.memory import Belief
from eddas_writ.gates import decide


def belief(bid=1):
    return Belief(
        id=bid, npc="edda", subject="pip", predicate="has_royal_writ", value=True,
        source_type="testimony", source="pip", confidence=0.7, origin=None,
        corr_id="corr-1", event_id="e0001", tick=1
    )


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return self.payload


class OllamaProposerTests(unittest.TestCase):
    def _fake_urlopen(self, request, timeout=0):
        if request.full_url.endswith("/api/tags"):
            return FakeResponse({"models": [{"name": "qwen3:4b", "digest": "sha256:test"}]})
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "qwen3:4b")
        self.assertFalse(body["think"])
        self.assertEqual(body["options"]["temperature"], 0)
        self.assertEqual(body["format"]["properties"]["kind"]["enum"], list(OllamaProposer.ACTIONS))
        return FakeResponse({
            "model": "qwen3:4b", "created_at": "2026-11-27T00:00:00Z",
            "message": {"content": json.dumps({"kind": "request_passage", "justification": [1]})},
            "total_duration": 100, "prompt_eval_count": 30, "eval_count": 12
        })

    @patch("eddas_writ.proposers.urllib.request.urlopen")
    def test_valid_structured_proposal_and_audit_metadata(self, mocked):
        mocked.side_effect = self._fake_urlopen
        proposer = OllamaProposer(model="qwen3:4b", seed=0)
        action = proposer.propose("request_passage", [belief()])
        self.assertEqual(action.kind, "request_passage")
        self.assertEqual(action.justification, [1])
        self.assertEqual(action.metadata["model_digest"], "sha256:test")
        self.assertEqual(action.metadata["provider"], "ollama")
        self.assertEqual(action.metadata["eval_count"], 12)
        self.assertIn("prompt_sha256", action.metadata)

    @patch("eddas_writ.proposers.urllib.request.urlopen")
    def test_rejects_unknown_belief_ids(self, mocked):
        def fake(request, timeout=0):
            if request.full_url.endswith("/api/tags"):
                return FakeResponse({"models": [{"name": "qwen3:4b", "digest": "sha256:test"}]})
            return FakeResponse({
                "model": "qwen3:4b",
                "message": {"content": json.dumps({"kind": "request_passage", "justification": [999]})}
            })
        mocked.side_effect = fake
        with self.assertRaisesRegex(ValueError, "not supplied"):
            OllamaProposer().propose("request_passage", [belief()])

    def test_decline_request_never_reaches_protected_movement(self):
        decision = decide(
            "N0", Action("decline_request", []), [], None, "pip", {}, "corr", "decision"
        )
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.protected)
        self.assertEqual(decision.reason, "proposer_declined_to_request_passage")

    @patch("eddas_writ.proposers.urllib.request.urlopen")
    def test_rejects_invalid_action(self, mocked):
        def fake(request, timeout=0):
            if request.full_url.endswith("/api/tags"):
                return FakeResponse({"models": [{"name": "qwen3:4b", "digest": "sha256:test"}]})
            return FakeResponse({
                "model": "qwen3:4b",
                "message": {"content": json.dumps({"kind": "grant_access", "justification": []})}
            })
        mocked.side_effect = fake
        with self.assertRaisesRegex(ValueError, "Unsupported proposed action"):
            OllamaProposer().propose("request_passage", [])


if __name__ == "__main__":
    unittest.main()
