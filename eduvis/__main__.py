import sys
from pathlib import Path

# Support running directly as a script without parent package context (e.g. `python eduvis/__main__.py` or `uv run eduvis`)
if not __package__:
    _ROOT = Path(__file__).resolve().parent.parent
    if str(_ROOT) not in sys.path:
        sys.path.insert(0, str(_ROOT))
    from eduvis.cli import cli
else:
    from .cli import cli

if __name__ == "__main__":
    cli()
