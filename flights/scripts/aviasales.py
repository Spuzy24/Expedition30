#!/usr/bin/env python3
"""Aviasales.com live meta-search via headless Chromium (Playwright).

Why a browser: the search API (tickets-api.aviasales.com/search/v2/start + /search/v3.2/results)
requires an AWS-WAF token (x-aws-waf-token) minted by JavaScript in the page. The old public
cached endpoints (min-prices.aviasales.ru calendar_preload / price_matrix, map.aviasales.ru)
are gone (404/302) and the Travelpayouts Data API needs a partner token (account signup).

The script opens https://www.aviasales.com/search/<ORIG><DDMM><DEST>[<DDMM>]<pax>, lets the page
run the search (after answering the cookie banner - the search waits for it), collects the
results), collects every results chunk (each holds the 10 "best" tickets + the cheapest
ticket; the page-size cannot be raised - rewriting the request breaks the WAF check) and
prints the tickets sorted by price, plus the overall cheapest / cheapest-with-baggage.
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
import os
import sys
import time

from _browser import browser_page, click_consent, wait_until
from _common import dump_json, print_table, split_codes, to_eur


def search_url(o: str, d: str, dep: str, ret: str | None, adults: int, currency: str) -> str:
    dd = dt.date.fromisoformat(dep).strftime("%d%m")
    rr = dt.date.fromisoformat(ret).strftime("%d%m") if ret else ""
    return (f"https://www.aviasales.com/search/{o}{dd}{d}{rr}{adults}"
            f"?currency={currency.lower()}&language=en")


def run(o, d, dep, ret, adults=1, currency="EUR", timeout=90) -> list[dict]:
    url = search_url(o, d, dep, ret, adults, currency)
    chunks = []

    with browser_page(capture=lambda u: ("/search/v3.2/results" in u or "/search/v2/start" in u
                                         or "/search/prices/ribbon" in u)) as (page, cap):
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        consent = {"done": False}

        def done():
            # The search only starts after the cookie banner is answered, which can appear late.
            if not consent["done"]:
                consent["done"] = click_consent(page, tries=1)
            res = [c for c in cap if "/results" in c["url"] and c.get("json")]
            return any(isinstance(c["json"], list) and c["json"] and
                       c["json"][0].get("last_update_timestamp") == 0 for c in res)
        ok = wait_until(done, timeout, step=1.5, page=page)
        print(f"[aviasales] {o}->{d} {dep}{'/' + ret if ret else ''}: "
              f"{'complete' if ok else 'TIMEOUT (partial)'}; title={page.title()!r}", file=sys.stderr)
        chunks = [c["json"][0] for c in cap if "/results" in c["url"] and isinstance(c.get("json"), list) and c["json"]]
        ribbon = next((c["json"] for c in cap if "/ribbon" in c["url"] and c.get("json")), None)
        if ribbon:
            print(f"[aviasales] nearby-dates ribbon (cached): {json.dumps(ribbon)[:600]}", file=sys.stderr)
        if chunks:
            m = chunks[-1].get("meta") or {}
            print(f"[aviasales] total tickets={m.get('total_tickets_count')} cheapest="
                  f"{round(m.get('first_ticket_price') or 0)} cheapest_with_baggage="
                  f"{round(m.get('cheapest_baggage_ticket_price') or 0)} (EUR)", file=sys.stderr)
        if os.environ.get("AVIA_DEBUG"):
            for c in cap:
                print("  [debug]", c["status"], c["url"][:90], type(c.get("json")).__name__, c.get("err"), file=sys.stderr)
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
            # same ticket, cheapest seller that includes >= 1 checked bag (e.g. Kiwi.com 0 bags EUR 735
            # vs Gotogate/Trip.com 2x23 kg for a few euros more): the cheapest offer alone hid that
            pb = [x for x in t["proposals"] if ((x.get("minimum_fare") or {}).get("baggage") or {}).get("count", 0) >= 1]
            pb = min(pb, key=lambda x: x["price"]["value"]) if pb else None
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
                "eur_with_bag": to_eur(pb["price"]["value"], pb["price"]["currency_code"]) if pb else None,
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
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--show-urls", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    allrows = []
    for o in split_codes(a.origins):
        for d in split_codes(a.dests):
            rows = run(o, d, a.depart, a.ret, a.adults, a.currency, a.timeout)
            print(f"\n== Aviasales {o}->{d} {a.depart}{' / ' + a.ret if a.ret else ''}: "
                  f"{len(rows)} tickets  {search_url(o, d, a.depart, a.ret, a.adults, a.currency)}")
            print_table(rows, [("eur", "EUR"), ("agent", "SELLER"), ("checked_bags", "BAGS"), ("eur_with_bag", "EUR+BAG"),
                               ("self_transfer", "SELF-TR"), ("airlines", "AIRLINES"),
                               ("itinerary", "ITINERARY")], limit=a.limit, maxw=110)
            allrows += rows
            time.sleep(5)
    dump_json(allrows, a.json)


if __name__ == "__main__":
    main()
