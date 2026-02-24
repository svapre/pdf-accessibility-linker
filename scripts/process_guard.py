"""Compatibility wrapper for control-loop toolkit process guard."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _wire_toolkit_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    override = os.getenv("CONTROL_LOOP_KIT_PATH")
    toolkit_root = Path(override) if override else (repo_root / "tooling" / "control-loop-kit")
    if not toolkit_root.exists():
        raise RuntimeError(
            "Missing toolkit dependency. Expected CONTROL_LOOP_KIT_PATH or tooling/control-loop-kit. "
            "Initialize submodules before running process gates."
        )
    sys.path.insert(0, str(toolkit_root))


_wire_toolkit_path()

from control_loop.process_guard import *  # noqa: F403


if __name__ == "__main__":
    raise SystemExit(main())  # type: ignore[name-defined]
