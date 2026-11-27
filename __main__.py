"""Launch the playable Edda's Writ adventure."""
import sys
from .adventure import main
if __name__ == "__main__":
    raise SystemExit(main(["--menu"] if len(sys.argv) == 1 else None))
