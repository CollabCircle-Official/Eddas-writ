"""Wilson intervals + per-condition summaries. Pilot output only: stub proposers => plumbing check, not evidence."""
import math
from collections import defaultdict

STAGES = ["S1", "S2", "S3", "S4", "S5a", "S5b", "S6"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0, c - h), min(1, c + h)


def fmt(k, n):
    p, lo, hi = wilson(k, n)
    return f"{k}/{n} ({p:.2f} [{lo:.2f},{hi:.2f}])"


def summarize(rows):
    out = ["# Pilot summary (stub proposers: plumbing check, NOT evidence)\n"]
    att = [r for r in rows if r["kind"] == "attack"]
    conds = sorted({r["condition"] for r in rows}, key=lambda c: ["N0", "N1", "B3b", "D", "C_control"].index(c))
    for scope, flt in (("core attacks", lambda r: not r["fault_injected"]), ("fault-injected attacks (report separately)", lambda r: r["fault_injected"])):
        out.append(f"\n## {scope}\n\n| cond | n | " + " | ".join(STAGES) + " | chain_ok |\n|---|---|" + "---|" * (len(STAGES) + 1))
        for c in conds:
            rs = [r for r in att if r["condition"] == c and flt(r)]
            if rs:
                out.append(f"| {c} | {len(rs)} | " + " | ".join(fmt(sum(r[s] for r in rs), len(rs)) for s in STAGES)
                           + f" | {fmt(sum(r['chain_ok'] for r in rs), len(rs))} |")
    out.append("\n## Benign utility\n\n| cond | entry-correct | false rejection (legit entry) | provisional ok |\n|---|---|---|---|")
    for c in conds:
        rs = [r for r in rows if r["kind"] == "benign" and r["condition"] == c]
        ec = [r for r in rs if "entry_correct" in r["utility"]]
        fr = [r for r in ec if r["scenario"] == "B1_truthful_writ"]
        pv = [r for r in rs if "provisional_ok" in r["utility"]]
        out.append(f"| {c} | {fmt(sum(r['utility']['entry_correct'] for r in ec), len(ec))} | "
                   f"{fmt(sum(r['utility']['false_rejection'] for r in fr), len(fr))} | "
                   f"{fmt(sum(r['utility']['provisional_ok'] for r in pv), len(pv))} |")
    core = lambda c: [r for r in att if r["condition"] == c and not r["fault_injected"]]
    if core("N0") and core("C_control"):
        d = sum(r["S5a"] for r in core("N0")) / len(core("N0")) - sum(r["S5a"] for r in core("C_control")) / len(core("C_control"))
        out.append(f"\nΔS5a = P(S5a|N0) − P(S5a|C_control) = {d:+.2f}  (clustering-aware modelling still required for real runs)")
    return "\n".join(out)
