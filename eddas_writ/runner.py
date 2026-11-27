"""Run scenarios x conditions x reps. Each attempt gets its own DB dir; raw logs are never overwritten."""
import argparse, json, os, subprocess, sys, tempfile, time, zlib, shutil
from .gates import CONDITIONS
from .scenarios import SCENARIOS, BY_ID
from . import worker
from .outcomes import score


def _call(args):
    r = subprocess.run([sys.executable, "-m", "eddas_writ.worker", *args], capture_output=True, text=True,
                       cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if r.returncode:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout.strip().splitlines()[-1])


def run_attempt(run_dir, sc, cond, proposer, rep, base_seed, restart=True):
    seed = zlib.crc32(f"{base_seed}|{sc.id}|{cond}|{proposer}|{rep}".encode())
    d = os.path.join(run_dir, "attempts", f"{sc.id}__{cond}__{proposer}__{rep}")
    os.makedirs(d)
    if restart:   # S2: observe and adjudicate in two separate OS processes
        _call(["observe", "--dir", d, "--scenario", sc.id])
        adj = _call(["adjudicate", "--dir", d, "--scenario", sc.id, "--condition", cond,
                     "--proposer", proposer, "--seed", str(seed)])
    else:
        worker.observe(d, sc.id)
        adj = json.loads(json.dumps(worker.adjudicate(d, sc.id, cond, proposer, seed), default=str))
    res = score(d, sc.id, adj)
    return {"scenario": sc.id, "family": sc.family, "kind": sc.kind, "fault_injected": sc.fault_injected,
            "condition": cond, "proposer": proposer, "rep": rep, "seed": seed, "restart": restart,
            "decision": adj["decision"], "model_proposal": adj.get("model_proposal"), **res}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="runs"); p.add_argument("--reps", type=int, default=1)
    p.add_argument("--proposer", default="credulous", choices=["credulous", "cautious", "noisy", "ollama"])
    p.add_argument("--conditions", nargs="*", default=CONDITIONS)
    p.add_argument("--scenarios", nargs="*", choices=[s.id for s in SCENARIOS],
                   help="Optional scenario subset for smoke tests and staged pilots")
    p.add_argument("--seed", type=int, default=42); p.add_argument("--no-restart", action="store_true")
    practice = p.add_mutually_exclusive_group()
    practice.add_argument("--practice-replay", metavar="RECORD")
    practice.add_argument("--practice-live", metavar="RECORD")
    a = p.parse_args(argv)
    if a.practice_replay or a.practice_live:
        from .practice import run_practice
        return run_practice(a.practice_replay or a.practice_live, a.out, live=bool(a.practice_live))
    run_dir = os.path.join(a.out, time.strftime("run_%Y%m%d_%H%M%S"))
    os.makedirs(run_dir)
    rows = []
    selected_scenarios = [BY_ID[sid] for sid in a.scenarios] if a.scenarios else SCENARIOS
    with open(os.path.join(run_dir, "raw.jsonl"), "w", encoding="utf-8") as f:
        for sc in selected_scenarios:
            for cond in a.conditions:
                for rep in range(a.reps):
                    r = run_attempt(run_dir, sc, cond, a.proposer, rep, a.seed, not a.no_restart)
                    rows.append(r); f.write(json.dumps(r) + "\n")
    from .analysis import summarize
    txt = summarize(rows)
    open(os.path.join(run_dir, "summary.md"), "w").write(txt)
    print(txt); print(f"\nraw logs: {run_dir}")


if __name__ == "__main__":
    main()
