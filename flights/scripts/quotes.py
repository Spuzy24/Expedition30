#!/usr/bin/env python3
"""Quote log: one place to record every fare found, from any source, and rank
them by TRUE total cost (fare + bags + ground transport + extras + card fee).

Data lives in flights/searches/quotes.jsonl (append-only, one JSON per line).
Ground-transport costs per origin airport come from flights/searches/ground.json
(created by `quotes.py ground-init`, edit it to match reality).

Commands
  add      record a quote
  list     show quotes ranked by total EUR (filters: --trip, --since, --source)
  best     best quote per (origin, destination) pair
  ground-init   write a starter ground.json for the Zagreb region

Examples
  python3 quotes.py add --trip tyo-2027-03 --source google_flights \
      --origin VIE --dest NRT --out 2027-03-10 --ret 2027-03-24 \
      --price 612 --cur EUR --carriers "CA" --stops 1 --via PEK \
      --bags-included 2x23 --seller "Air China" --link "https://..." \
      --notes "1 ticket, protected connection"
  python3 quotes.py add ... --price 2350 --cur PLN --bag-cost 0 --self-transfer
  python3 quotes.py list --trip tyo-2027-03 --top 20
  python3 quotes.py best --trip tyo-2027-03

Total cost (EUR) = fare_eur*(1+card_fee%) + bag_cost_eur + ground_eur(origin)
                   + ground_eur(return airport if different/open-jaw)
                   + extras_eur (hotel night before, seat fees, transit visa...)
Everything is PER PERSON: ground cost (round trip from home, from ground.json
unless --ground overrides it), --bag-cost and --extras. A fare recorded with
--per total is divided by --pax before ranking. A ground.json 'hotel' is counted once,
for the departure airport only. Airports missing from ground.json get a conservative
default (ground.json '_missing_eur', else the most expensive airport) and show '?'.
"""
import argparse
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fx import to_eur  # noqa: E402

DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "searches"))
QUOTES = os.path.join(DATA_DIR, "quotes.jsonl")
GROUND = os.path.join(DATA_DIR, "ground.json")

# Starter values: per person, home(Zagreb) -> airport -> home, cheapest
# realistic public transport, EUR. VERIFY/EDIT in ground.json before relying on it.
GROUND_STARTER = {
    "_comment": "Per-person ROUND-TRIP ground cost EUR from home (Zagreb) to each airport, cheapest realistic option. Edit me. Add 'hotel' if an early flight forces a night before.",
    "ZAG": {"eur": 10, "how": "airport bus/Uber", "hours": 0.5},
}


def load_ground():
    try:
        with open(GROUND) as f:
            return json.load(f)
    except FileNotFoundError:
        return GROUND_STARTER


def ground_parts(iata, ground):
    """(round-trip transport EUR, hotel-night EUR) for an airport, or None if not in ground.json."""
    g = ground.get(iata.upper()) if iata else None
    if isinstance(g, dict):
        return float(g.get("eur", 0)), float(g.get("hotel", 0))
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


def load_quotes():
    out = []
    if not os.path.exists(QUOTES):
        return out
    with open(QUOTES) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def total(q, ground):
    """Per-person total EUR (quotes recorded with --per total are divided by pax).

    Returns (total, ground_eur, ground_missing)."""
    div = q.get("pax", 1) if q.get("per") == "total" else 1
    fare = q["price_eur"] / div * (1 + q.get("card_fee_pct", 0) / 100.0)
    g_out, missing = q.get("ground_eur"), False
    if g_out is None:
        o = q["origin"]
        r = q.get("return_to") or o
        p1, p2 = ground_parts(o, ground), ground_parts(r, ground)
        missing = p1 is None or p2 is None
        dflt = (missing_ground_eur(ground), 0.0)
        (e1, h1), (e2, _h2) = p1 or dflt, p2 or dflt
        # transport: the round-trip figure for one airport, or half of each for an open jaw;
        # hotel: only the night before the OUTBOUND flight, never halved, never at the return airport
        g_out = (e1 if r == o else e1 / 2 + e2 / 2) + h1
    t = fare + q.get("bag_cost_eur", 0) + q.get("extras_eur", 0) + g_out
    return round(t, 2), round(g_out, 2), missing


def cmd_add(a):
    os.makedirs(DATA_DIR, exist_ok=True)
    if a.per == "total" and a.pax < 2:
        sys.exit("--per total needs --pax N (N >= 2); otherwise the fare is not divided")
    try:
        price_eur = a.price if a.cur.upper() == "EUR" else round(to_eur(a.price, a.cur), 2)
        bag_eur = a.bag_cost if a.bag_cur.upper() == "EUR" else round(to_eur(a.bag_cost, a.bag_cur), 2)
    except KeyError as e:
        sys.exit(f"unknown currency {e.args[0]}")
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
    with open(QUOTES, "a") as f:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")
    t, g, miss = total(q, load_ground())
    print(f"added: {q['origin']}->{q['dest']} {q['out']}/{q['ret'] or '-'} "
          f"{a.price} {q['cur']} (={price_eur} EUR) total≈{t} EUR (ground {g}"
          f"{' - NOT in ground.json, conservative default used' if miss else ''})")


def fmt_rows(rows, ground):
    hdr = f"{'total€':>8} {'fare€pp':>7} {'gnd€':>5} {'bag€':>5}  {'route':<17} {'dates':<23} {'carrier/via':<20} {'st':>2} {'ST':<2} {'risk':<8} {'source/seller':<28} checked"
    print(hdr)
    print("-" * len(hdr))
    for q in rows:
        t, g, miss = total(q, ground)
        fare_pp = q["price_eur"] / (q.get("pax", 1) if q.get("per") == "total" else 1)
        route = f"{q['origin']}-{q['dest']}"
        if q.get("return_from") and q["return_from"] != q["dest"]:
            route += f"/{q['return_from']}"
        if q.get("return_to") and q["return_to"] != q["origin"]:
            route += f"-{q['return_to']}"
        dates = f"{q['out']}/{q.get('ret') or '-'}"
        cv = f"{q.get('carriers') or ''} {('via ' + q['via']) if q.get('via') else ''}".strip()
        src = f"{q['source']}/{q.get('seller') or ''}"
        gtxt = f"{g:.0f}{'?' if miss else ''}"
        print(f"{t:>8.0f} {fare_pp:>7.0f} {gtxt:>5} {q.get('bag_cost_eur', 0):>5.0f}  "
              f"{route:<17} {dates:<23} {cv[:20]:<20} {str(q.get('stops') if q.get('stops') is not None else ''):>2} "
              f"{'Y' if q.get('self_transfer') else '':<2} {(q.get('risk') or '')[:8]:<8} {src[:28]:<28} {q['ts'][:16]}")


def filt(a):
    qs = load_quotes()
    if a.trip:
        qs = [q for q in qs if q.get("trip") == a.trip]
    if getattr(a, "source", None):
        qs = [q for q in qs if q.get("source") == a.source]
    if getattr(a, "since", None):
        qs = [q for q in qs if q["ts"] >= a.since]
    return qs


def cmd_list(a):
    ground = load_ground()
    qs = sorted(filt(a), key=lambda q: total(q, ground)[0])
    fmt_rows(qs[: a.top], ground)


def cmd_best(a):
    ground = load_ground()
    best = {}
    for q in filt(a):
        k = (q["origin"], q["dest"])
        if k not in best or total(q, ground)[0] < total(best[k], ground)[0]:
            best[k] = q
    fmt_rows(sorted(best.values(), key=lambda q: total(q, ground)[0]), ground)


def cmd_ground_init(a):
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(GROUND) and not a.force:
        print(f"{GROUND} exists (use --force to overwrite)")
        return
    with open(GROUND, "w") as f:
        json.dump(GROUND_STARTER, f, indent=2)
    print(f"wrote {GROUND}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("add")
    s.add_argument("--trip", required=True, help="trip id, e.g. tyo-2027-03")
    s.add_argument("--source", required=True, help="where found: google_flights, kiwi, matrix, skyscanner, momondo, trip_com, airline, deal_site...")
    s.add_argument("--seller", default="", help="who you'd actually pay (airline or OTA name)")
    s.add_argument("--origin", required=True)
    s.add_argument("--dest", required=True)
    s.add_argument("--return-from", help="open-jaw: Japan airport you fly home from")
    s.add_argument("--return-to", help="open-jaw: home-side airport you return to")
    s.add_argument("--out", required=True, help="YYYY-MM-DD")
    s.add_argument("--ret", default=None, help="YYYY-MM-DD (omit for one-way)")
    s.add_argument("--pax", type=int, default=1)
    s.add_argument("--per", default="person", choices=["person", "total"])
    s.add_argument("--price", type=float, required=True)
    s.add_argument("--cur", default="EUR")
    s.add_argument("--carriers", default="")
    s.add_argument("--stops", type=int)
    s.add_argument("--via", default="")
    s.add_argument("--duration", default="", help="e.g. 17h30 out / 15h ret")
    s.add_argument("--bags-included", default="", help="e.g. 'carry-on 8kg', '1x23', '2x23'")
    s.add_argument("--bag-cost", type=float, default=0.0, help="extra cost to add the bags the traveler needs")
    s.add_argument("--bag-cur", default="EUR")
    s.add_argument("--extras", type=float, default=0.0, help="EUR: hotel night, seat, transit visa, airport transfer at layover...")
    s.add_argument("--ground", type=float, default=None, help="override ground cost EUR (round trip)")
    s.add_argument("--card-fee", type=float, default=0.0, help="%% FX/card fee if paying in foreign currency")
    s.add_argument("--self-transfer", action="store_true", help="separate tickets / unprotected connection")
    s.add_argument("--risk", default="", help="safe | low | moderate | risky | tos")
    s.add_argument("--live", action="store_true", help="price re-verified on the seller's checkout page")
    s.add_argument("--link", default="")
    s.add_argument("--notes", default="")
    s.set_defaults(fn=cmd_add)

    for name, fn in (("list", cmd_list), ("best", cmd_best)):
        s = sp.add_parser(name)
        s.add_argument("--trip")
        s.add_argument("--source")
        s.add_argument("--since", help="ISO date/time prefix")
        s.add_argument("--top", type=int, default=30)
        s.set_defaults(fn=fn)

    s = sp.add_parser("ground-init")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_ground_init)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
