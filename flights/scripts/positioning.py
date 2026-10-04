#!/usr/bin/env python3
"""Combine a cheap positioning flight (Ryanair / Wizz, separate ticket) with the cheapest
long-haul fare to Japan from a European hub (Kiwi web GraphQL), respecting a minimum
connection buffer. Answers: "from my home airports, which hub + which day is cheapest in total?"

  total = positioning (home -> hub, FR/W6 fare-only)  +  long-haul (hub -> Japan, Kiwi live)

Direction "out": home -> hub (arrive >= --buffer hours before the long-haul departure;
                 the day before is allowed, i.e. an overnight at the hub)
Direction "back": Japan -> hub, then hub -> home (depart >= --buffer hours after arrival,
                 same day or next day)
A hub that is itself a home airport needs no positioning (cost 0).

Example
-------
  python3 positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --to TYO,OSA \
      --dates 2027-03-05..2027-03-12 --hubs BRU,IST,MXP,BGY,WAW,HEL,FRA,MUC,BCN,MAD,CDG,AMS,PRG,ARN,CPH,STN,DUB,FCO
  python3 positioning.py --direction back --home ZAG,VIE,BUD --to TYO,OSA --dates 2027-03-22..2027-03-26

Caveats: positioning prices are fare-only (no cabin/checked bag); with --checked-bags the total adds
--pos-bag-eur per bag per positioning flight. Wizz timetable has no arrival time, so its arrival is
estimated as departure + --wizz-block hours, converted between the airports' time zones. Long-haul fares may be Kiwi
self-transfer combos themselves (flag shown); use --single-ticket to keep only 1-PNR long-haul.
Missed connections on separate tickets are at your own risk - prefer an overnight buffer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import functools
import sys
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import kiwi_graphql as kg
import ryanair_wizz as rw
from _common import dump_json, parse_date_range, print_table, split_codes

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


def longhaul(hub: str, dests: list[str], d1: dt.date, d2: dt.date, back: bool, a) -> list[dict]:
    ns = SimpleNamespace(origins=[",".join(dests)] if back else [hub],
                         dests=[hub] if back else [",".join(dests)],
                         dates=f"{d1}..{d2}", return_dates=None, nights=None,
                         currency="EUR", market="hr", adults=1, checked_bags=a.checked_bags,
                         hand_bags=0, max_stops=None, no_self_transfer=a.single_ticket, hacks=False,
                         limit=0, limit_api=40)
    rows = kg.run_search(ns, quiet=True)
    out = []
    for r in rows:
        first, last = r["times"].split("->")
        dep = _dt(first)
        # arrival "MM-DD HH:MM" -> add year (handle Dec->Jan rollover)
        arr = dt.datetime.strptime(f"{dep.year}-{last.strip()}", "%Y-%m-%d %H:%M")
        if arr < dep:
            arr = arr.replace(year=dep.year + 1)
        out.append({**r, "dep": dep, "arr": arr, "hub": hub})
    return out


def positioning_flights(home: str, hub: str, d1: dt.date, d2: dt.date, back: bool, a) -> list[dict]:
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", nargs="+", required=True, help="home airports, e.g. ZAG,LJU,VIE,BUD")
    ap.add_argument("--to", nargs="+", default=["TYO,OSA"], help="Japan codes (TYO,OSA,NGO,FUK...)")
    ap.add_argument("--hubs", nargs="+", default=[DEFAULT_HUBS])
    ap.add_argument("--dates", required=True, help="long-haul departure window (out) / Japan departure window (back)")
    ap.add_argument("--direction", choices=["out", "back"], default="out")
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
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json")
    a = ap.parse_args()
    a.airlines = split_codes(a.airlines)
    if a.pos_bag_eur is None:
        a.pos_bag_eur = 40.0 if a.checked_bags else 0.0
        if a.checked_bags:
            print(f"[pos] note: adding EUR {a.pos_bag_eur:.0f} per bag to each FR/W6 positioning fare "
                  "(fare-only); set --pos-bag-eur to the real fee", file=sys.stderr)
    pos_bag = a.pos_bag_eur * a.checked_bags
    homes, hubs, dests = split_codes(a.home), split_codes(a.hubs), split_codes(a.to)
    back = a.direction == "back"
    d1, d2 = parse_date_range(a.dates)
    combos = []
    for hub in hubs:
        try:
            lh = longhaul(hub, dests, d1, d2, back, a)
        except Exception as e:
            print(f"[pos] long-haul {hub}: {e}", file=sys.stderr)
            continue
        if not lh:
            print(f"[pos] {hub}: no long-haul results", file=sys.stderr)
            continue
        print(f"[pos] {hub}: cheapest long-haul {lh[0]['eur']} EUR ({lh[0]['route']})", file=sys.stderr)
        for home in homes:
            if home == hub:
                best = lh[0]
                combos.append({"home": home, "hub": hub, "pos_flight": "-", "pos_dep": "-",
                               "pos_eur": 0.0, "lh_route": best["route"], "lh_times": best["times"],
                               "lh_eur": best["eur"], "lh_flags": best["flags"],
                               "total_eur": best["eur"], "gap_h": None})
                continue
            # positioning window: day before .. last day (out) / first day .. day after (back)
            p1, p2 = (d1 - dt.timedelta(days=1), d2) if not back else (d1, d2 + dt.timedelta(days=2))
            pos = positioning_flights(home, hub, p1, p2, back, a)
            if not a.no_siblings:
                for sib in SIBLINGS.get(hub, []):
                    if sib == home:
                        continue
                    for f in positioning_flights(home, sib, p1, p2, back, a):
                        f["sibling"] = sib
                        pos.append(f)
            if not pos:
                continue
            best = None
            for L in lh:
                for P in pos:
                    gap = ((L["dep"] - P["arr_dt"]) if not back else (P["dep"] - L["arr"])).total_seconds() / 3600
                    need = a.buffer + (a.sibling_extra if P.get("sibling") else 0)
                    if need <= gap <= a.max_gap:
                        tot = round(P["price_eur"] + pos_bag + L["eur"], 2)
                        if best is None or tot < best["total_eur"]:
                            best = {"home": home, "hub": hub,
                                    "pos_flight": f"{P['airline']} {P['from']}-{P['to']}"
                                                  + (f" (+ground {P['sibling']}<->{hub})" if P.get("sibling") else ""),
                                    "pos_dep": P["dep"].strftime("%m-%d %H:%M"),
                                    "pos_eur": round(P["price_eur"] + pos_bag, 2),
                                    "lh_route": L["route"], "lh_times": L["times"], "lh_eur": L["eur"],
                                    "lh_flags": L["flags"], "total_eur": tot, "gap_h": round(gap, 1)}
            if best:
                combos.append(best)
    combos.sort(key=lambda r: r["total_eur"])
    print_table(combos, [("total_eur", "TOTAL EUR"), ("home", "HOME"), ("hub", "HUB"),
                         ("pos_flight", "POSITIONING"), ("pos_dep", "POS DEP"), ("pos_eur", "POS EUR"),
                         ("gap_h", "GAP H"), ("lh_route", "LONG-HAUL"), ("lh_times", "LH TIMES"),
                         ("lh_eur", "LH EUR"), ("lh_flags", "LH FLAGS")], limit=a.limit, maxw=60)
    dump_json(combos, a.json)


if __name__ == "__main__":
    main()
