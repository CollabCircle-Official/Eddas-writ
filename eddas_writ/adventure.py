"""Edda's Writ: A Lantern for the Vale."""
import argparse
import json
import sqlite3
import subprocess
import sys
from uuid import uuid4
from contextlib import closing
from pathlib import Path

from .actions import present_writ, tell
from .adapter import Adapter
from .game import WRITS, build, status
from .proposers import Credulous
from .scenarios import PLAYER, ROLES

SCENES = {
    "ford": ("The flooded ford", "A ferry strains against its mooring. A child calls from the reed bed."),
    "gate": ("The cave mouth", "Edda guards the tunnel. Hild keeps the Crown ledger beside a guttering lantern."),
    "tunnel": ("The twisting tunnel", "Water rises through the cracks. An abandoned signal lamp hangs from a nail."),
    "shelter": ("The shepherd's shelter", "A dry shelf holds the shepherd's spare torch."),
    "tower": ("The watchtower", "Below you, the valley road is sinking into the flood."),
    "end": ("Journey's end", "The night will be remembered in the vale."),
}
ACTIONS = {
    "ford": {"help": "Rescue the child (costs 1 hour)", "road": "Take the ridge road"},
    "gate": {"talk": "Tell Edda your story", "ledger": "Ask Hild to check the ledger",
             "show": "Present your writ", "pass": "Request passage", "trail": "Take the old sheep trail (costs 1 hour)",
             "guard": "Switch between Edda and Hild", "rest": "Wait for the guard handover and reload the save"},
    "tunnel": {"lamp": "Retrieve the signal lamp (costs 1 hour)", "climb": "Climb to the tower"},
    "shelter": {"torch": "Take the spare torch (costs 1 hour)", "ridge": "Continue without a torch"},
    "tower": {"signal": "Light the warning beacon", "bell": "Ring the flood bell (costs 1 hour)"},
    "end": {},
}


def advance(state, action, memory, world, trace, adapter):
    scene = state["scene"]
    if action not in ACTIONS[scene]:
        return None
    if action == "help":
        state.update(rescued=True, scene="gate")
        state["hours"] -= 1
        return "You pull the child aboard. Her father gives you a flask of lamp oil."
    if action == "road":
        state["scene"] = "gate"
        return "You reach the gate before the rain gets worse."
    npc = state["guard"]
    name = npc.title()
    if action == "guard":
        state["guard"] = "hild" if npc == "edda" else "edda"
        return f"You turn to {state['guard'].title()}."
    if action == "talk":
        text = "I carry a royal writ."
        tell(memory, trace, npc, PLAYER, text, state["tick"], stype="testimony")
        return f'You say, "{text}" {name} records your claim.'
    if action == "rest":
        known = {belief.corr_id for belief in memory.for_npc("hild")}
        for belief in memory.for_npc("edda"):
            if belief.corr_id in known:
                continue
            heard = memory.observe(
                "hild", PLAYER, belief.predicate, belief.value, "hearsay", "edda",
                round(belief.confidence * 0.8, 3), belief.corr_id, state["tick"],
                origin=belief.story,
            )
            trace.record(heard.corr_id, "propagation", {
                "belief_id": heard.id, "from": "edda", "to": "hild", "origin": heard.origin,
            })
        return "Edda hands over the ledger. Hild takes the next watch. Reloading your save."
    if action == "ledger":
        return ("The ledger lists a valid writ in your name."
                if world.is_verified(PLAYER) else
                "The ledger has no writ in your name. The sheep trail is open to travelers.")
    if action == "show":
        if state["role"] == "traveler":
            return "You carry no writ. Hild offers directions to the public sheep trail."
        _, verified = present_writ(world, trace, PLAYER, WRITS["courier" if state["role"] == "courier" else "impostor"])
        return ("The seal matches the Crown ledger." if verified else
                "The guards reject the forged writ. The sheep trail is still open.")
    if action == "pass":
        chain, decision = adapter.adjudicate(npc, PLAYER, "request_passage")
        state["last_chain"] = chain
        if decision.allowed and decision.protected:
            state["scene"] = "tunnel"
            if decision.satisfied_by == "belief_materialized":
                return (f"{name} opens the gate. This policy trusted a remembered claim. "
                        "No writ was checked against the Crown ledger for this clearance.")
            return f"{name} checks your clearance and opens the gate."
        if memory.for_npc(npc, "has_royal_writ", PLAYER):
            return f"{name} remembers the claim but keeps the gate shut. This policy needs stronger evidence."
        return f"{name} keeps the gate shut. Show a writ or take the public sheep trail."
    if action == "trail":
        state["hours"] -= 1
        state["scene"] = "shelter"
        return "The sheep trail brings you to a shelter on the ridge."
    if action in ("torch", "ridge"):
        state["scene"] = "tower"
        if action == "torch":
            state["hours"] -= 1
            state["lamp"] = True
            return "You light the shepherd's spare torch and carry it to the tower."
        return "You leave the shelter and follow the ridge to the tower."
    if action == "lamp":
        state["hours"] -= 1
        state.update(lamp=True, scene="tower")
        return "You carry the lamp up the stairwell. Its wick still smells of oil."
    if action == "climb":
        state["scene"] = "tower"
        return "You climb to the watchtower as the water closes over the bottom stair."
    if action == "signal" and not (state["lamp"] or state["rescued"]):
        return "The beacon is dry. Ring the bell to warn the valley."
    if action == "bell":
        state["hours"] -= 1
    state["scene"] = "end"
    if state["hours"] <= 0:
        return "ENDING: Too Late. The road is underwater before your warning reaches the valley."
    if action == "signal":
        return "ENDING: Beacon in the Rain. The watchfires answer. The valley reaches higher ground."
    return "ENDING: The Bell Holds. The nearest homes hear you and evacuate before dawn."


def play(db, state, memory, world, trace, adapter):
    while True:
        scene = state["scene"]
        title, description = SCENES[scene]
        print(f"\n{title.upper()} | {state['role'].title()} | {state['hours']} hours left")
        print(description)
        if scene == "end":
            print("Type journal to review this journey or new to start another with the same role and policy.")
        if scene == "gate":
            print(f"Speaking to {state['guard'].title()} | Policy: {state['gate']}")
        for key, label in ACTIONS[scene].items():
            print(f"  {key:7} {label}")
        print("  journal Show beliefs, decisions, and trace status\n  quit    Save and leave")
        try:
            action = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if action == "quit":
            return None
        if action == "new" and scene == "end":
            return "new"
        if action == "journal":
            print(status(memory, world, trace, state.get("last_chain")))
            continue
        state["tick"] += 1
        message = advance(state, action, memory, world, trace, adapter)
        if message is None:
            print("Choose one of the commands shown.")
            continue
        with db:
            db.execute("INSERT INTO history(state,message) VALUES (?,?)",
                       (json.dumps(state), message))
        print(message, flush=True)
        if action == "rest":
            return "rest"


def choose(prompt, options):
    for number, (_, label) in enumerate(options, 1):
        print(f"  {number}. {label}")
    while True:
        answer = input(prompt).strip()
        if answer.isdecimal() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1][0]
        print("Choose one of the listed numbers.")


def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save", type=Path, default=Path("adventure_saves/courier"))
    parser.add_argument("--role", choices=("courier", "impostor", "traveler"), default="courier")
    parser.add_argument("--gate", choices=("N0", "N1", "B3b", "D", "C_control"), default="D")
    parser.add_argument("--new", action="store_true", help="Start in a new, unused save folder.")
    parser.add_argument("--menu", action="store_true", help="Choose a new game or resume.")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        return supervise(args, parser)
    folder = args.save.resolve()
    if args.new and folder.exists():
        parser.error("Choose a new save folder.")
    folder.mkdir(parents=True, exist_ok=True)
    memory, world, trace, _ = build(folder, "standalone")
    with closing(memory.db), closing(world.db), closing(trace.db), closing(sqlite3.connect(folder / "story.db")) as db:
        db.execute("CREATE TABLE IF NOT EXISTS history (turn INTEGER PRIMARY KEY, state TEXT NOT NULL, message TEXT NOT NULL)")
        row = db.execute("SELECT state, message FROM history ORDER BY turn DESC LIMIT 1").fetchone()
        if row:
            state = json.loads(row[0])
            print(row[1])
        else:
            role = args.role
            if role == "courier":
                world.seed_verified_writ(PLAYER, WRITS[role])
            state = dict(scene="ford", hours=3, role=role, rescued=False, lamp=False,
                         gate=args.gate, tick=0, guard="edda")
            with db:
                db.execute("INSERT INTO history(state,message) VALUES (?,?)",
                           (json.dumps(state), "The vale is flooding. Reach the watchtower."))
        adapter = Adapter(memory, world, trace, Credulous(), state["gate"], ROLES)
        restart = play(db, state, memory, world, trace, adapter)
    return {"rest": 20, "new": 21}.get(restart, 0)


def supervise(args, parser):
    folder = args.save.resolve()
    role, gate = args.role, args.gate
    fresh = args.new
    if args.menu:
        saves = sorted(folder.parent.glob("*/story.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        try:
            mode = choose("Journey > ", [
                (None, "New journey"),
                *((path.parent, f"Resume {path.parent.name}") for path in saves),
            ])
            if mode is None:
                role = choose("Role > ", [
                    ("courier", "Courier: carry a genuine writ"),
                    ("traveler", "Traveler: take the public trail without a writ"),
                    ("impostor", "Impostor: carry a forged writ"),
                ])
                gate = choose("Policy > ", [
                    ("D", "Registry-only: require verified clearance"),
                    ("N0", "Naive simulation: a remembered claim can grant clearance"),
                    ("N1", "Evidence classification: evaluate sources before granting clearance"),
                ])
                folder = folder.parent / f"{role}_{uuid4().hex[:10]}"
                fresh = True
            else:
                folder = mode
                fresh = False
        except (EOFError, KeyboardInterrupt):
            return 0

    command = [sys.executable, "-m", "eddas_writ.adventure", "--worker"]
    while True:
        if fresh and folder.exists():
            parser.error("Choose a new save folder.")
        result = subprocess.call([
            *command, "--save", str(folder), "--role", role, "--gate", gate,
        ])
        if result == 20:
            fresh = False
            continue
        if result != 21:
            return result
        with closing(sqlite3.connect(folder / "story.db")) as db:
            saved = db.execute("SELECT state FROM history ORDER BY turn DESC LIMIT 1").fetchone()
        state = json.loads(saved[0])
        role, gate = state["role"], state["gate"]
        folder = folder.parent / f"{role}_{uuid4().hex[:10]}"
        fresh = True


if __name__ == "__main__":
    raise SystemExit(main())
