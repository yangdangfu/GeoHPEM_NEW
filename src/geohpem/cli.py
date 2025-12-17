from __future__ import annotations

import argparse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="geohpem")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("about", help="Show basic project info.")
    ex = sub.add_parser("contract-example", help="Write a minimal Contract v0.1 example into a folder.")
    ex.add_argument("--out", default=None, help="Output folder (default: examples/contract_v0_1_minimal)")

    gui = sub.add_parser("gui", help="Launch the GUI.")
    gui.add_argument("--open", dest="open_dir", default=None, help="Open a case folder on startup.")

    run = sub.add_parser("run", help="Run a solver (fake or external) for a prepared request folder.")
    run.add_argument("case_dir", help="Folder containing request.json + mesh.npz")
    run.add_argument(
        "--solver",
        default="fake",
        help="Solver backend: fake | python:<module> (default: fake)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from geohpem.util.logging import configure_logging

    configure_logging()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "about":
        from geohpem import __version__

        print(f"geohpem {__version__}")
        return 0

    if args.cmd == "contract-example":
        from geohpem.examples.contract_example import write_contract_example

        out = write_contract_example(args.out)
        print(out)
        return 0

    if args.cmd == "run":
        from geohpem.app.run_case import run_case

        run_case(case_dir=args.case_dir, solver_selector=args.solver)
        return 0

    if args.cmd == "gui":
        from geohpem.gui.app import run_gui

        return int(run_gui(open_case_dir=args.open_dir))

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
