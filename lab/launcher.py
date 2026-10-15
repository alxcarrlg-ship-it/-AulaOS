"""Executable entry point; diagnostics never open the user's database."""
import argparse
import json
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description='AulaOS')
    parser.add_argument('--self-test', metavar='REPORT', help='Write synthetic packaging checks to a new JSON report')
    parser.add_argument('--check-gui', action='store_true', help='Also initialize Tk during self-test')
    args = parser.parse_args(argv)
    if args.self_test:
        from release_check import run_checks
        report = run_checks(check_gui=args.check_gui)
        # Never overwrite an existing file, including a user's document.
        with Path(args.self_test).open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        return 0 if report['ok'] else 1
    if args.check_gui:
        parser.error('--check-gui requires --self-test')
    from aulaos_lab import AulaOS
    AulaOS().mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
