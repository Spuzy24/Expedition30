#!/usr/bin/env python3
"""
gflights.py - Google Flights search toolkit (multi-origin x multi-destination x dates).

Talks directly to Google Flights' internal JSON-RPC endpoints (the same ones the
web app uses), so no browser is needed for the normal path:

  GetShoppingResults  - itinerary list for a specific date (one-way / round-trip)
  GetCalendarGraph    - cheapest price per departure date (61-day window per call)
  GetCalendarGrid     - round-trip departure x return price matrix (<=200 cells)

Fallbacks (``--backend``):
  rpc      (default) the RPC above, plain `requests`
  html     GET https://www.google.com/travel/flights?q=... and parse the embedded
           `ds:1` JSON (fewer results, ~10-15 "top" flights, but a different code path)
  browser  same page rendered by headless Chromium via Playwright (handles the EU
           consent page); parses the same `ds:1` blob
  auto     rpc -> html -> browser

Subcommands
  search    origins x destinations x dates; one-way or round-trip; sorted table + JSON
  calendar  cheapest price per day over a date range (one-way, or round-trip with a
            fixed / ranged stay length)
  grid      round-trip date grid (departure window x return window)
  sweep     Europe-wide (or any list) origin sweep: one calendar call per origin,
            resumable JSON cache, cheapest-per-origin table, optional detail lookups

Examples
  python gflights.py search --from ZAG,LJU,GRZ,VIE,BUD --to TYO,OSA --date 2027-02-09
  python gflights.py search --from ZAG --to TYO --date 2027-03-10 --return 2027-03-24 --expand 3
  python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31
  python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 12-16
  python gflights.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21
  python gflights.py sweep --origins europe --to TYO,OSA --start 2027-02-01 --end 2027-03-31 \
        --stay 14 --cache sweep_cache.json --details 5

Prices are for 1 adult (change with --adults), economy, in --curr (default EUR),
point of sale --gl (default HR), language --hl (default en). All prices are what
Google Flights would show; always re-check on the booking site before paying.

Be polite: the default is >= 3 s (+ jitter) between requests. Google answers abuse
with HTTP 429 or a reCAPTCHA "unusual traffic" page; the client then backs off and,
after repeated failures, stops (sweep progress is saved in the cache file).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import random
import re
import sys
import time
import urllib.parse
from typing import Any, Iterable

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("pip install requests  (see flights/scripts/requirements.txt)")

RPC_BASE = ("https://www.google.com/_/FlightsFrontendUi/data/"
            "travel.frontend.flights.FlightsFrontendService/")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

# --------------------------------------------------------------------------------------
# Airport groups / presets
# --------------------------------------------------------------------------------------
CITY_CODES: dict[str, list[str]] = {
    # Japan
    "TYO": ["NRT", "HND"],
    "OSA": ["KIX", "ITM", "UKB"],
    "SPK": ["CTS"],
    "JPN": ["NRT", "HND", "KIX", "ITM", "NGO", "FUK", "CTS", "OKA"],
    "JAPAN": ["NRT", "HND", "KIX", "ITM", "NGO", "FUK", "CTS", "OKA"],
    # Europe multi-airport cities
    "LON": ["LHR", "LGW", "STN", "LTN", "LCY"],
    "PAR": ["CDG", "ORY"],
    "MIL": ["MXP", "LIN", "BGY"],
    "ROM": ["FCO", "CIA"],
    "STO": ["ARN", "BMA", "NYO"],
    "OSL": ["OSL"],
    "BER": ["BER"],
    "VEN": ["VCE", "TSF"],
    "BRU": ["BRU", "CRL"],
    "IST": ["IST", "SAW"],
    "MOW": ["SVO", "DME", "VKO"],
}

PRESETS: dict[str, list[str]] = {
    # Airports reachable from Zagreb by car/bus/train within ~1 day
    "zagreb": ["ZAG", "LJU", "GRZ", "VIE", "BUD", "VCE", "TSF", "TRS", "MUC", "BEG",
               "BTS", "PRG", "MXP", "BGY", "BLQ", "SZG", "KLU", "PUY", "RJK", "SPU"],
    # Long-haul relevant European airports (incl. Ryanair/Wizz-positioning targets)
    "europe": ["ARN", "CPH", "OSL", "HEL", "AMS", "BRU", "CDG", "FRA", "MUC", "ZRH",
               "VIE", "BUD", "PRG", "WAW", "MXP", "FCO", "MAD", "BCN", "LIS", "ATH",
               "IST", "SAW", "BEG", "OTP", "SOF", "LHR", "LGW", "MAN", "DUB", "DUS",
               "HAM", "BER", "GVA", "ZAG", "LJU", "VCE", "BLQ", "NCE", "LYS", "MRS",
               "TLS", "OPO", "AGP", "PMI", "EDI", "BHX", "GOT", "BLL", "KRK", "KTW",
               "RIX", "VNO", "TLL", "SKG", "LCA", "MLA", "BSL", "STR", "CGN", "NAP"],
}


def expand_codes(spec: str | Iterable[str]) -> list[str]:
    """'ZAG,TYO,europe' -> list of IATA airport codes (city codes / presets expanded)."""
    if isinstance(spec, str):
        items = [s.strip() for s in spec.replace(" ", ",").split(",") if s.strip()]
    else:
        items = list(spec)
    out: list[str] = []
    for it in items:
        key = it.upper()
        if it.lower() in PRESETS:
            codes = PRESETS[it.lower()]
        elif os.path.isfile(it):
            with open(it) as fh:
                codes = [c.strip().upper() for line in fh for c in line.split("#")[0].replace(",", " ").split() if c.strip()]
        elif key in CITY_CODES:
            codes = CITY_CODES[key]
        else:
            codes = [key]
        for c in codes:
            if c not in out:
                out.append(c)
    return out


def chunks(seq: list, n: int) -> list[list]:
    return [seq[i:i + n] for i in range(0, len(seq), max(1, n))]


def parse_date_spec(spec: str) -> list[str]:
    """'2027-03-10', '2027-03-10,2027-03-12', '2027-03-10..2027-03-14' -> list of dates."""
    out: list[str] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ".." in part:
            a, b = part.split("..")
            d0, d1 = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
            while d0 <= d1:
                out.append(d0.isoformat())
                d0 += dt.timedelta(days=1)
        else:
            out.append(dt.date.fromisoformat(part).isoformat())
    return out


def parse_range(spec: str | None) -> tuple[int, int] | None:
    if spec in (None, ""):
        return None
    s = str(spec)
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a), int(b)
    return int(s), int(s)


# --------------------------------------------------------------------------------------
# HTTP client with polite pacing and rate-limit detection
# --------------------------------------------------------------------------------------
class RateLimited(RuntimeError):
    pass


class Client:
    def __init__(self, hl="en", gl="HR", curr="EUR", min_interval=3.0, jitter=1.5,
                 timeout=60, max_retries=3, verbose=True):
        self.hl, self.gl, self.curr = hl, gl.upper(), curr.upper()
        self.min_interval, self.jitter = min_interval, jitter
        self.timeout, self.max_retries, self.verbose = timeout, max_retries, verbose
        self.s = requests.Session()
        self.s.headers.update({"user-agent": UA, "accept-language": f"{hl},en;q=0.8"})
        self._last = 0.0
        self.n_requests = 0

    def log(self, *a):
        if self.verbose:
            print(*a, file=sys.stderr, flush=True)

    def _pace(self):
        wait = self._last + self.min_interval + random.uniform(0, self.jitter) - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def locale_qs(self) -> str:
        return urllib.parse.urlencode({"hl": self.hl, "gl": self.gl, "curr": self.curr})

    def _request(self, method: str, url: str, **kw) -> requests.Response:
        backoff = 30
        for attempt in range(self.max_retries + 1):
            self._pace()
            self.n_requests += 1
            try:
                r = self.s.request(method, url, timeout=self.timeout, allow_redirects=True, **kw)
            except requests.RequestException as e:
                self.log(f"  ! network error {e!r}; retry in {backoff}s")
                time.sleep(backoff)
                backoff *= 2
                continue
            blocked = (r.status_code == 429 or "/sorry/" in r.url
                       or "unusual traffic" in r.text[:5000])
            if blocked:
                if attempt >= self.max_retries:
                    raise RateLimited(f"Google rate limit / captcha (HTTP {r.status_code}) on {url[:80]}")
                self.log(f"  ! rate limited (HTTP {r.status_code}); sleeping {backoff}s")
                time.sleep(backoff)
                backoff *= 2
                continue
            if r.status_code >= 500:
                self.log(f"  ! HTTP {r.status_code}; retry in 10s")
                time.sleep(10)
                continue
            return r
        raise RuntimeError(f"giving up on {url[:80]}")

    def rpc(self, method: str, freq: Any) -> Any:
        """POST f.req to a FlightsFrontendService method; return decoded inner JSON."""
        url = f"{RPC_BASE}{method}?{self.locale_qs()}"
        body = "f.req=" + urllib.parse.quote(json.dumps([None, json.dumps(freq, separators=(",", ":"))],
                                                        separators=(",", ":")))
        r = self._request("POST", url, data=body,
                          headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"})
        if r.status_code != 200:
            raise RuntimeError(f"{method}: HTTP {r.status_code}: {r.text[:200]}")
        return decode_wrb(r.content)


def decode_wrb(raw: bytes) -> Any:
    """Decode the )]}' + length-prefixed wrb.fr framing; return first inner payload."""
    raw = raw.lstrip()
    if raw.startswith(b")]}'"):
        raw = raw[4:].lstrip()
    payloads = []
    if raw[:1].isdigit():
        cur = 0
        while cur < len(raw):
            nl = raw.find(b"\n", cur)
            if nl < 0:
                break
            try:
                n = int(raw[cur:nl])
            except ValueError:
                break
            chunk = raw[nl + 1: nl + n]
            cur = nl + n
            try:
                payloads.append(json.loads(chunk.decode("utf-8")))
            except ValueError:
                continue
    else:
        payloads.append(json.loads(raw.decode("utf-8")))
    for outer in payloads:
        for row in outer if isinstance(outer, list) else []:
            if isinstance(row, list) and len(row) > 2 and row[0] == "wrb.fr" and isinstance(row[2], str):
                return json.loads(row[2])
    return None


# --------------------------------------------------------------------------------------
# Request builders (flat format; see research/05-tools-google-matrix.md)
# --------------------------------------------------------------------------------------
STOPS = {"any": 0, "0": 1, "nonstop": 1, "1": 2, "2": 3}
CABIN = {"economy": 1, "premium": 2, "business": 3, "first": 4}
SORT = {"top": 0, "best": 1, "cheapest": 2, "departure": 3, "arrival": 4, "duration": 5}


def _airports(codes: list[str]) -> list:
    # [[code, 0]] = airport; Google city ids (e.g. "/m/07dfk" Tokyo) use type 5
    return [[[c, 5 if c.startswith("/m/") else 0] for c in codes]]


def build_segment(origins, dests, date, stops=0, classifier=3, selected=None,
                  airlines=None, via=None, max_duration=None):
    return [_airports(origins), _airports(dests), None, stops, airlines or None, None, date,
            [max_duration] if max_duration else None, selected, via or None,
            None, None, None, None, classifier]


def build_main(segments, trip_type, adults=1, cabin=1, bags=None, max_price=None,
               exclude_basic=False):
    main = [None, None, trip_type, None, [], cabin, [adults, 0, 0, 0],
            [None, max_price] if max_price else None, None, None, bags, None, None,
            segments, None, None, None, 1]
    main += [None] * 10 + [1 if exclude_basic else 0]
    return main


# --------------------------------------------------------------------------------------
# Response parsing
# --------------------------------------------------------------------------------------
def _hm(v) -> str:
    v = list(v or []) + [None, None]
    return f"{(v[0] or 0):02d}:{(v[1] or 0):02d}"


def _date(v) -> str:
    try:
        return f"{v[0]:04d}-{v[1]:02d}-{v[2]:02d}"
    except Exception:
        return "?"


def _currency_from_token(tok: str | None) -> str | None:
    if not tok:
        return None
    try:
        raw = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4))
        m = re.search(rb"\x1a\x03([A-Z]{3})", raw)
        return m.group(1).decode() if m else None
    except Exception:
        return None


def parse_itinerary(row: list, default_curr: str) -> dict | None:
    try:
        d = row[0]
        price = row[1][0][1] if row[1] and row[1][0] and len(row[1][0]) > 1 else None
        curr = _currency_from_token(row[1][1] if len(row[1]) > 1 else None) or default_curr
        legs = []
        for s in d[2] or []:
            al = s[22] or [None, None, None, None]
            legs.append({
                "from": s[3], "to": s[6],
                "dep": f"{_date(s[20])} {_hm(s[8])}", "arr": f"{_date(s[21])} {_hm(s[10])}",
                "flight": f"{al[0]}{al[1]}", "carrier": al[3], "duration_min": s[11],
                "aircraft": s[17] if len(s) > 17 else None,
            })
        lays = []
        for lo in d[13] or []:
            lays.append({"minutes": lo[0], "airport": lo[1],
                         "airport_change": (lo[1] != lo[2]) if len(lo) > 2 else False})
        return {
            "price": price, "currency": curr,
            "airline": d[0], "airlines": d[1],
            "origin": d[3], "destination": d[6],
            "depart": f"{_date(d[4])} {_hm(d[5])}", "arrive": f"{_date(d[7])} {_hm(d[8])}",
            "duration_min": d[9], "stops": max(len(legs) - 1, 0),
            "layovers": [l["airport"] for l in lays], "layover_detail": lays,
            "self_transfer": bool(d[12]) if len(d) > 12 else False,
            "flights": [l["flight"] for l in legs], "legs": legs,
        }
    except (IndexError, TypeError, KeyError):
        return None


def parse_shopping(inner: Any, default_curr: str) -> tuple[list[dict], dict]:
    if not isinstance(inner, list):
        return [], {}
    rows = []
    for i in (2, 3):
        if len(inner) > i and isinstance(inner[i], list) and inner[i] and isinstance(inner[i][0], list):
            rows.extend(inner[i][0])
    its = [x for x in (parse_itinerary(r, default_curr) for r in rows) if x]
    insights = {}
    try:
        pi = inner[5]
        if isinstance(pi, list) and len(pi) > 5:
            insights = {"lowest_now": (pi[1] or [None, None])[1],
                        "typical_low": (pi[4] or [None, None])[1],
                        "typical_high": (pi[5] or [None, None])[1]}
    except (IndexError, TypeError):
        pass
    return its, insights


def parse_calendar(inner: Any) -> list[dict]:
    out = []
    items = inner[-1] if isinstance(inner, list) and inner else []
    for it in items if isinstance(items, list) else []:
        try:
            price = it[2][0][1]
        except (IndexError, TypeError):
            price = None
        if price is None:
            continue
        out.append({"depart": it[0], "return": it[1] if len(it) > 1 else None, "price": price,
                    "currency": _currency_from_token(it[2][1] if len(it[2]) > 1 else None)})
    return out


def parse_ds1_html(html: str) -> Any:
    """Extract the `ds:1` AF_initDataCallback payload (search results) from a results page."""
    i = html.find("key: 'ds:1'")
    if i < 0:
        return None
    j = html.find("data:", i)
    if j < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(html[j + 5:])
        return obj
    except ValueError:
        return None


# --------------------------------------------------------------------------------------
# High level operations
# --------------------------------------------------------------------------------------
def _pb_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b, n = n & 0x7F, n >> 7
        out.append(b | 0x80 if n else b)
        if not n:
            return bytes(out)


def _pb_ld(field: int, payload: bytes) -> bytes:
    return _pb_varint(field << 3 | 2) + _pb_varint(len(payload)) + payload


def tfs_param(origins, dests, date, ret=None, adults=1, cabin=1) -> str:
    """Encode the `tfs=` protobuf used by google.com/travel/flights/search URLs.

    Info{3: FlightData[], 8: passengers(packed), 9: seat, 19: trip}
    FlightData{2: date, 13: Airport[] (from), 14: Airport[] (to)}, Airport{2: code}
    Repeated 13/14 entries = multi-airport search (verified Oct 2026)."""
    def fd(o, d, day):
        b = _pb_ld(2, day.encode())
        for x in o:
            b += _pb_ld(13, _pb_ld(2, x.encode()))
        for x in d:
            b += _pb_ld(14, _pb_ld(2, x.encode()))
        return b
    out = _pb_ld(3, fd(origins, dests, date))
    if ret:
        out += _pb_ld(3, fd(dests, origins, ret))
    out += _pb_ld(8, bytes([1] * adults)) + _pb_varint(9 << 3) + _pb_varint(cabin)
    out += _pb_varint(19 << 3) + _pb_varint(1 if ret else 2)
    return base64.urlsafe_b64encode(out).decode().rstrip("=")


def gf_url(origins, dests, date, ret=None, c: Client | None = None, adults=1) -> str:
    """Shareable Google Flights results URL (works in a normal browser)."""
    qs = {"tfs": tfs_param(origins, dests, date, ret, adults)}
    if c:
        qs.update({"hl": c.hl, "gl": c.gl, "curr": c.curr})
    return "https://www.google.com/travel/flights/search?" + urllib.parse.urlencode(qs)


def search_rpc(c: Client, origins, dests, date, ret=None, a=None) -> tuple[list[dict], dict]:
    stops = STOPS[a.stops]
    segs = [build_segment(origins, dests, date, stops, 3, via=a.via_list)]
    trip = 2
    if ret:
        segs.append(build_segment(dests, origins, ret, stops, 1, via=a.via_list))
        trip = 1
    main = build_main(segs, trip, a.adults, CABIN[a.cabin], bags=a.bags_filter,
                      max_price=a.max_price, exclude_basic=a.exclude_basic)
    inner = c.rpc("GetShoppingResults", [[], main, SORT[a.sort], 1, 0, 1])
    return parse_shopping(inner, c.curr)


def expand_return(c: Client, it: dict, origins, dests, date, ret, a) -> dict | None:
    """Fetch return options for a chosen outbound (round trip) and return the cheapest."""
    stops = STOPS[a.stops]
    selected = []
    for leg in it["legs"]:
        m = re.match(r"([A-Z0-9]{2})(\d+)", leg["flight"] or "")
        if not m:
            return None
        selected.append([leg["from"], leg["dep"][:10], leg["to"], None, m.group(1), m.group(2)])
    segs = [build_segment(origins, dests, date, stops, 3, selected=selected, via=a.via_list),
            build_segment(dests, origins, ret, stops, 1, via=a.via_list)]
    main = build_main(segs, 1, a.adults, CABIN[a.cabin], bags=a.bags_filter,
                      max_price=a.max_price, exclude_basic=a.exclude_basic)
    inner = c.rpc("GetShoppingResults", [[], main, SORT["cheapest"], 1, 0, 1])
    rets, _ = parse_shopping(inner, c.curr)
    rets = [r for r in rets if r["price"] is not None]
    return min(rets, key=lambda r: r["price"]) if rets else None


def search_html(c: Client, origins, dests, date, ret=None, a=None) -> tuple[list[dict], dict]:
    r = c._request("GET", gf_url(origins, dests, date, ret, c, getattr(a, "adults", 1)))
    p = parse_ds1_html(r.text)
    if p is None:
        raise RuntimeError("html backend: ds:1 block not found (consent page or layout change)")
    return parse_shopping(p, c.curr)


def search_browser(c: Client, origins, dests, date, ret=None, a=None) -> tuple[list[dict], dict]:
    c._pace()
    c.n_requests += 1
    html = browser_fetch(gf_url(origins, dests, date, ret, c, getattr(a, "adults", 1)), verbose=c.verbose)
    p = parse_ds1_html(html)
    if p is None:
        raise RuntimeError("browser backend: ds:1 block not found")
    return parse_shopping(p, c.curr)


def browser_fetch(url: str, verbose=True, wait_ms=4000) -> str:
    """Render a Google page in headless Chromium (Playwright), passing the EU consent wall."""
    from playwright.sync_api import sync_playwright  # lazy import
    launch: dict[str, Any] = {"headless": True}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        launch["proxy"] = {"server": proxy}
    exe = os.environ.get("CHROMIUM_PATH")
    if exe:
        launch["executable_path"] = exe
    with sync_playwright() as p:
        b = p.chromium.launch(**launch)
        ctx = b.new_context(locale="en-GB", viewport={"width": 1400, "height": 1000})
        # Pre-seed the consent cookie (EU); harmless elsewhere.
        ctx.add_cookies([{"name": "SOCS", "value": "CAESHAgBEhJnd3NfMjAyMzA4MTAtMF9SQzIaAmVuIAEaBgiA_LyaBg",
                          "domain": ".google.com", "path": "/"}])
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        if "consent.google" in page.url:
            for label in ("Reject all", "Accept all", "Alle ablehnen", "Odbij sve", "Tout refuser"):
                btn = page.get_by_role("button", name=label)
                if btn.count():
                    btn.first.click()
                    page.wait_for_load_state("domcontentloaded")
                    break
        page.wait_for_timeout(wait_ms)
        html = page.content()
        b.close()
    if "unusual traffic" in html[:20000]:
        raise RateLimited("browser got Google captcha page")
    return html


def do_search_one(c: Client, backend: str, origins, dests, date, ret, a):
    order = {"rpc": [search_rpc], "html": [search_html], "browser": [search_browser],
             "auto": [search_rpc, search_html, search_browser]}[backend]
    last = None
    for fn in order:
        try:
            its, ins = fn(c, origins, dests, date, ret, a)
            if its or fn is order[-1]:
                return its, ins, fn.__name__.replace("search_", "")
        except RateLimited:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            c.log(f"  ! backend {fn.__name__} failed: {e!r}")
    if last:
        raise last
    return [], {}, "none"


def calendar_rpc(c: Client, origins, dests, start, end, stay=None, a=None) -> list[dict]:
    """GetCalendarGraph in <=61-day chunks. stay=(min,max) nights => round trip.

    Google only honours a single fixed stay length per call, so a range 12-16 costs
    one call per length (per 61-day chunk)."""
    if stay and stay[0] != stay[1]:
        rows = []
        for n in range(stay[0], stay[1] + 1):
            rows.extend(calendar_rpc(c, origins, dests, start, end, (n, n), a))
        return rows
    out = []
    d0, d_end = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    stops = STOPS[a.stops] if a else 0
    while d0 <= d_end:
        d1 = min(d0 + dt.timedelta(days=60), d_end)
        segs = [build_segment(origins, dests, d0.isoformat(), stops, 3, via=getattr(a, "via_list", None))]
        trip = 2
        if stay:
            segs.append(build_segment(dests, origins, (d0 + dt.timedelta(days=stay[0])).isoformat(),
                                      stops, 3, via=getattr(a, "via_list", None)))
            trip = 1
        main = build_main(segs, trip, getattr(a, "adults", 1), CABIN[getattr(a, "cabin", "economy")],
                          bags=getattr(a, "bags_filter", None), max_price=getattr(a, "max_price", None))
        freq = [None, main, [d0.isoformat(), d1.isoformat()]]
        if stay:
            freq += [None, [stay[0], stay[1]]]
        inner = c.rpc("GetCalendarGraph", freq)
        out.extend(parse_calendar(inner))
        d0 = d1 + dt.timedelta(days=1)
    # de-dupe (dep, ret) keeping min
    best: dict[tuple, dict] = {}
    for x in out:
        k = (x["depart"], x["return"])
        if k not in best or x["price"] < best[k]["price"]:
            best[k] = x
    return sorted(best.values(), key=lambda x: (x["depart"], x["return"] or ""))


def grid_rpc(c: Client, origins, dests, dep_dates: list[str], ret_dates: list[str], a=None) -> list[dict]:
    stops = STOPS[a.stops] if a else 0
    segs = [build_segment(origins, dests, dep_dates[0], stops, 3),
            build_segment(dests, origins, ret_dates[0], stops, 1)]
    main = build_main(segs, 1, getattr(a, "adults", 1), CABIN[getattr(a, "cabin", "economy")])
    out = []
    # <=200 cells per call
    step = max(1, 200 // max(1, len(ret_dates)))
    for dchunk in chunks(dep_dates, step):
        freq = [None, main, [dchunk[0], dchunk[-1]], [ret_dates[0], ret_dates[-1]]]
        out.extend(parse_calendar(c.rpc("GetCalendarGrid", freq)))
    return out


# --------------------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------------------
def fmt_dur(m):
    return f"{m // 60}h{m % 60:02d}" if isinstance(m, int) else "?"


def print_table(rows: list[dict], top: int, rt: bool):
    hdr = f"{'#':>3} {'price':>8} {'cur':3} {'from':4}>{'to':4} {'depart':16} {'dur':>6} {'st':>2} {'via':12} {'ST':2} airline / flights"
    print(hdr)
    print("-" * len(hdr))
    for i, r in enumerate(rows[:top], 1):
        via = ",".join(r["layovers"])[:12]
        st = "ST" if r.get("self_transfer") else ""
        fl = " ".join(r["flights"])
        al = ", ".join(r["airlines"] or [])[:30]
        line = (f"{i:>3} {r['price'] if r['price'] is not None else '-':>8} {r['currency']:3} "
                f"{r['origin']:4}>{r['destination']:4} {r['depart']:16} {fmt_dur(r['duration_min']):>6} "
                f"{r['stops']:>2} {via:12} {st:2} {al} | {fl}")
        if rt and r.get("return_leg"):
            rl = r["return_leg"]
            line += f"\n{'':>13}return: {rl['origin']}>{rl['destination']} {rl['depart']} via {','.join(rl['layovers'])} | {' '.join(rl['flights'])} (total {rl['price']})"
        print(line)


def dump(obj, path):
    s = json.dumps(obj, indent=1, ensure_ascii=False)
    if path in (None, "-"):
        print(s)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(s)
        print(f"[saved {path}]", file=sys.stderr)


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------
def cmd_search(a, c: Client):
    origins, dests = expand_codes(a.origins), expand_codes(a.to)
    dates = parse_date_spec(a.date)
    rets = parse_date_spec(a.ret) if a.ret else [None]
    stay = parse_range(a.stay)
    pairs: list[tuple[str, str | None]] = []
    for d in dates:
        if stay:
            for n in range(stay[0], stay[1] + 1):
                pairs.append((d, (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()))
        else:
            for r in rets:
                if r is None or r > d:
                    pairs.append((d, r))
    batches = [[o] for o in origins] if a.per_origin else chunks(origins, a.batch)
    total = len(pairs) * len(batches)
    c.log(f"search: {len(origins)} origins in {len(batches)} batch(es) x {len(pairs)} date(s) = {total} request(s)")
    results, meta = [], []
    t0 = time.time()
    k = 0
    for (d, r) in pairs:
        for ob in batches:
            k += 1
            c.log(f"[{k}/{total}] {','.join(ob)} -> {','.join(dests)} {d}{' / ' + r if r else ''}")
            try:
                its, ins, used = do_search_one(c, a.backend, ob, dests, d, r, a)
            except RateLimited as e:
                c.log(f"  !! {e}; stopping early (partial results kept)")
                meta.append({"error": str(e)})
                break
            for it in its:
                it["query_date"], it["query_return"] = d, r
                it["trip"] = "round-trip" if r else "one-way"
                it["google_flights_url"] = gf_url([it["origin"]], [it["destination"]], d, r, c)
            if a.no_self_transfer:
                its = [x for x in its if not x["self_transfer"]]
            results.extend(its)
            meta.append({"origins": ob, "date": d, "return": r, "n": len(its), "backend": used,
                         "price_insights": ins})
        else:
            continue
        break
    # dedupe
    seen, uniq = set(), []
    for x in sorted([x for x in results if x["price"] is not None], key=lambda x: x["price"]):
        key = (tuple(x["flights"]), x["query_date"], x["query_return"], x["price"])
        if key not in seen:
            seen.add(key)
            uniq.append(x)
    if a.expand and any(x["query_return"] for x in uniq):
        for x in uniq[: a.expand]:
            if not x["query_return"]:
                continue
            c.log(f"expand return for {x['origin']} {' '.join(x['flights'])} {x['price']}")
            try:
                x["return_leg"] = expand_return(c, x, [x["origin"]], dests, x["query_date"], x["query_return"], a)
            except Exception as e:  # noqa: BLE001
                c.log(f"  ! expand failed: {e!r}")
    out = {"query": {"origins": origins, "destinations": dests, "pairs": pairs, "gl": c.gl,
                     "curr": c.curr, "hl": c.hl, "adults": a.adults, "cabin": a.cabin, "stops": a.stops},
           "generated": dt.datetime.now().isoformat(timespec="seconds"),
           "elapsed_s": round(time.time() - t0, 1), "requests": c.n_requests,
           "meta": meta, "results": uniq}
    if not a.json_only:
        print_table(uniq, a.top, bool(rets[0] or stay))
        cheapest_by_origin = {}
        for x in uniq:
            cheapest_by_origin.setdefault(x["origin"], x)
        print("\ncheapest per origin: " + ", ".join(f"{o} {v['price']}" for o, v in
                                                  sorted(cheapest_by_origin.items(), key=lambda kv: kv[1]["price"])))
        print(f"({len(uniq)} itineraries, {c.n_requests} requests, {out['elapsed_s']} s)")
    if a.out or a.json_only:
        dump(out, a.out or "-")


def cmd_calendar(a, c: Client):
    origins, dests = expand_codes(a.origins), expand_codes(a.to)
    stay = parse_range(a.stay)
    groups = [[o] for o in origins] if a.per_origin else [origins]
    allrows = []
    for g in groups:
        c.log(f"calendar {','.join(g)} -> {','.join(dests)} {a.start}..{a.end} stay={stay}")
        try:
            rows = calendar_rpc(c, g, dests, a.start, a.end, stay, a)
        except RateLimited as e:
            c.log(f"  !! {e}")
            break
        for r in rows:
            r["origins"] = ",".join(g)
        allrows.extend(rows)
    allrows.sort(key=lambda x: x["price"])
    if not a.json_only:
        print(f"{'price':>7} {'cur':3} {'origin(s)':20} {'depart':10} {'return':10}")
        for r in allrows[: a.top]:
            print(f"{r['price']:>7} {r['currency'] or c.curr:3} {r['origins'][:20]:20} {r['depart']:10} {r['return'] or '':10}")
        if a.heatmap:
            print_month_grid(allrows)
    if a.out or a.json_only:
        dump({"query": vars_clean(a), "gl": c.gl, "curr": c.curr, "results": allrows}, a.out or "-")


def print_month_grid(rows):
    by = {}
    for r in rows:
        by[r["depart"]] = min(by.get(r["depart"], 1e12), r["price"])
    if not by:
        return
    days = sorted(by)
    d = dt.date.fromisoformat(days[0])
    d -= dt.timedelta(days=d.weekday())
    last = dt.date.fromisoformat(days[-1])
    print("\n      Mon    Tue    Wed    Thu    Fri    Sat    Sun")
    while d <= last:
        cells = []
        for i in range(7):
            x = d + dt.timedelta(days=i)
            v = by.get(x.isoformat())
            cells.append(f"{x.day:02d}:{int(v):<4}" if v else f"{x.day:02d}:-   ")
        print(f"{d.isoformat()[:7]} " + " ".join(cells))
        d += dt.timedelta(days=7)


def cmd_grid(a, c: Client):
    origins, dests = expand_codes(a.origins), expand_codes(a.to)
    deps, rets = parse_date_spec(a.depart), parse_date_spec(a.ret)
    rows = grid_rpc(c, origins, dests, deps, rets, a)
    cell = {(r["depart"], r["return"]): r["price"] for r in rows}
    if not a.json_only:
        print("depart \\ return " + " ".join(f"{x[5:]:>6}" for x in rets))
        for d in deps:
            print(f"{d:16}" + " ".join(f"{cell.get((d, r), '-'):>6}" for r in rets))
        if rows:
            b = min(rows, key=lambda r: r["price"])
            print(f"\ncheapest: {b['price']} {c.curr}  {b['depart']} -> {b['return']}")
    if a.out or a.json_only:
        dump({"query": vars_clean(a), "gl": c.gl, "curr": c.curr, "results": rows}, a.out or "-")


def cmd_sweep(a, c: Client):
    origins, dests = expand_codes(a.origins), expand_codes(a.to)
    stay = parse_range(a.stay)
    sig = json.dumps({"dests": dests, "start": a.start, "end": a.end, "stay": stay, "gl": c.gl,
                      "curr": c.curr, "stops": a.stops, "adults": a.adults, "cabin": a.cabin,
                      "date": a.date, "ret": a.ret}, sort_keys=True)
    cache = {"signature": sig, "origins": {}}
    if a.cache and os.path.exists(a.cache):
        with open(a.cache) as fh:
            old = json.load(fh)
        if old.get("signature") == sig:
            cache = old
            c.log(f"resuming: {len(cache['origins'])} origin(s) already cached in {a.cache}")
        else:
            c.log("cache signature differs (other query) - starting a fresh cache section")
            cache = {"signature": sig, "origins": {}, "previous": old.get("signature")}

    def save():
        if a.cache:
            tmp = a.cache + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(cache, fh, indent=1)
            os.replace(tmp, a.cache)

    t0 = time.time()
    todo = [o for o in origins if o not in cache["origins"] or cache["origins"][o].get("error")]
    c.log(f"sweep: {len(origins)} origins ({len(todo)} to do) -> {','.join(dests)}; mode={'dates' if a.date else 'calendar'}")
    for i, o in enumerate(todo, 1):
        c.log(f"[{i}/{len(todo)}] {o}")
        try:
            if a.date:  # specific-date mode (itinerary details directly)
                its, ins, _ = do_search_one(c, a.backend, [o], dests, a.date, a.ret, a)
                its = [x for x in its if x["price"] is not None and (not a.no_self_transfer or not x["self_transfer"])]
                its.sort(key=lambda x: x["price"])
                cache["origins"][o] = {"cheapest": its[0]["price"] if its else None,
                                       "best": its[0] if its else None, "top": its[:5],
                                       "date": a.date, "return": a.ret, "insights": ins}
            else:
                rows = calendar_rpc(c, [o], dests, a.start, a.end, stay, a)
                rows.sort(key=lambda x: x["price"])
                cache["origins"][o] = {"cheapest": rows[0]["price"] if rows else None,
                                       "best_dates": rows[:5], "n_dates": len(rows),
                                       "calendar": {f"{r['depart']}|{r['return'] or ''}": r["price"] for r in rows}}
        except RateLimited as e:
            c.log(f"  !! {e} - progress saved; rerun the same command later to resume")
            cache["origins"].setdefault(o, {"error": str(e)})
            save()
            break
        except Exception as e:  # noqa: BLE001
            c.log(f"  ! {o}: {e!r}")
            cache["origins"][o] = {"error": repr(e)}
        save()
    # optional detail lookups for the best origins (calendar mode)
    ranked = sorted([(o, v) for o, v in cache["origins"].items() if v.get("cheapest") is not None and o in origins],
                    key=lambda kv: kv[1]["cheapest"])
    if a.details and not a.date:
        for o, v in ranked[: a.details]:
            if v.get("detail"):
                continue
            bd = v["best_dates"][0]
            c.log(f"detail: {o} {bd['depart']} {bd['return'] or ''}")
            try:
                its, _, _ = do_search_one(c, a.backend, [o], dests, bd["depart"], bd["return"], a)
                its = sorted([x for x in its if x["price"] is not None], key=lambda x: x["price"])
                v["detail"] = its[:3]
            except RateLimited as e:
                c.log(f"  !! {e}")
                break
            save()
    elapsed = round(time.time() - t0, 1)
    print(f"{'#':>3} {'origin':6} {'price':>7} {'cur':3} {'best date(s)':24} detail")
    for i, (o, v) in enumerate(ranked[: a.top], 1):
        if v.get("best_dates"):
            bd = v["best_dates"][0]
            when = f"{bd['depart']}{'>' + bd['return'] if bd['return'] else ''}"
        else:
            when = f"{v.get('date')}{'>' + v['return'] if v.get('return') else ''}"
        det = v.get("detail", [None])[0] if v.get("detail") else v.get("best")
        dtxt = ""
        if det:
            dtxt = f"{det['price']} {','.join(det['airlines'] or [])} via {','.join(det['layovers'])} {' '.join(det['flights'])}{' SELF-TRANSFER' if det['self_transfer'] else ''}"
        print(f"{i:>3} {o:6} {v['cheapest']:>7} {c.curr:3} {when:24} {dtxt}")
    missing = [o for o in origins if o not in cache["origins"] or cache["origins"][o].get("cheapest") is None]
    if missing:
        print(f"no price / not done: {', '.join(missing)}")
    print(f"({c.n_requests} requests this run, {elapsed} s)")
    if a.out:
        dump({"signature": json.loads(sig), "ranked": [{"origin": o, **v} for o, v in ranked]}, a.out)


def vars_clean(a):
    return {k: v for k, v in vars(a).items() if k not in ("func",) and not callable(v)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gl", default="HR", help="point-of-sale country (default HR)")
    ap.add_argument("--curr", default="EUR", help="currency (default EUR)")
    ap.add_argument("--hl", default="en", help="UI language (default en)")
    ap.add_argument("--sleep", type=float, default=3.0, help="min seconds between requests (default 3)")
    ap.add_argument("--quiet", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, dates=True):
        p.add_argument("--from", dest="origins", required=(p.prog.split()[-1] != "sweep"),
                       help="origins: IATA list, city codes (TYO), presets (zagreb, europe) or a file")
        p.add_argument("--to", required=True, help="destinations, e.g. TYO,OSA or JPN")
        p.add_argument("--adults", type=int, default=1)
        p.add_argument("--cabin", default="economy", choices=list(CABIN))
        p.add_argument("--stops", default="any", choices=list(STOPS))
        p.add_argument("--via", default=None, help="restrict connection airports, e.g. IST,DOH")
        p.add_argument("--max-price", type=int, default=None)
        p.add_argument("--bags", type=int, default=None, help="checked bags to include in price (0-2)")
        p.add_argument("--carry-on", action="store_true", help="include carry-on fee in price")
        p.add_argument("--exclude-basic", action="store_true", help="exclude basic economy")
        p.add_argument("--backend", default="rpc", choices=["rpc", "html", "browser", "auto"])
        p.add_argument("--sort", default="cheapest", choices=list(SORT))
        p.add_argument("--top", type=int, default=30)
        p.add_argument("--out", help="write JSON here")
        p.add_argument("--json-only", action="store_true", help="print JSON to stdout, no table")
        p.add_argument("--no-self-transfer", action="store_true", help="drop self-transfer itineraries")

    p = sub.add_parser("search", help="specific dates")
    common(p)
    p.add_argument("--date", required=True, help="YYYY-MM-DD, list a,b or range a..b")
    p.add_argument("--return", dest="ret", help="return date(s) (round trip)")
    p.add_argument("--stay", help="instead of --return: nights, e.g. 14 or 12-16")
    p.add_argument("--batch", type=int, default=7, help="origins per request (multi-airport query)")
    p.add_argument("--per-origin", action="store_true", help="one request per origin")
    p.add_argument("--expand", type=int, default=0, help="round trip: fetch return flights for top N")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("calendar", help="cheapest price per date")
    common(p)
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--stay", help="round trip nights, e.g. 14 or 10-14 (omit for one-way)")
    p.add_argument("--per-origin", action="store_true")
    p.add_argument("--heatmap", action="store_true", help="print a week x day grid")
    p.set_defaults(func=cmd_calendar)

    p = sub.add_parser("grid", help="round-trip departure x return grid")
    common(p)
    p.add_argument("--depart", required=True, help="e.g. 2027-03-01..2027-03-07")
    p.add_argument("--return", dest="ret", required=True, help="e.g. 2027-03-15..2027-03-21")
    p.set_defaults(func=cmd_grid)

    p = sub.add_parser("sweep", help="many origins, one calendar call each; resumable")
    common(p)
    p.add_argument("--origins", dest="origins_alias", default=None,
                   help="alias of --from (preset 'europe', 'zagreb', list or file)")
    p.add_argument("--start", help="calendar window start (calendar mode)")
    p.add_argument("--end", help="calendar window end")
    p.add_argument("--stay", help="round trip nights for calendar mode, e.g. 14 or 12-16")
    p.add_argument("--date", help="specific-date mode instead of calendar")
    p.add_argument("--return", dest="ret", help="return date for specific-date mode")
    p.add_argument("--cache", default="gflights_sweep_cache.json")
    p.add_argument("--details", type=int, default=0, help="look up itineraries for best N origins")
    p.set_defaults(func=cmd_sweep)

    a = ap.parse_args(argv)
    if a.cmd == "sweep":
        a.origins = a.origins_alias or a.origins
        if not a.origins:
            ap.error("sweep needs --origins (or --from)")
        if not a.date and not (a.start and a.end):
            ap.error("sweep needs --start/--end (calendar mode) or --date")
    a.via_list = expand_codes(a.via) if getattr(a, "via", None) else None
    a.bags_filter = ([a.bags or 0, int(a.carry_on)] if (a.bags or a.carry_on) else None)
    c = Client(hl=a.hl, gl=a.gl, curr=a.curr, min_interval=a.sleep, verbose=not a.quiet)
    a.func(a, c)


if __name__ == "__main__":
    main()
