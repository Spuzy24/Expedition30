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

  # Nearby airports of Zagreb, +-3 days flexible, one-way, on kayak.de (dedupe is on by default)
  python3 kayak.py --site www.kayak.de --from ZAG --nearby --to TYO,OSA --depart 2027-03-10 --flex 3

  # Nearby airports of ZAG AND of BUD: one search per origin, merged into one table
  python3 kayak.py --from ZAG,BUD --nearby --to TYO,OSA --depart 2027-03-10

  # Several date pairs in one run (spaced out politely); --json gets every fetched page
  python3 kayak.py --from VIE --to TYO --depart 2027-03-08,2027-03-10 --return 2027-03-24 --pages 2 --json out.json

Output columns: EUR/pp (price PER PERSON: with --adults 2 Kayak shows the same per-person
price, verified 2026-10-04; JSON has eur_total = eur x adults), provider (OTA/airline selling it),
TICKET, bags included (checked count / FEE / UNKNOWN), EUR+BAG (cheapest option of the same
itinerary with >= 1 checked bag), ROWS (with dedupe: how many rows the line stands for), and the
itinerary per direction ("airports times airlines"; directions separated by " | ").
  * '~' in a route = station change inside one direction, e.g. ZAG-CRL~BRU-PVG-KIX (FR to
    Charleroi, then get yourself to Brussels). JSON: route, carriers, airport_change.
  * TICKET: 1 = one ticket; self-transfer = Kiwi virtual interlining (providers SKYPICKER/KIWIVI/
    KIWIVILCC, Kayak's SELF_TRANSFER warning or a virtual-interline option); hacker = Kayak
    "Hacker fare" (separate tickets, e.g. provider splitbookingow). JSON: self_transfer, hacker,
    separate_tickets.
  * --dedupe (default ON with --flex > 0, several origins or --nearby; --no-dedupe = off) keeps
    the cheapest row per (marketing carriers, airport sequence, provider), so a +-3-day search
    doesn't fill the top 30 with one fare on 30 dates. --json always holds ALL rows of all pages
    (hidden ones have dedupe_hidden: true).
Keep request volume low (default >= 3 s between calls). If you get HTML "captcha/robot"
pages instead of JSON, stop and retry later or use a browser manually.
"""
from __future__ import annotations

import argparse
import itertools
import re
import sys
import time

from _common import (dump_json, polite_session, price_header, print_table, split_codes,
                     station_route, to_eur)

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
              "airports": {}, "pages": []}
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
    _merge(merged, d, 1)
    for page in range(2, pages + 1):
        body["searchMetaData"]["pageNumber"] = page
        p = s.post(poll_url, json=body, headers=hdr)
        try:
            d = p.json()
        except ValueError:
            print(f"[{site}] page {page}: non-JSON response (HTTP {p.status_code}); stopping paging",
                  file=sys.stderr)
            break
        n = _merge(merged, d, page)
        print(f"[{site}] page {page}: {d.get('status')} results={n}", file=sys.stderr)
        if not n:
            break
    merged.update({"url": url, "searchId": body["userSearchParams"].get("searchId"),
                   "status": d.get("status"), "totalCount": d.get("totalCount")})
    return merged


def _merge(m: dict, d: dict, page: int = 1) -> int:
    """Add one poll/page answer to the merged result; returns the number of new core results."""
    seen = {x.get("resultId") for x in m["results"] if x.get("resultId")}
    new = [dict(x, _page=page) for x in d.get("results") or []
           if x.get("type") == "core" and (not x.get("resultId") or x["resultId"] not in seen)]
    m["results"] += new
    for k in ("legs", "segments", "airlines", "providers", "airports"):
        if isinstance(d.get(k), dict):
            m[k].update(d[k])
    m["pages"].append({"page": page, "results": len(new), "status": d.get("status")})
    return len(new)


# Kiwi.com sells its "virtual interlining" combos on Kayak/momondo under these provider codes:
# separate tickets with a self-transfer, whatever hasHackerFares says (it is False for them).
KIWI_SELF_TRANSFER = {"SKYPICKER", "KIWIVI", "KIWIVILCC"}


def ticket_type(res: dict, bo: dict) -> tuple[bool, bool]:
    """(self_transfer, hacker) for one result + its cheapest booking option.

    self_transfer: Kayak's SELF_TRANSFER warning, a virtual-interline booking option, a
    segment flagged hasSelfTransfer, or a Kiwi provider code (SKYPICKER/KIWIVI/KIWIVILCC).
    hacker: Kayak "Hacker fare" = separate tickets per direction/part (hasHackerFares, split
    booking options or a splitbooking* provider)."""
    prov = (bo.get("providerCode") or "").upper()
    st = ("SELF_TRANSFER" in (res.get("warnings") or [])
          or bool((bo.get("flags") or {}).get("hasVirtualInterline"))
          or any(sg.get("hasSelfTransfer") for lg in res.get("legs", []) for sg in lg.get("segments", []))
          or prov in KIWI_SELF_TRANSFER)
    hk = bool(res.get("hasHackerFares")) or bool(bo.get("splitBookingOptions")) or prov.startswith("SPLITBOOKING")
    return st, hk


def flatten(m: dict, site: str) -> list[dict]:
    rows = []
    for res in m["results"]:
        if not res.get("bookingOptions"):
            continue
        bo = res["bookingOptions"][0]  # always the cheapest option (checked 2026-10-04)
        price = bo["displayPrice"]["price"]
        cur = bo["displayPrice"]["currency"]
        legs_txt, routes, carriers, change = [], [], [], False
        for lg in res.get("legs", []):
            L = m["legs"].get(lg["id"], {})
            segs = [m["segments"].get(sg["id"], {}) for sg in L.get("segments", lg.get("segments", []))]
            if not segs:
                continue
            path, ch = station_route([(x.get("origin", "?"), x.get("destination", "?")) for x in segs])
            change = change or ch
            al = ",".join(dict.fromkeys(x.get("airline", "?") for x in segs))
            routes.append(path)
            carriers.append(al)
            legs_txt.append(f"{path} {L.get('departure', '')[5:16].replace('T', ' ')}"
                            f"->{L.get('arrival', '')[5:16].replace('T', ' ')} {al}")
        am = {x["type"]: x for x in bo.get("fareAmenities", [])}
        chk = am.get("CHECKED_BAG", {})
        st, hk = ticket_type(res, bo)
        bag_bucket = next((b for b in res.get("bookingOptionsBuckets") or []
                           if b.get("type") == "CHECKED_BAG_OPTIONS" and b.get("topPrice")), None)
        rows.append({
            "price": price, "currency": cur, "eur": to_eur(price, cur),
            "provider": bo.get("providerCode"),
            "itinerary": " | ".join(legs_txt),
            # route per direction, ' | ' between directions; '~' = station change inside a direction
            "route": " | ".join(routes), "carriers": " | ".join(carriers),
            "airport_change": change,
            "carry_on": am.get("CARRYON_BAG", {}).get("restriction"),
            "checked": (chk.get("includedCheckedBagCount") if chk.get("restriction") == "INCLUDED"
                        else chk.get("restriction")),
            # cheapest option of this result that includes >= 1 checked bag (Kayak's "+1 bag" tab)
            "eur_with_bag": (to_eur(bag_bucket["topPrice"]["price"], bag_bucket["topPrice"]["currency"])
                             if bag_bucket else None),
            "hacker": hk, "self_transfer": st, "separate_tickets": st or hk,
            "ticket": ("self-transfer+hacker" if st and hk else "self-transfer" if st
                       else "hacker" if hk else "1"),
            "providers": res.get("totalProviders"),
            "page": res.get("_page", 1),
            "url": f"https://{site}{res.get('shareableUrl', '')}",
            "book": f"https://{site}{bo['bookingUrl']['url']}" if bo.get("bookingUrl") else None,
        })
    rows.sort(key=lambda x: x["eur"] if x["eur"] is not None else x["price"])
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    """Keep the cheapest row per (marketing carriers, airport sequence, provider). Rows must be
    sorted cheapest first. With --flex, Kayak returns the same fare on many dates and times; this
    keeps one row per fare (`dupes` = how many rows it stands for). Hidden rows get
    `dedupe_hidden: True` and stay in --json."""
    kept: dict[tuple, dict] = {}
    for r in rows:
        k = (r["carriers"], r["route"], r["provider"])
        if k in kept:
            kept[k]["dupes"] += 1
            r["dedupe_hidden"] = True
        else:
            r["dupes"], r["dedupe_hidden"] = 1, False
            kept[k] = r
    return list(kept.values())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default="www.momondo.de",
                    help="www.momondo.de (EUR, default), www.kayak.de, www.kayak.com (USD), ...")
    ap.add_argument("--from", dest="origins", nargs="+", required=True)
    ap.add_argument("--nearby", action="store_true",
                    help="each origin + its nearby airports (several origins = one search per origin, merged)")
    ap.add_argument("--to", dest="dests", nargs="+", required=True, help="e.g. TYO OSA NGO FUK")
    ap.add_argument("--depart", required=True, help="date or comma list of dates")
    ap.add_argument("--return", dest="ret", help="return date or comma list (omit = one-way)")
    ap.add_argument("--flex", type=int, default=0, choices=[0, 1, 2, 3], help="+-N days")
    ap.add_argument("--pages", type=int, default=1, help="result pages (~50 per page); all go to --json")
    ap.add_argument("--adults", type=int, default=1,
                    help="adults; prices shown are PER PERSON (Kayak/momondo display convention)")
    ap.add_argument("--dedupe", dest="dedupe", action="store_true", default=None,
                    help="table: cheapest row per (carriers, airports, provider). Default ON with "
                         "--flex > 0, several origins or --nearby")
    ap.add_argument("--no-dedupe", dest="dedupe", action="store_false", help="show every row")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--show-links", action="store_true", help="print result URLs")
    ap.add_argument("--json", help="write JSON rows (all pages, incl. rows hidden by --dedupe) to path or '-'")
    a = ap.parse_args()
    origins, dests = split_codes(a.origins), split_codes(a.dests)
    rets = [x.strip() for x in a.ret.split(",")] if a.ret else [None]
    dd = a.dedupe if a.dedupe is not None else (a.flex > 0 or len(origins) > 1 or a.nearby)
    # Kayak's nearbyAirports location takes ONE anchor airport, so --nearby with several origins
    # runs one search per origin and merges them (it used to silently drop all but the first).
    groups = [[o] for o in origins] if (a.nearby and len(origins) > 1) else [origins]
    if len(groups) > 1:
        print(f"[kayak] --nearby with {len(origins)} origins: {len(groups)} searches per date pair "
              f"(one per origin), merged", file=sys.stderr)
    price_hdr = price_header(a.adults, "per_person")  # verified: same price for 1 and 2 adults
    all_rows = []
    first = True
    for dep, ret in itertools.product([x.strip() for x in a.depart.split(",")], rets):
        rows, urls, total = [], [], 0
        for g in groups:
            if not first:
                time.sleep(3)
            first = False
            try:
                m = search(a.site, g, dests, dep, ret, a.flex, a.nearby, a.pages, adults=a.adults)
            except RuntimeError as e:
                print(f"[error] {e}", file=sys.stderr)
                continue
            part = flatten(m, a.site)
            for r in part:
                r.update({"depart": dep, "return": ret, "search_origin": ",".join(g),
                          "pax": a.adults, "price_basis": "per_person",
                          "eur_total": round(r["eur"] * a.adults, 2) if r["eur"] is not None else None})
            rows += part
            urls.append(m["url"])
            total += m.get("totalCount") or 0
        rows.sort(key=lambda x: x["eur"] if x["eur"] is not None else x["price"])
        all_rows += rows
        shown = dedupe(rows) if dd else rows
        print(f"\n== {a.site} {','.join(origins)}{' +nearby' if a.nearby else ''} -> "
              f"{','.join(dests)} {dep}{' / ' + ret if ret else ''}  ({len(rows)} results"
              f"{f', {len(shown)} after dedupe' if dd else ''}, {total} total; "
              f"{'price per person, ' + str(a.adults) + ' adults' if a.adults > 1 else '1 adult'})  "
              f"{' '.join(urls)}")
        cols = [("eur", price_hdr), ("price", "PRICE"), ("currency", "CUR"), ("provider", "PROVIDER"),
                ("ticket", "TICKET"), ("checked", "BAGS"), ("eur_with_bag", "EUR+BAG")]
        if dd:
            cols.append(("dupes", "ROWS"))
        cols.append(("itinerary", "ITINERARY"))
        if a.show_links:
            cols.append(("url", "URL"))
        print_table(shown, cols, limit=a.limit, maxw=130)
        if any(r["airport_change"] for r in shown[: a.limit]):
            print("'~' in a route = station change (e.g. CRL~BRU): you must get to another airport yourself")
        if any(r["separate_tickets"] for r in shown[: a.limit]):
            print("TICKET self-transfer/hacker = separate tickets (missed connections are your risk)")
    dump_json(all_rows, a.json)


if __name__ == "__main__":
    main()
