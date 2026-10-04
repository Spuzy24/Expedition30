#!/usr/bin/env python3
"""Aviasales.com live meta-search via headless Chromium (Playwright).

Why a browser: the search API (tickets-api.aviasales.com/search/v2/start + /search/v3.2/results)
requires an AWS-WAF token (x-aws-waf-token) minted by JavaScript in the page. The old public
cached endpoints (min-prices.aviasales.ru calendar_preload / price_matrix, map.aviasales.ru)
are gone (404/302) and the Travelpayouts Data API needs a partner token (account signup).

The script opens https://www.aviasales.com/search/<ORIG><DDMM><DEST>[<DDMM>]<pax>, lets the page
run the search, raises the results page size from 10 to --page-size (by rewriting the page's
own results request), collects every results chunk and prints tickets sorted by price.
Prices are LIVE offers from OTAs/airlines (agent = seller), in EUR. Many cheapest offers are
self-transfer combos sold by OTAs such as Mytrip/Gotogate (e.g. Ryanair + China Eastern).

Examples
--------
  python3 aviasales.py --from VIE --to TYO --depart 2027-03-10
  python3 aviasales.py --from ZAG --to TYO --depart 2027-03-10 --return 2027-03-24 --json out.json
  python3 aviasales.py --from BUD --to OSA --depart 2027-03-10 --show-urls

Limits: ~40-60 s per search; keep to a handful of searches per run (bot protection).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time

from _browser import browser_page, click_consent, wait_until
from _common import dump_json, print_table, split_codes, to_eur


def search_url(o: str, d: str, dep: str, ret: str | None, adults: int, currency: str) -> str:
    dd = dt.date.fromisoformat(dep).strftime("%d%m")
    rr = dt.date.fromisoformat(ret).strftime("%d%m") if ret else ""
    return (f"https://www.aviasales.com/search/{o}{dd}{d}{rr}{adults}"
            f"?currency={currency.lower()}&language=en")


def run(o, d, dep, ret, adults=1, currency="EUR", page_size=100, timeout=90) -> list[dict]:
    url = search_url(o, d, dep, ret, adults, currency)
    chunks = []

    def set_limit(route, request):
        try:
            body = json.loads(request.post_data or "{}")
            body["limit"] = page_size
            route.continue_(post_data=json.dumps(body))
        except Exception:
            route.continue_()

    with browser_page(capture=lambda u: "/search/v3.2/results" in u or "/search/v2/start" in u) as (page, cap):
        page.route("**/search/v3.2/results", set_limit)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        click_consent(page, tries=3)

        def done():
            res = [c for c in cap if "/results" in c["url"] and c.get("json")]
            return any(isinstance(c["json"], list) and c["json"] and
                       c["json"][0].get("last_update_timestamp") == 0 for c in res)
        ok = wait_until(done, timeout)
        print(f"[aviasales] {o}->{d} {dep}{'/' + ret if ret else ''}: "
              f"{'complete' if ok else 'TIMEOUT (partial)'}; title={page.title()!r}", file=sys.stderr)
        chunks = [c["json"][0] for c in cap if "/results" in c["url"] and isinstance(c.get("json"), list) and c["json"]]
        if not chunks:
            if any(c["url"].endswith("/start") and c["status"] >= 400 for c in cap):
                print("[aviasales] search/start rejected (bot check) - try later", file=sys.stderr)
    return parse_chunks(chunks, url)


def parse_chunks(chunks: list[dict], url: str) -> list[dict]:
    rows, seen = [], set()
    for ch in chunks:
        legs = ch.get("flight_legs") or []
        agents = ch.get("agents") or {}
        tickets = list(ch.get("tickets") or [])
        if ch.get("cheapest_ticket"):
            tickets.append(ch["cheapest_ticket"])
        for t in tickets:
            if not t.get("proposals"):
                continue
            p = min(t["proposals"], key=lambda x: x["price"]["value"])
            segs_txt, carriers = [], []
            for sg in t["segments"]:
                fl = [legs[i] for i in sg["flights"] if i < len(legs)]
                if not fl:
                    continue
                path = "-".join([fl[0]["origin"]] + [f["destination"] for f in fl])
                segs_txt.append(f"{path} {fl[0]['local_departure_date_time'][5:]}->"
                                f"{fl[-1]['local_arrival_date_time'][5:]}")
                carriers.append(",".join(dict.fromkeys(f["operating_carrier_designator"]["carrier"] for f in fl)))
            key = (" | ".join(segs_txt), round(p["price"]["value"]))
            if key in seen or not segs_txt:
                continue
            seen.add(key)
            mf = p.get("minimum_fare") or {}
            vi = any(x.get("is_virtual_interline") for tt in p.get("transfer_terms") or [] for x in tt)
            ag = agents.get(str(p.get("agent_id")), {})
            rows.append({
                "price": round(p["price"]["value"], 2), "currency": p["price"]["currency_code"],
                "eur": to_eur(p["price"]["value"], p["price"]["currency_code"]),
                "itinerary": " | ".join(segs_txt), "airlines": " | ".join(carriers),
                "agent": (ag.get("label", {}).get("en", {}) or {}).get("default") or ag.get("gate_name"),
                "checked_bags": (mf.get("baggage") or {}).get("count"),
                "self_transfer": vi or any("recheck_baggage" in json.dumps(sg.get("transfers")) and
                                           any(tr.get("recheck_baggage") for tr in sg.get("transfers") or [])
                                           for sg in t["segments"]),
                "offers": len(t["proposals"]),
            })
    rows.sort(key=lambda r: r["eur"] if r["eur"] is not None else r["price"])
    for r in rows:
        r["search_url"] = url
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="origins", nargs="+", required=True, help="IATA airport/city codes")
    ap.add_argument("--to", dest="dests", nargs="+", required=True, help="e.g. TYO OSA")
    ap.add_argument("--depart", required=True)
    ap.add_argument("--return", dest="ret")
    ap.add_argument("--adults", type=int, default=1)
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--show-urls", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    allrows = []
    for o in split_codes(a.origins):
        for d in split_codes(a.dests):
            rows = run(o, d, a.depart, a.ret, a.adults, a.currency, a.page_size, a.timeout)
            print(f"\n== Aviasales {o}->{d} {a.depart}{' / ' + a.ret if a.ret else ''}: "
                  f"{len(rows)} tickets  {search_url(o, d, a.depart, a.ret, a.adults, a.currency)}")
            print_table(rows, [("eur", "EUR"), ("agent", "SELLER"), ("checked_bags", "BAGS"),
                               ("self_transfer", "SELF-TR"), ("airlines", "AIRLINES"),
                               ("itinerary", "ITINERARY")], limit=a.limit, maxw=110)
            allrows += rows
            time.sleep(5)
    dump_json(allrows, a.json)


if __name__ == "__main__":
    main()
