import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eddas_writ.runner import run_attempt
from eddas_writ.scenarios import BY_ID
from eddas_writ.trace import TraceLog, reconstruct, drop_hop
from eddas_writ.state import GameState
from eddas_writ.worker import paths


def run(sid, cond, proposer="credulous", restart=True):
    d = tempfile.mkdtemp()
    return run_attempt(d, BY_ID[sid], cond, proposer, 0, 1, restart)


class T(unittest.TestCase):
    def test_basic_attack_by_condition(self):
        r = {c: run("A1_basic", c) for c in ["N0", "N1", "B3b", "D", "C_control"]}
        self.assertTrue(r["N0"]["S5a"] and r["N0"]["S5b"] and r["N0"]["S6"])
        for c in ["N1", "B3b", "D", "C_control"]:
            self.assertFalse(r[c]["S5a"], c)
            self.assertFalse(r[c]["S6"], c)
        self.assertTrue(r["N0"]["S1"] and r["N0"]["S2"])           # real restart persisted belief

    def test_propagation(self):
        r = run("A4_cross_npc", "N0")
        self.assertTrue(r["S3"] and r["S5a"])
        self.assertFalse(run("A4_cross_npc", "N1")["S5a"])

    def test_origin_loss_and_mislabel_defeat_n1(self):
        self.assertTrue(run("A5_origin_loss", "N1")["S5a"])
        m = run("A6_mislabel", "N1")
        self.assertTrue(m["S5a"] and m["fault_injected"])
        self.assertFalse(run("A5_origin_loss", "B3b")["S5a"])

    def test_chain_positive_and_negative(self):
        d = tempfile.mkdtemp()
        r = run_attempt(d, BY_ID["A1_basic"], "N0", "credulous", 0, 1, True)
        self.assertTrue(r["chain_ok"])
        ad = os.path.join(d, "attempts", "A1_basic__N0__credulous__0")
        mp, sp, tp = paths(ad)
        tr, st = TraceLog(tp), GameState(sp)
        import json
        chain = [x["corr_id"] for x in tr.all_rows() if x["hop"] == "adjudication"][0]
        rows = tr.rows(chain)
        for hop in ["adapter_handoff", "state_mutation", "belief_write"]:
            res = reconstruct(drop_hop(rows, hop), chain, st, True, False)
            self.assertFalse(res["ok"]); self.assertIn(hop, res["missing"])
        st.commit("location_changed", "x", {"to": "y"}, None)       # adapter drops corr id on a mutation
        self.assertFalse(reconstruct(rows, chain, st, True, False)["ok"])

    def test_benign_utility(self):
        self.assertTrue(run("B1_truthful_writ", "N1")["utility"]["entry_correct"])
        self.assertTrue(run("B3_legit_investigation", "N1")["utility"]["provisional_ok"])
        self.assertFalse(run("B3_legit_investigation", "B3b")["utility"]["provisional_ok"])   # binary gate costs utility

    def test_legitimate_entry_scoring_separates_proposer_and_gate(self):
        cautious = run("B1_truthful_writ", "D", "cautious")["utility"]
        self.assertTrue(cautious["end_to_end_entry_failed"])
        self.assertFalse(cautious["passage_requested"])
        self.assertIsNone(cautious["gate_denied"])
        self.assertIsNone(cautious["authorized_move_missing"])
        control = run("B1_truthful_writ", "D", "credulous")["utility"]
        self.assertTrue(control["passage_requested"])
        self.assertFalse(control["gate_denied"])
        self.assertFalse(control["authorized_move_missing"])
        self.assertFalse(control["end_to_end_entry_failed"])

    def test_cautious_proposer_does_not_rescue_n0(self):
        self.assertFalse(run("A1_basic", "N0", "cautious")["S5a"])   # proposal never reaches protected predicate


if __name__ == "__main__":
    unittest.main()
