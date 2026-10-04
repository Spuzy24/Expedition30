#!/usr/bin/env python3
"""
matrix.py - ITA Matrix (matrix.itasoftware.com, "Matrix v5") search from the command line.

The Matrix web app is an Angular front-end over a JSON API:

    POST https://content-alkalimatrix-pa.googleapis.com/v1/search?key=<public web key>&alt=json
    headers: x-alkali-application-key: applications/matrix
             x-alkali-auth-apps-namespace: alkali_v2
             x-alkali-auth-entities-namespace: alkali_v2
             content-type: application/json, origin/referer: https://matrix.itasoftware.com

The browser also sends a BotGuard token ("bgProgramResponse"); as of 2026-10-04 the API
answers without it. If that ever changes, --backend browser (EXPERIMENTAL) drives the real web
app in headless Chromium (Playwright): it submits a dummy form search and swaps the request
body for ours while keeping the app's BotGuard token. Deep links (/flights?search=<base64>) do
not start a search in headless mode. The swap answered once (a small query) but two later
heavier queries never got a response within 3-5 min - treat it as a last resort.

Subcommands
  search    specific dates: one-way, round-trip (--return) or multi-city (--slice ...),
            optional +/- day flexibility, routing codes (--route / --route-ret) and extension
            codes (--ext / --ext-ret), sales city (--sales-city) and currency (--curr)
  calendar  "calendar of lowest fares": cheapest price per departure day over a window
            (~1 month per call; longer windows are split). Round trip with --stay N or N-M nights.

Routing / extension code cheat-sheet (Matrix syntax, per slice):
  --route "CA+"           one or more Air China flights    --route "X:PEK"   connect in PEK
  --route "C:CA"          exactly one CA flight (nonstop)  --route "C:CA X:PEK C:CA"  CA-PEK-CA
  --route "O:EK"          one flight operated by EK (C:/O: each denote ONE segment)
  --ext "MAXSTOPS 1"      max 1 stop                        --ext "MINCONNECT 120" / "MAXCONNECT 240" (minutes)
  --ext "-CODESHARE" / "-REDEYES" / "-AIRLINES TK" / "F BC=K"  (see report for which were verified)
  Invalid codes return a QPX error message, e.g. 'SLICE-PROHIBITED-CABINS ...'.

Examples
  python matrix.py search --from VIE --to TYO --date 2027-03-10 --curr EUR
  python matrix.py search --from ARN --to TYO --date 2027-02-09 --return 2027-02-23 --route "CA+" --route-ret "CA+" --sales-city STO --no-avail
  python matrix.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 14
  python matrix.py search --slice ZAG:NRT:2027-03-10 --slice KIX:ZAG:2027-03-24
  python matrix.py search --from VIE --to TYO --date 2027-03-10 --carriers QR,EK,TK,CA,LO,AY,KE   # beat pruning

Notes
  * A Matrix query takes 20-60 s server-side. Be patient; default pacing is 5 s between calls.
  * Matrix only shows published fares it can price ("ITA" content). Many carriers that Google
    Flights shows (low-cost, NDC-only, some Gulf/Asian carriers) are missing - treat Matrix
    as a fare-construction / routing tool, not as a "cheapest overall" oracle.
  * --no-avail (checkAvailability=false) shows fares even when ITA can't confirm seats - useful
    to discover cheap published fares (e.g. Air China ex-ARN), but they may not be bookable.
  * Matrix cannot book. Use the itinerary (flights + fare basis) to book with the airline/OTA.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import random
import sys
import time
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("pip install requests  (see flights/scripts/requirements.txt)")

API_KEY = os.environ.get("MATRIX_API_KEY", "AIzaSyBH1mte6BdKzvf0c2mYprkyvfHCRWmfX7g")  # public web key
API = "https://content-alkalimatrix-pa.googleapis.com/v1/search"
HEADERS = {
    "content-type": "application/json",
    "x-alkali-application-key": "applications/matrix",
    "x-alkali-auth-apps-namespace": "alkali_v2",
    "x-alkali-auth-entities-namespace": "alkali_v2",
    "origin": "https://matrix.itasoftware.com",
    "referer": "https://matrix.itasoftware.com/",
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"),
}
CABINS = {"economy": "COACH", "premium": "PREMIUM-COACH", "business": "BUSINESS", "first": "FIRST"}
SEARCH_SUMMARIZERS = ["carrierStopMatrix", "currencyNotice", "solutionList", "itineraryPriceSlider",
                      "itineraryCarrierList", "itineraryDepartureTimeRanges", "itineraryArrivalTimeRanges",
                      "durationSliderItinerary", "itineraryOrigins", "itineraryDestinations",
                      "itineraryStopCountList", "warningsItinerary"]
CAL_SUMMARIZERS = ["calendar", "overnightFlightsCalendar", "itineraryStopCountList",
                   "itineraryCarrierList", "currencyNotice"]


class MatrixError(RuntimeError):
    pass


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def codes(s: str) -> list[str]:
    return [x.strip().upper() for x in s.replace(" ", ",").split(",") if x.strip()]


def price_num(p: str | None) -> float | None:
    """'EUR1033.09' -> 1033.09"""
    if not p:
        return None
    i = 0
    while i < len(p) and p[i].isalpha():
        i += 1
    try:
        return float(p[i:])
    except ValueError:
        return None


# --------------------------------------------------------------------------------------
# Request building
# --------------------------------------------------------------------------------------
def slice_obj(origins, dests, date=None, route=None, ext=None, minus=0, plus=0):
    s: dict[str, Any] = {"origins": origins, "destinations": dests,
                         "filter": {"warnings": {"values": []}}, "selected": False}
    if date:
        s.update({"date": date, "dateModifier": {"minus": minus, "plus": plus}, "isArrivalDate": False})
    if route:
        s["routeLanguage"] = route
    if ext:
        s["commandLine"] = ext
    return s


def base_inputs(a, slices):
    inp: dict[str, Any] = {
        "filter": {}, "pax": {"adults": a.adults}, "slices": slices,
        "firstDayOfWeek": "SUNDAY", "internalUser": False, "sliceIndex": 0, "sorts": "default",
        "cabin": CABINS[a.cabin], "changeOfAirport": not a.no_airport_change,
        "checkAvailability": not a.no_avail,
    }
    if a.extra_stops is not None and a.extra_stops >= 0:
        inp["maxLegsRelativeToMin"] = a.extra_stops
    if a.max_stops is not None and a.max_stops >= 0:
        inp["maxStopCount"] = a.max_stops
    if a.curr:
        inp["currency"] = a.curr.upper()
    if a.sales_city:
        inp["salesCity"] = a.sales_city.upper()
    return inp


def post(body: dict, timeout=240, retries=2) -> dict:
    for attempt in range(retries + 1):
        try:
            r = requests.post(f"{API}?key={API_KEY}&alt=json", headers=HEADERS,
                              data=json.dumps(body), timeout=timeout)
        except requests.RequestException as e:
            if attempt >= retries:
                raise MatrixError(f"network error: {e!r}")
            log(f"  ! network error {e!r}; retrying in 20 s")
            time.sleep(20)
            continue
        if r.status_code in (429, 503):
            if attempt >= retries:
                raise MatrixError(f"HTTP {r.status_code} (rate limited)")
            log(f"  ! HTTP {r.status_code}; backing off 60 s")
            time.sleep(60)
            continue
        try:
            d = r.json()
        except ValueError:
            raise MatrixError(f"HTTP {r.status_code}: non-JSON response {r.text[:200]!r}")
        if r.status_code != 200 or "error" in d:
            raise MatrixError(f"HTTP {r.status_code}: {json.dumps(d.get('error', d))[:400]}")
        return d
    raise MatrixError("unreachable")


# --------------------------------------------------------------------------------------
# Matrix web URLs (reproduce the search in a browser)
# --------------------------------------------------------------------------------------
def web_state(a, kind: str, slices_spec: list[dict], start=None) -> dict:
    st: dict[str, Any] = {"type": kind, "slices": [], "options": {
        "cabin": CABINS[a.cabin], "stops": str(a.max_stops if a.max_stops is not None else -1),
        "extraStops": str(a.extra_stops if a.extra_stops is not None else -1),
        "allowAirportChanges": str(not a.no_airport_change).lower(),
        "showOnlyAvailable": str(not a.no_avail).lower()}, "pax": {"adults": str(a.adults)}}
    if a.curr:
        st["options"]["currency"] = {"displayName": a.curr.upper(), "code": a.curr.upper()}
    if a.sales_city:
        st["options"]["salesCity"] = {"code": a.sales_city.upper(), "name": a.sales_city.upper()}
    for s in slices_spec:
        x: dict[str, Any] = {"origin": s["origins"], "dest": s["destinations"]}
        if s.get("routeLanguage"):
            x["routing"] = s["routeLanguage"]
        if s.get("commandLine"):
            x["ext"] = s["commandLine"]
        st["slices"].append(x)
    return st


def web_url(state: dict, page="flights") -> str:
    return f"https://matrix.itasoftware.com/{page}?search=" + base64.b64encode(
        json.dumps(state, separators=(",", ":")).encode()).decode()


# --------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------
def parse_solutions(d: dict) -> list[dict]:
    out = []
    for s in d.get("solutionList", {}).get("solutions", []):
        it = s.get("itinerary", {})
        slices = []
        for x in it.get("slices", []):
            slices.append({
                "from": x["origin"]["code"], "to": x["destination"]["code"],
                "departure": x.get("departure"), "arrival": x.get("arrival"),
                "flights": x.get("flights", []), "stops": [st["code"] for st in x.get("stops", [])],
                "duration_min": x.get("duration"), "cabins": x.get("cabins"),
            })
        out.append({
            "price": price_num(s.get("displayTotal")), "display_total": s.get("displayTotal"),
            "carriers": [c["code"] for c in it.get("carriers", [])],
            "dominant_carrier": (it.get("ext", {}).get("dominantCarrier") or {}).get("code"),
            "slices": slices, "id": s.get("id"),
            "price_per_mile": s.get("ext", {}).get("pricePerMile"),
        })
    out.sort(key=lambda x: (x["price"] is None, x["price"]))
    return out


def parse_calendar(d: dict) -> list[dict]:
    rows = []
    for m in d.get("calendar", {}).get("months", []):
        for w in m.get("weeks", []):
            for day in w.get("days", []):
                if day.get("disabled") or not day.get("minPrice"):
                    continue
                date = f"{m['year']:04d}-{m['month']:02d}-{day['date']:02d}"
                opts = (day.get("tripDuration") or {}).get("options") or []
                if opts:
                    for o in opts:
                        tl = o.get("tripLength")
                        rows.append({"depart": date, "nights": tl if isinstance(tl, int) and tl >= 0 else None,
                                     "price": price_num(o.get("minPrice")), "display": o.get("minPrice"),
                                     "solutions": o.get("solutionCount")})
                else:
                    rows.append({"depart": date, "nights": None, "price": price_num(day["minPrice"]),
                                 "display": day["minPrice"], "solutions": day.get("solutionCount")})
    return rows


# --------------------------------------------------------------------------------------
# Browser backend (Playwright) - drives the real web app, captures the API JSON
# --------------------------------------------------------------------------------------
def browser_search(body: dict, timeout_s=300) -> dict:
    """Run `body` through the real Matrix web app (headless Chromium).

    Deep links (/flights?search=...) do not trigger a search in headless mode, so we
    drive a trivial one-way search through the form and, in a request interceptor,
    swap the app's /v1/search JSON for ours while keeping the app's BotGuard token
    (bgProgramResponse). The captured JSON response is returned."""
    from playwright.sync_api import sync_playwright
    launch: dict[str, Any] = {"headless": True}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        launch["proxy"] = {"server": proxy}
    if os.environ.get("CHROMIUM_PATH"):
        launch["executable_path"] = os.environ["CHROMIUM_PATH"]
    found: dict[str, Any] = {}

    def rewrite(route):
        req = route.request
        pd = req.post_data or ""
        if os.environ.get("MATRIX_DEBUG"):
            log(f"  [debug] batch request: {pd[pd.find('Content-ID'):][:160]!r} ... has /v1/search: {'/v1/search' in pd}")
        if "/v1/search" not in pd:
            return route.continue_()
        i, j = pd.find("{"), pd.rfind("}")
        try:
            orig = json.loads(pd[i:j + 1])
        except ValueError:
            return route.continue_()
        mine = dict(body)
        if orig.get("bgProgramResponse"):
            mine["bgProgramResponse"] = orig["bgProgramResponse"]
        found["swapped"] = True
        route.continue_(post_data=pd[:i] + json.dumps(mine) + pd[j + 1:])

    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        page = b.new_page(viewport={"width": 1400, "height": 1100})
        page.route("**/content-alkalimatrix-pa.googleapis.com/batch**", rewrite)

        def on_resp(r):
            if "alkalimatrix" in r.url and "batch" in r.url and found.get("swapped") and "d" not in found:
                try:
                    t = r.text()
                except Exception:  # noqa: BLE001
                    return
                if os.environ.get("MATRIX_DEBUG"):
                    log(f"  [debug] batch response {r.status}: {t[:300]!r}")
                if '"solutionList"' in t or '"calendar"' in t or '"error"' in t:
                    i, j = t.find("{"), t.rfind("}")
                    try:
                        found["d"] = json.loads(t[i:j + 1])
                    except ValueError:
                        pass
        page.on("response", on_resp)
        page.goto("https://matrix.itasoftware.com/search", wait_until="load", timeout=90000)
        page.wait_for_timeout(2500)
        page.get_by_text("One Way", exact=True).click()
        page.wait_for_timeout(600)
        inputs = page.locator("input")
        for idx, code in ((0, "VIE"), (1, "NRT")):
            el = inputs.nth(idx)
            el.click()
            el.type(code, delay=120)
            page.wait_for_timeout(2500)
            opts = page.locator("mat-option, [role=option]")
            if opts.count():
                opts.first.click()
            page.wait_for_timeout(400)
        dummy = (dt.date.today() + dt.timedelta(days=60)).strftime("%m/%d/%Y")
        d = inputs.nth(2)
        d.click()
        d.type(dummy, delay=40)
        page.keyboard.press("Escape")
        page.keyboard.press("Tab")
        page.wait_for_timeout(800)
        btn = page.get_by_role("button", name="Search").last
        for _ in range(20):
            if btn.is_enabled():
                break
            page.wait_for_timeout(500)
        if not btn.is_enabled():
            page.screenshot(path="matrix_browser_debug.png")
            b.close()
            raise MatrixError("browser backend: search form not valid (see matrix_browser_debug.png)")
        btn.click()
        t0 = time.time()
        while "d" not in found and time.time() - t0 < timeout_s:
            page.wait_for_timeout(1000)
        if "d" not in found and os.environ.get("MATRIX_DEBUG"):
            page.screenshot(path="matrix_browser_debug.png")
            log(f"  [debug] swapped={found.get('swapped')} url={page.url[:120]}")
        b.close()
    if "d" not in found:
        raise MatrixError("browser backend: no search response captured")
    if "error" in found["d"]:
        raise MatrixError(json.dumps(found["d"]["error"]))
    return found["d"]


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------
def run(a, body: dict, url: str) -> dict:
    if a.backend in ("http", "auto"):
        try:
            return post(body)
        except MatrixError as e:
            if a.backend == "http" or "QPX" in str(e) or '"input"' in str(e):
                raise
            log(f"  ! http backend failed ({e}); trying browser")
    return browser_search(body)


def cmd_search(a):
    if getattr(a, "carriers", None):
        return cmd_search_carriers(a)
    return _cmd_search(a)


def cmd_search_carriers(a):
    """Matrix prunes its default answer to a handful of solutions; forcing one carrier at a time
    ("QR+" on every slice) surfaces fares that a plain query hides (verified: QR, EK on VIE-TYO)."""
    allsol, per = [], []
    base_route, base_route_ret = a.route, a.route_ret
    for i, cx in enumerate(codes(a.carriers)):
        if i:
            time.sleep(a.sleep + random.uniform(0, 2))
        a.route = f"{cx}+" if not base_route else base_route
        a.route_ret = f"{cx}+" if not base_route_ret else base_route_ret
        log(f"[{i + 1}] carrier {cx}")
        try:
            out = _cmd_search(a, quiet=True)
        except MatrixError as e:
            log(f"  ! {cx}: {e}")
            per.append({"carrier": cx, "error": str(e)})
            continue
        best = out["solutions"][0] if out["solutions"] else None
        per.append({"carrier": cx, "min": best["price"] if best else None, "n": out["solution_count"],
                    "matrix_url": out["matrix_url"]})
        for sol in out["solutions"]:
            sol["forced_carrier"] = cx
        allsol.extend(out["solutions"])
    a.route, a.route_ret = base_route, base_route_ret
    allsol.sort(key=lambda x: (x["price"] is None, x["price"]))
    if not a.json_only:
        print("per carrier: " + ", ".join(f"{p['carrier']} {p.get('min') or p.get('error', '-')}" for p in per))
        for i, sol in enumerate(allsol[: a.top], 1):
            segs = " || ".join(f"{x['from']}-{'-'.join(x['stops'])+'-' if x['stops'] else ''}{x['to']} "
                               f"{(x['departure'] or '')[:16]} {' '.join(x['flights'])}" for x in sol["slices"])
            print(f"{i:>3} {sol['display_total']:>13}  {','.join(sol['carriers']):10} {segs}")
    if a.out or a.json_only:
        dump({"query": {k: v for k, v in vars(a).items() if k != "func"}, "per_carrier": per,
              "solutions": allsol}, a.out or "-")


def _cmd_search(a, quiet=False):
    slices = []
    if a.slice:
        for sp in a.slice:
            o, d, date = sp.split(":")[:3]
            slices.append(slice_obj(codes(o.replace("/", ",")), codes(d.replace("/", ",")), date,
                                    minus=a.minus, plus=a.plus))
        kind = "multi-city"
        if a.route:
            slices[0]["routeLanguage"] = a.route
        if a.ext:
            slices[0]["commandLine"] = a.ext
    else:
        if not (a.origins and a.to and a.date):
            sys.exit("need --from/--to/--date or --slice O:D:DATE ...")
        o, d = codes(a.origins), codes(a.to)
        slices.append(slice_obj(o, d, a.date, a.route, a.ext, a.minus, a.plus))
        kind = "one-way"
        if a.ret:
            slices.append(slice_obj(d, o, a.ret, a.route_ret, a.ext_ret, a.minus, a.plus))
            kind = "round-trip"
    inputs = base_inputs(a, slices)
    inputs["page"] = {"current": 1, "size": a.page_size}
    body = {"summarizers": SEARCH_SUMMARIZERS, "inputs": inputs, "summarizerSet": "wholeTrip",
            "name": "specificDatesSlice"}
    st = web_state(a, kind, slices)
    for x, s in zip(st["slices"], slices):
        x["dates"] = {"searchDateType": "specific", "departureDate": s["date"], "departureDateType": "depart",
                      "departureDateModifier": str(s["dateModifier"]["plus"]), "departureDatePreferredTimes": [],
                      "returnDateType": "depart", "returnDateModifier": "0", "returnDatePreferredTimes": []}
    url = web_url(st, "flights")
    log(f"matrix search ({kind}) ... (typically 20-60 s)")
    t0 = time.time()
    d = run(a, body, url)
    sols = parse_solutions(d)
    carriers = [(g["label"]["code"], g.get("minPrice")) for g in d.get("itineraryCarrierList", {}).get("groups", [])]
    out = {"query": {k: v for k, v in vars(a).items() if k != "func"}, "matrix_url": url,
           "elapsed_s": round(time.time() - t0, 1), "solution_count": d.get("solutionCount"),
           "min_price": d.get("solutionList", {}).get("minPrice"), "carrier_min_prices": carriers,
           "currency_notice": d.get("currencyNotice"), "solutions": sols}
    if quiet:
        return out
    if not a.json_only:
        print(f"solutions: {d.get('solutionCount')}  min: {out['min_price']}  ({out['elapsed_s']} s)")
        print("carriers: " + ", ".join(f"{c} {p}" for c, p in carriers))
        for i, s in enumerate(sols[: a.top], 1):
            segs = " || ".join(f"{x['from']}-{'-'.join(x['stops'])+'-' if x['stops'] else ''}{x['to']} "
                               f"{(x['departure'] or '')[:16]} {' '.join(x['flights'])}" for x in s["slices"])
            print(f"{i:>3} {s['display_total']:>13}  {','.join(s['carriers']):10} {segs}")
        print(f"\nopen in browser: {url}")
    if a.out or a.json_only:
        dump(out, a.out or "-")


def cmd_calendar(a):
    o, d = codes(a.origins), codes(a.to)
    stay = None
    if a.stay:
        s = a.stay.split("-")
        stay = (int(s[0]), int(s[-1]))
    start = dt.date.fromisoformat(a.start)
    end = dt.date.fromisoformat(a.end) if a.end else start + dt.timedelta(days=30)
    rows: list[dict] = []
    meta = []
    t0 = time.time()
    cur = start
    first = True
    while cur <= end:
        chunk_end = min(cur + dt.timedelta(days=a.chunk_days - 1), end)
        slices = [slice_obj(o, d, None, a.route, a.ext)]
        if stay:
            slices.append(slice_obj(d, o, None, a.route_ret, a.ext_ret))
        inputs = base_inputs(a, slices)
        inputs.update({"startDate": cur.isoformat(), "endDate": chunk_end.isoformat(), "page": {"size": 25}})
        if stay:
            inputs["layover"] = {"min": stay[0], "max": stay[1]}
        body = {"summarizers": CAL_SUMMARIZERS, "inputs": inputs,
                "summarizerSet": "calendarRoundTrip" if stay else "calendarOneWay", "name": "calendar"}
        st = web_state(a, "round-trip" if stay else "one-way", slices)
        for x in st["slices"][:1]:
            x["dates"] = {"searchDateType": "calendar", "departureDate": cur.isoformat(),
                          "departureDateType": "depart", "departureDateModifier": "0",
                          "departureDatePreferredTimes": [], "returnDateType": "depart",
                          "returnDateModifier": "0", "returnDatePreferredTimes": []}
            if stay:
                x["dates"]["duration"] = a.stay
        url = web_url(st, "calendar")
        if not first:
            time.sleep(a.sleep + random.uniform(0, 2))
        first = False
        log(f"matrix calendar {cur} .. {chunk_end} stay={stay} ... (typically 30-60 s)")
        try:
            dd = run(a, body, url)
        except MatrixError as e:
            log(f"  ! {e}")
            meta.append({"start": cur.isoformat(), "end": chunk_end.isoformat(), "error": str(e)})
            cur = chunk_end + dt.timedelta(days=1)
            continue
        part = parse_calendar(dd)
        rows.extend(part)
        meta.append({"start": cur.isoformat(), "end": chunk_end.isoformat(), "n": len(part), "url": url,
                     "carriers": [(g["label"]["code"], g.get("minPrice"))
                                  for g in dd.get("itineraryCarrierList", {}).get("groups", [])]})
        cur = chunk_end + dt.timedelta(days=1)
    rows = [r for r in rows if r["price"] is not None]
    rows.sort(key=lambda r: (r["price"], r["depart"]))
    out = {"query": {k: v for k, v in vars(a).items() if k != "func"}, "elapsed_s": round(time.time() - t0, 1),
           "chunks": meta, "results": rows}
    if not a.json_only:
        for m in meta:
            print(f"chunk {m['start']}..{m['end']}: {m.get('n', 'ERR')} day(s) priced; carriers {m.get('carriers', m.get('error'))}")
        print(f"{'price':>9}  {'depart':10} nights")
        for r in rows[: a.top]:
            print(f"{r['display']:>9}  {r['depart']:10} {r['nights'] if r['nights'] is not None else '-'}")
        print(f"({out['elapsed_s']} s)")
    if a.out or a.json_only:
        dump(out, a.out or "-")


def dump(obj, path):
    s = json.dumps(obj, indent=1, ensure_ascii=False)
    if path in (None, "-"):
        print(s)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(s)
        log(f"[saved {path}]")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--from", dest="origins", help="origin airport/city codes, comma separated")
        p.add_argument("--to", help="destination codes, e.g. TYO or NRT,HND")
        p.add_argument("--route", help="routing code, outbound (e.g. 'C:CA', 'X:PEK', 'N')")
        p.add_argument("--ext", help="extension code, outbound (e.g. '-CODESHARE', 'MAXSTOPS 1')")
        p.add_argument("--route-ret", help="routing code, return slice")
        p.add_argument("--ext-ret", help="extension code, return slice")
        p.add_argument("--sales-city", help="point of sale city, e.g. ZAG, STO, LON (default: departure city)")
        p.add_argument("--curr", default="EUR", help="currency (default EUR; '' = sales-city currency)")
        p.add_argument("--adults", type=int, default=1)
        p.add_argument("--cabin", default="economy", choices=list(CABINS))
        p.add_argument("--max-stops", type=int, default=None)
        p.add_argument("--extra-stops", type=int, default=1, help="extra stops vs. minimum (default 1, -1=any)")
        p.add_argument("--no-avail", action="store_true", help="checkAvailability=false (show unconfirmed fares)")
        p.add_argument("--no-airport-change", action="store_true")
        p.add_argument("--backend", default="http", choices=["http", "browser", "auto"])
        p.add_argument("--top", type=int, default=25)
        p.add_argument("--out", help="write JSON here")
        p.add_argument("--json-only", action="store_true")
        p.add_argument("--sleep", type=float, default=5.0, help="seconds between calls (calendar chunks)")

    p = sub.add_parser("search", help="specific dates")
    common(p)
    p.add_argument("--date", help="outbound date YYYY-MM-DD")
    p.add_argument("--return", dest="ret", help="return date (round trip)")
    p.add_argument("--slice", action="append", help="multi-city slice ORIG:DEST:DATE (repeat); '/' separates multiple airports")
    p.add_argument("--minus", type=int, default=0, help="date flexibility: days before")
    p.add_argument("--plus", type=int, default=0, help="date flexibility: days after")
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--carriers", help="run one query per carrier with routing 'XX+' and merge, e.g. QR,EK,TK,CA,LO,AY")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("calendar", help="calendar of lowest fares")
    common(p)
    p.add_argument("--start", required=True)
    p.add_argument("--end", help="default start+30 days")
    p.add_argument("--stay", help="round trip nights, e.g. 14 or 10-16 (omit for one-way)")
    p.add_argument("--chunk-days", type=int, default=31, help="days per API call (default 31)")
    p.set_defaults(func=cmd_calendar)

    # allow `--ext -CODESHARE` (values starting with '-') by rewriting to `--ext=-CODESHARE`
    argv = list(sys.argv[1:] if argv is None else argv)
    fixed, i = [], 0
    while i < len(argv):
        if argv[i] in ("--ext", "--ext-ret", "--route", "--route-ret") and i + 1 < len(argv):
            fixed.append(f"{argv[i]}={argv[i + 1]}")
            i += 2
            continue
        fixed.append(argv[i])
        i += 1
    a = ap.parse_args(fixed)
    if a.curr == "":
        a.curr = None
    if a.cmd == "calendar" and not (a.origins and a.to):
        ap.error("calendar needs --from and --to")
    a.func(a)


if __name__ == "__main__":
    main()
