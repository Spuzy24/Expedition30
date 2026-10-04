#!/usr/bin/env python3
"""KAYAK / momondo (same platform, Booking Holdings) live meta-search via the site's own JSON
poll API - plain HTTPS, no browser, no key.

How it works (as the website does it):
  1. GET https://<site>/flight-search/<ORIG>-<DEST>/<date>[/<return>]?sort=price_a
     -> HTML contains "formtoken" (CSRF) and sets session cookies.
  2. POST https://<site>/i/api/search/dynamic/flights/poll  (header x-csrf: <formtoken>)
     with {"userSearchParams": {legs, passengers, sortMode}, ...}; repeat (passing the
     returned searchId) until status == "complete". Each poll returns ~60 results/page.

Prices are LIVE (fetched from airlines/OTAs during the search), in the site's currency:
  momondo.de / kayak.de / kayak.ie / momondo.fr ... = EUR, kayak.com/momondo.com = USD,
  kayak.co.uk = GBP. Different sites can show slightly different provider sets.

Examples
--------
  # Multi-origin round trip, cheapest first (EUR on momondo.de)
  python3 kayak.py --from ZAG,VIE,BUD --to TYO --depart 2027-03-10 --return 2027-03-24

  # Nearby airports of Zagreb, +-3 days flexible, one-way, on kayak.de
  python3 kayak.py --site www.kayak.de --from ZAG --nearby --to TYO,OSA --depart 2027-03-10 --flex 3

  # Several date pairs in one run (spaced out politely)
  python3 kayak.py --from VIE --to TYO --depart 2027-03-08,2027-03-10 --return 2027-03-24 --json out.json

Output columns: price (and EUR), provider (OTA/airline selling it), itinerary per leg
(airports, times, airlines, stops), bags included (carry-on / checked), booking link.
Notes: KIWI* / "Hacker fare" providers = separate tickets (self-transfer risk).
Keep request volume low (default >= 3 s between calls). If you get HTML "captcha/robot"
pages instead of JSON, stop and retry later or use a browser manually.
"""
from __future__ import annotations

import argparse
import itertools
import re
import sys
import time

from _common import dump_json, polite_session, print_table, split_codes, to_eur

FLEX = {0: "exact", 1: "plusminusone", 2: "plusminustwo", 3: "plusminusthree"}


def _loc(codes: list[str], nearby: bool) -> dict:
    if nearby:
        return {"airport": codes[0], "locationType": "nearbyAirports"}
    return {"airports": codes, "locationType": "airports"}


def search(site: str, origins: list[str], dests: list[str], depart: str, ret: str | None,
           flex: int = 0, nearby: bool = False, pages: int = 1, max_polls: int = 15,
           adults: int = 1) -> dict:
    s = polite_session(min_delay=3.0, jitter=1.5)
    s.headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    o_path = (origins[0] + ",nearby") if nearby else ",".join(origins)
    d_path = ",".join(dests)
    dpart = depart + (f"-flexible-{flex}day{'s' if flex > 1 else ''}" if flex else "")
    path = f"{o_path}-{d_path}/{dpart}" + (f"/{ret}" + (f"-flexible-{flex}day{'s' if flex > 1 else ''}" if flex else "") if ret else "")
    url = f"https://{site}/flight-search/{path}?sort=price_a"
    r = s.get(url)
    m = re.search(r'"formtoken"\s*:\s*"([^"]+)"', r.text)
    if r.status_code != 200 or not m:
        raise RuntimeError(f"{site}: no CSRF token (HTTP {r.status_code}); bot check? URL={url}")
    legs = [{"origin": _loc(origins, nearby), "destination": _loc(dests, False),
             "date": depart, "flex": FLEX[flex]}]
    if ret:
        legs.append({"origin": _loc(dests, False), "destination": _loc(origins, nearby),
                     "date": ret, "flex": FLEX[flex]})
    body = {"filterParams": {}, "userSearchParams": {
        "legs": legs, "passengers": ["ADT"] * adults,
        "passengerDetails": [{"ptc": "ADT"}] * adults, "sortMode": "price_a"},
        "searchMetaData": {"pageNumber": 1, "searchTypes": []}}
    hdr = {"x-csrf": m.group(1), "x-requested-with": "XMLHttpRequest",
           "content-type": "application/json", "accept": "*/*", "referer": url,
           "origin": f"https://{site}"}
    poll_url = f"https://{site}/i/api/search/dynamic/flights/poll"
    merged = {"results": [], "legs": {}, "segments": {}, "airlines": {}, "providers": {},
              "airports": {}}
    d = {}
    for i in range(max_polls):
        p = s.post(poll_url, json=body, headers=hdr)
        try:
            d = p.json()
        except ValueError:
            raise RuntimeError(f"{site}: non-JSON poll response (HTTP {p.status_code}) - bot check?")
        if d.get("searchId"):
            body["userSearchParams"]["searchId"] = d["searchId"]
        print(f"[{site}] poll {i}: {d.get('status')} results={len(d.get('results') or [])} "
              f"total={d.get('totalCount')}", file=sys.stderr)
        if d.get("status") == "complete":
            break
    _merge(merged, d)
    for page in range(2, pages + 1):
        body["searchMetaData"]["pageNumber"] = page
        d = s.post(poll_url, json=body, headers=hdr).json()
        _merge(merged, d)
    merged.update({"url": url, "searchId": body["userSearchParams"].get("searchId"),
                   "status": d.get("status"), "totalCount": d.get("totalCount")})
    return merged


def _merge(m: dict, d: dict):
    m["results"] += [x for x in d.get("results") or [] if x.get("type") == "core"]
    for k in ("legs", "segments", "airlines", "providers", "airports"):
        if isinstance(d.get(k), dict):
            m[k].update(d[k])


def flatten(m: dict, site: str) -> list[dict]:
    rows = []
    for res in m["results"]:
        if not res.get("bookingOptions"):
            continue
        bo = res["bookingOptions"][0]
        price = bo["displayPrice"]["price"]
        cur = bo["displayPrice"]["currency"]
        legs_txt = []
        for lg in res.get("legs", []):
            L = m["legs"].get(lg["id"], {})
            segs = [m["segments"].get(sg["id"], {}) for sg in L.get("segments", lg.get("segments", []))]
            if not segs:
                continue
            path = "-".join([segs[0].get("origin", "?")] + [x.get("destination", "?") for x in segs])
            al = ",".join(dict.fromkeys(x.get("airline", "?") for x in segs))
            legs_txt.append(f"{path} {L.get('departure', '')[5:16].replace('T', ' ')}"
                            f"->{L.get('arrival', '')[5:16].replace('T', ' ')} {al}")
        am = {x["type"]: x for x in bo.get("fareAmenities", [])}
        chk = am.get("CHECKED_BAG", {})
        rows.append({
            "price": price, "currency": cur, "eur": to_eur(price, cur),
            "provider": bo.get("providerCode"),
            "itinerary": " | ".join(legs_txt),
            "carry_on": am.get("CARRYON_BAG", {}).get("restriction"),
            "checked": (chk.get("includedCheckedBagCount") if chk.get("restriction") == "INCLUDED"
                        else chk.get("restriction")),
            "hacker": res.get("hasHackerFares"),
            "providers": res.get("totalProviders"),
            "url": f"https://{site}{res.get('shareableUrl', '')}",
            "book": f"https://{site}{bo['bookingUrl']['url']}" if bo.get("bookingUrl") else None,
        })
    rows.sort(key=lambda x: x["eur"] if x["eur"] is not None else x["price"])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default="www.momondo.de",
                    help="www.momondo.de (EUR, default), www.kayak.de, www.kayak.com (USD), ...")
    ap.add_argument("--from", dest="origins", nargs="+", required=True)
    ap.add_argument("--nearby", action="store_true", help="first origin + nearby airports")
    ap.add_argument("--to", dest="dests", nargs="+", required=True, help="e.g. TYO OSA NGO FUK")
    ap.add_argument("--depart", required=True, help="date or comma list of dates")
    ap.add_argument("--return", dest="ret", help="return date or comma list (omit = one-way)")
    ap.add_argument("--flex", type=int, default=0, choices=[0, 1, 2, 3], help="+-N days")
    ap.add_argument("--pages", type=int, default=1, help="result pages (~60 per page)")
    ap.add_argument("--adults", type=int, default=1)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--show-links", action="store_true", help="print result URLs")
    ap.add_argument("--json", help="write JSON rows to path or '-'")
    a = ap.parse_args()
    origins, dests = split_codes(a.origins), split_codes(a.dests)
    rets = [x.strip() for x in a.ret.split(",")] if a.ret else [None]
    all_rows = []
    for dep, ret in itertools.product([x.strip() for x in a.depart.split(",")], rets):
        try:
            m = search(a.site, origins, dests, dep, ret, a.flex, a.nearby, a.pages, adults=a.adults)
        except RuntimeError as e:
            print(f"[error] {e}", file=sys.stderr)
            continue
        rows = flatten(m, a.site)
        for r in rows:
            r["depart"], r["return"] = dep, ret
        all_rows += rows
        print(f"\n== {a.site} {','.join(origins)}{' +nearby' if a.nearby else ''} -> "
              f"{','.join(dests)} {dep}{' / ' + ret if ret else ''}  ({len(rows)} results, "
              f"{m.get('totalCount')} total)  {m['url']}")
        cols = [("eur", "EUR"), ("price", "PRICE"), ("currency", "CUR"), ("provider", "PROVIDER"),
                ("checked", "BAGS"), ("itinerary", "ITINERARY")]
        if a.show_links:
            cols.append(("url", "URL"))
        print_table(rows, cols, limit=a.limit, maxw=130)
        time.sleep(3)
    dump_json(all_rows, a.json)


if __name__ == "__main__":
    main()
