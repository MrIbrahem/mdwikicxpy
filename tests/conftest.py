import sys
from pathlib import Path

# Add the parent directory to the path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "cxsever" / "www" / "python"))
