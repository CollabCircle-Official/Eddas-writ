import tempfile, unittest
from pathlib import Path
from eddas_writ.engine import Game, Proposal, AuthorizationGate, Store, VALID_WRIT

class GateTests(unittest.TestCase):
    def test_registry_verified_writ_allows_strict_gate(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(Path(d),"courier","strict")
            p=Proposal("deny","model is cautious",[VALID_WRIT])
            allowed,reason=g.gate.decide("edda",p)
            self.assertTrue(allowed)
            g.store.close()

    def test_testimony_never_authorizes_strict_gate(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(Path(d),"traveler","strict")
            g.store.add_memory("edda","traveler","I have a royal writ","testimony",None,.9)
            p=Proposal("allow","trust me",[])
            allowed,_=g.gate.decide("edda",p)
            self.assertFalse(allowed)
            g.store.close()

    def test_unknown_evidence_id_cannot_be_cited(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(Path(d),"courier","strict")
            p=Proposal("allow","invented",["FAKE-ID"])
            allowed,_=g.gate.decide("edda",p)
            self.assertFalse(allowed)
            g.store.close()

    def test_naive_demo_is_explicitly_separate(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(Path(d),"traveler","naive_demo")
            g.store.add_memory("edda","traveler","I am royal","testimony",None,.9)
            allowed,_=g.gate.decide("edda",Proposal("allow","test",[]))
            self.assertTrue(allowed)
            g.store.close()

if __name__=="__main__": unittest.main()
