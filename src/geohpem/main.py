from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geohpem")
    parser.add_argument("--open", dest="open_dir", default=None, help="Open a case folder on startup.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    from geohpem.gui.app import run_gui

    return int(run_gui(open_case_dir=args.open_dir))
