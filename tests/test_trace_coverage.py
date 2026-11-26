from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from eddas_writ.state import GameState
from eddas_writ.trace import reconstruct, required_hops


class TraceCoverageTest(TestCase):
    def test_persisted_events_must_all_be_linked_once(self):
        with TemporaryDirectory() as folder:
            state = GameState(Path(folder) / "state.db")
            chain = "test-chain"
            first = state.commit("location_changed", "player", {"to": "tunnel"}, chain)
            second = state.commit("location_changed", "player", {"to": "gate"}, chain)
            hops = required_hops(False, False, True)
            for seqs, expected in (
                ([first, second], True), ([], False), ([first], False),
                ([first, second, second], False), ([first, second, 999], False),
                (None, False),
            ):
                with self.subTest(seqs=seqs):
                    rows = [{"hop": hop, "payload": {}} for hop in hops]
                    rows[-1]["payload"]["seqs"] = seqs
                    self.assertEqual(reconstruct(rows, chain, state, False, False)["ok"],
                                     expected)
            state.db.close()
