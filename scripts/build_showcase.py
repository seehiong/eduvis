#!/usr/bin/env python3
"""
Build Showcase Assets Script.

1. Syncs Python source files into showcase/ so Pyodide always loads
   the latest code — showcase/*.py are auto-generated, never hand-edited.
2. Renders all showcase lesson YAML files to their showcase/assets/ dirs.
"""

import shutil
import sys
import subprocess
from pathlib import Path

# Workspace root is the parent of the scripts directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Maps showcase flat filename -> source path within the repo.
# Pyodide fetches these files by name and writes them into its virtual FS.
# The source files in eduvis/ are the single source of truth.
PYODIDE_SOURCE_MAP = {
    "engine.py":        "eduvis/core/engine.py",
    "validator.py":     "eduvis/core/validator.py",
    "generic.py":       "eduvis/core/elements/generic.py",
    "renderers_base.py":"eduvis/renderers/svg/renderers_base.py",
    "curriculum.py":    "eduvis/core/curriculum.py",
    "core_init.py":     "eduvis/core/__init__.py",
    "main_init.py":     "eduvis/__init__.py",
    "constants.py":     "eduvis/core/constants.py",
    "ast_editor.py":    "eduvis/core/ast_editor.py",
}

SHOWCASE_DIR = ROOT_DIR / "showcase"

SHOWCASE_MAP = {
    # Lesson showcases — full pedagogical flow
    "showcase/lessons/negative-numbers-confidence-ladder-lesson.yaml": "showcase/assets/negative-numbers",
    # Feature showcases — one feature or element family per file
    "showcase/features/adaptive-remediation-branching-lesson.yaml": "showcase/assets/adaptive-remediation",
    "showcase/features/visual-elements-catalog-lesson.yaml": "showcase/assets/visual-elements",
    "showcase/features/assessment-schemas-lesson.yaml": "showcase/assets/assessment-schemas",
}


def sync_pyodide_sources() -> bool:
    """Copy source files into showcase/ so Pyodide loads the latest code."""
    print("Syncing Pyodide source files to showcase/...")
    ok = True
    for dest_name, src_rel in PYODIDE_SOURCE_MAP.items():
        src = ROOT_DIR / src_rel
        dest = SHOWCASE_DIR / dest_name
        if not src.is_file():
            print(f"  MISSING  {src_rel}", file=sys.stderr)
            ok = False
            continue
        shutil.copy2(src, dest)
        print(f"  OK  {src_rel} -> showcase/{dest_name}")

    import re
    import zipfile
    import os
    from eduvis.core.constants import PACKAGE_VERSION

    source_dir = ROOT_DIR / "eduvis"
    zip_path = SHOWCASE_DIR / "eduvis.zip"
    print(f"  Archiving {source_dir} -> showcase/eduvis.zip...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            if ".pytest_cache" in dirs:
                dirs.remove(".pytest_cache")
            for file in files:
                if file.endswith((".pyc", ".pyo", ".pyd")):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, ROOT_DIR)
                zipf.write(file_path, arcname)

    html_path = SHOWCASE_DIR / "editor.html"
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8")
        updated = re.sub(r'(\?v=)[0-9\.]+', rf'\g<1>{PACKAGE_VERSION}', content)
        if content != updated:
            html_path.write_text(updated, encoding="utf-8")
            print(f"  OK  Updated version string in editor.html to {PACKAGE_VERSION}")

    return ok

def main() -> None:
    print("Building showcase assets...")
    if not sync_pyodide_sources():
        print("\nAborting: source sync failed.", file=sys.stderr)
        sys.exit(1)
    print()
    success = True

    for src_rel, dest_rel in SHOWCASE_MAP.items():
        src_path = ROOT_DIR / src_rel
        dest_path = ROOT_DIR / dest_rel

        print(f"\nRendering: {src_rel} -> {dest_rel}")

        # Clean and recreate destination directory to prevent stale assets
        if dest_path.exists():
            shutil.rmtree(dest_path)
        dest_path.mkdir(parents=True, exist_ok=True)

        # Run render CLI command using the current python interpreter
        cmd = [
            sys.executable,
            "-m",
            "eduvis",
            "render",
            str(src_path),
            "-o",
            str(dest_path),
        ]

        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(res.stdout.strip())
        except subprocess.CalledProcessError as err:
            print(f"Error rendering {src_rel}:", file=sys.stderr)
            print(err.stderr, file=sys.stderr)
            success = False

    if success:
        print("\nShowcase build completed successfully!")
        sys.exit(0)
    else:
        print("\nShowcase build failed with errors.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
