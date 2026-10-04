#!/usr/bin/env python3
"""Currency conversion for comparing fares across points of sale.

Rates: ECB reference rates via frankfurter.dev (primary), falling back to
open.er-api.com, which also covers currencies the ECB doesn't publish
(RSD, AED, QAR, TWD, VND, ...). Rates are cached for 12h in ~/.cache.

Note: these are mid-market rates. What you actually pay also depends on the
card: a no-FX-fee card (Revolut/Wise) pays ~mid-market; a typical bank card
adds 1-3% plus possibly a fixed fee. Use --card-fee to model that.

Usage:
  python3 fx.py 1250 PLN                 # -> EUR
  python3 fx.py 98000 JPY --to EUR --card-fee 2
  python3 fx.py --rates                  # print cached EUR-based table
As a module:
  from fx import to_eur; to_eur(1250, "PLN")
"""
import argparse
import json
import os
import sys
import time
import urllib.request

CACHE = os.path.expanduser("~/.cache/flights_fx_eur.json")
TTL = 12 * 3600


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "flights-fx/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rates_eur():
    """Return dict currency -> units per 1 EUR."""
    try:
        with open(CACHE) as f:
            c = json.load(f)
        if time.time() - c["ts"] < TTL:
            return c["rates"]
    except Exception:
        pass
    rates = {}
    try:  # broader coverage first, then overwrite with ECB where available
        d = _get("https://open.er-api.com/v6/latest/EUR")
        rates.update(d.get("rates", {}))
    except Exception as e:
        print(f"[fx] open.er-api failed: {e}", file=sys.stderr)
    try:
        d = _get("https://api.frankfurter.dev/v1/latest?base=EUR")
        rates.update(d.get("rates", {}))
    except Exception as e:
        print(f"[fx] frankfurter failed: {e}", file=sys.stderr)
    if not rates:
        raise RuntimeError("no FX source reachable")
    rates["EUR"] = 1.0
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump({"ts": time.time(), "rates": rates}, f)
    return rates


def convert(amount, frm, to="EUR", card_fee_pct=0.0):
    r = rates_eur()
    frm, to = frm.upper(), to.upper()
    for c in (frm, to):
        if c not in r:
            raise KeyError(f"{c} (no FX rate; known: {len(r)} currencies, see fx.py --rates)")
    eur = amount / r[frm]
    out = eur * r[to]
    return out * (1 + card_fee_pct / 100.0)


def to_eur(amount, frm, card_fee_pct=0.0):
    return convert(amount, frm, "EUR", card_fee_pct)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("amount", nargs="?", type=float)
    p.add_argument("currency", nargs="?")
    p.add_argument("--to", default="EUR")
    p.add_argument("--card-fee", type=float, default=0.0, help="card FX markup in %%")
    p.add_argument("--rates", action="store_true")
    a = p.parse_args()
    if a.rates:
        for k, v in sorted(rates_eur().items()):
            print(f"{k}\t{v}")
        return
    if a.amount is None or not a.currency:
        p.error("give AMOUNT CURRENCY")
    try:
        v = convert(a.amount, a.currency, a.to, a.card_fee)
    except KeyError as e:
        p.error(f"unknown currency {e.args[0]}")
    print(f"{a.amount:,.2f} {a.currency.upper()} = {v:,.2f} {a.to.upper()}"
          + (f" (incl. {a.card_fee}% card fee)" if a.card_fee else ""))


if __name__ == "__main__":
    main()
