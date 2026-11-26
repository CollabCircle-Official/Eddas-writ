"""Correlation-ID trace log + chain reconstruction (blueprint section 8 / P3).

Rule: the same corr_id must survive every hop. Missing links are NEVER repaired
by timestamp or text matching; they are reported as a broken chain.
"""
import json, sqlite3, time, uuid


def new_corr_id() -> str:
    return str(uuid.uuid4())


def field(value=None, status="populated"):
    """Every promotion-record field carries a status:
    populated | not_applicable | not_recorded | unknown."""
    return {"value": value, "status": status}


class TraceLog:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS trace(
            id INTEGER PRIMARY KEY AUTOINCREMENT, corr_id TEXT NOT NULL,
            hop TEXT NOT NULL, payload TEXT NOT NULL, ts REAL NOT NULL)""")
        self.db.commit()

    def record(self, corr_id, hop, payload):
        self.db.execute("INSERT INTO trace(corr_id,hop,payload,ts) VALUES(?,?,?,?)",
                        (corr_id, hop, json.dumps(payload, default=str), time.time()))
        self.db.commit()

    def rows(self, corr_id):
        cur = self.db.execute("SELECT hop,payload FROM trace WHERE corr_id=? ORDER BY id", (corr_id,))
        return [{"hop": h, "payload": json.loads(p)} for h, p in cur.fetchall()]

    def all_rows(self):
        cur = self.db.execute("SELECT corr_id,hop,payload FROM trace ORDER BY id")
        return [{"corr_id": c, "hop": h, "payload": json.loads(p)} for c, h, p in cur.fetchall()]


def required_hops(has_utterance, propagated, committed):
    r = ["utterance", "belief_write"] if has_utterance else []
    if propagated:
        r.append("propagation")
    r += ["belief_retrieve", "adapter_handoff", "adjudication"]
    if committed:
        r += ["tool_exec", "state_mutation"]
    return r


def reconstruct(rows, corr_id, state, has_utterance, propagated):
    """Return {ok, missing, problems}. `committed` comes from the STATE store
    (ground truth), not from the trace, so a dropped hop cannot hide itself."""
    seen = {r["hop"] for r in rows}
    committed = {seq for (seq,) in state.events_for(corr_id)}
    missing = [h for h in required_hops(has_utterance, propagated, bool(committed)) if h not in seen]
    problems = []
    linked = set()
    for row in rows:
        if row["hop"] != "state_mutation":
            continue
        seqs = row["payload"].get("seqs")
        if not isinstance(seqs, list) or not seqs:
            problems.append("state_mutation_missing_sequences")
            continue
        for seq in seqs:
            if type(seq) is not int or seq not in committed:
                problems.append(f"state_link_mismatch seq={seq}")
            elif seq in linked:
                problems.append(f"duplicate_state_link seq={seq}")
            else:
                linked.add(seq)
    for seq in sorted(committed - linked):
        problems.append(f"unreferenced_state_event seq={seq}")
    if state.unlinked_events():
        problems.append("unlinked_state_events")
    return {"ok": not missing and not problems, "missing": missing, "problems": problems}


def drop_hop(rows, hop):
    """Negative-probe helper: simulate an adapter that omits one hop."""
    return [r for r in rows if r["hop"] != hop]
