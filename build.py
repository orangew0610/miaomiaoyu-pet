#!/usr/bin/env python3
"""Build the Windows DebugPet executable with the active environment."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC_FILE = ROOT / "DebugPet.spec"


def build() -> None:
    """Run PyInstaller from the current isolated Python environment."""

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]
    print("[build]", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)
    print(f"[build] complete: {ROOT / 'dist' / 'DebugPet.exe'}")


if __name__ == "__main__":
    build()
