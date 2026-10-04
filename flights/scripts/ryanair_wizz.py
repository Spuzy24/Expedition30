#!/usr/bin/env python3
"""Positioning-flight finder: Ryanair + Wizz Air public fare APIs (no key, plain HTTPS).

Purpose: price the cheap "positioning" leg from home (ZAG/LJU/GRZ/VIE/BUD/TSF/VCE/TRS/BTS...)
to whichever European hub has the cheapest long-haul fare to Japan, and back.

Sub-commands
------------
  anywhere  Cheapest fare from each origin to EVERY destination (or a --to hub list) in a
            date window. Ryanair: 1 call per origin (farfnd "oneWayFares" or "roundTripFares").
            Wizz: 1 timetable call per (origin, destination) pair (destinations from the
            Wizz route map), optionally with the return leg in the same call.
  calendar  Day-by-day cheapest fare for one route (both airlines).
  routes    List the destinations each airline serves from an airport.

Examples
--------
  # One-way, any destination, 1-10 Mar 2027, from all home airports, cheapest first
  python3 ryanair_wizz.py anywhere --from ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS \
      --dates 2027-03-01..2027-03-10

  # Only hubs with cheap long-haul to Japan, with the return leg 20-25 Mar
  python3 ryanair_wizz.py anywhere --from ZAG,BUD,VIE,TSF --to IST,SAW,BGY,MXP,STN,LTN,FRA,MUC,HEL,WAW,AUH,DXB,BRU,CRL,MAD,BCN,ARN,CPH,OSL,AMS,CDG \
      --dates 2027-03-01..2027-03-05 --return 2027-03-20..2027-03-25

  python3 ryanair_wizz.py calendar --from ZAG --to BGY --dates 2027-03-01..2027-03-31
  python3 ryanair_wizz.py routes --from ZAG,BUD

Data notes
----------
* Ryanair farfnd = cached "fare finder" prices (refreshed often; `priceUpdated` shows when),
  base fare only: no cabin bag (only small personal item), no checked bag, no seat.
* Wizz timetable = the cheapest regular (non-Discount-Club) fare per day, in the departure
  country currency (HUF, PLN, RON...), converted to EUR with ECB rates. Fare only, no bags.
* Always verify on the airline site before buying. These are separate tickets: leave a big
  buffer (ideally overnight) before a long-haul connection; a missed connection is your risk.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from typing import Iterable

from _common import (daterange, dump_json, parse_date_range, polite_session, print_table,
                     split_codes, to_eur, UA)

FR_BASE = "https://services-api.ryanair.com/farfnd/v4"
FR_WWW = "https://www.ryanair.com/api"
WIZZ_HOME = "https://www.wizzair.com/en-gb"

S = polite_session(min_delay=2.0, jitter=1.0)


# ------------------------------------------------------------------ Ryanair
def fr_oneway(origin: str, d1: dt.date, d2: dt.date, currency="EUR", market="en-gb",
              dest: str | None = None) -> list[dict]:
    """Cheapest one-way fare per destination from `origin` departing d1..d2 (inclusive)."""
    p = dict(departureAirportIataCode=origin, outboundDepartureDateFrom=d1.isoformat(),
             outboundDepartureDateTo=d2.isoformat(), currency=currency, market=market)
    if dest:
        p["arrivalAirportIataCode"] = dest
    r = S.get(f"{FR_BASE}/oneWayFares", params=p)
    if r.status_code != 200:
        print(f"[FR] {origin} HTTP {r.status_code}: {r.text[:150]}", file=sys.stderr)
        return []
    out = []
    for f in r.json().get("fares", []):
        o = f["outbound"]
        out.append(_fr_leg(o, "FR"))
    return out


def fr_roundtrip(origin: str, d1, d2, r1, r2, currency="EUR", market="en-gb") -> list[dict]:
    p = dict(departureAirportIataCode=origin, outboundDepartureDateFrom=d1.isoformat(),
             outboundDepartureDateTo=d2.isoformat(), inboundDepartureDateFrom=r1.isoformat(),
             inboundDepartureDateTo=r2.isoformat(), currency=currency, market=market)
    r = S.get(f"{FR_BASE}/roundTripFares", params=p)
    if r.status_code != 200:
        print(f"[FR] RT {origin} HTTP {r.status_code}: {r.text[:150]}", file=sys.stderr)
        return []
    out = []
    for f in r.json().get("fares", []):
        ob, ib = _fr_leg(f["outbound"], "FR"), _fr_leg(f["inbound"], "FR")
        out.append({**ob, "ret_date": ib["date"], "ret_flight": ib["flight"],
                    "ret_price": ib["price"],
                    "price_eur": _sum(ob["price_eur"], ib["price_eur"]),
                    "price": round(ob["price"] + ib["price"], 2)})
    return out


def _fr_leg(o: dict, airline: str) -> dict:
    price = o["price"]["value"]
    cur = o["price"]["currencyCode"]
    return {"airline": airline, "from": o["departureAirport"]["iataCode"],
            "to": o["arrivalAirport"]["iataCode"],
            "to_city": o["arrivalAirport"].get("city", {}).get("name") or o["arrivalAirport"]["name"],
            "date": o["departureDate"].replace("T", " ")[:16],
            "arr": o["arrivalDate"].replace("T", " ")[11:16],
            "flight": o.get("flightNumber"), "price": price, "currency": cur,
            "price_eur": to_eur(price, cur)}


def fr_cheapest_per_day(origin: str, dest: str, d1: dt.date, d2: dt.date,
                        currency="EUR") -> list[dict]:
    out = []
    month = dt.date(d1.year, d1.month, 1)
    while month <= d2:
        r = S.get(f"{FR_WWW}/farfnd/v4/oneWayFares/{origin}/{dest}/cheapestPerDay",
                  params=dict(outboundMonthOfDate=month.isoformat(), currency=currency))
        if r.status_code == 200:
            for f in r.json().get("outbound", {}).get("fares", []):
                day = dt.date.fromisoformat(f["day"])
                if d1 <= day <= d2 and f.get("price") and not f.get("soldOut"):
                    out.append({"airline": "FR", "from": origin, "to": dest,
                                "date": (f.get("departureDate") or f["day"]).replace("T", " ")[:16],
                                "arr": (f.get("arrivalDate") or "")[11:16],
                                "flight": "", "price": f["price"]["value"],
                                "currency": f["price"]["currencyCode"],
                                "price_eur": to_eur(f["price"]["value"], f["price"]["currencyCode"])})
        else:
            print(f"[FR] calendar {origin}-{dest} HTTP {r.status_code}", file=sys.stderr)
        month = (month + dt.timedelta(days=32)).replace(day=1)
    return out


def fr_routes(origin: str) -> list[str]:
    r = S.get(f"{FR_WWW}/views/locate/searchWidget/routes/en/airport/{origin}")
    if r.status_code != 200:
        return []
    return sorted({x["arrivalAirport"]["code"] for x in r.json()})


# -------------------------------------------------------------------- Wizz
_WIZZ_API: str | None = None
_WIZZ_MAP: dict[str, list[str]] | None = None


def wizz_api() -> str:
    """Discover the versioned API base, e.g. https://be.wizzair.com/29.19.0/Api ."""
    global _WIZZ_API
    if _WIZZ_API:
        return _WIZZ_API
    r = S.get(WIZZ_HOME, headers={"accept": "text/html"})
    m = re.search(r'https://be\.wizzair\.com/(\d+\.\d+\.\d+)/Api', r.text)
    if not m:
        raise RuntimeError("could not discover Wizz API version from homepage")
    _WIZZ_API = f"https://be.wizzair.com/{m.group(1)}/Api"
    return _WIZZ_API


def _wizz_headers():
    h = {"origin": "https://www.wizzair.com", "referer": "https://www.wizzair.com/",
         "content-type": "application/json", "user-agent": UA}
    # After the first call Wizz sets a RequestVerificationToken cookie and then rejects
    # requests ("InvalidProtocol") unless the same value is echoed in this header.
    tok = next((c.value for c in S.cookies if c.name == "RequestVerificationToken"), None)
    if tok:
        h["x-requestverificationtoken"] = tok
    return h


def wizz_map() -> dict[str, list[str]]:
    """{origin IATA: [destination IATA, ...]} from Wizz's route map."""
    global _WIZZ_MAP
    if _WIZZ_MAP is not None:
        return _WIZZ_MAP
    r = S.get(f"{wizz_api()}/asset/map", params={"languageCode": "en-gb"}, headers=_wizz_headers())
    r.raise_for_status()
    _WIZZ_MAP = {c["iata"]: [x["iata"] for x in c.get("connections", [])]
                 for c in r.json().get("cities", [])}
    return _WIZZ_MAP


def wizz_timetable(origin: str, dest: str, d1: dt.date, d2: dt.date,
                   r1: dt.date | None = None, r2: dt.date | None = None) -> tuple[list, list]:
    """Cheapest fare per day; Wizz allows ~31 days per call so long windows are chunked."""
    outs, rets = [], []
    a = d1
    while a <= d2:
        b = min(d2, a + dt.timedelta(days=30))
        fl = [{"departureStation": origin, "arrivalStation": dest,
               "from": a.isoformat(), "to": b.isoformat()}]
        if r1 and a == d1:  # ask for the return leg once (first chunk)
            fl.append({"departureStation": dest, "arrivalStation": origin,
                       "from": r1.isoformat(), "to": min(r2, r1 + dt.timedelta(days=30)).isoformat()})
        body = {"flightList": fl, "priceType": "regular", "adultCount": 1,
                "childCount": 0, "infantCount": 0}
        r = S.post(f"{wizz_api()}/search/timetable", json=body, headers=_wizz_headers())
        if r.status_code != 200:
            print(f"[W6] {origin}-{dest} HTTP {r.status_code}: {r.text[:120]}", file=sys.stderr)
            a = b + dt.timedelta(days=1)
            continue
        d = r.json()
        outs += [_wizz_leg(f) for f in d.get("outboundFlights") or [] if f.get("price")]
        rets += [_wizz_leg(f) for f in d.get("returnFlights") or [] if f.get("price")]
        a = b + dt.timedelta(days=1)
    return outs, rets


def _wizz_leg(f: dict) -> dict:
    amt, cur = f["price"]["amount"], f["price"]["currencyCode"]
    times = f.get("departureDates") or [f["departureDate"]]
    return {"airline": "W6", "from": f["departureStation"], "to": f["arrivalStation"],
            "to_city": "", "date": times[0].replace("T", " ")[:16],
            "arr": "", "flight": f"{len(times)} dep/day" if len(times) > 1 else "",
            "price": amt, "currency": cur, "price_eur": to_eur(amt, cur),
            "price_type": f.get("priceType")}


def _sum(a, b):
    return None if a is None or b is None else round(a + b, 2)


# ----------------------------------------------------------------- commands
def cmd_anywhere(a) -> list[dict]:
    origins = split_codes(a.origins)
    hubs = set(split_codes(a.to)) if a.to else None
    d1, d2 = parse_date_range(a.dates)
    r1 = r2 = None
    if a.ret:
        r1, r2 = parse_date_range(a.ret)
    rows: list[dict] = []
    airlines = split_codes(a.airlines)
    for o in origins:
        if "FR" in airlines:
            if r1:
                res = fr_roundtrip(o, d1, d2, r1, r2)
            elif a.per_day:
                res = []
                for day in daterange(d1, d2):
                    res += fr_oneway(o, day, day)
            else:
                res = fr_oneway(o, d1, d2)
            rows += [x for x in res if not hubs or x["to"] in hubs]
            print(f"[FR] {o}: {len(res)} fares", file=sys.stderr)
        if "W6" in airlines:
            dests = wizz_map().get(o, [])
            if hubs:
                dests = [x for x in dests if x in hubs]
            if not dests:
                continue
            if not hubs and len(dests) > a.wizz_max_dests:
                print(f"[W6] {o}: {len(dests)} destinations; limiting to first {a.wizz_max_dests}"
                      f" (pass --to or --wizz-max-dests)", file=sys.stderr)
                dests = dests[: a.wizz_max_dests]
            print(f"[W6] {o}: querying {len(dests)} routes (~{len(dests) * 2.5:.0f}s)", file=sys.stderr)
            for dst in dests:
                outs, rets = wizz_timetable(o, dst, d1, d2, r1, r2)
                if not outs:
                    continue
                best_o = min(outs, key=lambda x: x["price_eur"] or 1e9)
                if r1:
                    if not rets:
                        continue
                    best_r = min(rets, key=lambda x: x["price_eur"] or 1e9)
                    rows.append({**best_o, "ret_date": best_r["date"], "ret_price": best_r["price"],
                                 "price": round(best_o["price"] + best_r["price"], 2),
                                 "price_eur": _sum(best_o["price_eur"], best_r["price_eur"])})
                else:
                    rows.append(best_o)
    if a.max_price:
        rows = [x for x in rows if x["price_eur"] is not None and x["price_eur"] <= a.max_price]
    # Wizz answers some city-group queries with the sibling airport (e.g. DXB -> AUH): dedupe
    seen, uniq = set(), []
    for x in rows:
        k = (x["airline"], x["from"], x["to"], x["date"], x.get("ret_date"), x["price"])
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    rows = uniq
    rows.sort(key=lambda x: (x["price_eur"] is None, x["price_eur"] or 0))
    cols = [("airline", "AL"), ("from", "FROM"), ("to", "TO"), ("to_city", "CITY"),
            ("date", "DEPART"), ("arr", "ARR"), ("flight", "FLIGHT")]
    if r1:
        cols += [("ret_date", "RETURN")]
    cols += [("price", "PRICE"), ("currency", "CUR"), ("price_eur", "EUR")]
    print_table(rows, cols, limit=a.limit)
    return rows


def cmd_calendar(a) -> list[dict]:
    d1, d2 = parse_date_range(a.dates)
    rows = []
    for o in split_codes(a.origins):
        for dst in split_codes(a.to):
            if "FR" in split_codes(a.airlines) and dst in fr_routes(o):
                rows += fr_cheapest_per_day(o, dst, d1, d2)
            if "W6" in split_codes(a.airlines) and dst in wizz_map().get(o, []):
                rows += wizz_timetable(o, dst, d1, d2)[0]
    rows.sort(key=lambda x: (x["date"], x["price_eur"] or 0))
    print_table(rows, [("airline", "AL"), ("from", "FROM"), ("to", "TO"), ("date", "DEPART"),
                       ("arr", "ARR"), ("price", "PRICE"), ("currency", "CUR"),
                       ("price_eur", "EUR")])
    return rows


def cmd_routes(a) -> dict:
    out = {}
    for o in split_codes(a.origins):
        fr = fr_routes(o) if "FR" in split_codes(a.airlines) else []
        w6 = sorted(wizz_map().get(o, [])) if "W6" in split_codes(a.airlines) else []
        out[o] = {"FR": fr, "W6": w6}
        print(f"{o}  Ryanair ({len(fr)}): {' '.join(fr)}")
        print(f"{o}  Wizz    ({len(w6)}): {' '.join(w6)}")
    return out


def main(argv: Iterable[str] | None = None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--from", dest="origins", required=True, nargs="+",
                       help="origin IATA codes, comma or space separated")
        p.add_argument("--airlines", default="FR,W6", help="FR,W6 (default both)")
        p.add_argument("--json", help="write results as JSON to this path ('-' = stdout)")

    p = sub.add_parser("anywhere", help="cheapest fare per destination in a date window")
    common(p)
    p.add_argument("--to", nargs="*", help="only these destination IATA codes (hubs)")
    p.add_argument("--dates", required=True, help="2027-03-01..2027-03-10 or 2027-03-05+-2")
    p.add_argument("--return", dest="ret", help="return window (enables round-trip pricing)")
    p.add_argument("--per-day", action="store_true",
                   help="Ryanair: one query per departure day (cheapest per dest per day)")
    p.add_argument("--max-price", type=float, help="drop results above this EUR price")
    p.add_argument("--wizz-max-dests", type=int, default=40,
                   help="cap Wizz routes per origin when --to is not given (default 40)")
    p.add_argument("--limit", type=int, default=80, help="rows to print (default 80)")

    p = sub.add_parser("calendar", help="day-by-day cheapest fare for routes")
    common(p)
    p.add_argument("--to", required=True, nargs="+")
    p.add_argument("--dates", required=True)

    p = sub.add_parser("routes", help="destinations served from an airport")
    common(p)

    a = ap.parse_args(argv)
    res = {"anywhere": cmd_anywhere, "calendar": cmd_calendar, "routes": cmd_routes}[a.cmd](a)
    dump_json(res, a.json)


if __name__ == "__main__":
    main()
