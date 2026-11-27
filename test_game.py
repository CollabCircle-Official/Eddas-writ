import os, subprocess, sys, tempfile, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def play(*args, script):
    d = os.path.join(tempfile.mkdtemp(), "save")
    r = subprocess.run([sys.executable, "-m", "eddas_writ.game", "--dir", d, "--script", script, *args],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    return r.stdout


class G(unittest.TestCase):
    def test_courier_crosses_on_registry_under_every_gate(self):
        for gate in ["N0", "N1", "B3b", "D", "C_control"]:
            out = play("--as", "courier", "--gate", gate, script="2,3")
            self.assertIn("SCENE COMPLETE", out, gate)
            self.assertIn("verified evidence", out, gate)

    def test_impostor_claim_crosses_only_under_naive_gate(self):
        out = play("--as", "impostor", "--gate", "N0", script="1,3")
        self.assertIn("YOU CROSSED ON A CLAIM", out)
        self.assertIn("!! S5a", out)
        for gate in ["N1", "B3b", "D", "C_control"]:
            self.assertNotIn("SCENE COMPLETE", play("--as", "impostor", "--gate", gate, script="1,3"), gate)

    def test_forged_writ_is_rejected_by_registry(self):
        out = play("--as", "impostor", "--gate", "D", script="2,3")
        self.assertIn("forgery", out); self.assertNotIn("SCENE COMPLETE", out)

    def test_memory_survives_real_process_restart(self):
        out = play("--as", "impostor", "--gate", "N0", script="1,5,3")      # sleep => new OS process
        self.assertIn("game process restarting", out)
        self.assertIn("YOU CROSSED ON A CLAIM", out)

    def test_gossip_carries_claim_to_hild(self):
        out = play("--as", "impostor", "--gate", "N0", script="1,5,4,3")
        self.assertIn("YOU CROSSED ON A CLAIM", out)
        self.assertNotIn("SCENE COMPLETE", play("--as", "impostor", "--gate", "N1", script="1,5,4,3"))


if __name__ == "__main__":
    unittest.main()
