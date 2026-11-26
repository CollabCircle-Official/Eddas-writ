"""Mirror binding to the REAL Thespis and Dungeons and Agents checkouts.  *** UNTESTED HERE ***

Ported from the working framework_scene.py. It does NOT replace the local stores; it mirrors
each belief write into Thespis (HTTP /observe + snapshot + restore + retrieve) and each
authorized move through the DnA HTTP turn route, then records the NATIVE ids in the trace
('native_belief', 'native_move') under the same correlation id. Gossip is not mirrored.
Locate checkouts with THESPIS_DIR / DND_AGENTS_DIR, else as siblings of this game folder.
Run via play_research.cmd so uv supplies both environments.
"""
import asyncio, inspect, json, os, runpy, sqlite3
from contextlib import closing
from pathlib import Path


class FrameworkLink:
    def __init__(self, workdir, trace):
        game_root = Path(__file__).resolve().parents[2]
        self.thespis = Path(os.environ.get("THESPIS_DIR", game_root.parent / "Thespis"))
        self.dnd = Path(os.environ.get("DND_AGENTS_DIR", game_root.parent / "Dungeons-and-Agents"))
        self.workdir, self.trace = Path(workdir), trace
        self.loop = asyncio.new_event_loop()

    # ---- setup -------------------------------------------------------------------------
    def connect(self):
        import dnd_agent.agent  # noqa: F401  (load first: known circular import)
        from dnd_agent.agent.tools import move_to
        from dnd_agent.api.app import create_app
        from dnd_agent.cli.sse import iter_sse_data
        from dnd_agent.store.event_store import EventStore
        from httpx import ASGITransport, AsyncClient
        from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
        from pydantic_ai.models.function import DeltaToolCall, FunctionModel

        self._iter_sse = iter_sse_data
        args = {list(inspect.signature(move_to).parameters)[1]: "twisting_tunnel"}

        def has_result(msgs):
            return any(p.part_kind == "tool-return" for m in msgs for p in m.parts)

        async def reply(msgs, info):
            return ModelResponse(parts=[TextPart(content="You enter the tunnel.")]) if has_result(msgs) \
                else ModelResponse(parts=[ToolCallPart(tool_name="move_to", args=args)])

        async def stream(msgs, info):
            if has_result(msgs):
                yield "You enter the tunnel."
            else:
                yield {0: DeltaToolCall(name="move_to")}
                yield {0: DeltaToolCall(json_args=json.dumps(args))}

        model = FunctionModel(reply, stream_function=stream)

        town = runpy.run_path(str(self.thespis / "tests/test_growing_cast.py"))   # fragile: uses Thespis test fixtures
        self.game = town["Game"].parse(town["TOWN_TOML"].replace("robbed", "holds_royal_writ"), "town")
        self.Session = town["Session"]
        self.claim = {**town["ROBBED"], "pred": "holds_royal_writ"}
        self._tc = town["TestClient"](town["create_app"]({"town": self.game}))
        self.npc = self._tc.__enter__()
        r = self.npc.post("/v1/sessions", json={"game": "town"}); r.raise_for_status()
        self.session = r.json()["session"]; self.url = "/v1/sessions/" + self.session
        self.npc.post(self.url + "/npcs", json={"id": "edda", "kind": "townsfolk", "name": "Edda", "at": "market"}).raise_for_status()

        async def start():
            self.db_path = self.workdir / "dnd.sqlite"
            self.store = EventStore(self.db_path); await self.store.open()
            app = create_app(store=self.store, turn_model=model)
            app.state.store = self.store; app.state.turn_model = model
            self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
            r = await self.client.post("/sessions", json={"scenario_id": "goblin_cave", "rng_seed": 42})
            r.raise_for_status(); self.dnd_session = r.json()["session_id"]
            if (await self.store.get_snapshot(self.dnd_session)).location != "cave_mouth":
                raise RuntimeError("Expected to start at the cave mouth")
        self.loop.run_until_complete(start())

    # ---- mirrors -----------------------------------------------------------------------
    def mirror_belief(self, corr):
        r = self.npc.post(self.url + "/observe", json={"verb": "tell", "actor": "player", "target": "edda",
                          "at": "market", "claim": self.claim, "said": True, "conf": 0.7})
        r.raise_for_status(); event_id = r.json()["id"]
        snap = self.npc.get(self.url + "/snapshot"); snap.raise_for_status()
        (self.workdir / "thespis.snapshot.json").write_text(json.dumps({"session": self.session, "snapshot": snap.json()}, indent=2))
        restored = self.Session.restore(self.game, snap.json())
        for belief in restored.inspect("edda")["beliefs"]:
            for ev in belief["evidence"]:
                if ev["event"] == event_id and belief["claim"] == self.claim:
                    rec = {**ev, "session": self.session}
                    self.trace.record(corr, "native_belief", rec); return rec
        raise RuntimeError("saved Thespis belief could not be retrieved")

    def mirror_move(self, corr):
        async def cross():
            r = await self.client.post(f"/sessions/{self.dnd_session}/turns", json={"player_text": "I move to the Twisting Tunnel."})
            r.raise_for_status()
            done = next((e for e in self._iter_sse(r.text.splitlines()) if e["type"] == "done"), {})
            saved = await self.store.get_snapshot(self.dnd_session)
            if done.get("status") != "ok" or saved.location != "twisting_tunnel":
                raise RuntimeError(f"expected arrival at the tunnel: {r.text}")
            with closing(sqlite3.connect(self.db_path)) as db:
                rows = db.execute("SELECT seq, payload_json FROM events WHERE session_id=?", (self.dnd_session,)).fetchall()
            moves = [(s, e) for s, raw in rows if (e := json.loads(raw))["type"] == "location_changed"]
            if len(moves) != 1:
                raise RuntimeError(f"expected one movement event: {moves}")
            return {"session_id": self.dnd_session, "seq": moves[0][0], "payload": moves[0][1]}
        rec = self.loop.run_until_complete(cross())
        self.trace.record(corr, "native_move", rec); return rec

    def close(self):
        try:
            self.loop.run_until_complete(self.client.aclose()); self._tc.__exit__(None, None, None)
        except Exception:
            pass
