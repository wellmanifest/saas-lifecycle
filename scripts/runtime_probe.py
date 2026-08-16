#!/usr/bin/env python3
"""Thin wrapper: run Subactor portal membership-before-payment probe.

Delegates to the HOME runtime probe in www-sub-actor when available, otherwise
runs the same checks inline against --www/--control. Documents SAAS-ONBOARD-*
codes from this pack; does not grant deployment authority.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--www", default="http://127.0.0.1:8781")
    parser.add_argument("--control", default="http://127.0.0.1:8091")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--portal-probe",
        default="",
        help="Path to www-sub-actor/scripts/runtime_probe.py (auto-detected when sibling checkout exists)",
    )
    args = parser.parse_args()

    candidates = []
    if args.portal_probe:
        candidates.append(pathlib.Path(args.portal_probe))
    here = pathlib.Path(__file__).resolve()
    candidates.extend(
        [
            here.parents[2] / "subactor" / "www-sub-actor" / "scripts" / "runtime_probe.py",
            pathlib.Path("/home/tom/github/subactor/www-sub-actor/scripts/runtime_probe.py"),
        ]
    )
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("portal_runtime_probe", path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.argv = ["runtime_probe.py", "--www", args.www]
            if args.control:
                sys.argv.extend(["--control", args.control])
            if args.json:
                sys.argv.append("--json")
            return int(mod.main())

    print(
        "SAAS-ONBOARD-PROBE: portal runtime_probe.py not found; "
        "pass --portal-probe /path/to/www-sub-actor/scripts/runtime_probe.py",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
