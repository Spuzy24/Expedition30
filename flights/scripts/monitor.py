#!/usr/bin/env python3
"""Price monitor: re-run a saved watchlist of searches, track the cheapest price per check
over time, and flag new lows / prices under the user's threshold.

Designed to be run by a scheduled Routine (or manually) after a hunt, so the agent only has
to read the summary. Each check is a normal toolkit command; the monitor adds the right
JSON flag, extracts the minimum EUR price from the JSON, and keeps history.

WHAT THE NUMBER IS: the cheapest row of each check's output, FARE ONLY: no ground, no bags,
no extras, in the tool's party convention (Kiwi MCP/Skiplagged with --adults N = party total).
It is NOT a quotes.py total, so set threshold_eur on the fare and re-verify the full total
(quotes.py) before telling the user. Build every check like-for-like, or a "new low" is just a
worse construction:
  - no Kiwi bag flags (--bags / --checked-bags): they add Kiwi's bag add-on and hide MU/CA/CZ;
  - --no-self-transfer (kiwi, kiwi_graphql, gflights) / --single-ticket (positioning) if the user
    wants single tickets;
  - one origin per check where possible (a multi-origin min can jump between airports with very
    different ground costs);
  - never ITA Matrix --no-avail (fare levels without seats are leads, not prices);
  - the real --adults; no hidden-city (mcp_flights sk excludes it by default).

Watch file (flights/searches/<trip>/watch.json):
{
  "trip": "tyo-2027-05",
  "threshold_eur": 650,                      # alert when a check's min first goes <= this
  "sleep": 8,                                # seconds between checks (politeness)
  "checks": [
    {"name": "momondo BUD RT", "json": "file:--json",
     "note": "MU/CZ single ticket via OTA; 2x23 included",           # optional, echoed in output
     "cmd": "kayak.py --site www.momondo.de --from BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26"},
    {"name": "kiwi mcp BUD RT 1-ticket", "json": "stdout:--json", "threshold_eur": 700,  # per-check override
     "cmd": "mcp_flights.py kiwi BUD TYO,OSA 2027-05-12 --ret 2027-05-26 --flex 2 --ret-flex 2 --no-self-transfer"},
    {"name": "GF BUD RT", "json": "file:--out",
     "cmd": "gflights.py search --from BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26"},
    {"name": "Matrix MU", "json": "file:--out",
     "cmd": "matrix.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --route MU+ --route-ret MU+"}
  ]
}
json modes: "file:<flag>" appends `<flag> <tmpfile>` and reads it; "stdout:<flag>" appends <flag>
and parses stdout. Commands are relative to flights/scripts/. Optional per check: "note"
(free text, printed under the check's line and in --history) and "threshold_eur" (overrides
the file-level one).

Usage:
  python3 monitor.py flights/searches/tyo-2027-05/watch.json            # run all checks
  python3 monitor.py flights/searches/tyo-2027-05/watch.json --only GF  # checks whose name contains GF
  python3 monitor.py flights/searches/tyo-2027-05/watch.json --history  # show stored history

State: watch_state.json next to the watch file (history, best, last_alert_price per check).
Lines starting with "ALERT" (the Routine just greps them):
  - "ALERT new low"         : a new all-time low for the check;
  - "ALERT under threshold" : only when the check FIRST goes <= threshold, or drops below the
                              last alerted price. While it stays at/above that price it prints
                              "(under threshold, alerted at EUR X)" without ALERT; going back
                              above the threshold re-arms the alert.
"""
import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PRICE_KEYS = ("eur", "price_eur", "total_eur", "priceEur", "total")


def min_eur(obj):
    """Walk any JSON and return (min_price_eur, the dict it came from)."""
    best = [None, None]

    def consider(v, d):
        try:
            v = float(v)
        except (TypeError, ValueError):
            return
        if v > 0 and (best[0] is None or v < best[0]):
            best[0], best[1] = v, d

    def walk(x):
        if isinstance(x, dict):
            hit = False
            for k in PRICE_KEYS:
                if k in x and isinstance(x[k], (int, float)):
                    consider(x[k], x)
                    hit = True
                    break
            if not hit and isinstance(x.get("price"), (int, float)):
                cur = str(x.get("currency") or x.get("cur") or "EUR").upper()
                if cur == "EUR":
                    consider(x["price"], x)
            for v in x.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return best[0], best[1]


def describe(d):
    if not isinstance(d, dict):
        return ""
    keys = ("route", "route_out", "itinerary", "airlines", "carriers", "airline", "provider", "seller",
            "out", "depart", "times", "flights")
    parts = [f"{d[k]}" for k in keys if d.get(k)]
    return " | ".join(str(p) for p in parts)[:160]


def run_check(chk, timeout):
    mode, _, flag = chk.get("json", "file:--json").partition(":")
    argv = shlex.split(chk["cmd"])
    script = os.path.join(HERE, argv[0])
    cmd = [sys.executable, script] + argv[1:]
    tmp = None
    if mode == "file":
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        cmd += [flag, tmp]
    elif flag:
        cmd += [flag]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=HERE)
    except subprocess.TimeoutExpired:
        return None, None, f"timeout after {timeout}s", time.time() - t0
    secs = time.time() - t0
    try:
        if mode == "file":
            with open(tmp) as f:
                data = json.load(f)
        else:
            out = p.stdout
            data = json.loads(out[out.find("{") if out.strip().startswith("{") else out.find("["):])
    except Exception as e:
        err = (p.stderr or p.stdout or "").strip().splitlines()[-1:] or [str(e)]
        return None, None, f"no JSON (exit {p.returncode}): {err[0][:160]}", secs
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    price, row = min_eur(data)
    if price is None:
        return None, None, f"no prices in output (exit {p.returncode})", secs
    return price, row, "", secs


def threshold_alert(h, price, thr, name, now):
    """Under-threshold alert lines; updates h['last_alert_price'].

    Fires when the check first goes <= thr, or when it drops below the last alerted price.
    A price back above thr clears last_alert_price, so the next crossing alerts again."""
    if thr is None:
        return []
    last_alert = h.get("last_alert_price")
    if price > thr:
        if last_alert is not None:
            h.pop("last_alert_price", None)
            h.pop("last_alert_ts", None)
            return [f"    (back above threshold €{thr}; under-threshold alert re-armed)"]
        return []
    if last_alert is None or price < last_alert:
        h["last_alert_price"], h["last_alert_ts"] = price, now
        was = f", last alert €{last_alert:.0f}" if last_alert is not None else ""
        return [f"ALERT under threshold: '{name}' €{price:.0f} <= €{thr}{was}"]
    return [f"    (under threshold, alerted at €{last_alert:.0f} on {h.get('last_alert_ts', '')[:10]})"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("watch")
    ap.add_argument("--only", help="substring filter on check names")
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args()

    with open(a.watch) as f:
        w = json.load(f)
    state_path = os.path.join(os.path.dirname(os.path.abspath(a.watch)), "watch_state.json")
    try:
        with open(state_path) as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}

    notes = {c["name"]: c.get("note") for c in w.get("checks", [])}
    if a.history:
        for name, h in state.items():
            la = f"  last alert €{h['last_alert_price']:.0f}" if h.get("last_alert_price") is not None else ""
            print(f"== {name}  best €{h.get('best')} ({h.get('best_ts', '')[:16]}){la}")
            if notes.get(name):
                print(f"   note: {notes[name]}")
            for e in h.get("runs", [])[-15:]:
                print(f"   {e['ts'][:16]}  €{e.get('price')}  {e.get('err', '') or e.get('desc', '')}")
        return

    thr = w.get("threshold_eur")
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    print(f"# Monitor {w.get('trip', '')}  {now}  threshold €{thr}")
    overall = None
    for i, chk in enumerate(w["checks"]):
        if a.only and a.only.lower() not in chk["name"].lower():
            continue
        if i:
            time.sleep(w.get("sleep", 8))
        price, row, err, secs = run_check(chk, a.timeout)
        h = state.setdefault(chk["name"], {"runs": []})
        prev_best = h.get("best")
        last = h["runs"][-1]["price"] if h["runs"] and h["runs"][-1].get("price") else None
        entry = {"ts": now, "price": price, "err": err, "desc": describe(row) if row else ""}
        h["runs"].append(entry)
        h["runs"] = h["runs"][-200:]
        if price is None:
            print(f"- {chk['name']}: FAILED ({err}) [{secs:.0f}s]")
            if chk.get("note"):
                print(f"    note: {chk['note']}")
            continue
        delta = f" ({price - last:+.0f} vs last)" if last else ""
        print(f"- {chk['name']}: €{price:.0f}{delta}  {entry['desc']} [{secs:.0f}s]")
        if chk.get("note"):
            print(f"    note: {chk['note']}")
        if prev_best is None or price < prev_best:
            h["best"], h["best_ts"] = price, now
            if prev_best is not None:
                print(f"ALERT new low for '{chk['name']}': €{price:.0f} (was €{prev_best:.0f})")
        for line in threshold_alert(h, price, chk.get("threshold_eur", thr), chk["name"], now):
            print(line)
        overall = price if overall is None else min(overall, price)
    with open(state_path, "w") as f:
        json.dump(state, f, indent=1)
    print(f"cheapest this run: €{overall:.0f}" if overall else "cheapest this run: n/a")


if __name__ == "__main__":
    main()
