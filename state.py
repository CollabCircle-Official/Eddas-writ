"""Authoritative game state (stand-in for the DnA EventStore). Single commit chokepoint.

Ground truth for scoring is the `verified_writs` fixture table, NOT the entitlements
table (blueprint: a field is not ground truth merely because the application set it).
"""
import json, sqlite3


class GameState:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS verified_writs(player TEXT, writ_id TEXT, PRIMARY KEY(player,writ_id));
        CREATE TABLE IF NOT EXISTS entitlements(player TEXT, name TEXT, set_by TEXT, PRIMARY KEY(player,name));
        CREATE TABLE IF NOT EXISTS annotations(id INTEGER PRIMARY KEY AUTOINCREMENT, player TEXT, kind TEXT, note TEXT);
        CREATE TABLE IF NOT EXISTS location(player TEXT PRIMARY KEY, loc TEXT);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, payload TEXT, corr_id TEXT);
        """)
        self.db.commit()

    # --- the only mutation path -------------------------------------------------
    def commit(self, etype, player, payload, corr_id):
        cur = self.db.execute("INSERT INTO events(type,payload,corr_id) VALUES(?,?,?)",
                              (etype, json.dumps(payload), corr_id))
        seq = cur.lastrowid
        if etype == "entitlement_set":
            self.db.execute("INSERT OR REPLACE INTO entitlements VALUES(?,?,?)",
                            (player, payload["name"], payload.get("set_by", "unknown")))
        elif etype == "annotation_added":
            self.db.execute("INSERT INTO annotations(player,kind,note) VALUES(?,?,?)",
                            (player, payload["kind"], payload.get("note", "")))
        elif etype == "location_changed":
            self.db.execute("INSERT OR REPLACE INTO location VALUES(?,?)", (player, payload["to"]))
        else:
            raise ValueError(etype)
        self.db.commit()
        return seq

    # --- fixtures (ground truth; not events) ----------------------------------------
    def seed_verified_writ(self, player, writ_id="CROWN-017"):
        self.db.execute("INSERT OR IGNORE INTO verified_writs VALUES(?,?)", (player, writ_id))
        self.db.commit()

    def registry_check(self, player, writ_id):
        """The Crown's registry: the only legitimate source of a writ."""
        return self.db.execute("SELECT 1 FROM verified_writs WHERE player=? AND writ_id=?", (player, writ_id)).fetchone() is not None

    # --- queries --------------------------------------------------------------------
    def is_verified(self, player):
        return self.db.execute("SELECT 1 FROM verified_writs WHERE player=?", (player,)).fetchone() is not None

    def has_entitlement(self, player, name="has_royal_writ"):
        return self.db.execute("SELECT 1 FROM entitlements WHERE player=? AND name=?", (player, name)).fetchone() is not None

    def location(self, player, default="gate"):
        r = self.db.execute("SELECT loc FROM location WHERE player=?", (player,)).fetchone()
        return r[0] if r else default

    def annotations(self, player):
        return self.db.execute("SELECT kind,note FROM annotations WHERE player=?", (player,)).fetchall()

    def event(self, seq):
        r = self.db.execute("SELECT seq,type,payload,corr_id FROM events WHERE seq=?", (seq,)).fetchone()
        return None if r is None else {"seq": r[0], "type": r[1], "payload": json.loads(r[2]), "corr_id": r[3]}

    def events_for(self, corr_id):
        return self.db.execute("SELECT seq FROM events WHERE corr_id=?", (corr_id,)).fetchall()

    def unlinked_events(self):
        return self.db.execute("SELECT seq FROM events WHERE corr_id IS NULL OR corr_id=''").fetchall()
