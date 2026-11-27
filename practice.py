"""Record a neutral Ollama proposal separately from scored scenarios."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


def run_practice(path, out, live=False):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("practice_only") is not True:
        raise ValueError("Expected a neutral practice record")
    request = record["request"]
    if live:
        body = json.dumps(request).encode()
        call = Request("http://localhost:11434/api/generate", data=body,
                       headers={"Content-Type": "application/json"})
        with urlopen(call, timeout=300) as response:
            reply = json.load(response)
    else:
        reply = record["reply"]
    directory = Path(out) / "practice"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (uuid4().hex + ".json")
    trace = dict(practice_only=True, mode="live" if live else "replay",
                 request=request, reply=reply, gate_status="not_run", game_status="not_run")
    try:
        if reply.get("done") is not True or reply.get("model") != request["model"]:
            raise ValueError("Incomplete response or model mismatch")
        proposal = json.loads(reply["response"])
        if not isinstance(proposal, dict) or set(proposal) != {"action"} or proposal["action"] not in (
            "give_directions", "ask_clarification", "wait"
        ):
            raise ValueError("Invalid neutral proposal")
        if not live and "parsed_proposal" in record and proposal != record["parsed_proposal"]:
            raise ValueError("Parsed proposal differs from archived value")
        trace["proposal"] = proposal
    except (KeyError, TypeError, ValueError) as exc:
        trace["error"] = str(exc)
        raise
    finally:
        target.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        print("Practice trace:", target.resolve())
    print(trace["mode"], proposal["action"], "| gate: not run | game: not run")
