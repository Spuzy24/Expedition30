#!/usr/bin/env python3
"""Quote log: one place to record every fare found, from any source, and rank
them by TRUE total cost (fare + bags + ground transport + extras + card fee).

Data lives in flights/searches/quotes.jsonl (append-only, one JSON per line;
--quotes-file PATH or env FLIGHTS_QUOTES_FILE points elsewhere, e.g. for tests).

Ground costs per departure airport (per person, ROUND TRIP home<->airport) come from
  1. --ground-file PATH (global option: overrides everything), else
  2. flights/searches/<trip>/ground.json if that file exists (per-trip file: use it for a
     different home base so older trips keep their totals), else
  3. the shared flights/searches/ground.json (`quotes.py ground-init`, edit it to match reality).

Commands
  add          record a quote (--lead for a non-bookable fare level, --supersedes for a re-price)
  list         quotes ranked by per-person total EUR
               filters: --trip --since --source --rt-only --ow-only --latest --need-bag [EUR]
                        --include-leads --include-superseded --top N
  best         best bookable quote per (origin, destination); same filters except leads,
               which are never used
  ground-init  write a starter ground.json (shared file, or --trip T for a per-trip file)

Examples
  python3 quotes.py add --trip tyo-2027-03 --source google_flights \\
      --origin VIE --dest NRT --out 2027-03-10 --ret 2027-03-24 \\
      --price 612 --cur EUR --carriers "CA" --stops 1 --via PEK \\
      --bags-included 2x23 --seller "Air China" --link "https://..." \\
      --notes "1 ticket, protected connection"
  python3 quotes.py add ... --price 2350 --cur PLN --bag-cost 0 --self-transfer
  python3 quotes.py add ... --source matrix --lead              # Matrix --no-avail fare level
  python3 quotes.py add ... --price 744 --supersedes 12         # re-price of row #12 (hides it)
  python3 quotes.py list --trip tyo-2027-03 --top 20 --latest --need-bag 70
  python3 quotes.py list --trip tyo-2027-03 --ow-only
  python3 quotes.py best --trip tyo-2027-03 --rt-only
  python3 quotes.py --ground-file /tmp/ground_ljubljana.json list --trip lju-2027-06
  python3 quotes.py ground-init --trip lju-2027-06              # per-trip starter file

Total cost (EUR, per person) = fare_eur*(1+card_fee%) + bag_cost_eur + extras_eur + ground
  Round trip : ground = the airport's 'eur' (round trip), or half of each airport's 'eur' for an
               open jaw on the home side; + the departure airport's 'hotel' (once, never halved).
  One-way    : (no --ret) ground = HALF the home-side airport's 'eur'; + its 'hotel' only when the
               row is the OUTBOUND departure. Direction: origin listed in the ground file = outbound,
               else dest listed = return leg; force it with `add --leg out|ret`. Dates show 'OW'.
  --ground EUR on `add` replaces the computed ground as-is (give a one-way figure for one-ways).
Everything is PER PERSON: --bag-cost and --extras are per person; a fare recorded with
--per total is divided by --pax before ranking. Airports missing from the ground file get a
conservative default (ground file '_missing_eur', else the most expensive airport) and show '?'.

Columns
  #       row number in the quote log (use it with `add --supersedes N`)
  bag€    '0?' = no bag cost set and --bags-included does not clearly include a checked bag
          (clear: 1x23, 2x23, '2 x 23kg', '2PC', '1 checked', 'checked', 'incl', a bare '2').
          `--need-bag` lists them in a footer; `--need-bag EUR` also adds EUR to their total
          (shown as ~EUR) so bagless fares stop outranking bag-inclusive ones.
  extra€  --extras (hotel night, seats, transit visa...)
  risk    'LEAD' = non-bookable fare level (add --lead, or --risk lead): hidden from the default
          list (--include-leads shows them) and never used by `best`.
Re-prices: `list/best --latest` keeps only the newest row per (trip, origin, dest, return_from,
return_to, out, ret, carriers, seller, source). `add --supersedes N[,N]` (row numbers, or a full
timestamp if it is unique in the trip) hides those rows everywhere (--include-superseded shows them).
`add` warns when the departure airport has a 'hotel_if' note in the ground file and --extras is 0:
check the flight time and pass --extras <hotel EUR> if a night before is needed.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fx import to_eur  # noqa: E402

DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "searches"))
QUOTES = os.environ.get("FLIGHTS_QUOTES_FILE") or os.path.join(DATA_DIR, "quotes.jsonl")
GROUND = os.path.join(DATA_DIR, "ground.json")
GROUND_OVERRIDE = None  # --ground-file
_GROUND_CACHE = {}

# Starter values: per person, home(Zagreb) -> airport -> home, cheapest
# realistic public transport, EUR. VERIFY/EDIT in ground.json before relying on it.
GROUND_STARTER = {
    "_comment": "Per-person ROUND-TRIP ground cost EUR from home (Zagreb) to each airport, cheapest realistic option. Edit me. Add 'hotel' if an early flight forces a night before.",
    "ZAG": {"eur": 10, "how": "airport bus/Uber", "hours": 0.5},
}


# ---------------------------------------------------------------- ground
def ground_path(trip=None):
    """--ground-file, else flights/searches/<trip>/ground.json if present, else the shared file."""
    if GROUND_OVERRIDE:
        return GROUND_OVERRIDE
    if trip and re.fullmatch(r"[\w][\w.-]*", trip):
        p = os.path.join(DATA_DIR, trip, "ground.json")
        if os.path.isfile(p):
            return p
    return GROUND


def load_ground(trip=None):
    path = ground_path(trip)
    if path not in _GROUND_CACHE:
        try:
            with open(path) as f:
                _GROUND_CACHE[path] = json.load(f)
        except FileNotFoundError:
            if path == GROUND_OVERRIDE:
                sys.exit(f"--ground-file {path}: file not found")
            _GROUND_CACHE[path] = GROUND_STARTER
    return _GROUND_CACHE[path]


def ground_parts(iata, ground):
    """(round-trip transport EUR, hotel-night EUR) for an airport, or None if not in ground.json."""
    g = ground.get(iata.upper()) if iata else None
    if isinstance(g, dict):
        return float(g.get("eur", 0)), float(g.get("hotel", 0) or 0)
    return None


def ground_cost(iata, ground):
    parts = ground_parts(iata, ground)
    return None if parts is None else parts[0] + parts[1]


def missing_ground_eur(ground):
    """Conservative stand-in for an airport missing from ground.json: ground['_missing_eur'] if set,
    else the most expensive known airport. (Treating it as 0 ranked unknown airports FIRST.)"""
    if isinstance(ground.get("_missing_eur"), (int, float)):
        return float(ground["_missing_eur"])
    vals = [float(v.get("eur", 0)) for k, v in ground.items() if isinstance(v, dict) and not k.startswith("_")]
    return max(vals, default=0.0)


# ---------------------------------------------------------------- quote helpers
def load_quotes():
    """All quotes; each gets '_n' = its 1-based row number in the log (not stored)."""
    out = []
    if not os.path.exists(QUOTES):
        return out
    with open(QUOTES) as f:
        for line in f:
            line = line.strip()
            if line:
                q = json.loads(line)
                q["_n"] = len(out) + 1
                out.append(q)
    return out


def is_oneway(q):
    return not q.get("ret")


def is_lead(q):
    return bool(q.get("lead")) or str(q.get("risk") or "").strip().lower() == "lead"


def oneway_leg(q, ground):
    """'out' (home -> away: ground at origin, + hotel) or 'ret' (away -> home: ground at dest)."""
    if q.get("leg") in ("out", "ret"):
        return q["leg"]
    if ground_parts(q.get("origin"), ground) is not None:
        return "out"
    if ground_parts(q.get("dest"), ground) is not None:
        return "ret"
    return "out"


def departure_airport(q, ground):
    """Home-side airport of the OUTBOUND departure, or None for a one-way return leg."""
    if is_oneway(q) and oneway_leg(q, ground) == "ret":
        return None
    return q.get("origin")


def total(q, ground=None):
    """Per-person total EUR (quotes recorded with --per total are divided by pax).

    Returns (total, ground_eur, ground_missing)."""
    if ground is None:
        ground = load_ground(q.get("trip"))
    div = q.get("pax", 1) if q.get("per") == "total" else 1
    fare = q["price_eur"] / div * (1 + q.get("card_fee_pct", 0) / 100.0)
    g_out, missing = q.get("ground_eur"), False
    if g_out is None:
        o = q["origin"]
        dflt = (missing_ground_eur(ground), 0.0)
        if is_oneway(q):
            # one-way: half the round-trip ground of the home-side airport; hotel only before an outbound
            if oneway_leg(q, ground) == "out":
                p = ground_parts(o, ground)
                e, h = p or dflt
                g_out = e / 2 + h
            else:
                p = ground_parts(q.get("dest"), ground)
                e, _h = p or dflt
                g_out = e / 2
            missing = p is None
        else:
            r = q.get("return_to") or o
            p1, p2 = ground_parts(o, ground), ground_parts(r, ground)
            missing = p1 is None or p2 is None
            (e1, h1), (e2, _h2) = p1 or dflt, p2 or dflt
            # transport: the round-trip figure for one airport, or half of each for an open jaw;
            # hotel: only the night before the OUTBOUND flight, never halved, never at the return airport
            g_out = (e1 if r == o else e1 / 2 + e2 / 2) + h1
    t = fare + q.get("bag_cost_eur", 0) + q.get("extras_eur", 0) + g_out
    return round(t, 2), round(g_out, 2), missing


# A checked bag is "clearly included" only with a positive statement and no hedge/negation.
_BAG_YES = re.compile(
    r"[1-9]\s*x\s*(1[5-9]|[2-4]\d)(?!\d)"      # 1x23, 2x23, 2 x 23kg, 1x20
    r"|\b[1-9]\s*(pc|pcs|piece|pieces)\b"       # 2PC
    r"|\b(1[5-9]|[2-4]\d)\s*kg\b"               # 23kg
    r"|\bchecked\b|\bhold\b|\bincl"              # '1 checked', 'checked bag incl.'
    r"|^\s*[1-9]\s*$",                           # a bare count, e.g. momondo BAGS '2'
    re.I)
_BAG_NO = re.compile(
    r"\b(no|not|non|without|excl\w*|extra|fees?|paid|unknown|none|n/a)\b|\?"
    r"|\b(checked|hold)\W*0\b|\b0\s*(x\b|checked|hold|pc)"
    r"|\b(carry-on|cabin|hand)[- ]?(bag\s*)?only\b",
    re.I)


def bag_known(q):
    """True if a checked bag is costed (bag_cost_eur > 0) or bags_included clearly includes one."""
    if float(q.get("bag_cost_eur") or 0) > 0:
        return True
    s = str(q.get("bags_included") or "")
    return bool(_BAG_YES.search(s)) and not _BAG_NO.search(s)


def dedupe_key(q):
    return (q.get("trip"), q.get("origin"), q.get("dest"), q.get("return_from") or q.get("dest"),
            q.get("return_to") or q.get("origin"), q.get("out"), q.get("ret") or "",
            q.get("carriers") or "", q.get("seller") or "", q.get("source") or "")


def latest_only(qs):
    best = {}
    for q in qs:  # file order; a later row with the same ts wins
        k = dedupe_key(q)
        if k not in best or (q.get("ts") or "") >= (best[k].get("ts") or ""):
            best[k] = q
    return list(best.values())


def superseded_set(all_qs):
    """Row numbers hidden by a later row's --supersedes (matched on row number AND timestamp)."""
    by_n = {q["_n"]: q for q in all_qs}
    hidden = set()
    for q in all_qs:
        for s in q.get("supersedes") or []:
            old = by_n.get(s.get("n"))
            if old is not None and old.get("ts") == s.get("ts"):
                hidden.add(old["_n"])
    return hidden


def resolve_supersedes(spec, trip, all_qs):
    """'12,#13' or a timestamp -> [{'n': 12, 'ts': ...}, ...]; exits on unknown/ambiguous refs."""
    out = []
    by_n = {q["_n"]: q for q in all_qs}
    for ref in [x.strip() for x in spec.split(",") if x.strip()]:
        r = ref.lstrip("#")
        if r.isdigit():
            q = by_n.get(int(r))
            if q is None:
                sys.exit(f"--supersedes {ref}: no row #{r} in {QUOTES}")
            if q.get("trip") != trip:
                print(f"note: row #{r} is trip '{q.get('trip')}', not '{trip}'", file=sys.stderr)
            hits = [q]
        else:
            hits = [q for q in all_qs if q.get("trip") == trip and (q.get("ts") or "").startswith(ref)]
            if not hits:
                sys.exit(f"--supersedes {ref}: no row of trip '{trip}' has that timestamp")
            if len(hits) > 1:
                sys.exit(f"--supersedes {ref}: ambiguous ({len(hits)} rows share it: "
                         f"{', '.join('#%d' % h['_n'] for h in hits)}); pass the row number(s)")
        out += [{"n": h["_n"], "ts": h.get("ts")} for h in hits]
    return out


def hotel_warning(q, ground):
    """Text of the hotel_if warning for `add`, or None."""
    if float(q.get("extras_eur") or 0) > 0:
        return None
    ap = departure_airport(q, ground)
    g = ground.get(ap) if ap else None
    if not isinstance(g, dict) or not g.get("hotel_if") or float(g.get("hotel") or 0) > 0:
        return None
    return (f"WARNING: ground file says {ap} hotel_if: '{g['hotel_if']}', and --extras is 0. Check the "
            f"departure time on {q.get('out')}; if a night before is needed, re-log with --extras <hotel EUR> "
            f"(and --supersedes the row printed above).")


# ---------------------------------------------------------------- commands
def cmd_add(a):
    if a.per == "total" and a.pax < 2:
        sys.exit("--per total needs --pax N (N >= 2); otherwise the fare is not divided")
    try:
        price_eur = a.price if a.cur.upper() == "EUR" else round(to_eur(a.price, a.cur), 2)
        bag_eur = a.bag_cost if a.bag_cur.upper() == "EUR" else round(to_eur(a.bag_cost, a.bag_cur), 2)
    except KeyError as e:
        sys.exit(f"unknown currency {e.args[0]}")
    all_qs = load_quotes()
    sup = resolve_supersedes(a.supersedes, a.trip, all_qs) if a.supersedes else None
    q = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "trip": a.trip, "source": a.source, "seller": a.seller,
        "origin": a.origin.upper(), "dest": a.dest.upper(),
        "return_from": (a.return_from or a.dest).upper(),
        "return_to": (a.return_to or a.origin).upper(),
        "out": a.out, "ret": a.ret, "pax": a.pax,
        "price": a.price, "cur": a.cur.upper(), "price_eur": price_eur,
        "per": a.per, "carriers": a.carriers, "stops": a.stops, "via": a.via,
        "duration": a.duration, "bags_included": a.bags_included,
        "bag_cost_eur": bag_eur, "extras_eur": a.extras,
        "card_fee_pct": a.card_fee, "self_transfer": a.self_transfer,
        "risk": a.risk, "link": a.link, "notes": a.notes, "verified_live": a.live,
    }
    if a.ground is not None:
        q["ground_eur"] = a.ground
    if a.lead:
        q["lead"] = True
    if a.leg:
        q["leg"] = a.leg
    if sup:
        q["supersedes"] = sup
    d = os.path.dirname(os.path.abspath(QUOTES))
    os.makedirs(d, exist_ok=True)
    with open(QUOTES, "a") as f:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
    ground = load_ground(a.trip)
    t, g, miss = total(q, ground)
    n = len(all_qs) + 1
    print(f"added #{n}: {q['origin']}->{q['dest']} {q['out']}/{q['ret'] or 'OW'} "
          f"{a.price} {q['cur']} (={price_eur} EUR) total≈{t} EUR (ground {g}"
          f"{' - NOT in ground file, conservative default used' if miss else ''})"
          f"{' [LEAD: not bookable, hidden from best/list]' if a.lead else ''}"
          f"{' [bags unknown: bag€ 0?]' if not bag_known(q) else ''}"
          f"{' [supersedes ' + ', '.join('#%d' % s['n'] for s in sup) + ']' if sup else ''}")
    if ground_path(a.trip) != GROUND:
        print(f"  ground file: {ground_path(a.trip)}")
    w = hotel_warning(q, ground)
    if w:
        print(w, file=sys.stderr)


def row_metrics(q, need_bag=None):
    """(rank total, ground, ground missing, bag unknown, bag estimate added)."""
    t, g, miss = total(q)
    unknown = not bag_known(q)
    est = need_bag if (need_bag and unknown) else 0.0
    return round(t + est, 2), g, miss, unknown, est


def fmt_rows(rows, need_bag=None):
    hdr = (f"{'#':>4} {'total€':>7} {'fare€pp':>7} {'gnd€':>5} {'bag€':>5} {'extra€':>6}  {'route':<17} "
           f"{'dates':<21} {'carrier/via':<20} {'st':>2} {'ST':<2} {'risk':<8} {'source/seller':<28} checked")
    print(hdr)
    print("-" * len(hdr))
    for q in rows:
        t, g, miss, unknown, est = row_metrics(q, need_bag)
        fare_pp = q["price_eur"] / (q.get("pax", 1) if q.get("per") == "total" else 1)
        route = f"{q['origin']}-{q['dest']}"
        if not is_oneway(q):
            if q.get("return_from") and q["return_from"] != q["dest"]:
                route += f"/{q['return_from']}"
            if q.get("return_to") and q["return_to"] != q["origin"]:
                route += f"-{q['return_to']}"
        dates = f"{q['out']}/{'OW' if is_oneway(q) else q['ret']}"
        cv = f"{q.get('carriers') or ''} {('via ' + q['via']) if q.get('via') else ''}".strip()
        src = f"{q['source']}/{q.get('seller') or ''}"
        gtxt = f"{g:.0f}{'?' if miss else ''}"
        if est:
            btxt = f"~{est:.0f}"
        elif unknown:
            btxt = "0?"
        else:
            btxt = f"{q.get('bag_cost_eur', 0):.0f}"
        risk = "LEAD" if is_lead(q) else (q.get("risk") or "")
        print(f"{q.get('_n', ''):>4} {t:>7.0f} {fare_pp:>7.0f} {gtxt:>5} {btxt:>5} {q.get('extras_eur', 0) or 0:>6.0f}  "
              f"{route:<17} {dates:<21} {cv[:20]:<20} {str(q.get('stops') if q.get('stops') is not None else ''):>2} "
              f"{'Y' if q.get('self_transfer') else '':<2} {risk[:8]:<8} {src[:28]:<28} {q['ts'][:16]}")
    notes = []
    if need_bag is not None:
        unk = [q for q in rows if not bag_known(q)]
        if unk:
            notes.append(f"note: {len(unk)} row(s) have no checked bag priced (bag€ {'~%.0f added' % need_bag if need_bag else '0?'}): "
                         f"{', '.join('#%s' % q.get('_n') for q in unk[:20])}. Confirm the allowance or re-log "
                         f"with --bag-cost / --bags-included 1x23 (--supersedes N).")
    paths = sorted({ground_path(q.get("trip")) for q in rows} - {GROUND})
    if paths:
        notes.append("note: ground file(s): " + ", ".join(paths))
    for n in notes:
        print(n)


def filt(a, leads=False):
    all_qs = load_quotes()
    qs = all_qs
    if a.trip:
        qs = [q for q in qs if q.get("trip") == a.trip]
    if getattr(a, "source", None):
        qs = [q for q in qs if q.get("source") == a.source]
    if getattr(a, "since", None):
        qs = [q for q in qs if q["ts"] >= a.since]
    if getattr(a, "rt_only", False):
        qs = [q for q in qs if not is_oneway(q)]
    if getattr(a, "ow_only", False):
        qs = [q for q in qs if is_oneway(q)]
    if not getattr(a, "include_superseded", False):
        hidden = superseded_set(all_qs)
        qs = [q for q in qs if q["_n"] not in hidden]
    if not leads:
        qs = [q for q in qs if not is_lead(q)]
    if getattr(a, "latest", False):
        qs = latest_only(qs)
    return qs


def cmd_list(a):
    qs = sorted(filt(a, leads=a.include_leads), key=lambda q: row_metrics(q, a.need_bag)[0])
    fmt_rows(qs[: a.top], a.need_bag)


def cmd_best(a):
    best = {}
    for q in filt(a, leads=False):  # a lead is not a bookable price: never "best"
        k = (q["origin"], q["dest"])
        if k not in best or row_metrics(q, a.need_bag)[0] < row_metrics(best[k], a.need_bag)[0]:
            best[k] = q
    fmt_rows(sorted(best.values(), key=lambda q: row_metrics(q, a.need_bag)[0]), a.need_bag)


def cmd_ground_init(a):
    path = GROUND_OVERRIDE or (os.path.join(DATA_DIR, a.trip, "ground.json") if a.trip else GROUND)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and not a.force:
        print(f"{path} exists (use --force to overwrite)")
        return
    with open(path, "w") as f:
        json.dump(GROUND_STARTER, f, indent=2)
    print(f"wrote {path}")


def main():
    global QUOTES, GROUND_OVERRIDE
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    def globals_(s, default):
        s.add_argument("--ground-file", default=default, metavar="PATH",
                       help="ground-cost JSON to use for every trip (overrides per-trip and shared files)")
        s.add_argument("--quotes-file", default=default, metavar="PATH",
                       help="quote log to read/append (default flights/searches/quotes.jsonl, env FLIGHTS_QUOTES_FILE)")

    globals_(p, None)
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("add", help="record a quote")
    globals_(s, argparse.SUPPRESS)
    s.add_argument("--trip", required=True, help="trip id, e.g. tyo-2027-03")
    s.add_argument("--source", required=True, help="where found: google_flights, kiwi, matrix, skyscanner, momondo, trip_com, airline, deal_site...")
    s.add_argument("--seller", default="", help="who you'd actually pay (airline or OTA name)")
    s.add_argument("--origin", required=True)
    s.add_argument("--dest", required=True)
    s.add_argument("--return-from", help="open-jaw: Japan airport you fly home from")
    s.add_argument("--return-to", help="open-jaw: home-side airport you return to")
    s.add_argument("--out", required=True, help="YYYY-MM-DD")
    s.add_argument("--ret", default=None, help="YYYY-MM-DD (omit for one-way: one-way ground, 'OW' in dates)")
    s.add_argument("--leg", choices=["out", "ret"],
                   help="one-way only: out = home->away (ground at origin + hotel), ret = away->home "
                        "(ground at dest). Default: auto from the ground file")
    s.add_argument("--pax", type=int, default=1)
    s.add_argument("--per", default="person", choices=["person", "total"])
    s.add_argument("--price", type=float, required=True)
    s.add_argument("--cur", default="EUR")
    s.add_argument("--carriers", default="")
    s.add_argument("--stops", type=int)
    s.add_argument("--via", default="")
    s.add_argument("--duration", default="", help="e.g. 17h30 out / 15h ret")
    s.add_argument("--bags-included", default="",
                   help="e.g. 'carry-on 8kg', '1x23', '2x23', 'unknown'. Not clearly a checked bag -> bag€ '0?'")
    s.add_argument("--bag-cost", type=float, default=0.0, help="extra cost to add the bags the traveler needs")
    s.add_argument("--bag-cur", default="EUR")
    s.add_argument("--extras", type=float, default=0.0, help="EUR: hotel night, seat, transit visa, airport transfer at layover...")
    s.add_argument("--ground", type=float, default=None,
                   help="override ground cost EUR, used as-is (round trip; for a one-way give the one-way figure)")
    s.add_argument("--card-fee", type=float, default=0.0, help="%% FX/card fee if paying in foreign currency")
    s.add_argument("--self-transfer", action="store_true", help="separate tickets / unprotected connection")
    s.add_argument("--risk", default="", help="safe | low | moderate | risky | tos | lead")
    s.add_argument("--lead", action="store_true",
                   help="non-bookable fare level (e.g. ITA Matrix --no-avail): shown as LEAD, excluded from "
                        "best and from the default list")
    s.add_argument("--supersedes", metavar="N[,N]",
                   help="row number(s) from the list '#' column (or a timestamp unique in the trip) that this "
                        "quote replaces; they are hidden from list/best")
    s.add_argument("--live", action="store_true", help="price re-verified on the seller's checkout page")
    s.add_argument("--link", default="")
    s.add_argument("--notes", default="")
    s.set_defaults(fn=cmd_add)

    for name, fn, hlp in (("list", cmd_list, "quotes ranked by per-person total"),
                          ("best", cmd_best, "best bookable quote per origin->destination")):
        s = sp.add_parser(name, help=hlp)
        globals_(s, argparse.SUPPRESS)
        s.add_argument("--trip")
        s.add_argument("--source")
        s.add_argument("--since", help="ISO date/time prefix")
        s.add_argument("--top", type=int, default=30)
        g = s.add_mutually_exclusive_group()
        g.add_argument("--rt-only", action="store_true", help="round trips only (rows with a return date)")
        g.add_argument("--ow-only", action="store_true", help="one-way rows only")
        s.add_argument("--latest", action="store_true",
                       help="keep only the newest row per (trip, origin, dest, return_from, return_to, out, ret, "
                            "carriers, seller, source)")
        s.add_argument("--need-bag", nargs="?", type=float, const=0.0, default=None, metavar="EUR",
                       help="the traveller needs a checked bag: list rows whose bag status is unknown (bag€ 0?); "
                            "with EUR, add that per-person estimate to their total")
        s.add_argument("--include-superseded", action="store_true", help="also show rows hidden by --supersedes")
        if name == "list":
            s.add_argument("--include-leads", action="store_true", help="also show LEAD rows (non-bookable fare levels)")
        s.set_defaults(fn=fn)

    s = sp.add_parser("ground-init", help="write a starter ground.json")
    globals_(s, argparse.SUPPRESS)
    s.add_argument("--trip", help="write flights/searches/<trip>/ground.json (per-trip file) instead of the shared one")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_ground_init)

    a = p.parse_args()
    if a.quotes_file:
        QUOTES = os.path.abspath(a.quotes_file)
    if a.ground_file:
        GROUND_OVERRIDE = os.path.abspath(a.ground_file)
    a.fn(a)


if __name__ == "__main__":
    main()
