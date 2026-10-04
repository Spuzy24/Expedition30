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
             + up to 100 results, hidden-city & virtual-interlining flags, date calendars.

Commands
  kiwi   FROM TO DATE [--ret DATE] [--flex N] [--ret-flex N] [--date-to D] [--ret-to D]
         [--nights A-B] [--bags N] [--cabin-bag] [--no-self-transfer] [--max-stops N]
         [--exclude-airlines X,Y] [--only-airlines X,Y] [--via X,Y] [--cur EUR] [--sort price]
  sk     FROM TO DATE [--ret DATE] [--limit 50] [--no-hidden-city] [--no-vi] [--sort price]
  skcal  FROM TO DATE [--ret DATE]                 # flexible-date calendar (price per date)
  sksweep FROM DATE [--ret DATE]                   # cheapest destinations from FROM ("anywhere")
  raw    SERVER TOOL JSON                          # call any tool, print raw result
  tools  SERVER                                    # list tools + schemas

Dates: YYYY-MM-DD everywhere (converted for Kiwi). Output: table (default) or --json.
Add --log TRIP to append the top N (--log-top, default 3) results to the quote log
(flights/searches/quotes.jsonl) with verified_live=False.

Examples
  python3 mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD TYO,OSA 2027-01-20 --flex 3 --ret 2027-02-03 --ret-flex 3
  python3 mcp_flights.py kiwi BUD TYO 2027-01-15 --date-to 2027-02-15 --nights 12-16 --bags 1
  python3 mcp_flights.py sk ZAG TYO 2027-01-20 --ret 2027-02-03 --limit 30 --no-hidden-city
  python3 mcp_flights.py skcal VIE TYO 2027-01-20 --ret 2027-02-03
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
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
        rows.append({
            "source": "kiwi", "price": it["price"], "cur": obj.get("currency", a.cur),
            "origin": o["from"], "dest": o["to"], "out": o["departureTime"],
            "ret": i.get("departureTime", ""), "return_from": i.get("from", ""), "return_to": i.get("to", ""),
            "route_out": "-".join(o["route"]), "route_ret": "-".join(i.get("route", [])),
            "carriers": ",".join(dict.fromkeys(s["carrier"] for s in segs)),
            "stops": max(o.get("stops", 0), i.get("stops", 0) if i else 0),
            "dur_out": o.get("durationSeconds"), "dur_ret": i.get("durationSeconds"),
            "bags": it.get("baggage"), "link": it.get("bookingUrl"),
            "flights": " ".join(s["flightNumber"] for s in segs),
        })
    return obj.get("query", ""), rows


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
        rows.append({
            "source": "skiplagged", "price": (f.get("price") or {}).get("amount"),
            "cur": (f.get("price") or {}).get("currency", "?"),
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


def sk_search(a):
    args = {"origin": a.frm, "destination": a.to, "departureDate": a.date, "limit": a.limit,
            "sort": a.sort, "adults": a.adults,
            "includeHiddenCity": not a.no_hidden_city,
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
def print_kiwi(query, rows, a):
    print(f"# Kiwi: {query}  ({len(rows)} results, sorted by {a.sort})")
    print(f"{'price':>7} {'cur':<3}  {'out':<16} {'route out':<20} {'ret':<16} {'route back':<20} {'carriers':<14} {'dur o/r':<11} bags(p/c/h)")
    for r in rows:
        b = r["bags"] or {}
        print(f"{r['price']:>7.0f} {r['cur']:<3}  {r['out'][:16]:<16} {r['route_out'][:20]:<20} {r['ret'][:16]:<16} "
              f"{r['route_ret'][:20]:<20} {r['carriers'][:14]:<14} {hours(r['dur_out']):>5}/{hours(r['dur_ret']):<5} "
              f"{b.get('personalItem', '?')}/{b.get('cabinBag', '?')}/{b.get('checkedBag', '?')}  {r['link']}")


def print_sk(rows):
    print(f"{'price':>7} {'cur':<3}  {'type':<18} {'stops':<8} {'duration':<17} {'route':<32} carriers / link")
    for r in rows:
        if "raw" in r:
            print(json.dumps(r["raw"])[:300])
            continue
        print(f"{(r['price'] or 0):>7.0f} {r['cur']:<3}  {r['type'][:18]:<18} {r['stops'][:8]:<8} {r['duration'][:17]:<17} "
              f"{r['route'][:32]:<32} {r['carriers']}\n{'':>13}{' | '.join(r['segments'])}\n{'':>13}{r['link']}")


def log_rows(rows, a, source):
    """Append top results to the quote log via quotes.py (unverified)."""
    import os
    q = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes.py")
    for r in rows[: a.log_top]:
        if r.get("price") is None:
            continue
        cmd = [sys.executable, q, "add", "--trip", a.log, "--source", source,
               "--seller", "Kiwi.com" if source == "kiwi" else "", "--price", str(r["price"]), "--cur", r["cur"]]
        if source == "kiwi":
            b = r["bags"] or {}
            cmd += ["--origin", r["origin"], "--dest", r["dest"], "--out", r["out"][:10],
                    "--carriers", r["carriers"], "--via", r["route_out"], "--link", r["link"] or "",
                    "--bags-included", f"cabin {b.get('cabinBag', '?')} / checked {b.get('checkedBag', '?')}",
                    "--stops", str(r["stops"])]
            if r["ret"]:
                cmd += ["--ret", r["ret"][:10], "--return-from", r["return_from"], "--return-to", r["return_to"]]
        else:
            route = r.get("route", "")
            if not route or not r.get("origin") or not r.get("dest"):
                continue
            # dest = where the OUTBOUND ends (route[-3:] of a round-trip string is the origin again)
            cmd += ["--origin", r["origin"], "--dest", r["dest"], "--out", a.date, "--carriers", r["carriers"],
                    "--via", route, "--link", r["link"], "--notes", r.get("type", "")]
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
        subprocess.run(cmd, check=False)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("frm")
        s.add_argument("to")
        s.add_argument("date", help="YYYY-MM-DD")
        s.add_argument("--ret", help="YYYY-MM-DD return")
        s.add_argument("--adults", type=int, default=1)
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
    s.add_argument("--bags", type=int, help="checked bags per adult required (0-2)")
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
    s.add_argument("--no-hidden-city", action="store_true")
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
            print_sk(rows)
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
