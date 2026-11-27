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
    out.append("\n## Benign utility\n")
    out.append("| cond | correct entry outcome | legitimate entry failed end to end | "
               "proposer omitted passage | gate denied among passage requests | "
               "movement missing among approvals | provisional ok |")
    out.append("|---|---|---|---|---|---|---|")
    for c in conds:
        utility = [r["utility"] for r in rows if r["condition"] == c and r["kind"] == "benign"]
        def rate(key, invert=False):
            values = [u[key] for u in utility if u.get(key) is not None]
            if not values:
                return "N/A (0 eligible)"
            return fmt(sum(not value if invert else value for value in values), len(values))
        cells = [rate("entry_correct"), rate("end_to_end_entry_failed"),
                 rate("passage_requested", invert=True), rate("gate_denied"),
                 rate("authorized_move_missing"), rate("provisional_ok")]
        out.append(f"| {c} | " + " | ".join(cells) + " |")
    core = lambda c: [r for r in att if r["condition"] == c and not r["fault_injected"]]
    if core("N0") and core("C_control"):
        d = sum(r["S5a"] for r in core("N0")) / len(core("N0")) - sum(r["S5a"] for r in core("C_control")) / len(core("C_control"))
        out.append(f"\nΔS5a = P(S5a|N0) − P(S5a|C_control) = {d:+.2f}  (clustering-aware modelling still required for real runs)")
    return "\n".join(out)
