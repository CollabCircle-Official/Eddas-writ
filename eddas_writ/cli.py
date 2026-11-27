import argparse
from pathlib import Path
from .engine import Game, POLICIES

def main():
    p=argparse.ArgumentParser(description="Edda's Writ v5")
    p.add_argument("--save",default="saves/default")
    p.add_argument("--role",choices=["courier","traveler","impostor"],default="courier")
    p.add_argument("--policy",choices=list(POLICIES),default="strict")
    p.add_argument("--provider",choices=["rules","ollama"],default="rules")
    p.add_argument("--model",default=None)
    p.add_argument("--reset",action="store_true",help="Delete this save first (use a new folder instead when preserving data matters).")
    a=p.parse_args()
    folder=Path(a.save)
    if a.reset and folder.exists():
        import shutil
        shutil.rmtree(folder)
    game=Game(folder,a.role,a.policy,a.provider,a.model)
    game.run()
if __name__=="__main__": main()
