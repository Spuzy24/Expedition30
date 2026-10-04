#!/usr/bin/env python3
"""Combine a cheap positioning flight (Ryanair / Wizz, separate ticket) with the cheapest
long-haul fare to Japan from a European hub (Kiwi web GraphQL), respecting a minimum
connection buffer. Answers: "from my home airports, which hub + which day is cheapest in total?"

One-way (default):
  total = positioning (home -> hub, FR/W6 fare-only)  +  long-haul (hub -> Japan, Kiwi live)
  Direction "out": home -> hub (arrive >= --buffer hours before the long-haul departure;
                   the day before is allowed, i.e. an overnight at the hub)
  Direction "back": Japan -> hub, then hub -> home (depart >= --buffer hours after arrival,
                   same day or next day)
Round trip (--return-dates R1..R2, the Japan departure window of the return):
  total = hub<->Japan ROUND TRIP (Kiwi; often far below 2x one-way) + positioning home -> hub
          before it + positioning hub -> home after it (+ --pos-bag-eur per bag on EACH FR/W6 leg).
  If Kiwi's round trip comes back to another airport (e.g. out of BRU, back to CRL), the return
  positioning starts there. All parts are separate tickets (flag sep-tickets(N)).
A hub that is itself a home airport needs no positioning (cost 0).

Passengers: --adults N goes to the Kiwi long-haul, whose price is the PARTY TOTAL (verified
2026-10-04); FR/W6 fares are per person and are multiplied by N. Tables show "TOTAL EUR total
(N pax)" plus TOTAL EUR/pp; POS EUR/pp is per person; JSON total_eur (party) and total_pp.

Quick pre-check: --compare-home-rt EUR (per person, the best round trip from home) skips every
hub whose cheapest long-haul is not >= --min-saving (default 150) EUR/pp cheaper, printing
"skip: <HUB> hub RT not >= EUR 150 cheaper than home RT", before any FR/W6 lookup. Smaller
margins are eaten by positioning fares, bags, transfers and a hub night (dry run 2026-10-04:
ATH EUR 588 vs BUD EUR 717 left EUR 129 and could not win).

Examples
--------
  python3 positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --to TYO,OSA \
      --dates 2027-03-05..2027-03-12 --hubs BRU,IST,MXP,BGY,WAW,HEL,FRA,MUC,BCN,MAD,CDG,AMS,PRG,ARN,CPH,STN,DUB,FCO
  python3 positioning.py --direction back --home ZAG,VIE,BUD --to TYO,OSA --dates 2027-03-22..2027-03-26
  python3 positioning.py --home ZAG,BUD --to TYO,OSA --dates 2027-05-11..2027-05-13 \
      --return-dates 2027-05-25..2027-05-27 --hubs IST,BGY,STN,ATH --adults 2 --checked-bags 1 \
      --pos-bag-eur 45 --compare-home-rt 717

Caveats: positioning prices are fare-only (no cabin/checked bag); with --checked-bags the total adds
--pos-bag-eur per bag per positioning flight. The long-haul bag is Kiwi's add-on (no bag data for
MU/CA/CZ, whose fares include bags). Wizz timetable has no arrival time, so its arrival is
estimated as departure + --wizz-block hours, converted between the airports' time zones. Long-haul
fares may be Kiwi self-transfer combos themselves (flag shown); use --single-ticket to keep only
1-PNR long-haul. Sibling-airport ground transfers and hub hotel nights are not costed. Missed
connections on separate tickets are at your own risk - prefer an overnight buffer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import re
import sys
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import kiwi_graphql as kg
import ryanair_wizz as rw
from _common import dump_json, parse_date_range, price_header, print_table, split_codes

# Same-city alternative airports: positioning may land at a sibling and transfer by ground
# (extra --sibling-extra hours are required on top of --buffer). Total excludes ground cost.
SIBLINGS = {"BRU": ["CRL"], "CRL": ["BRU"], "MXP": ["BGY", "LIN"], "BGY": ["MXP", "LIN"],
            "LIN": ["MXP", "BGY"], "IST": ["SAW"], "SAW": ["IST"], "WAW": ["WMI"], "WMI": ["WAW"],
            "CDG": ["BVA", "ORY"], "ORY": ["CDG", "BVA"], "BVA": ["CDG", "ORY"],
            "LHR": ["STN", "LTN", "LGW"], "LGW": ["STN", "LTN", "LHR"], "STN": ["LTN", "LGW", "LHR"],
            "LTN": ["STN", "LGW", "LHR"], "ARN": ["NYO", "BMA"], "NYO": ["ARN"], "BCN": ["GRO", "REU"],
            "FCO": ["CIA"], "CIA": ["FCO"], "FRA": ["HHN"], "HHN": ["FRA"], "MUC": ["FMM"],
            "FMM": ["MUC"], "VIE": ["BTS"], "BTS": ["VIE"], "AMS": ["EIN"], "EIN": ["AMS"],
            "DUS": ["NRN", "CGN"], "OSL": ["TRF"], "TRF": ["OSL"], "CPH": ["MMX"], "MMX": ["CPH"]}

# Airport time zones, for the Wizz arrival estimate (Wizz's timetable has no arrival time:
# departure is origin-local, Kiwi's long-haul departure is hub-local, so "dep + block" must be
# converted, e.g. BUD->AUH 10:00 + 5.5 h block = 17:30 Dubai time, not 15:30).
_TZ = {"Europe/Zagreb": "ZAG", "Europe/Ljubljana": "LJU", "Europe/Vienna": "GRZ VIE KLU SZG LNZ",
       "Europe/Budapest": "BUD DEB", "Europe/Rome": "TSF VCE TRS MXP BGY LIN FCO CIA BLQ NAP PSA",
       "Europe/Bratislava": "BTS", "Europe/Brussels": "BRU CRL", "Europe/Istanbul": "IST SAW",
       "Europe/Warsaw": "WAW WMI KRK KTW GDN", "Europe/Helsinki": "HEL", "Europe/Berlin":
       "FRA HHN MUC FMM DUS NRN CGN BER HAM STR", "Europe/Madrid": "BCN GRO REU MAD",
       "Europe/Paris": "CDG ORY BVA", "Europe/Amsterdam": "AMS EIN", "Europe/Prague": "PRG",
       "Europe/Stockholm": "ARN NYO BMA MMX", "Europe/Copenhagen": "CPH", "Europe/Oslo": "OSL TRF",
       "Europe/London": "STN LTN LGW LHR", "Europe/Dublin": "DUB", "Europe/Athens": "ATH",
       "Europe/Lisbon": "LIS", "Europe/Belgrade": "BEG", "Europe/Bucharest": "OTP",
       "Europe/Sofia": "SOF", "Asia/Dubai": "AUH DXB", "Asia/Nicosia": "LCA PFO"}
AIRPORT_TZ = {ap: tz for tz, aps in _TZ.items() for ap in aps.split()}


def _wizz_arrival(dep: dt.datetime, o: str, d: str, block_h: float) -> dt.datetime:
    """Destination-local arrival = origin-local departure + block, converted between zones."""
    to, td = AIRPORT_TZ.get(o), AIRPORT_TZ.get(d)
    if not (to and td):
        return dep + dt.timedelta(hours=block_h)  # unknown zone: old behaviour
    arr = dep.replace(tzinfo=ZoneInfo(to)) + dt.timedelta(hours=block_h)
    return arr.astimezone(ZoneInfo(td)).replace(tzinfo=None)


@functools.lru_cache(maxsize=None)
def _fr_routes(origin: str) -> tuple:
    return tuple(rw.fr_routes(origin))  # was re-fetched for every (home, hub, sibling) pair


DEFAULT_HUBS = ("BRU,IST,SAW,MXP,BGY,FCO,WAW,HEL,FRA,MUC,BCN,MAD,CDG,BVA,AMS,PRG,ARN,CPH,"
                "STN,LGW,DUB,ATH,LIS,BUD,VIE")


def _dt(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.strip().replace(" ", "T")[:16])


def _last_airport(route: str) -> str:
    """'HND-PEK~PKX-BRU' -> 'BRU' (arrival airport of the last direction of a Kiwi route)."""
    return re.split(r"[-~]", route.split(" | ")[-1].strip())[-1]


def longhaul(hub: str, dests: list[str], d1: dt.date, d2: dt.date, back: bool, a,
             ret: tuple[dt.date, dt.date] | None = None) -> list[dict]:
    """Kiwi long-haul from/to `hub`. One-way (out or back), or with `ret` a hub<->Japan ROUND TRIP.
    Kiwi prices are the PARTY TOTAL for a.adults (verified 2026-10-04: 2 adults = 2x)."""
    ns = SimpleNamespace(origins=[",".join(dests)] if back else [hub],
                         dests=[hub] if back else [",".join(dests)],
                         dates=f"{d1}..{d2}", return_dates=f"{ret[0]}..{ret[1]}" if ret else None, nights=None,
                         currency="EUR", market="hr", adults=a.adults, checked_bags=a.checked_bags,
                         hand_bags=0, max_stops=None, no_self_transfer=a.single_ticket, hacks=False,
                         limit=0, limit_api=40)
    rows = kg.run_search(ns, quiet=True)
    out = []
    for r in rows:
        dep, arr = _dt(r["dep_local"]), _dt(r["arr_local"])  # first departure / last arrival (local)
        out.append({**r, "dep": dep, "arr": arr, "hub": hub, "ret_airport": _last_airport(r["route"]),
                    "lh_pp": round(r["eur"] / a.adults, 2)})
    return out


def positioning_flights(home: str, hub: str, d1: dt.date, d2: dt.date, back: bool, a) -> list[dict]:
    """FR/W6 flights home->hub (out) or hub->home (back); fares are PER PERSON, fare only."""
    o, d = (hub, home) if back else (home, hub)
    res = []
    if "FR" in a.airlines and d in _fr_routes(o):
        for f in rw.fr_cheapest_per_day(o, d, d1, d2):
            dep = _dt(f["date"])
            arr = (dt.datetime.combine(dep.date(), dt.time.fromisoformat(f["arr"])) if f.get("arr")
                   else dep + dt.timedelta(hours=a.wizz_block))
            if arr < dep:
                arr += dt.timedelta(days=1)
            res.append({**f, "dep": dep, "arr_dt": arr})
    if "W6" in a.airlines and d in rw.wizz_map().get(o, []):
        for f in rw.wizz_timetable(o, d, d1, d2)[0]:
            dep = _dt(f["date"])
            res.append({**f, "dep": dep, "arr_dt": _wizz_arrival(dep, o, d, a.wizz_block)})
    return [x for x in res if x.get("price_eur") is not None]


_POS_CACHE: dict[tuple, list[dict]] = {}


def pos_options(home: str, hub: str, p1: dt.date, p2: dt.date, back: bool, a) -> list[dict]:
    """Positioning flights incl. sibling airports of the hub (cached per query)."""
    k = (home, hub, p1, p2, back)
    if k not in _POS_CACHE:
        pos = positioning_flights(home, hub, p1, p2, back, a)
        if not a.no_siblings:
            for sib in SIBLINGS.get(hub, []):
                if sib == home:
                    continue
                for f in positioning_flights(home, sib, p1, p2, back, a):
                    f["sibling"] = sib
                    pos.append(f)
        _POS_CACHE[k] = pos
    return _POS_CACHE[k]


def best_pos(pos: list[dict], when: dt.datetime, back: bool, a) -> tuple[dict | None, float | None]:
    """Cheapest positioning flight that connects: out = lands >= buffer before `when` (long-haul
    departure); back = leaves >= buffer after `when` (long-haul arrival). Returns (flight, gap_h)."""
    best, gap_best = None, None
    for P in pos:
        gap = ((P["dep"] - when) if back else (when - P["arr_dt"])).total_seconds() / 3600
        need = a.buffer + (a.sibling_extra if P.get("sibling") else 0)
        if need <= gap <= a.max_gap and (best is None or P["price_eur"] < best["price_eur"]):
            best, gap_best = P, gap
    return best, (round(gap_best, 1) if gap_best is not None else None)


def _pos_txt(P: dict | None, hub: str) -> str:
    if P is None:
        return "-"
    return (f"{P['airline']} {P['from']}-{P['to']} {P['dep'].strftime('%m-%d %H:%M')}"
            + (f" (+ground {P['sibling']}<->{hub})" if P.get("sibling") else ""))


def _precheck(hub: str, lh: list[dict], a) -> bool:
    """--compare-home-rt: skip a hub whose cheapest long-haul (per person) is not at least
    --min-saving cheaper than the home round trip. Positioning, bags and nights eat smaller gaps."""
    if a.compare_home_rt is None or not lh:
        return True
    best = min(x["lh_pp"] for x in lh)
    if a.compare_home_rt - best < a.min_saving:
        what = "RT" if a.return_dates else "fare"
        print(f"[pos] skip: {hub} hub {what} not >= EUR {a.min_saving:.0f} cheaper than home RT "
              f"(hub EUR {best:.0f}/pp vs home EUR {a.compare_home_rt:.0f}/pp)", file=sys.stderr)
        return False
    return True


def run_oneway(a, homes, hubs, dests, d1, d2, back, pos_bag) -> list[dict]:
    combos = []
    n = a.adults
    for hub in hubs:
        try:
            lh = longhaul(hub, dests, d1, d2, back, a)
        except Exception as e:
            print(f"[pos] long-haul {hub}: {e}", file=sys.stderr)
            continue
        if not lh:
            print(f"[pos] {hub}: no long-haul results", file=sys.stderr)
            continue
        print(f"[pos] {hub}: cheapest long-haul {lh[0]['eur']} EUR{f' total ({n} pax)' if n > 1 else ''} "
              f"({lh[0]['route']})", file=sys.stderr)
        if not _precheck(hub, lh, a):
            continue
        for home in homes:
            if home == hub:
                best = lh[0]
                combos.append({"home": home, "hub": hub, "pos_flight": "-", "pos_dep": "-",
                               "pos_eur": 0.0, "lh_route": best["route"], "lh_times": best["times"],
                               "lh_eur": best["eur"], "lh_flags": best["flags"],
                               "total_eur": best["eur"], "total_pp": best["lh_pp"], "gap_h": None,
                               "pax": n, "price_basis": "total"})
                continue
            # positioning window: day before .. last day (out) / first day .. day after (back)
            p1, p2 = (d1 - dt.timedelta(days=1), d2) if not back else (d1, d2 + dt.timedelta(days=2))
            pos = pos_options(home, hub, p1, p2, back, a)
            if not pos:
                continue
            best = None
            for L in lh:
                P, gap = best_pos(pos, L["arr"] if back else L["dep"], back, a)
                if P is None:
                    continue
                pos_pp = round(P["price_eur"] + pos_bag, 2)
                tot = round(L["eur"] + n * pos_pp, 2)
                if best is None or tot < best["total_eur"]:
                    best = {"home": home, "hub": hub,
                            "pos_flight": f"{P['airline']} {P['from']}-{P['to']}"
                                          + (f" (+ground {P['sibling']}<->{hub})" if P.get("sibling") else ""),
                            "pos_dep": P["dep"].strftime("%m-%d %H:%M"), "pos_eur": pos_pp,
                            "lh_route": L["route"], "lh_times": L["times"], "lh_eur": L["eur"],
                            "lh_flags": ",".join(x for x in ("sep-tickets", L["flags"]) if x),
                            "total_eur": tot, "total_pp": round(tot / n, 2), "gap_h": gap,
                            "pax": n, "price_basis": "total"}
            if best:
                combos.append(best)
    return combos


def run_roundtrip(a, homes, hubs, dests, d1, d2, r1, r2, pos_bag) -> list[dict]:
    """hub<->Japan round trip (Kiwi) + positioning home->hub before it and hub->home after it."""
    combos = []
    n = a.adults
    p_out = (d1 - dt.timedelta(days=1), d2)
    p_back = (r1, r2 + dt.timedelta(days=2))
    for hub in hubs:
        try:
            lh = longhaul(hub, dests, d1, d2, False, a, ret=(r1, r2))
        except Exception as e:
            print(f"[pos] long-haul RT {hub}: {e}", file=sys.stderr)
            continue
        if not lh:
            print(f"[pos] {hub}: no long-haul RT results", file=sys.stderr)
            continue
        print(f"[pos] {hub}: cheapest long-haul RT {lh[0]['eur']} EUR{f' total ({n} pax)' if n > 1 else ''} "
              f"({lh[0]['route']})", file=sys.stderr)
        if not _precheck(hub, lh, a):
            continue
        for home in homes:
            best = None
            out_pos = [] if home == hub else pos_options(home, hub, *p_out, False, a)
            if home != hub and not out_pos:
                continue
            for L in lh:
                ra = L["ret_airport"]  # Kiwi may return to another airport than it left from
                if home == hub:
                    Po, go = None, None
                else:
                    Po, go = best_pos(out_pos, L["dep"], False, a)
                    if Po is None:
                        continue
                if ra == home:
                    Pb, gb = None, None
                else:
                    Pb, gb = best_pos(pos_options(home, ra, *p_back, True, a), L["arr"], True, a)
                    if Pb is None:
                        continue
                pos_pp = round(sum(P["price_eur"] + pos_bag for P in (Po, Pb) if P), 2)
                tot = round(L["eur"] + n * pos_pp, 2)
                if best is None or tot < best["total_eur"]:
                    legs = sum(1 for P in (Po, Pb) if P)
                    best = {"home": home, "hub": hub, "ret_airport": ra,
                            "pos_out": _pos_txt(Po, hub), "pos_back": _pos_txt(Pb, ra),
                            "pos_eur": pos_pp, "gap_out_h": go, "gap_back_h": gb,
                            "lh_route": L["route"], "lh_times": L["times"], "lh_eur": L["eur"],
                            "lh_flags": ",".join(x for x in ((f"sep-tickets({legs + (L.get('tickets') or 1)})"
                                                               if legs else ""), L["flags"]) if x),
                            "total_eur": tot, "total_pp": round(tot / n, 2), "pax": n, "price_basis": "total"}
            if best:
                combos.append(best)
    return combos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", nargs="+", required=True, help="home airports, e.g. ZAG,LJU,VIE,BUD")
    ap.add_argument("--to", nargs="+", default=["TYO,OSA"], help="Japan codes (TYO,OSA,NGO,FUK...)")
    ap.add_argument("--hubs", nargs="+", default=[DEFAULT_HUBS])
    ap.add_argument("--dates", required=True, help="long-haul departure window (out) / Japan departure window (back)")
    ap.add_argument("--return-dates", help="round trip: Japan departure window of the return, e.g. 2027-05-24..2027-05-28 "
                                           "(hub<->Japan RT + positioning out AND back)")
    ap.add_argument("--direction", choices=["out", "back"], default="out", help="one-way mode only")
    ap.add_argument("--adults", type=int, default=1,
                    help="adults; the Kiwi long-haul is priced for all of them (party total), positioning "
                         "fares are per person x N")
    ap.add_argument("--buffer", type=float, default=4.0, help="min connection hours (default 4)")
    ap.add_argument("--max-gap", type=float, default=30.0, help="max hours between the two flights")
    ap.add_argument("--no-siblings", action="store_true", help="don't use same-city alternative airports")
    ap.add_argument("--sibling-extra", type=float, default=3.0,
                    help="extra buffer hours when positioning lands at a sibling airport (default 3)")
    ap.add_argument("--airlines", default="FR,W6")
    ap.add_argument("--wizz-block", type=float, default=3.0, help="assumed Wizz flight hours")
    ap.add_argument("--single-ticket", action="store_true", help="long-haul must be one ticket")
    ap.add_argument("--checked-bags", type=int, default=0, help="price bags into the long-haul")
    ap.add_argument("--pos-bag-eur", type=float, default=None,
                    help="EUR per checked bag per positioning flight (Ryanair/Wizz fares exclude bags). "
                         "Default with --checked-bags: 40; without: 0")
    ap.add_argument("--compare-home-rt", type=float, metavar="EUR",
                    help="per-person price of the best round trip from home; hubs whose long-haul is not "
                         "at least --min-saving cheaper are skipped before any positioning lookup")
    ap.add_argument("--min-saving", type=float, default=150.0, help="EUR/pp for --compare-home-rt (default 150)")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json")
    a = ap.parse_args()
    a.airlines = split_codes(a.airlines)
    if a.pos_bag_eur is None:
        a.pos_bag_eur = 40.0 if a.checked_bags else 0.0
        if a.checked_bags:
            print(f"[pos] note: adding EUR {a.pos_bag_eur:.0f} per bag to each FR/W6 positioning fare "
                  "(fare-only); set --pos-bag-eur to the real fee", file=sys.stderr)
    if a.checked_bags:
        print("[pos] note: the long-haul bag is Kiwi's add-on; Kiwi has no bag data for MU/CA/CZ (their fares "
              "include bags), so their long-haul prices are overstated", file=sys.stderr)
    if a.adults > 1:
        print(f"[pos] {a.adults} adults: long-haul = Kiwi party total; positioning = FR/W6 per-person fare x "
              f"{a.adults} (the cheapest FR/W6 fare may not have {a.adults} seats: re-check)", file=sys.stderr)
    if a.return_dates and a.direction == "back":
        ap.error("--return-dates already covers both directions; drop --direction back")
    pos_bag = a.pos_bag_eur * a.checked_bags
    homes, hubs, dests = split_codes(a.home), split_codes(a.hubs), split_codes(a.to)
    d1, d2 = parse_date_range(a.dates)
    hdr = price_header(a.adults, "total")
    if a.return_dates:
        r1, r2 = parse_date_range(a.return_dates)
        combos = run_roundtrip(a, homes, hubs, dests, d1, d2, r1, r2, pos_bag)
        combos.sort(key=lambda r: r["total_eur"])
        cols = [("total_eur", f"TOTAL {hdr}")] + ([("total_pp", "TOTAL EUR/pp")] if a.adults > 1 else [])
        print_table(combos, cols + [("home", "HOME"), ("hub", "HUB"), ("pos_out", "POS OUT"),
                                    ("gap_out_h", "GAP"), ("pos_back", "POS BACK"), ("gap_back_h", "GAP"),
                                    ("pos_eur", "POS EUR/pp"), ("lh_route", "LONG-HAUL RT"),
                                    ("lh_times", "LH TIMES"), ("lh_eur", f"LH {hdr}"), ("lh_flags", "FLAGS")],
                    limit=a.limit, maxw=70)
        print("TOTAL = Kiwi hub<->Japan round trip + positioning out + back (+ --pos-bag-eur per bag per FR/W6 leg). "
              "Separate tickets; sibling-airport ground transfers and hub hotel nights are NOT included.")
    else:
        back = a.direction == "back"
        combos = run_oneway(a, homes, hubs, dests, d1, d2, back, pos_bag)
        combos.sort(key=lambda r: r["total_eur"])
        cols = [("total_eur", f"TOTAL {hdr}")] + ([("total_pp", "TOTAL EUR/pp")] if a.adults > 1 else [])
        print_table(combos, cols + [("home", "HOME"), ("hub", "HUB"),
                                    ("pos_flight", "POSITIONING"), ("pos_dep", "POS DEP"), ("pos_eur", "POS EUR/pp"),
                                    ("gap_h", "GAP H"), ("lh_route", "LONG-HAUL"), ("lh_times", "LH TIMES"),
                                    ("lh_eur", f"LH {hdr}"), ("lh_flags", "LH FLAGS")], limit=a.limit, maxw=60)
        print("ONE-WAY totals (use --return-dates for a round trip). Separate tickets; ground transfers not included.")
    dump_json(combos, a.json)


if __name__ == "__main__":
    main()
