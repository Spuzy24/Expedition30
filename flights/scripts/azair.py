#!/usr/bin/env python3
"""AZair.eu low-cost-carrier search (positioning flights in Europe), plain HTTP GET + HTML parse.

AZair indexes cached low-cost fares (Ryanair, Wizz, easyJet, Vueling, Volotea, Transavia,
Eurowings, Pegasus, flydubai...) and also builds self-transfer LCC combos ("1 change").
It is the easiest "from many home airports to ANYWHERE" search for cheap European legs.

Examples
--------
  # One-way from Zagreb (+Ljubljana, Graz) to anywhere, departing 1-10 Nov 2026
  python3 azair.py --from ZAG,LJU,GRZ --anywhere --dates 2026-11-01..2026-11-10

  # Return trip ZAG/VIE/BUD -> Istanbul (both airports) or Milan, out 1-5 Mar, stay 14-21 days
  python3 azair.py --from ZAG,VIE,BUD --to IST,SAW,MXP,BGY --dates 2027-03-01..2027-03-05 \
      --return --min-days 14 --max-days 21

Important limitations (tested 2026-10-04)
-----------------------------------------
* Prices are CACHED: each leg shows how many hours ago it was checked ("age_h"), often
  hundreds of hours. Treat as indicative; confirm on the airline site.
* Search horizon is short in practice: the web form only offers ~4 months ahead and queries
  further out (Feb-Mar 2027) returned "No results". Use ryanair_wizz.py for far-future dates.
* The backend often answers "not able to answer your query in a timely manner" (an
  overload/soft-throttle message, returned instantly). The script retries with back-off;
  keep searches narrow (few airports, <= ~10 day windows) and space them out (>= 10 s).
* Fare only (no bags). Multi-leg "1 change" results are self-transfer on separate tickets.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

from _common import (CACHE_DIR, dump_json, parse_date_range, polite_session, print_table,
                     split_codes)

BASE = "https://www.azair.eu/azfin.php"
AIRPORTS_JS = "https://static7.azair.us/www-azair-eu-assets/js/airports_array.js"
S = polite_session(min_delay=10.0, jitter=3.0)
S.headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


def airport_names() -> dict[str, str]:
    """IATA -> AZair display name (e.g. 'STN' -> 'London (Stansted)'), cached 7 days."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "azair_airports.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 7 * 86400:
        return json.loads(cache.read_text())
    r = S.get(AIRPORTS_JS)
    names = dict(re.findall(r'"([A-Z0-9]{3})"\s*:\s*"([^"]+)"', r.text))
    cache.write_text(json.dumps(names))
    return names


def _label(codes: list[str], names: dict[str, str]) -> str:
    first = codes[0]
    lab = f"{names.get(first, first)} [{first}]"
    if len(codes) > 1:
        lab += f" (+{','.join(codes[1:])})"
    return lab


def build_params(src: list[str], dst: list[str] | None, d1: dt.date, d2: dt.date,
                 oneway: bool, min_days: int, max_days: int, max_changes: int,
                 currency: str, adults: int) -> dict:
    names = airport_names()
    p = {"searchtype": "flexi", "tp": "0", "isOneway": "oneway" if oneway else "return",
         "srcAirport": _label(src, names), "srcFreeAirport": "", "srcTypedText": "",
         "srcFreeTypedText": "", "srcMC": "",
         "dstAirport": "Anywhere [XXX]" if not dst else _label(dst, names),
         "dstFreeAirport": "", "dstTypedText": "", "dstFreeTypedText": "", "dstMC": "",
         "depmonth": d1.strftime("%Y%m"), "depdate": d1.isoformat(), "aid": "0",
         "arrmonth": d2.strftime("%Y%m"), "arrdate": d2.isoformat(),
         "minDaysStay": str(min_days), "maxDaysStay": str(max_days),
         "samedep": "true", "samearr": "true", "minHourStay": "0:45", "maxHourStay": "23:20",
         "minHourOutbound": "0:00", "maxHourOutbound": "24:00", "minHourInbound": "0:00",
         "maxHourInbound": "24:00", "autoprice": "true", "adults": str(adults),
         "children": "0", "infants": "0", "maxChng": str(max_changes), "currency": currency,
         "lang": "en", "indexSubmit": "Search"}
    for i in range(7):
        p[f"dep{i}"] = "true"
        p[f"arr{i}"] = "true"
    for i, c in enumerate(src[1:]):
        p[f"srcap{i}"] = c
    if dst:
        for i, c in enumerate(dst[1:]):
            p[f"dstap{i}"] = c
    else:
        p["anywhere"] = "true"
    return p


def _money(t: str) -> float | None:
    m = re.search(r"([\d.,]+)", t.replace("\xa0", " "))
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def parse(html: str) -> tuple[list[dict], str]:
    s = BeautifulSoup(html, "lxml")
    txt = s.get_text(" ", strip=True)
    status = ("busy" if "timely manner" in txt else
              "no_results" if "No results were found" in txt else "ok")
    out = []
    for res in s.select("div.result"):
        heads = res.select("div.text > p")
        if not heads:
            continue
        legs = []
        for lp in res.select("div.detail p"):
            fr, to = lp.select_one("span.from"), lp.select_one("span.to")
            if not fr or not to:
                continue
            fcode = fr.select_one("span.code")
            tcode = to.select_one("span.code")
            flight = to.select_one("a")
            chk = lp.select_one("span.checked")
            legs.append({
                "dep": re.sub(r"\s+", " ", fr.find(string=True, recursive=False) or "").strip(),
                "from": fcode.find(string=True, recursive=False).strip() if fcode else None,
                "arr": re.sub(r"\s+", " ", to.find(string=True, recursive=False) or "").strip(),
                "to": tcode.find(string=True, recursive=False).strip() if tcode else None,
                "flight": flight.get_text(strip=True) if flight else None,
                "airline": (lp.select_one("span.airline").get_text(strip=True)
                            if lp.select_one("span.airline") else None),
                "price": _money(lp.select_one("span.legPrice").get_text()) if lp.select_one("span.legPrice") else None,
                "age_h": int(chk["data-age"]) if chk and chk.get("data-age", "").isdigit() else None,
            })
        hd = heads[0]
        date = hd.select_one("span.date").get_text(strip=True) if hd.select_one("span.date") else ""
        m = re.search(r"(\d\d)/(\d\d)/(\d\d)", date)
        iso = f"20{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else date

        def codes_of(p):
            c = [x.find(string=True, recursive=False).strip() for x in p.select("span.code")]
            return c[0] if c else None, c[-1] if c else None
        o, d = codes_of(hd)
        ret = None
        if len(heads) > 1 and heads[1].select_one("span.date"):
            m2 = re.search(r"(\d\d)/(\d\d)/(\d\d)", heads[1].select_one("span.date").get_text())
            ret = f"20{m2.group(3)}-{m2.group(2)}-{m2.group(1)}" if m2 else None
        tp = res.select_one("div.totalPrice span.tp") or res.select_one("span.sumPrice span.bp")
        out.append({
            "from": o, "to": d, "date": iso,
            "dep_time": hd.select_one("span.from strong").get_text(strip=True) if hd.select_one("span.from strong") else "",
            "duration": (hd.select_one("span.durcha").get_text(" ", strip=True) if hd.select_one("span.durcha") else ""),
            "return": ret,
            "price": _money(tp.get_text()) if tp else _money(hd.select_one("span.subPrice").get_text()),
            "airlines": ",".join(sorted({l["airline"] for l in legs if l["airline"]})),
            "flights": " ".join(l["flight"] or "?" for l in legs),
            "max_age_h": max([l["age_h"] for l in legs if l["age_h"] is not None], default=None),
            "legs": legs,
        })
    return out, status


def search(a) -> list[dict]:
    src = split_codes(a.origins)
    dst = split_codes(a.to) if a.to else None
    d1, d2 = parse_date_range(a.dates)
    params = build_params(src, None if a.anywhere else dst, d1, d2, not a.ret, a.min_days,
                          a.max_days, a.max_changes, a.currency, a.adults)
    for attempt in range(a.retries + 1):
        r = S.get(BASE, params=params, timeout=120)
        rows, status = parse(r.text)
        print(f"[azair] HTTP {r.status_code} status={status} results={len(rows)} "
              f"(attempt {attempt + 1})", file=sys.stderr)
        if status != "busy":
            break
        time.sleep(20 * (attempt + 1))
    if a.verbose:
        print(r.url, file=sys.stderr)
    rows.sort(key=lambda x: (x["price"] is None, x["price"] or 0))
    cols = [("from", "FROM"), ("to", "TO"), ("date", "DATE"), ("dep_time", "DEP"),
            ("duration", "DURATION/CHANGES")]
    if a.ret:
        cols.append(("return", "RETURN"))
    cols += [("airlines", "AIRLINES"), ("flights", "FLIGHTS"), ("price", a.currency),
             ("max_age_h", "AGE_H")]
    print_table(rows, cols, limit=a.limit)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="origins", nargs="+", required=True,
                    help="origin IATA codes (first is primary; others are added as alternatives)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--to", nargs="+", help="destination IATA codes")
    g.add_argument("--anywhere", action="store_true", help="any destination")
    ap.add_argument("--dates", required=True,
                    help="departure window 2026-11-01..2026-11-10 (for --return: earliest "
                         "departure .. latest return)")
    ap.add_argument("--return", dest="ret", action="store_true", help="return trips")
    ap.add_argument("--min-days", type=int, default=1, help="min stay (return mode)")
    ap.add_argument("--max-days", type=int, default=8, help="max stay (return mode)")
    ap.add_argument("--max-changes", type=int, default=1, choices=[0, 1, 2, 3])
    ap.add_argument("--currency", default="EUR")
    ap.add_argument("--adults", type=int, default=1)
    ap.add_argument("--retries", type=int, default=2, help="retries when AZair says it is busy")
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--json", help="write JSON (with per-leg details) to path or '-'")
    ap.add_argument("-v", "--verbose", action="store_true", help="print the AZair URL")
    a = ap.parse_args()
    dump_json(search(a), a.json)


if __name__ == "__main__":
    main()
