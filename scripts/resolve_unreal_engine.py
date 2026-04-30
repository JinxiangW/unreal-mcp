"""Resolve the Unreal Engine source root used by this harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from unreal_harness_runtime.config import get_runtime_paths  # noqa: E402


def main() -> int:
    print(json.dumps(get_runtime_paths(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
