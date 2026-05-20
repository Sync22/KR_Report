"""Import-only Kronos research-lane probe.

This script intentionally avoids production project imports and does not load
Hugging Face model weights. It checks package metadata and importability only.
"""

from __future__ import annotations

import importlib.metadata


def main() -> int:
    version = importlib.metadata.version("kronos-model-arch")
    from model import Kronos, KronosTokenizer  # noqa: PLC0415

    _ = (Kronos, KronosTokenizer)
    print(f"kronos-model-arch metadata ok: {version}")
    print("kronos model imports ok")
    print("research-only lane: stored KRX OHLCV offline experiments only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
