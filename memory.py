"""NPC persistent belief store (stand-in for Thespis; swap via the same interface).

Mirrors the audit's observed behaviour: evidence has source, event id, confidence,
optional origin; `story` = origin or source (Evidence.story in Thespis).
Confidence is NOT trust. No trust/authority field exists here on purpose.
"""
import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass
class Belief:
    id: int
    npc: str
    subject: str
    predicate: str
    value: bool
    source_type: str      # direct_observation | testimony | hearsay | inference | player_claim
    source: str
    confidence: float
    origin: Optional[str]
    corr_id: str
    event_id: str
    tick: int

    @property
    def story(self):
        return self.origin or self.source


COLS = "id,npc,subject,predicate,value,source_type,source,confidence,origin,corr_id,event_id,tick"


class BeliefStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS beliefs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, npc TEXT, subject TEXT, predicate TEXT,
            value INTEGER, source_type TEXT, source TEXT, confidence REAL, origin TEXT,
            corr_id TEXT NOT NULL, event_id TEXT, tick INTEGER)""")
        self.db.commit()

    def _next_event(self):
        n = self.db.execute("SELECT COUNT(*) FROM beliefs").fetchone()[0]
        return f"e{n + 1:04d}"

    def _insert(self, **k):
        cur = self.db.execute(
            "INSERT INTO beliefs(npc,subject,predicate,value,source_type,source,confidence,origin,corr_id,event_id,tick)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (k["npc"], k["subject"], k["predicate"], int(k["value"]), k["source_type"], k["source"],
             k["confidence"], k["origin"], k["corr_id"], self._next_event(), k["tick"]))
        self.db.commit()
        return self.get(cur.lastrowid)

    def get(self, bid):
        r = self.db.execute(f"SELECT {COLS} FROM beliefs WHERE id=?", (bid,)).fetchone()
        return self._row(r)

    @staticmethod
    def _row(r):
        return Belief(r[0], r[1], r[2], r[3], bool(r[4]), r[5], r[6], r[7], r[8], r[9], r[10], r[11])

    def observe(self, npc, subject, predicate, value, source_type, source, confidence, corr_id, tick, origin=None):
        return self._insert(npc=npc, subject=subject, predicate=predicate, value=value,
                            source_type=source_type, source=source, confidence=confidence,
                            origin=origin, corr_id=corr_id, tick=tick)

    def for_npc(self, npc, predicate=None, subject=None):
        q, a = f"SELECT {COLS} FROM beliefs WHERE npc=?", [npc]
        if predicate:
            q += " AND predicate=?"; a.append(predicate)
        if subject:
            q += " AND subject=?"; a.append(subject)
        return [self._row(r) for r in self.db.execute(q + " ORDER BY id", a).fetchall()]

    def all(self):
        return [self._row(r) for r in self.db.execute(f"SELECT {COLS} FROM beliefs ORDER BY id").fetchall()]

    def gossip(self, teller, listener, tick, keep_origin=True, decay=0.8):
        """Teller repeats its beliefs to listener as hearsay. corr_id is preserved.
        keep_origin=False models the audit's observation that some paths supply no
        explicit origin, so the listener's story becomes the teller."""
        out = []
        for b in self.for_npc(teller):
            out.append(self.observe(
                listener, b.subject, b.predicate, b.value, "hearsay", teller,
                round(b.confidence * decay, 3), b.corr_id, tick,
                origin=(b.origin or b.source) if keep_origin else None))
        return out
