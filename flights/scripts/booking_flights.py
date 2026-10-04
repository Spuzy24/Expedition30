#!/usr/bin/env python3
"""Booking.com Flights live search via headless Chromium (Playwright).

Booking.com flights is powered by Etraveli (the same inventory/fares as Gotogate, Mytrip,
Flightnetwork, Supersaver...). Those OTA sites themselves return 403 to scripts, but
flights.booking.com only needs an AWS-WAF JS challenge that a real browser solves
automatically (plain curl gets HTTP 202 + challenge page).

The page calls  GET https://flights.booking.com/api/flights/?type=ONEWAY|ROUNDTRIP&from=..&to=..
&depart=YYYY-MM-DD[&return=..]&sort=CHEAPEST&currency=EUR...  which returns JSON
(flightOffers with full price breakdown, legs, carriers, included baggage, and an
`aggregation` block with totalCount and min price per number of stops / airline).
Prices are LIVE, total incl. taxes and Booking/Etraveli fees, in EUR.

Location codes: airports as XXX.AIRPORT, metro cities as XXX.CITY (TYO, OSA, LON, MIL, ...).
The script appends the suffix automatically (city list below; override with an explicit
suffix, e.g. --to TYO.CITY). Several origins may be given (comma) - they are searched in turn.

Output: EUR = TOTAL for all travellers (with --adults 2 the price doubles, verified 2026-10-04);
the header says "EUR total (N pax)" and adds EUR/pp (per-traveller price from travellerPrices).
BAGS = checked bags per traveller; SELF-TR = Etraveli virtual interlining (separate tickets).
Routes: one direction each, " | " between directions; '~' = station change inside a direction
(e.g. ZAG-CRL~BRU-PVG-KIX). JSON: route, airport_change, eur_pp, pax, price_basis.

Examples
--------
  python3 booking_flights.py --from VIE --to TYO --depart 2027-03-10
  python3 booking_flights.py --from ZAG,BUD --to TYO,OSA --depart 2027-03-10 --return 2027-03-24
"""
from __future__ import annotations

import argparse
import sys
import time
from urllib.parse import urlencode

from _browser import browser_page, click_consent, wait_until
from _common import dump_json, price_header, print_table, split_codes, station_route, to_eur

METRO = {"TYO", "OSA", "SPK", "LON", "MIL", "PAR", "ROM", "STO", "BER", "MOW", "NYC", "BUH",
         "BJS", "SHA", "SEL", "OSL", "IST", "REK", "CHI", "WAS", "YTO", "BRU", "VEN", "NAG"}


def loc(code: str) -> str:
    if "." in code:
        return code
    return f"{code}.CITY" if code in METRO else f"{code}.AIRPORT"


def search(o: str, d: str, dep: str, ret: str | None, adults=1, currency="EUR", timeout=75):
    q = {"type": "ROUNDTRIP" if ret else "ONEWAY", "adults": adults, "cabinClass": "ECONOMY",
         "children": "", "from": loc(o), "to": loc(d), "depart": dep, "sort": "CHEAPEST",
         "travelPurpose": "leisure", "locale": "en-gb", "currency": currency}
    if ret:
        q["return"] = ret
    url = f"https://flights.booking.com/flights/{loc(o)}-{loc(d)}/?{urlencode(q)}"
    with browser_page(capture=lambda u: "flights.booking.com/api/flights/" in u) as (page, cap):
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        consent = {"done": False}

        def done():
            if not consent["done"]:
                consent["done"] = click_consent(page, tries=1)
            return any(c.get("json") and c["json"].get("flightOffers") is not None for c in cap)
        ok = wait_until(done, timeout, step=1.5, page=page)
        page.wait_for_timeout(2000)
        print(f"[booking] {o}->{d} {dep}{'/' + ret if ret else ''}: {'ok' if ok else 'TIMEOUT'}; "
              f"title={page.title()!r}", file=sys.stderr)
    data = next((c["json"] for c in reversed(cap) if c.get("json") and c["json"].get("flightOffers") is not None), None)
    return (parse(data) if data else [], data, url)


def _money(m):
    return round(m["units"] + m.get("nanos", 0) / 1e9, 2), m["currencyCode"]


def parse(d: dict) -> list[dict]:
    rows = []
    for o in d.get("flightOffers", []):
        price, cur = _money(o["priceBreakdown"]["total"])
        legs_txt, carriers, vi, checked, routes, change = [], [], False, [], [], False
        for s in o["segments"]:  # one segment = one direction; '~' marks a station change inside it
            path, ch = station_route([(l["departureAirport"]["code"], l["arrivalAirport"]["code"]) for l in s["legs"]])
            change = change or ch
            routes.append(path)
            legs_txt.append(f"{path} {s['departureTime'][5:16].replace('T', ' ')}->{s['arrivalTime'][5:16].replace('T', ' ')}")
            carriers.append(",".join(dict.fromkeys(l["flightInfo"]["carrierInfo"]["marketingCarrier"] for l in s["legs"])))
            vi = vi or bool(s.get("isVirtualInterlining"))
            # one entry per traveller: take the minimum per-traveller allowance, not the sum over travellers
            per_trav = [(x.get("luggageAllowance") or {}).get("maxPiece", 0) for x in s.get("travellerCheckedLuggage") or []]
            checked.append(min(per_trav) if per_trav else 0)
        brand = (o.get("brandedFareInfo") or {}).get("fareName")
        # priceBreakdown.total = ALL travellers (verified 2026-10-04: 1 adult EUR 415.45; 2 adults EUR 850.98
        # = 2 x 425.49 in travellerPrices); eur stays the total (monitor.py reads it)
        tp = [_money(x["travellerPriceBreakdown"]["total"]) for x in o.get("travellerPrices") or []
              if (x.get("travellerPriceBreakdown") or {}).get("total")]
        n_trav = len(tp) or 1
        eur_pp = (to_eur(max(p for p, _ in tp), tp[0][1]) if tp else None)
        rows.append({"price": price, "currency": cur, "eur": to_eur(price, cur), "fare_brand": brand,
                     "eur_pp": eur_pp if eur_pp is not None else round(to_eur(price, cur) / n_trav, 2),
                     "itinerary": " | ".join(legs_txt), "airlines": " | ".join(carriers),
                     "route": " | ".join(routes), "airport_change": change,
                     "checked_bags": min(checked) if checked else 0, "self_transfer": vi,
                     "flight_key": o.get("flightKey")})
    rows.sort(key=lambda r: r["eur"] or r["price"])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="origins", nargs="+", required=True)
    ap.add_argument("--to", dest="dests", nargs="+", required=True)
    ap.add_argument("--depart", required=True)
    ap.add_argument("--return", dest="ret")
    ap.add_argument("--adults", type=int, default=1, help="adults; prices are the party TOTAL (+ EUR/pp column)")
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json")
    a = ap.parse_args()
    allrows, first = [], True
    for o in split_codes(a.origins):
        for d in split_codes(a.dests):
            if not first:
                time.sleep(5)
            first = False
            rows, raw, url = search(o, d, a.depart, a.ret, a.adults, a.currency)
            agg = (raw or {}).get("aggregation") or {}
            stops = {s["numberOfStops"]: _money(s["minPrice"])[0] for s in agg.get("stops", [])}
            print(f"\n== Booking.com {o}->{d} {a.depart}{' / ' + a.ret if a.ret else ''}: "
                  f"{agg.get('totalCount')} offers; min price by stops {stops}\n   {url}")
            for r in rows:
                r.update({"from": o, "to": d, "depart": a.depart, "return": a.ret, "url": url})
            for r in rows:
                r.update({"pax": a.adults, "price_basis": "total"})
            cols = [("eur", price_header(a.adults, "total", a.currency.upper()))]
            if a.adults > 1:
                cols.append(("eur_pp", "EUR/pp"))
            print_table(rows, cols + [("checked_bags", "BAGS"), ("fare_brand", "BRAND"), ("self_transfer", "SELF-TR"),
                                      ("airlines", "AIRLINES"), ("itinerary", "ITINERARY")],
                        limit=a.limit, maxw=110)
            if any(r["airport_change"] for r in rows[: a.limit]):
                print("'~' in a route = station change (e.g. CRL~BRU): you must get to another airport yourself")
            allrows += rows
    dump_json(allrows, a.json)


if __name__ == "__main__":
    main()
