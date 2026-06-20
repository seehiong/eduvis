#!/usr/bin/env python3
"""
Code Maintainability and Quality Check Runner.

Runs Ruff and Pylint to enforce code style, cyclomatic complexity,
nesting depth, function length, module length, and code duplication rules.
"""

import sys
import subprocess
import shutil
from pathlib import Path

# Workspace root is the parent of the scripts directory
ROOT_DIR = Path(__file__).resolve().parent.parent


def run_tool(cmd: list[str], description: str) -> bool:
    print("\n==========================================")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("==========================================\n")

    # Check if executable exists
    exe = cmd[0]
    if not shutil.which(exe):
        print(
            f"Error: '{exe}' executable not found in PATH.\n"
            f"Please ensure you have installed the development dependencies:\n"
            f"  uv sync\n"
            f"or\n"
            f"  pip install -e \".[dev]\"\n",
            file=sys.stderr
        )
        return False

    try:
        # Run process, streaming stdout/stderr to the console
        result = subprocess.run(cmd, cwd=ROOT_DIR, check=False)
        if result.returncode == 0:
            print(f"\n[SUCCESS] {description} passed.")
            return True
        print(f"\n[FAILURE] {description} exited with code {result.returncode}.", file=sys.stderr)
        return False
    except (subprocess.SubprocessError, OSError) as e:
        print(f"Failed to run '{exe}': {e}", file=sys.stderr)
        return False


def main() -> None:
    print("Starting eduvis quality and maintainability checks...")

    # Define targets to check
    targets = ["eduvis", "tests", "scripts"]

    # 1. Run Ruff for style, complexity (C901), and statement counts (PLR0915)
    ruff_ok = run_tool(["ruff", "check"] + targets, "Ruff (Linter, Complexity, & Function Length)")

    # 2. Run Pylint for nesting depth, module size, and duplication
    pylint_ok = run_tool(["pylint", "--disable=unrecognized-option"] + targets, "Pylint (Nesting Depth, Module Size, & Duplication)")

    if ruff_ok and pylint_ok:
        print("\nAll maintainability checks passed successfully!")
        sys.exit(0)
    else:
        print("\nOne or more checks failed. Please fix the violations before committing.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
