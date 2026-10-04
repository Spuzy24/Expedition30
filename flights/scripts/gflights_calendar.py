#!/usr/bin/env python3
"""Shortcut for `gflights.py calendar ...` (cheapest price per date) and `gflights.py grid ...`.

    python gflights_calendar.py --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 [--stay 14] [--heatmap]
    python gflights_calendar.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21

Global options (--gl/--curr/--hl/--sleep) may be given first, exactly as for gflights.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gflights  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:]
    glob, rest = [], list(argv)
    while rest and rest[0] in ("--gl", "--curr", "--hl", "--sleep", "--quiet"):
        if rest[0] == "--quiet":  # flag (no value); may appear between the others
            glob.append(rest.pop(0))
        else:
            glob += rest[:2]
            rest = rest[2:]
    if not rest or rest[0] not in ("calendar", "grid"):
        rest = ["calendar"] + rest
    gflights.main(glob + rest)
