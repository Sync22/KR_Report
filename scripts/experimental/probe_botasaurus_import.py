"""Import-only Botasaurus probe.

This script intentionally avoids project runtime paths. It only verifies that
the experimental virtual environment can import Botasaurus.
"""

from __future__ import annotations

import importlib.metadata


def main() -> int:
    version = importlib.metadata.version("botasaurus")
    print(f"botasaurus import ok: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
