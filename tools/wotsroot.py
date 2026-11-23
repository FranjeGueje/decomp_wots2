"""Where the project's folder is: the repository, or, in the packaged patcher
(tools/spanish_patcher.py made into a program), the folder the program is in."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent
