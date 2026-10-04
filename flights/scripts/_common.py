"""Shared helpers for the OTA / meta-search / airline scripts in this folder.

Nothing here talks to a specific travel site. It provides:
  * polite_session()  - requests.Session with a realistic desktop UA and a
                        per-host minimum delay between requests (rate limiting).
  * eur_rates()/to_eur() - ECB daily reference rates (cached for 12 h on disk)
                        so prices from different sources can be compared in EUR.
  * print_table()     - simple fixed-width table printer (no extra deps).
  * daterange()/parse_date_range() - date helpers for "2027-03-01..2027-03-10"
                        or "2027-03-05+-3" style arguments.
  * dump_json()       - writes --json output.

Environment notes (Claude Code sandbox): outbound HTTPS goes through a proxy;
requests honours HTTPS_PROXY and REQUESTS_CA_BUNDLE automatically.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import random
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
CACHE_DIR = Path(os.environ.get("FLIGHTS_CACHE_DIR", Path.home() / ".cache" / "expedition-flights"))


class PoliteSession(requests.Session):
    """requests.Session that waits `min_delay` (+ jitter) between calls to the same host."""

    def __init__(self, min_delay: float = 2.0, jitter: float = 1.0):
        super().__init__()
        self.min_delay = min_delay
        self.jitter = jitter
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()
        self.headers.update({
            "user-agent": UA,
            "accept-language": "en-GB,en;q=0.9",
            "accept": "application/json, text/plain, */*",
        })

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        host = urlparse(url).netloc
        with self._lock:
            last = self._last.get(host)
            if last is not None:
                wait = self.min_delay + random.uniform(0, self.jitter) - (time.time() - last)
                if wait > 0:
                    time.sleep(wait)
            self._last[host] = time.time()
        kwargs.setdefault("timeout", 60)
        return super().request(method, url, *args, **kwargs)


def polite_session(min_delay: float = 2.0, jitter: float = 1.0) -> PoliteSession:
    return PoliteSession(min_delay, jitter)


# --------------------------------------------------------------------------- FX
_RATES: dict[str, float] | None = None


def eur_rates() -> dict[str, float]:
    """Return {currency: units per 1 EUR} from the ECB daily feed (cached 12 h)."""
    global _RATES
    if _RATES is not None:
        return _RATES
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / "ecb_rates.json"
    if cache.exists() and time.time() - cache.stat().st_mtime < 12 * 3600:
        _RATES = json.loads(cache.read_text())
        return _RATES
    rates = {"EUR": 1.0}
    try:
        r = requests.get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
                         headers={"user-agent": UA}, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        for el in root.iter():
            if el.get("currency") and el.get("rate"):
                rates[el.get("currency")] = float(el.get("rate"))
        cache.write_text(json.dumps(rates))
    except Exception as e:  # pragma: no cover - network failure
        print(f"[warn] could not fetch ECB rates ({e}); non-EUR prices left unconverted",
              file=sys.stderr)
    _RATES = rates
    return rates


def to_eur(amount: float | None, currency: str | None) -> float | None:
    if amount is None or currency is None:
        return None
    currency = currency.upper()
    if currency == "EUR":
        return round(float(amount), 2)
    rate = eur_rates().get(currency)
    if not rate:
        return None
    return round(float(amount) / rate, 2)


# ------------------------------------------------------------------------ dates
def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def parse_date_range(s: str) -> tuple[dt.date, dt.date]:
    """'2027-03-01' | '2027-03-01..2027-03-10' | '2027-03-05+-3'  -> (start, end)."""
    s = s.strip()
    if ".." in s:
        a, b = s.split("..", 1)
        return parse_date(a), parse_date(b)
    if "+-" in s:
        a, n = s.split("+-", 1)
        d = parse_date(a)
        return d - dt.timedelta(days=int(n)), d + dt.timedelta(days=int(n))
    d = parse_date(s)
    return d, d


def daterange(a: dt.date, b: dt.date) -> Iterable[dt.date]:
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def split_codes(values: Sequence[str] | str | None) -> list[str]:
    """Accept 'ZAG,LJU' or ['ZAG','LJU'] or ['ZAG,LJU','GRZ'] -> ['ZAG','LJU','GRZ']."""
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    out: list[str] = []
    for v in values:
        out += [x.strip().upper() for x in v.split(",") if x.strip()]
    return out


# ----------------------------------------------------------------------- output
def print_table(rows: list[dict], cols: list[tuple[str, str]] | None = None,
                limit: int | None = None, file=sys.stdout) -> None:
    """cols = [(key, header), ...]. Values are str()'d and truncated to 60 chars."""
    if not rows:
        print("(no results)", file=file)
        return
    if cols is None:
        cols = [(k, k) for k in rows[0].keys()]
    rows = rows[:limit] if limit else rows
    cells = [[("" if r.get(k) is None else str(r.get(k)))[:60] for k, _ in cols] for r in rows]
    widths = [max(len(h), *(len(c[i]) for c in cells)) for i, (_, h) in enumerate(cols)]
    print("  ".join(h.ljust(w) for (_, h), w in zip(cols, widths)), file=file)
    print("  ".join("-" * w for w in widths), file=file)
    for c in cells:
        print("  ".join(v.ljust(w) for v, w in zip(c, widths)), file=file)


def dump_json(obj, path: str | None) -> None:
    """path '-' => stdout, else file path."""
    if not path:
        return
    txt = json.dumps(obj, indent=1, ensure_ascii=False, default=str)
    if path == "-":
        print(txt)
    else:
        Path(path).write_text(txt)
        print(f"[json] wrote {path}", file=sys.stderr)
