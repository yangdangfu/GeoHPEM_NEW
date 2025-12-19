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
        help="Solver backend: fake | ref_elastic | ref_seepage | python:<module> (default: fake)",
    )

    batch = sub.add_parser("batch-run", help="Run many case folders under a root directory.")
    batch.add_argument("root", help="Root folder containing multiple case folders (or a single case folder).")
    batch.add_argument(
        "--solver",
        default="fake",
        help="Solver backend: fake | ref_elastic | ref_seepage | python:<module> (default: fake)",
    )
    batch.add_argument("--baseline", default=None, help="Baseline root folder for optional comparisons.")
    batch.add_argument("--report", default=None, help="Write a JSON report to this path (default: <root>/batch_report.json)")
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

    if args.cmd == "batch-run":
        from pathlib import Path

        from geohpem.app.case_runner import discover_case_folders, run_cases, write_case_run_report

        root = Path(args.root)
        cases = discover_case_folders(root)
        if not cases:
            raise SystemExit(f"No case folders found under: {root}")

        baseline = Path(args.baseline) if args.baseline else None
        records = run_cases(cases, solver_selector=args.solver, baseline_root=baseline)

        report = Path(args.report) if args.report else (root / "batch_report.json")
        write_case_run_report(records, report)
        failed = sum(1 for r in records if r.status == "failed")
        canceled = sum(1 for r in records if r.status == "canceled")
        print(f"Wrote report: {report} (cases={len(records)}, failed={failed}, canceled={canceled})")
        return 0

    if args.cmd == "gui":
        from geohpem.gui.app import run_gui

        return int(run_gui(open_case_dir=args.open_dir))

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
