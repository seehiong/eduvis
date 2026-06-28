#!/usr/bin/env python3
"""
Build Showcase Assets Script.

Automatically renders all showcase lesson YAML files directly to their
respective docs/showcase/assets/ target directories.
"""

import sys
import subprocess
from pathlib import Path

# Workspace root is the parent of the scripts directory
ROOT_DIR = Path(__file__).resolve().parent.parent

SHOWCASE_MAP = {
    # Lesson showcases — full pedagogical flow
    "docs/showcase/lessons/negative-numbers-confidence-ladder-lesson.yaml": "docs/showcase/assets/negative-numbers",
    # Feature showcases — one feature or element family per file
    "docs/showcase/features/adaptive-remediation-branching-lesson.yaml": "docs/showcase/assets/adaptive-remediation",
    "docs/showcase/features/visual-elements-catalog-lesson.yaml": "docs/showcase/assets/visual-elements",
    "docs/showcase/features/assessment-schemas-lesson.yaml": "docs/showcase/assets/assessment-schemas",
}


def main() -> None:
    print("Building showcase assets...")
    success = True

    for src_rel, dest_rel in SHOWCASE_MAP.items():
        src_path = ROOT_DIR / src_rel
        dest_path = ROOT_DIR / dest_rel

        print(f"\nRendering: {src_rel} -> {dest_rel}")

        # Ensure destination directory exists
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
