# v6 automated test results

The following modules were run individually under CPython 3.13 in the build environment. Ollama HTTP is mocked; no local Ollama server was used.

| Test module | Result |
|---|---:|
| `tests.test_adventure` | 5 passed |
| `tests.test_game` | 5 passed |
| `tests.test_testbed` | 7 passed |
| `tests.test_dialogue` | 3 passed |
| `tests.test_ollama_proposer` | 4 passed |
| `tests.test_trace_coverage` | 1 passed |
| **Total** | **25 passed** |

Coverage includes safe/unsafe gate behavior, forged writ rejection, role routes and endings, save persistence across process restart, NPC dialogue personalities, Ollama structured output validation, unknown belief-ID rejection, fail-closed behavior when Ollama is unavailable, research scenario scoring, and trace-chain reconstruction.

Not covered by this environment run: a real Windows 10/11 manual playthrough, a live Ollama model call, or native Thespis/Dungeons and Agents integration. These remain explicit release checklist items.
