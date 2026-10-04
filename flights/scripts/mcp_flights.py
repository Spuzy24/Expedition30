#!/usr/bin/env python3
"""CLI client for the free, no-login flight MCP servers of Kiwi.com and Skiplagged.

Why: both expose live search over plain JSON-RPC (streamable HTTP), so we can
query them from any container without a browser or API key. Tested 2026-10-04.
If the servers are registered in .mcp.json you can also call them as native MCP
tools; this script is the fallback and the batch/sweep engine.

  Kiwi       https://mcp.kiwi.com              tool: search-flight
             + multi-origin/destination ("ZAG,LJU,VIE,BUD" -> "TYO,OSA"), ±10 day flex,
               date ranges, nights-in-destination, bags filter, self-transfer toggle,
               airline/stopover filters, sort=price. Returns ~15 itineraries per call.
  Skiplagged https://mcp.skiplagged.com/mcp    tools: sk_flights_search, sk_flex_departure_calendar,
               sk_flex_return_calendar, sk_destinations_anywhere
             + up to 100 results, hidden-city & virtual-interlining flags, date calendars. Prices USD.

Commands
  kiwi   FROM TO DATE [--ret DATE] [--flex N] [--ret-flex N] [--date-to D] [--ret-to D]
         [--nights A-B] [--bags N] [--cabin-bag] [--no-self-transfer] [--max-stops N]
         [--exclude-airlines X,Y] [--only-airlines X,Y] [--via X,Y] [--cur EUR] [--sort price]
  sk     FROM TO DATE [--ret DATE] [--limit 30] [--hidden-city] [--no-vi] [--sort price]
  skcal  FROM TO DATE [--ret DATE]   # fixed departure; with --ret it flexes the RETURN date (USD)
  sksweep FROM DATE [--ret DATE]                   # cheapest destinations from FROM ("anywhere")
  raw    SERVER TOOL JSON                          # call any tool, print raw result
  tools  SERVER                                    # list tools + schemas

Dates: YYYY-MM-DD everywhere (converted for Kiwi). Output: table (default) or --json
(rows carry an 'eur' key, so monitor.py can use `"json": "stdout:--json"`).

Passengers (verified 2026-10-04, BUD-TYO RT, --adults 1 vs 2): BOTH servers return the PARTY TOTAL.
  Kiwi: 15/15 identical itineraries cost 2.000-2.003x; its baggage counts are also party totals
  (the table divides them by --adults). Skiplagged: QR RT $914 -> $1,828 (2.0x), but the
  cheapest FM/MU RT went $806 -> $2,516: the cheapest bucket had ONE seat. Always search with
  the real --adults.

Skiplagged (sk)
  - Hidden-city fares are OFF by default (includeHiddenCity=false). --hidden-city opts in: ToS risk,
    needs the user's explicit opt-in, one-way + cabin bag only. --no-hidden-city is accepted (no-op).
  - EUR column = USD converted with fx.to_eur (mid-market). Round trips show both directions.
  - Every RT deep link has '#trip=OUT,RET'. That is the link format, NOT proof of two one-way
    tickets (tested 2026-10-04: RT prices are not the sum of the one-way prices), so no 2xOW label;
    check the ticket count at checkout.

Kiwi (kiwi)
  - bags(pers/cabin/HOLD), per adult: HOLD = checked bags included in the price. Kiwi has NO bag
    data for China Eastern/Air China/China Southern fares, so HOLD 0 there means unknown, not
    excluded. With --bags N the prices INCLUDE Kiwi's bag add-on (~EUR 335 RT on MU).
  - tkt = separately priced parts, inferred from Kiwi's itinerary id (undocumented; one id per
    segment, segments of one ticket share the prefix before '_'): '1' = one ticket, 'N OW+OW' =
    one-way tickets per direction, 'N self-tr' = a self-transfer inside a direction. '?' = no id.

--log TRIP appends the top N (--log-top, default 3) rows to the quote log via quotes.py
(verified_live=False):
  - --adults N > 1 -> --pax N --per total (both servers price the party).
  - Kiwi: inferred self-transfer -> --self-transfer --risk moderate; >= 2 marketing carriers
    otherwise -> note "self-transfer unknown (MCP gives no PNR count)". HOLD 0 on MU/CA/CZ/FM ->
    --bags-included unknown (never "checked 0"). One-way rows get one-way ground in quotes.py.
  - Skiplagged: virtual-interline -> --self-transfer; hidden-city -> --risk tos.

Examples
  python3 mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD TYO,OSA 2027-01-20 --flex 3 --ret 2027-02-03 --ret-flex 3
  python3 mcp_flights.py kiwi BUD TYO 2027-01-15 --date-to 2027-02-15 --nights 12-16
  python3 mcp_flights.py kiwi ZAG TYO,OSA 2027-01-18 --only-airlines CA --adults 2 --log tyo-2027-01
  python3 mcp_flights.py sk ZAG TYO 2027-01-20 --ret 2027-02-03 --limit 30
  python3 mcp_flights.py skcal VIE TYO 2027-01-20 --ret 2027-02-03
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

SERVERS = {
    "kiwi": "https://mcp.kiwi.com",
    "skiplagged": "https://mcp.skiplagged.com/mcp",
    "sk": "https://mcp.skiplagged.com/mcp",
}
_id = 0


class RPCError(RuntimeError):
    """A well-formed JSON-RPC error answer (bad arguments etc.): retrying cannot help."""


def rpc(server, method, params, timeout=180, retries=2):
    """POST one JSON-RPC message; parse JSON or SSE ('data: ...') response."""
    global _id
    _id += 1
    url = SERVERS.get(server, server)
    body = json.dumps({"jsonrpc": "2.0", "id": _id, "method": method, "params": params}).encode()
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, method="POST", headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": "flights-mcp-cli/1.0",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
            if raw.lstrip().startswith("{"):
                msg = json.loads(raw)
            else:
                datas = [l[5:].strip() for l in raw.splitlines() if l.startswith("data:")]
                msg = None
                for d in datas:
                    try:
                        m = json.loads(d)
                    except json.JSONDecodeError:
                        continue
                    if m.get("id") == _id or "result" in m or "error" in m:
                        msg = m
                if msg is None:
                    raise RuntimeError(f"no JSON-RPC message in response: {raw[:300]}")
            if "error" in msg:
                raise RPCError(f"RPC error: {msg['error']}")
            return msg["result"]
        except RPCError:
            raise  # deterministic: don't burn 3 calls + 18 s of sleeps on it
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code not in (408, 425, 429):
                raise  # bad request / not found / auth: deterministic, retrying cannot help
            last = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
        except Exception as e:  # network hiccup / server busy
            last = e
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
    raise last


def call_tool(server, tool, args, timeout=180):
    res = rpc(server, "tools/call", {"name": tool, "arguments": args}, timeout=timeout)
    if res.get("isError"):
        txt = " ".join(c.get("text", "") for c in res.get("content", []))
        raise RuntimeError(f"{tool} error: {txt[:500]}")
    return res


def ddmmyyyy(d):
    return dt.date.fromisoformat(d).strftime("%d/%m/%Y")


def hours(sec):
    return f"{sec / 3600:.1f}h" if sec else ""


_FX_FAILED = False


def eur(amount, cur):
    """amount in EUR via fx.to_eur (mid-market, cached 12 h), or None if no rate is available."""
    global _FX_FAILED
    if amount is None:
        return None
    if str(cur).upper() == "EUR":
        return float(amount)
    if _FX_FAILED:
        return None
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fx import to_eur
        return round(to_eur(float(amount), str(cur)), 2)
    except Exception as e:  # no network / unknown currency: keep going without the EUR column
        _FX_FAILED = True
        print(f"[fx] no EUR conversion for {cur}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------- Kiwi
def kiwi_search(a):
    args = {"flyFrom": a.frm, "flyTo": a.to, "departureDate": ddmmyyyy(a.date),
            "currency": a.cur, "sort": a.sort, "locale": "en"}
    if a.flex:
        args["departureDateFlexDays"] = a.flex
    if a.date_to:
        args["departureDateTo"] = ddmmyyyy(a.date_to)
    if a.ret:
        args["returnDate"] = ddmmyyyy(a.ret)
        if a.ret_flex:
            args["returnDateFlexDays"] = a.ret_flex
        if a.ret_to:
            args["returnDateTo"] = ddmmyyyy(a.ret_to)
    if a.nights:
        lo, hi = (a.nights.split("-") + [a.nights])[:2]
        args["nights_in_dst_from"], args["nights_in_dst_to"] = int(lo), int(hi)
    if a.bags is not None:
        args["adults_hold_bags"] = [a.bags] * a.adults
    if a.cabin_bag:
        args["adults_hand_bags"] = [1] * a.adults
    if a.adults != 1:
        args["adults"] = a.adults
    if a.no_self_transfer:
        args["allow_self_transfer"] = False
    if a.max_stops is not None:
        args["max_sector_stopovers"] = a.max_stops
    for k_cli, k_api in (("exclude_airlines", "exclude_airlines"), ("only_airlines", "select_airlines"),
                         ("via", "stopover_airports"), ("not_via", "exclude_stopover_airports"),
                         ("not_via_countries", "exclude_stopover_countries")):
        v = getattr(a, k_cli)
        if v:
            args[k_api] = v
    if a.max_hours:
        args["max_fly_duration"] = a.max_hours
    res = call_tool("kiwi", "search-flight", args)
    obj = res.get("structuredContent") or json.loads(res["content"][0]["text"])
    if obj.get("error"):
        print(f"[kiwi] error: {obj['error']}", file=sys.stderr)
    rows = []
    for it in obj.get("itineraries", []):
        o, i = it["outbound"], it.get("inbound") or {}
        segs = o["segments"] + i.get("segments", [])
        bags = it.get("baggage") or {}
        n_ad = max(a.adults, 1)
        tk = kiwi_tickets(it)
        cur = obj.get("currency", a.cur)
        rows.append({
            "source": "kiwi", "price": it["price"], "cur": cur, "eur": eur(it["price"], cur),
            "adults": n_ad, "price_is": "party total" if n_ad > 1 else "1 adult",
            "origin": o["from"], "dest": o["to"], "out": o["departureTime"],
            "ret": i.get("departureTime", ""), "return_from": i.get("from", ""), "return_to": i.get("to", ""),
            "route_out": "-".join(o["route"]), "route_ret": "-".join(i.get("route", [])),
            "carriers": ",".join(dict.fromkeys(s["carrier"] for s in segs)),
            "stops": max(o.get("stops", 0), i.get("stops", 0) if i else 0),
            "dur_out": o.get("durationSeconds"), "dur_ret": i.get("durationSeconds"),
            "bags": it.get("baggage"),
            "bags_pp": {k: per_adult(v, n_ad) for k, v in bags.items()},  # Kiwi counts are party totals
            "tickets": tk["tickets"], "tickets_label": tk["label"], "self_transfer": tk["self_transfer"],
            "link": it.get("bookingUrl"),
            "flights": " ".join(s["flightNumber"] for s in segs),
        })
    return obj.get("query", ""), rows


def per_adult(v, n):
    if not isinstance(v, (int, float)) or n <= 1:
        return v
    return v // n if v % n == 0 else round(v / n, 1)


def kiwi_tickets(it):
    """Ticket structure inferred from Kiwi's itinerary id (undocumented, checked 2026-10-04).

    The id has one '|'-separated part per segment ('<prefix>_<n>'); segments of one separately
    priced part share the prefix: MU BUD-PVG-NRT RT = 1 prefix, MU out + CZ back = 2 (one-way
    each), W6+VF+D7+CZ = 5. Returns {'tickets': N|None, 'label': str, 'self_transfer': bool|None}."""
    o = (it.get("outbound") or {}).get("segments", [])
    i = (it.get("inbound") or {}).get("segments", [])
    parts = str(it.get("id") or "").split("|")
    if not o or len(parts) != len(o) + len(i) or not all("_" in x for x in parts):
        return {"tickets": None, "label": "?", "self_transfer": None}
    pre = [x.rsplit("_", 1)[0] for x in parts]
    po, pi = pre[:len(o)], pre[len(o):]
    n = len(dict.fromkeys(pre))
    st = len(set(po)) > 1 or len(set(pi)) > 1
    label = "1" if n == 1 else f"{n} {'self-tr' if st else 'OW+OW'}"
    return {"tickets": n, "label": label, "self_transfer": st}


# ---------------------------------------------------------------- Skiplagged
def _route(segs):
    """ZAG-STN~LHR-DEL: '~' marks an airport change between segments (self-transfer red flag)."""
    out = segs[0][0]
    for i, x in enumerate(segs):
        if i and x[0] != segs[i - 1][1]:
            out += f"~{x[0]}"
        out += f"-{x[1]}"
    return out


_SEG_RX = re.compile(r"([A-Z]{3}) → ([A-Z]{3}) \(([\d-]+ [\d:]+)")


def _md_segments(line):
    """Segments of one markdown result row, split into (outbound, return).

    The row also has 'Outbound: 17h 20m<br/>Return: 22h 25m' in the Duration cell, so split
    only the Segments cell (the one with arrows) at its 'Return:' marker."""
    cell = next((c for c in line.split("|") if "→" in c), "")
    out_part, _, ret_part = cell.partition("Return:")
    return _SEG_RX.findall(out_part), _SEG_RX.findall(ret_part)


def _sk_rows(res, a):
    """Merge structuredContent.flights (price, type attributes, link) with the
    markdown table (segment details), which come in the same order.

    Round trips are kept as two directions (route_out / route_ret, joined with ' | ');
    '~' only marks an airport change INSIDE one direction (self-transfer red flag), never
    the arrival airport vs. the return airport two weeks later."""
    sc = res.get("structuredContent") or {}
    cards = sc.get("flights") or []
    txt = "\n".join(c.get("text", "") for c in res.get("content", []))
    md_segs = [_md_segments(line) for line in txt.splitlines()
               if re.match(r"\|\s*[€£$¥]?\s*[\d,]+", line)]
    rows = []
    for idx, f in enumerate(cards):
        segs_o, segs_r = md_segs[idx] if idx < len(md_segs) else ([], [])
        rf = f.get("returnFlight") or {}
        dep_o = (f.get("departure") or {}).get("airport", "")
        arr_o = (f.get("arrival") or {}).get("airport", "")
        dep_r = (rf.get("departure") or {}).get("airport", "")
        arr_r = (rf.get("arrival") or {}).get("airport", "")
        route_out = _route(segs_o) if segs_o else f"{dep_o}-{arr_o}"
        route_ret = (_route(segs_r) if segs_r else f"{dep_r}-{arr_r}") if rf else ""
        attrs = list(dict.fromkeys((f.get("attributes") or []) + (rf.get("attributes") or [])))
        amount = (f.get("price") or {}).get("amount")
        cur = (f.get("price") or {}).get("currency", "?")
        rows.append({
            "source": "skiplagged", "price": amount, "cur": cur, "eur": eur(amount, cur),
            "adults": max(getattr(a, "adults", 1), 1),
            "duration": f.get("duration", "") + (f" / {rf.get('duration', '')}" if rf else ""),
            "stops": str(f.get("layovers", "")) + (f"/{rf.get('layovers', '')}" if rf else ""),
            "type": ",".join(x for x in attrs if x not in ("standard",)) or "standard",
            "carriers": f.get("airlines", "") + (f" | {rf.get('airlines', '')}" if rf else ""),
            "segments": [f"{x[0]}-{x[1]} {x[2]}" for x in segs_o] + [f"RET {x[0]}-{x[1]} {x[2]}" for x in segs_r],
            "route": route_out + (f" | {route_ret}" if route_ret else ""),
            "route_out": route_out, "route_ret": route_ret,
            "origin": dep_o or route_out[:3], "dest": arr_o or route_out[-3:],
            "return_from": dep_r or route_ret[:3], "return_to": arr_r or route_ret[-3:],
            "out_time": (f.get("departure") or {}).get("dateTime", ""),
            "ret_time": (rf.get("departure") or {}).get("dateTime", ""),
            "link": f.get("deepLink", ""),
        })
    return rows


HIDDEN_CITY_WARNING = ("WARNING: --hidden-city: ToS risk; user opt-in required; one-way, cabin bag only "
                       "(never check a bag or book a return on a hidden-city ticket)")


def sk_search(a):
    if a.no_hidden_city:
        print("note: --no-hidden-city is now the default (flag ignored); use --hidden-city to opt in", file=sys.stderr)
    if a.hidden_city:
        print(HIDDEN_CITY_WARNING, file=sys.stderr)
    args = {"origin": a.frm, "destination": a.to, "departureDate": a.date, "limit": a.limit,
            "sort": a.sort, "adults": a.adults,
            "includeHiddenCity": bool(a.hidden_city),
            "includeVirtualInterlining": not a.no_vi}
    if a.ret:
        args["returnDate"] = a.ret
    res = call_tool("sk", "sk_flights_search", args)
    return res, _sk_rows(res, a)


def sk_calendar(a):
    tool = "sk_flex_return_calendar" if a.ret else "sk_flex_departure_calendar"
    args = {"origin": a.frm, "destination": a.to, "departureDate": a.date, "sort": "price"}
    if a.ret:
        args["returnDate"] = a.ret
    return call_tool("sk", tool, args)


def sk_anywhere(a):
    args = {"from": a.frm, "depart": a.date}
    if a.ret:
        args["return"] = a.ret
    return call_tool("sk", "sk_destinations_anywhere", args)


# ---------------------------------------------------------------- output
HOLD_UNKNOWN = {"MU", "CA", "CZ", "FM"}  # Kiwi has no bag data for these fares


def print_kiwi(query, rows, a):
    print(f"# Kiwi: {query}  ({len(rows)} results, sorted by {a.sort})")
    print(f"{'price':>7} {'cur':<3}  {'out':<16} {'route out':<20} {'ret':<16} {'route back':<20} {'carriers':<14} "
          f"{'dur o/r':<11} {'tkt':<9} bags(pers/cabin/HOLD)")
    for r in rows:
        b = r.get("bags_pp") or {}
        print(f"{r['price']:>7.0f} {r['cur']:<3}  {r['out'][:16]:<16} {r['route_out'][:20]:<20} {r['ret'][:16]:<16} "
              f"{r['route_ret'][:20]:<20} {r['carriers'][:14]:<14} {hours(r['dur_out']):>5}/{hours(r['dur_ret']):<5} "
              f"{r.get('tickets_label', '?'):<9} "
              f"{b.get('personalItem', '?')}/{b.get('cabinBag', '?')}/{b.get('checkedBag', '?'):<13} {r['link']}")
    print("HOLD = checked bags included in the price. Kiwi has NO bag data for China Eastern/Air China/China "
          "Southern fares, so 0 there means unknown, not excluded.")
    if a.bags is not None:
        print(f"--bags {a.bags}: prices INCLUDE Kiwi's checked-bag add-on (HOLD counts it). For MU/CA/CZ that add-on "
              f"is usually unnecessary (OTAs sell the same fare with 1-2x23kg): compare with a run without --bags.")
    if a.adults > 1:
        print(f"Prices are PARTY TOTALS for {a.adults} adults (verified 2026-10-04); bag counts are per adult.")
    print("tkt = separately priced parts inferred from Kiwi's itinerary id (undocumented): 1 = one ticket, "
          "OW+OW = one ticket per direction, self-tr = unprotected self-transfer. Verify on kiwi.com.")


def print_sk(rows, a=None):
    print(f"{'price':>7} {'cur':<3} {'EUR':>6}  {'type':<18} {'stops':<8} {'duration':<17} {'route':<32} carriers / link")
    for r in rows:
        if "raw" in r:
            print(json.dumps(r["raw"])[:300])
            continue
        e = f"{r['eur']:.0f}" if r.get("eur") is not None else "?"
        print(f"{(r['price'] or 0):>7.0f} {r['cur']:<3} {e:>6}  {r['type'][:18]:<18} {r['stops'][:8]:<8} {r['duration'][:17]:<17} "
              f"{r['route'][:32]:<32} {r['carriers']}\n{'':>13}{' | '.join(r['segments'])}\n{'':>13}{r['link']}")
    if a is not None and a.adults > 1:
        print(f"Prices are PARTY TOTALS for {a.adults} adults (verified 2026-10-04).")
    print("EUR = USD converted at the mid-market rate (fx.py). No bag data: check the allowance at checkout.")


def log_rows(rows, a, source):
    """Append top results to the quote log via quotes.py (unverified)."""
    q = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes.py")
    for r in rows[: a.log_top]:
        if r.get("price") is None:
            continue
        cmd = [sys.executable, q, "add", "--trip", a.log, "--source", source,
               "--seller", "Kiwi.com" if source == "kiwi" else "Skiplagged", "--price", str(r["price"]), "--cur", r["cur"]]
        if a.adults > 1:  # both servers return the party total (verified 2026-10-04)
            cmd += ["--pax", str(a.adults), "--per", "total"]
        notes = []
        if source == "kiwi":
            b = r.get("bags_pp") or {}
            carriers = [c for c in r["carriers"].split(",") if c]
            hold = b.get("checkedBag")
            if not hold and HOLD_UNKNOWN & set(carriers):
                bags_txt = "unknown (Kiwi has no bag data for MU/CA/CZ/FM)"
            else:
                bags_txt = f"cabin {b.get('cabinBag', '?')} / checked {'?' if hold is None else hold}"
                if a.bags is not None:
                    bags_txt += " (Kiwi bag add-on in price)"
            cmd += ["--origin", r["origin"], "--dest", r["dest"], "--out", r["out"][:10],
                    "--carriers", r["carriers"], "--via", r["route_out"], "--link", r["link"] or "",
                    "--bags-included", bags_txt, "--stops", str(r["stops"])]
            if r["ret"]:
                cmd += ["--ret", r["ret"][:10], "--return-from", r["return_from"], "--return-to", r["return_to"]]
            if r.get("self_transfer"):
                cmd += ["--self-transfer", "--risk", "moderate"]
                notes.append(f"Kiwi self-transfer: {r['tickets']} separately priced parts (inferred from itinerary id)")
            else:
                if r.get("tickets") and r["tickets"] > 1:
                    notes.append(f"{r['tickets']} one-way tickets (inferred from Kiwi itinerary id)")
                if len(set(carriers)) >= 2:
                    notes.append("self-transfer unknown (MCP gives no PNR count)")
            if a.bags is not None:
                notes.append(f"searched with --bags {a.bags}: price includes Kiwi's bag add-on")
        else:
            route = r.get("route", "")
            if not route or not r.get("origin") or not r.get("dest"):
                continue
            # dest = where the OUTBOUND ends (route[-3:] of a round-trip string is the origin again)
            cmd += ["--origin", r["origin"], "--dest", r["dest"], "--out", a.date, "--carriers", r["carriers"],
                    "--via", route, "--link", r["link"], "--bags-included", "unknown"]
            notes.append(r.get("type", ""))
            if a.ret:
                cmd += ["--ret", a.ret]
                if r.get("return_from"):
                    cmd += ["--return-from", r["return_from"]]
                if r.get("return_to"):
                    cmd += ["--return-to", r["return_to"]]
            if "interline" in r.get("type", "").lower():
                cmd += ["--self-transfer", "--risk", "moderate"]
            if "hidden" in r.get("type", "").lower():
                cmd += ["--risk", "tos"]
        notes = [n for n in notes if n]
        if notes:
            cmd += ["--notes", "; ".join(notes)]
        subprocess.run(cmd, check=False)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("frm")
        s.add_argument("to")
        s.add_argument("date", help="YYYY-MM-DD")
        s.add_argument("--ret", help="YYYY-MM-DD return")
        s.add_argument("--adults", type=int, default=1, help="prices returned are the PARTY TOTAL (verified)")
        s.add_argument("--json", action="store_true")
        s.add_argument("--log", metavar="TRIP", help="append top results to quote log under this trip id")
        s.add_argument("--log-top", type=int, default=3)

    s = sp.add_parser("kiwi")
    common(s)
    s.add_argument("--flex", type=int, default=0, help="± days around date (max 10)")
    s.add_argument("--date-to", help="latest departure date (range)")
    s.add_argument("--ret-flex", type=int, default=0)
    s.add_argument("--ret-to", help="latest return date (range)")
    s.add_argument("--nights", help="nights in destination, e.g. 12-16 (with --date-to range)")
    s.add_argument("--bags", type=int, help="checked bags per adult required (0-2); prices then include Kiwi's "
                                            "bag add-on (wrong for MU/CA/CZ: no bag data)")
    s.add_argument("--cabin-bag", action="store_true", help="require a cabin bag per adult")
    s.add_argument("--no-self-transfer", action="store_true")
    s.add_argument("--max-stops", type=int)
    s.add_argument("--max-hours", type=int, help="max total flight duration")
    s.add_argument("--exclude-airlines")
    s.add_argument("--only-airlines")
    s.add_argument("--via", help="only connect via these airports")
    s.add_argument("--not-via", help="never connect via these airports")
    s.add_argument("--not-via-countries", help="never connect via these countries, e.g. RU,BY")
    s.add_argument("--cur", default="EUR")
    s.add_argument("--sort", default="price", choices=["price", "duration", "quality", "date", "popularity"])

    s = sp.add_parser("sk")
    common(s)
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--sort", default="price", choices=["price", "duration", "value"])
    hc = s.add_mutually_exclusive_group()
    hc.add_argument("--hidden-city", action="store_true",
                    help="opt in to hidden-city fares (ToS risk; user opt-in required; one-way, cabin bag only)")
    hc.add_argument("--no-hidden-city", action="store_true",
                    help="deprecated no-op: hidden-city fares are excluded by default now")
    s.add_argument("--no-vi", action="store_true", help="exclude virtual interlining")

    s = sp.add_parser("skcal")
    common(s)
    s = sp.add_parser("sksweep")
    s.add_argument("frm")
    s.add_argument("date")
    s.add_argument("--ret")
    s.add_argument("--json", action="store_true")

    s = sp.add_parser("raw")
    s.add_argument("server")
    s.add_argument("tool")
    s.add_argument("args_json")
    s = sp.add_parser("tools")
    s.add_argument("server")

    a = p.parse_args()

    if a.cmd == "kiwi":
        query, rows = kiwi_search(a)
        if a.json:
            print(json.dumps({"query": query, "results": rows}, indent=1, ensure_ascii=False))
        else:
            print_kiwi(query, rows, a)
        if a.log:
            log_rows(rows, a, "kiwi")
    elif a.cmd == "sk":
        res, rows = sk_search(a)
        if a.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False))
        else:
            head = "\n".join(c.get("text", "") for c in res.get("content", [])).split("\n| Price")[0]
            print(head.strip())
            print_sk(rows, a)
        if a.log:
            log_rows(rows, a, "skiplagged")
    elif a.cmd in ("skcal", "sksweep"):
        res = sk_calendar(a) if a.cmd == "skcal" else sk_anywhere(a)
        if a.json:
            print(json.dumps(res.get("structuredContent") or res, indent=1, ensure_ascii=False))
        else:
            print("\n".join(c.get("text", "") for c in res.get("content", [])))
    elif a.cmd == "raw":
        print(json.dumps(call_tool(a.server, a.tool, json.loads(a.args_json)), indent=1, ensure_ascii=False))
    elif a.cmd == "tools":
        res = rpc(a.server, "tools/list", {})
        for t in res["tools"]:
            print(f"== {t['name']}\n{t.get('description', '')}\n{json.dumps(t.get('inputSchema', {}), indent=1)}\n")


if __name__ == "__main__":
    main()
