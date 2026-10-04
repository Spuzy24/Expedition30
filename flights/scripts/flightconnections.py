#!/usr/bin/env python3
"""FlightConnections.com route-network lookup (direct routes, frequency, airlines) via
headless Chromium. Useful for ROUTE DISCOVERY: which airports have nonstop service to
Japan, which airlines fly a route, and what the home airports connect to.

The site is behind an AWS-WAF JS challenge (curl gets HTTP 202 with an empty body), so a
real browser is used. Data comes from the server-rendered airport pages
(https://www.flightconnections.com/flights-from-<slug>-<iata>, ".popular-destination" items
with "N flights / month") and two small JSON/HTML endpoints the page itself calls:
  /airports_url.php?lang=en&iata=zag            -> {"a": "Zagreb (ZAG)", "c": 334}
  /airlines_url.php?lang=en&depAps=<id>&desAps=  -> airlines serving that airport
No prices. Schedules are FlightConnections' (current + upcoming season), not live.

Examples
--------
  python3 flightconnections.py from ZAG LJU VIE         # nonstop destinations + airlines
  python3 flightconnections.py to NRT HND KIX           # nonstop origins of Japanese airports
  python3 flightconnections.py from VIE --filter-country JP,CN,KR,AE,QA,TR
  python3 flightconnections.py route VIE NRT            # airlines on one route
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from bs4 import BeautifulSoup

from _browser import browser_page, click_consent
from _common import dump_json, print_table, split_codes

BASE = "https://www.flightconnections.com"


def _slug(name: str) -> str:
    # "Zagreb (ZAG)" -> "zagreb-zag" ; "Tokyo Narita (NRT)" -> "tokyo-narita-nrt"
    s = name.lower().replace("(", " ").replace(")", " ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _fetch(page, path: str) -> str:
    return page.evaluate("async (u) => { const r = await fetch(u, {credentials:'include', "
                         "headers:{'x-requested-with':'XMLHttpRequest'}}); return await r.text(); }",
                         BASE + path)


def airport_info(page, iata: str) -> dict:
    txt = _fetch(page, f"/airports_url.php?lang=en&iata={iata.lower()}")
    try:
        d = json.loads(txt)
        return {"name": d.get("a"), "id": d.get("c")}
    except ValueError:
        return {}


def parse_destinations(html: str, section: str = "popular-destinations") -> list[dict]:
    s = BeautifulSoup(html, "lxml")
    lst = s.find(id=section)
    rows = []
    for a in (lst.select("a.popular-destination") if lst else []):
        name = a.get("data-a") or ""
        m = re.search(r"\(([A-Z0-9]{3})\)", name)
        span = a.select_one("span")
        freq = span.get_text(strip=True) if span else ""
        fm = re.search(r"(\d+)\s+flights", freq)
        flag = a.select_one("img")
        rows.append({"iata": m.group(1) if m else None, "name": name,
                     "country": flag.get("alt") if flag else None,
                     "flights_per_month": int(fm.group(1)) if fm else None,
                     "href": a.get("href")})
    return rows


def airlines_for(page, ap_id, dest_id="") -> list[str]:
    html = _fetch(page, f"/airlines_url.php?lang=en&ids=&cl=&depAps={ap_id}&desAps={dest_id}")
    s = BeautifulSoup(html, "lxml")
    return [f"{d.get('data-name')} ({d.get('data-iata')})" for d in s.select("div.airline-option")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["from", "to", "route"])
    ap.add_argument("airports", nargs="+")
    ap.add_argument("--filter-country", help="only destinations in these country names/ISO2 "
                                             "(matches the flag alt text, e.g. Japan or JP)")
    ap.add_argument("--json")
    a = ap.parse_args()
    codes = split_codes(a.airports)
    out = {}
    with browser_page() as (page, _):
        page.goto(BASE + "/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        click_consent(page, tries=2)
        if a.mode == "route":
            o, d = codes[0], codes[1]
            oi, di = airport_info(page, o), airport_info(page, d)
            page.goto(f"{BASE}/flights-from-{o.lower()}-to-{d.lower()}", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            txt = BeautifulSoup(page.content(), "lxml").get_text(" ", strip=True)
            m = re.search(r"([^.]{0,200}direct flight[^.]{0,200}\.)", txt, re.I)
            als = airlines_for(page, oi.get("id"), di.get("id"))
            out = {"route": f"{o}-{d}", "airlines": als, "summary": m.group(1) if m else None}
            print(f"{o} ({oi.get('name')}) -> {d} ({di.get('name')})")
            print("airlines:", ", ".join(als) or "(none listed)")
            if m:
                print("page says:", m.group(1))
        else:
            for c in codes:
                info = airport_info(page, c)
                if not info.get("name"):
                    print(f"[fc] unknown airport {c}", file=sys.stderr)
                    continue
                slug = _slug(info["name"])
                url = f"{BASE}/flights-{'from' if a.mode == 'from' else 'to'}-{slug}"
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)
                rows = parse_destinations(page.content())
                if a.filter_country:
                    want = {x.strip().lower() for x in a.filter_country.split(",")}
                    rows = [r for r in rows if (r["country"] or "").lower() in want or
                            (r.get("href") or "").lower().endswith(tuple(f"-{w}" for w in want))]
                als = airlines_for(page, info["id"]) if a.mode == "from" else []
                out[c] = {"name": info["name"], "url": url, "routes": rows, "airlines": als}
                print(f"\n== {info['name']} - nonstop {'destinations' if a.mode == 'from' else 'origins'}: "
                      f"{len(rows)}   {url}")
                if als:
                    print("airlines:", ", ".join(als))
                print_table(sorted(rows, key=lambda r: -(r["flights_per_month"] or 0)),
                            [("iata", "IATA"), ("name", "AIRPORT"), ("country", "COUNTRY"),
                             ("flights_per_month", "FLIGHTS/MONTH")])
    dump_json(out, a.json)


if __name__ == "__main__":
    main()
