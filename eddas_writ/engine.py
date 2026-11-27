from __future__ import annotations
import json, os, sqlite3, urllib.request, urllib.error, hashlib, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACTIONS = {"allow", "deny", "investigate"}
SCENES = {
    "ford": ("THE FLOODED FORD", "Rain lashes the valley. A child is stranded beside the flooded crossing."),
    "gate": ("THE CROWN GATE", "Edda guards the old stone gate. Hild keeps the Crown ledger beneath a lantern."),
    "tunnel": ("THE UNDERPASS", "Water runs through the passage. An old signal lamp hangs from the wall."),
    "shelter": ("THE SHEPHERD'S SHELTER", "A dry shelter overlooks the ridge road. A spare torch rests by the hearth."),
    "tower": ("THE WATCHTOWER", "The valley is disappearing beneath the flood. The warning beacon waits above."),
    "ending": ("THE END OF THE JOURNEY", "Dawn breaks over the vale. The choices made at the gate will be remembered."),
}
ROLES = {
    "courier": "You are a Crown courier carrying a genuine writ registered in the ledger.",
    "traveler": "You are an ordinary traveler. You have no royal writ, but may use the public ridge trail.",
    "impostor": "You carry a forged writ and hope the guards will accept your story.",
}
POLICIES = {
    "strict": "Only registry-verified writs authorize protected passage.",
    "evidence": "Registry evidence authorizes passage; testimony can trigger investigation but never authorization.",
    "naive_demo": "Demonstration-only unsafe policy: a remembered claim may authorize passage. Never use in production.",
}
VALID_WRIT = "WRIT-ROYAL-1042"
FORGED_WRIT = "WRIT-ROYAL-9999"

@dataclass
class Proposal:
    action: str
    reason: str
    evidence_ids: list[str]
    provider: str = "rules"
    model: str = ""
    latency_ms: int = 0
    raw: str = ""

class Store:
    def __init__(self, folder: Path):
        folder.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(folder / "eddas_writ.db")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS game_state (
          id INTEGER PRIMARY KEY CHECK(id=1), role TEXT NOT NULL, policy TEXT NOT NULL,
          scene TEXT NOT NULL, hours INTEGER NOT NULL, rescued INTEGER NOT NULL DEFAULT 0,
          lamp INTEGER NOT NULL DEFAULT 0, guard TEXT NOT NULL DEFAULT 'edda',
          inventory TEXT NOT NULL DEFAULT '[]', completed INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS evidence (
          evidence_id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject TEXT NOT NULL,
          claim TEXT NOT NULL, value TEXT NOT NULL, source TEXT NOT NULL,
          confidence REAL NOT NULL, verified INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS memories (
          memory_id INTEGER PRIMARY KEY AUTOINCREMENT, npc TEXT NOT NULL,
          speaker TEXT NOT NULL, content TEXT NOT NULL, source_type TEXT NOT NULL,
          source_id TEXT, confidence REAL NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL,
          actor TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS decisions (
          decision_id INTEGER PRIMARY KEY AUTOINCREMENT, npc TEXT NOT NULL,
          proposed_action TEXT NOT NULL, final_action TEXT NOT NULL, allowed INTEGER NOT NULL,
          reason TEXT NOT NULL, evidence_ids TEXT NOT NULL, policy TEXT NOT NULL,
          provider TEXT NOT NULL, model TEXT NOT NULL, latency_ms INTEGER NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        self.db.commit()

    def event(self, kind, actor, detail):
        self.db.execute("INSERT INTO events(event_type,actor,detail) VALUES(?,?,?)",
                        (kind, actor, json.dumps(detail, ensure_ascii=False)))
        self.db.commit()

    def add_memory(self, npc, speaker, content, source_type="testimony", source_id=None, confidence=.65):
        cur = self.db.execute("""INSERT INTO memories(npc,speaker,content,source_type,source_id,confidence)
                                 VALUES(?,?,?,?,?,?)""",
                              (npc, speaker, content, source_type, source_id, confidence))
        self.db.commit()
        self.event("memory_created", npc, {"memory_id": cur.lastrowid, "speaker": speaker,
                                           "content": content, "source_type": source_type,
                                           "source_id": source_id})
        return cur.lastrowid

    def memories(self, npc=None, limit=12):
        if npc:
            rows = self.db.execute("SELECT * FROM memories WHERE npc=? ORDER BY memory_id DESC LIMIT ?", (npc, limit))
        else:
            rows = self.db.execute("SELECT * FROM memories ORDER BY memory_id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows.fetchall()]

    def evidence(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM evidence ORDER BY created_at,evidence_id")]

    def add_evidence(self, evidence_id, kind, subject, claim, value, source, confidence, verified=False):
        self.db.execute("""INSERT OR REPLACE INTO evidence
          (evidence_id,kind,subject,claim,value,source,confidence,verified) VALUES(?,?,?,?,?,?,?,?)""",
          (evidence_id, kind, subject, claim, value, source, confidence, int(verified)))
        self.db.commit()
        self.event("evidence_added", "world", {"evidence_id": evidence_id, "kind": kind,
                                               "source": source, "verified": bool(verified)})

    def state(self):
        row = self.db.execute("SELECT * FROM game_state WHERE id=1").fetchone()
        return dict(row) if row else None

    def save_state(self, **values):
        old = self.state() or {}
        old.update(values)
        fields = ["role","policy","scene","hours","rescued","lamp","guard","inventory","completed"]
        payload = {k: old[k] for k in fields}
        payload["updated_at"] = "CURRENT_TIMESTAMP"
        if self.state():
            self.db.execute("""UPDATE game_state SET role=?,policy=?,scene=?,hours=?,rescued=?,lamp=?,
                               guard=?,inventory=?,completed=?,updated_at=CURRENT_TIMESTAMP WHERE id=1""",
                tuple(payload[k] for k in fields))
        else:
            self.db.execute("""INSERT INTO game_state(id,role,policy,scene,hours,rescued,lamp,guard,inventory,completed)
                               VALUES(1,?,?,?,?,?,?,?,?,?)""", tuple(payload[k] for k in fields))
        self.db.commit()

    def close(self):
        self.db.close()

class OllamaProposer:
    """Untrusted model proposer. Its output is never an authorization decision."""
    def __init__(self, model=None, host=None, timeout=75):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen3:4b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.timeout = timeout

    def propose(self, npc, player_text, memories, evidence):
        allowed_ids = {e["evidence_id"] for e in evidence}
        system = (
            "You are an action proposer in a fictional game. Return only JSON with keys "
            "proposed_action, reason, evidence_ids. proposed_action must be allow, deny, or investigate. "
            "Never invent evidence IDs. Testimony is not registry verification. You cannot authorize "
            "protected movement; the deterministic game gate decides that."
        )
        context = {
            "npc": npc, "player_statement": player_text,
            "memories": [{"speaker":m["speaker"],"content":m["content"],
                          "source_type":m["source_type"],"source_id":m["source_id"],
                          "confidence":m["confidence"]} for m in memories],
            "available_evidence": [{"evidence_id":e["evidence_id"],"kind":e["kind"],
                                    "claim":e["claim"],"value":e["value"],
                                    "source":e["source"],"verified":bool(e["verified"])} for e in evidence]
        }
        body = {"model": self.model, "stream": False, "think": False, "format": {
            "type":"object","properties":{
                "proposed_action":{"type":"string","enum":["allow","deny","investigate"]},
                "reason":{"type":"string"},
                "evidence_ids":{"type":"array","items":{"type":"string"}}
            },"required":["proposed_action","reason","evidence_ids"],"additionalProperties":False
        }, "messages":[{"role":"system","content":system},
                       {"role":"user","content":json.dumps(context,ensure_ascii=False)}],
            "options":{"temperature":0,"seed":0}}
        raw = ""
        start = time.perf_counter()
        req = urllib.request.Request(self.host + "/api/chat", data=json.dumps(body).encode(),
                                     headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        raw = result.get("message",{}).get("content","")
        parsed = json.loads(raw)
        action = parsed.get("proposed_action")
        ids = parsed.get("evidence_ids")
        if action not in ACTIONS or not isinstance(ids,list) or any(not isinstance(x,str) for x in ids):
            raise ValueError("Ollama returned an invalid proposal schema")
        unknown = set(ids) - allowed_ids
        if unknown:
            raise ValueError("Ollama cited unknown evidence IDs: " + ", ".join(sorted(unknown)))
        return Proposal(action, str(parsed.get("reason","")), ids, "ollama", self.model,
                        int((time.perf_counter()-start)*1000), raw)

class RulesProposer:
    def propose(self, npc, player_text, memories, evidence):
        verified = [e["evidence_id"] for e in evidence if e["verified"] and e["kind"]=="royal_writ"]
        if verified:
            return Proposal("allow","A registry-verified writ is available.",verified)
        if memories:
            return Proposal("investigate","A remembered claim exists but is not registry verification.",[])
        return Proposal("deny","No verified writ or supporting evidence is available.",[])

class AuthorizationGate:
    def __init__(self, store: Store, policy: str):
        self.store, self.policy = store, policy

    def decide(self, npc, proposal: Proposal):
        evidence = {e["evidence_id"]:e for e in self.store.evidence()}
        unknown_ids = sorted(set(proposal.evidence_ids) - set(evidence))
        # Fail closed: unknown or fabricated identifiers can never reach an authorization rule.
        if unknown_ids:
            allowed = False
            reason = "Proposal cited unknown evidence identifiers: " + ", ".join(unknown_ids)
            self.store.db.execute("""INSERT INTO decisions
              (npc,proposed_action,final_action,allowed,reason,evidence_ids,policy,provider,model,latency_ms)
              VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (npc,proposal.action,"deny",0,reason,json.dumps(proposal.evidence_ids),
               self.policy,proposal.provider,proposal.model,proposal.latency_ms))
            self.store.db.commit()
            self.store.event("gate_decision",npc,{"proposal":proposal.action,"final":"deny",
                             "allowed":False,"reason":reason,"evidence_ids":proposal.evidence_ids,
                             "policy":self.policy,"provider":proposal.provider})
            return False, reason
        cited = [evidence[x] for x in proposal.evidence_ids]
        verified = any(e["verified"] and e["kind"]=="royal_writ" for e in cited)
        if self.policy in ("strict","evidence"):
            allowed = verified
            final = "allow" if allowed else ("investigate" if proposal.action=="investigate" else "deny")
            reason = "Registry-verified writ satisfies the gate." if allowed else (
                "No cited registry-verified writ. Model proposal cannot grant passage.")
        else:
            # Deliberately unsafe condition retained only for controlled research comparison.
            remembered_claim = bool(self.store.memories(npc))
            allowed = verified or (proposal.action=="allow" and remembered_claim)
            final = "allow" if allowed else proposal.action
            reason = ("DEMO ONLY: naive policy trusted a remembered claim." if allowed and not verified
                      else "Verified writ accepted." if verified else "Naive demonstration policy did not approve.")
        self.store.db.execute("""INSERT INTO decisions
          (npc,proposed_action,final_action,allowed,reason,evidence_ids,policy,provider,model,latency_ms)
          VALUES(?,?,?,?,?,?,?,?,?,?)""",
          (npc,proposal.action,final,int(allowed),reason,json.dumps(proposal.evidence_ids),
           self.policy,proposal.provider,proposal.model,proposal.latency_ms))
        self.store.db.commit()
        self.store.event("gate_decision",npc,{"proposal":proposal.action,"final":final,
                         "allowed":allowed,"reason":reason,"evidence_ids":proposal.evidence_ids,
                         "policy":self.policy,"provider":proposal.provider})
        return allowed, reason

class Game:
    def __init__(self, folder: Path, role="courier", policy="strict", provider="rules", model=None):
        self.store = Store(folder)
        self.provider = provider
        self.proposer = OllamaProposer(model=model) if provider=="ollama" else RulesProposer()
        state = self.store.state()
        if not state:
            self.store.save_state(role=role,policy=policy,scene="ford",hours=4,rescued=0,lamp=0,
                                  guard="edda",inventory="[]",completed=0)
            if role=="courier":
                self.store.add_evidence(VALID_WRIT,"royal_writ","traveler","has_valid_writ","true",
                                        "Crown registry",1.0,True)
            elif role=="impostor":
                self.store.add_evidence(FORGED_WRIT,"presented_document","traveler","has_valid_writ","unknown",
                                        "Traveler's presented document",.2,False)
            self.store.event("journey_started","player",{"role":role,"policy":policy})
        self.gate = AuthorizationGate(self.store, self.store.state()["policy"])

    @property
    def state(self): return self.store.state()

    def scene(self):
        s=self.state
        title, desc=SCENES[s["scene"]]
        print("\\n"+"="*68+"\\n"+title+f" | {s['role'].upper()} | {s['hours']} hours remaining")
        print(desc)
        if s["scene"]=="ford":
            print("\\nCommands: rescue, road, help, status, quit")
        elif s["scene"]=="gate":
            print(f"\\nGuard on duty: {s['guard'].title()} | Policy: {s['policy']}")
            print("Commands: talk <message>, ask, ledger, show, pass, trail, switch, journal, help, quit")
        elif s["scene"]=="tunnel":
            print("\\nCommands: lamp, climb, journal, help, quit")
        elif s["scene"]=="shelter":
            print("\\nCommands: torch, ridge, journal, help, quit")
        elif s["scene"]=="tower":
            print("\\nCommands: signal, bell, journal, help, quit")
        else:
            print("\\nCommands: journal, new, quit")

    def journal(self):
        s=self.store
        print("\\n--- JOURNAL / AUDIT TRAIL ---")
        print("Evidence:")
        for e in s.evidence():
            print(f"  {e['evidence_id']} | {e['kind']} | source={e['source']} | verified={bool(e['verified'])}")
        print("Recent memories:")
        for m in s.memories(limit=8):
            print(f"  #{m['memory_id']} {m['npc']} heard from {m['speaker']}: {m['content']} "
                  f"[{m['source_type']}, confidence={m['confidence']}]")
        print("Recent decisions:")
        for d in s.db.execute("SELECT * FROM decisions ORDER BY decision_id DESC LIMIT 8"):
            print(f"  {d['npc']}: proposal={d['proposed_action']} final={d['final_action']} "
                  f"allowed={bool(d['allowed'])}; {d['reason']}")
        print("Events:", s.db.execute("SELECT COUNT(*) FROM events").fetchone()[0])

    def npc_talk(self, text):
        s=self.state; npc=s["guard"]
        self.store.add_memory(npc,"traveler",text,"testimony",None,.55)
        # Gossip is explicit, attributed and confidence-reduced; it is not upgraded to evidence.
        other="hild" if npc=="edda" else "edda"
        self.store.add_memory(other,npc,f"I heard the traveler say: {text}","hearsay",
                              f"memory:{self.store.db.execute('SELECT last_insert_rowid()').fetchone()[0]}",.35)
        if self.provider=="ollama":
            try:
                payload=self.proposer.propose(npc,text,self.store.memories(npc),self.store.evidence())
                reply=f"{npc.title()} considers your words: {payload.reason}"
                self.store.event("npc_model_response",npc,{"proposal":payload.action,"reason":payload.reason})
            except Exception as exc:
                reply=f"{npc.title()} cannot consult the local model ({exc}). The gate remains unchanged."
        else:
            reply=f'{npc.title()} listens carefully. "I have recorded your statement, but a spoken claim is not a royal record."'
        print(reply)

    def passage(self):
        s=self.state; npc=s["guard"]
        memories=self.store.memories(npc)
        evidence=self.store.evidence()
        try:
            proposal=self.proposer.propose(npc,"I request passage through the Crown gate.",memories,evidence)
        except Exception as exc:
            proposal=Proposal("investigate",f"Proposer unavailable or invalid: {exc}",[],"fallback")
            print("Proposer warning:",exc)
        allowed,reason=self.gate.decide(npc,proposal)
        print(f"\\nProposer: {proposal.action.upper()} — {proposal.reason}")
        print(f"Authorization gate: {'APPROVED' if allowed else 'DENIED'} — {reason}")
        if allowed:
            self.store.save_state(scene="tunnel")
            print("The gate opens. Protected movement is recorded.")
        else:
            print("The gate remains shut. The public ridge trail remains available.")
        self.store.event("passage_attempt", "player", {"allowed":allowed,"policy":s["policy"]})

    def run(self):
        print("\\nEDDA'S WRIT V5 — A LANTERN FOR THE VALE")
        print("A story about memory, evidence, trust, and the cost of a decision.")
        while True:
            s=self.state; self.scene()
            try: raw=input("\\n> ").strip()
            except (EOFError,KeyboardInterrupt): raw="quit"
            if not raw: continue
            cmd,*rest=raw.split(" ",1); arg=rest[0] if rest else ""
            if cmd=="quit":
                self.store.event("game_saved","player",{"scene":s["scene"]})
                print("Journey saved.")
                break
            if cmd=="help":
                print("Choose a command shown for the current scene. NPC dialogue uses: talk <your words>.")
                continue
            if cmd=="journal": self.journal(); continue
            if cmd=="status":
                print(f"Role={s['role']} | policy={s['policy']} | scene={s['scene']} | hours={s['hours']}")
                continue
            scene=s["scene"]
            if scene=="ford":
                if cmd=="rescue":
                    self.store.save_state(scene="gate",rescued=1,hours=s["hours"]-1)
                    self.store.add_memory("edda","villager","The traveler rescued a child at the flooded ford.",
                                          "witness_report",None,.9)
                    print("You pull the child to safety. A villager tells the guards what happened.")
                elif cmd=="road":
                    self.store.save_state(scene="gate")
                    print("You reach the Crown gate before the river rises.")
                else: print("That action is unavailable here.")
            elif scene=="gate":
                if cmd=="talk" and arg: self.npc_talk(arg)
                elif cmd=="ask":
                    print(f'{s["guard"].title()}: "What proof do you carry? The ledger, not a rumour, decides a royal writ."')
                elif cmd=="ledger":
                    matches=[e for e in self.store.evidence() if e["kind"]=="royal_writ" and e["verified"]]
                    print("The Crown ledger confirms WRIT-ROYAL-1042." if matches else
                          "The Crown ledger has no matching royal writ for you.")
                elif cmd=="show":
                    if s["role"]=="courier": print("You present the sealed writ. The Crown ledger can verify its entry.")
                    elif s["role"]=="impostor": print("You present a document. Its seal looks plausible, but it is not registered.")
                    else: print("You have no writ to present.")
                elif cmd=="pass": self.passage()
                elif cmd=="trail":
                    self.store.save_state(scene="shelter",hours=s["hours"]-1)
                    print("You take the public sheep trail. No royal authorization is needed.")
                elif cmd=="switch":
                    new="hild" if s["guard"]=="edda" else "edda"
                    self.store.save_state(guard=new)
                    print(f"{new.title()} takes the watch.")
                else: print("That action is unavailable here.")
            elif scene=="tunnel":
                if cmd=="lamp":
                    self.store.save_state(scene="tower",lamp=1,hours=s["hours"]-1)
                    print("You retrieve the lamp and climb toward the tower.")
                elif cmd=="climb":
                    self.store.save_state(scene="tower")
                    print("You climb the wet stairs to the watchtower.")
                else: print("That action is unavailable here.")
            elif scene=="shelter":
                if cmd=="torch":
                    self.store.save_state(scene="tower",lamp=1,hours=s["hours"]-1)
                    print("You take the spare torch and climb the ridge.")
                elif cmd=="ridge":
                    self.store.save_state(scene="tower")
                    print("You continue along the ridge.")
                else: print("That action is unavailable here.")
            elif scene=="tower":
                if cmd in ("signal","bell"):
                    hours=s["hours"]-(1 if cmd=="bell" else 0)
                    success=hours>0 and (cmd=="bell" or s["lamp"] or s["rescued"])
                    ending="The warning beacon burns across the valley." if success else "The flood reaches the lower homes before the warning arrives."
                    self.store.save_state(scene="ending",hours=hours,completed=1)
                    self.store.event("ending","player",{"success":success,"ending":ending})
                    print("\\nENDING: "+("THE VALE IS WARNED" if success else "TOO LATE"))
                    print(ending)
                else: print("That action is unavailable here.")
            elif scene=="ending":
                if cmd=="new":
                    print("Start a new save folder to begin another role/policy combination.")
                    break
                print("Your completed journey remains saved. Use journal to inspect it.")
        self.store.close()
