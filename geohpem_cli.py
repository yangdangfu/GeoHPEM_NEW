from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main(argv: list[str] | None = None) -> int:
    """
    Development-friendly CLI entrypoint (no need for editable install).

    Usage: `python geohpem_cli.py ...`
    """
    _ensure_src_on_path()
    from geohpem.cli import main as cli_main

    return int(cli_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

