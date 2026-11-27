import json, unittest
from unittest.mock import patch
from eddas_writ.dialogue import OllamaDialogue, ScriptedDialogue

class FakeResponse:
 def __init__(self,payload): self.payload=json.dumps(payload).encode()
 def __enter__(self): return self
 def __exit__(self,*args): return False
 def read(self): return self.payload

class DialogueTests(unittest.TestCase):
 @patch("eddas_writ.dialogue.urllib.request.urlopen")
 def test_ollama_dialogue_uses_hild_personality(self,mocked):
  def fake(request,timeout=0):
   body=json.loads(request.data.decode())
   self.assertFalse(body["think"])
   self.assertIn("never authorize passage",body["messages"][0]["content"].lower())
   context=json.loads(body["messages"][1]["content"])
   self.assertEqual(context["npc"],"hild")
   self.assertIn("ledger keeper",context["personality"])
   return FakeResponse({"model":"qwen3:4b","message":{"content":"Hild closes the ledger gently."},"eval_count":12})
  mocked.side_effect=fake
  reply,meta=OllamaDialogue(model="qwen3:4b").reply("hild","I have a writ.",{"role":"traveler","scene":"gate"},[],[])
  self.assertEqual(reply,"Hild closes the ledger gently.")
  self.assertEqual(meta["provider"],"ollama")
 @patch("eddas_writ.dialogue.urllib.request.urlopen")
 def test_empty_reply_rejected(self,mocked):
  mocked.return_value=FakeResponse({"message":{"content":" "}})
  with self.assertRaisesRegex(ValueError,"empty NPC reply"):
   OllamaDialogue().reply("edda","hello",{},[],[])
 def test_scripted_npcs_are_distinct(self):
  d=ScriptedDialogue()
  self.assertNotEqual(d.reply("edda","hi",{},[],[]),d.reply("hild","hi",{},[],[]))

if __name__=="__main__": unittest.main()
