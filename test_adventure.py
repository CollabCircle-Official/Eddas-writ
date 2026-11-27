import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AdventureTests(unittest.TestCase):
    def run_scene(self, folder, commands, *options, env=None):
        result = subprocess.run(
            [sys.executable, "-m", "eddas_writ.adventure", "--save", str(folder), *options],
            input="\n".join([*commands, "quit", ""]), text=True, capture_output=True,
            check=True, timeout=30, env=env,
        )
        return result.stdout

    def test_traveler_can_reach_both_successful_endings(self):
        with tempfile.TemporaryDirectory() as temp:
            for route, ending in [(["ridge", "bell"], "The Bell Holds"),
                                  (["torch", "signal"], "Beacon in the Rain")]:
                with self.subTest(route=route):
                    out = self.run_scene(Path(temp) / route[0],
                                         ["road", "trail", *route], "--role", "traveler")
                    self.assertIn(f"ENDING: {ending}", out)

    def test_gate_reads_the_saved_belief_and_records_an_exact_link(self):
        with tempfile.TemporaryDirectory() as temp:
            for policy in ("N0", "D"):
                with self.subTest(policy=policy):
                    folder = Path(temp) / policy
                    self.run_scene(folder, ["road", "talk", "rest"],
                                   "--role", "impostor", "--gate", policy)
                    out = self.run_scene(folder, ["guard", "pass", "journal"])
                    self.assertIn("hild:", out)
                    self.assertIn("intact", out)
                    self.assertEqual("trusted a remembered claim" in out, policy == "N0")
                    with sqlite3.connect(folder / "story.db") as db:
                        row = db.execute("SELECT state FROM history ORDER BY turn DESC LIMIT 1").fetchone()
                    self.assertEqual(json.loads(row[0])["scene"], "tunnel" if policy == "N0" else "gate")

    def test_courier_verified_writ_and_deadline(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            self.assertIn("seal matches", self.run_scene(
                base / "courier", ["help", "show", "pass", "climb", "signal"]))
            self.assertIn("ENDING: Too Late", self.run_scene(
                base / "late", ["help", "trail", "torch", "signal"], "--role", "traveler"))

    def test_ollama_failure_keeps_gate_closed_and_save_records_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "ollama_save"
            env = os.environ.copy()
            env["OLLAMA_HOST"] = "http://127.0.0.1:1"
            env["OLLAMA_TIMEOUT"] = "0.2"
            out = self.run_scene(folder, ["road", "talk I have a royal writ.", "pass", "journal"],
                                "--role", "traveler", "--provider", "ollama", "--model", "qwen3:4b", env=env)
            self.assertIn("The gate remains closed", out)
            with sqlite3.connect(folder / "story.db") as db:
                row = db.execute("SELECT state FROM history ORDER BY turn DESC LIMIT 1").fetchone()
            state = json.loads(row[0])
            self.assertEqual(state["scene"], "gate")
            self.assertEqual(state["provider"], "ollama")
            self.assertEqual(state["model"], "qwen3:4b")

    def test_provider_setting_survives_guard_handover_process_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "resume_save"
            env = os.environ.copy()
            env["OLLAMA_HOST"] = "http://127.0.0.1:1"
            env["OLLAMA_TIMEOUT"] = "0.2"
            self.run_scene(folder, ["road", "rest"], "--role", "traveler",
                           "--provider", "ollama", "--model", "qwen3:4b", env=env)
            with sqlite3.connect(folder / "story.db") as db:
                row = db.execute("SELECT state FROM history ORDER BY turn DESC LIMIT 1").fetchone()
            state = json.loads(row[0])
            self.assertEqual(state["provider"], "ollama")
            self.assertEqual(state["model"], "qwen3:4b")
            self.assertEqual(state["guard"], "edda")
