#!/usr/bin/env python3
"""Kiwi.com web GraphQL ("umbrella") client - the API the kiwi.com website itself calls.

Complements the Kiwi MCP server (mcp.kiwi.com `search-flight`, see mcp_flights.py). Use THIS
script for things the MCP tool does not expose:
  * many origins/destinations in one query: IATA codes, cities, whole countries
    (Country:JP), continents (Continent:europe), regions, or "all airports within N km"
  * per-city cheapest fares ("one per city"): e.g. ZAG -> anywhere in Europe (positioning),
    or Continent:europe -> Country:JP  => cheapest European origin for every Japanese city
  * origin scan: query each European hub separately to rank the cheapest origin for Japan
  * price calendar (cheapest per day) for one-way or return
  * flags for self-transfer/virtual interlining, hidden-city, throwaway; checked bags priced in

Endpoint: POST https://api.skypicker.com/umbrella/v2/graphql?featureName=<Op>
No key, no cookies (tested 2026-10-04). Introspection is enabled. Results are LIVE Kiwi
prices (Kiwi's own fares incl. its self-transfer "virtual interlining" combos).

Location syntax for --from/--to (comma separated, mix freely):
  ZAG / VIE        -> airport or metro city (resolved via Kiwi places, e.g. TYO -> City:tokyo_jp)
  Country:JP       -> raw Kiwi id (also City:zagreb_hr, Station:airport:NRT, Continent:europe,
                      Region:central-europe)
  ZAG@400          -> all airports within 400 km of ZAG (expanded via the places API)

Examples
--------
  python3 kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates 2027-03-01..2027-03-15
  python3 kiwi_graphql.py search --from ZAG,VIE,BUD --to TYO,OSA --dates 2027-03-08..2027-03-12 \
          --return-dates 2027-03-22..2027-03-26 --checked-bags 1
  python3 kiwi_graphql.py search --from VIE --to TYO --dates 2027-03-01..2027-03-10 --nights 14-18
  python3 kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates 2027-03-01..2027-03-15
  python3 kiwi_graphql.py per-city --from ZAG,LJU,GRZ --to Continent:europe --dates 2027-03-08..2027-03-12
  python3 kiwi_graphql.py origin-scan --to Country:JP --dates 2027-03-01..2027-03-15 \
          --origins ZAG,VIE,BUD,MUC,FRA,IST,WAW,HEL,MXP,FCO,BRU,AMS,CDG,LHR,MAD,BCN,ARN,CPH,PRG
  python3 kiwi_graphql.py calendar --from ZAG --to TYO --dates 2027-02-01..2027-03-31
  python3 kiwi_graphql.py places --near ZAG --radius 400

Notes: a single multi-origin query returns at most ~25-50 itineraries sorted by price,
so one origin can dominate; use origin-scan to compare origins fairly. Very long origin
lists (e.g. 6 whole countries) can return 0 results - split them. Keep >= 2 s between calls.
"""
from __future__ import annotations

import argparse
import sys
import time

import requests

from _common import dump_json, parse_date_range, polite_session, print_table, split_codes

URL = "https://api.skypicker.com/umbrella/v2/graphql"
S = polite_session(min_delay=2.0, jitter=1.0)
S.headers.update({"content-type": "application/json", "origin": "https://www.kiwi.com",
                  "referer": "https://www.kiwi.com/"})

_SEG = """
fragment Seg on SectorSegment { layover { duration isBaggageRecheck }
  segment { duration code
    source { localTime station { code city { name } country { code } } }
    destination { localTime station { code city { name } country { code } } }
    carrier { code name } } }
fragment Itin on Itinerary { __typename id price { amount } priceEur { amount } duration pnrCount
  provider { code }
  bagsInfo { includedCheckedBags includedHandBags hasNoCheckedBaggage
    checkedBagTiers { tierPrice { amount } bags { weight { value } } } }
  travelHack { isTrueHiddenCity isVirtualInterlining isThrowawayTicket }
  bookingOptions { edges { node { bookingUrl } } } }
"""
Q_RET = """query SearchReturnItinerariesQuery($search: SearchReturnInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {
 returnItineraries(search: $search, filter: $filter, options: $options) { __typename
  ... on AppError { error: message }
  ... on Itineraries { metadata { itinerariesCount hasMorePending missingProviders { code }
     statusPerProvider { provider { code } pending errorHappened errorMessage } }
   itineraries { ...Itin ... on ItineraryReturn { outbound { sectorSegments { ...Seg } } inbound { sectorSegments { ...Seg } } } } } } }""" + _SEG
Q_OW = """query SearchOneWayItinerariesQuery($search: SearchOnewayInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {
 onewayItineraries(search: $search, filter: $filter, options: $options) { __typename
  ... on AppError { error: message }
  ... on Itineraries { metadata { itinerariesCount hasMorePending missingProviders { code }
     statusPerProvider { provider { code } pending errorHappened errorMessage } }
   itineraries { ...Itin ... on ItineraryOneWay { sector { sectorSegments { ...Seg } } } } } } }""" + _SEG
_OPC = """ { __typename ... on AppError { error: message }
  ... on OnePerCityItineraries { itineraries { price { amount } priceEur { amount } departureDate
     source { station { code city { name } } }
     destination { station { code city { name } country { code } } } } } } }"""
Q_OPC_OW = ("query OnewayOnePerCity($search: SearchOnewayInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {"
            " onewayOnePerCityItineraries(search: $search, filter: $filter, options: $options)" + _OPC)
Q_OPC_RET = ("query ReturnOnePerCity($search: SearchReturnInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {"
             " returnOnePerCityItineraries(search: $search, filter: $filter, options: $options)" + _OPC)
Q_CAL = """query PriceCalendar($search: SearchPricesCalendarInput, $filter: ItinerariesFilterInput, $options: ItinerariesOptionsInput) {
 itineraryPricesCalendar(search: $search, filter: $filter, options: $options) { __typename ... on AppError { error: message }
  ... on ItineraryPricesCalendar { calendar { date ratedPrice { price { amount } rating } } } } }"""
Q_PLACES = """query Places($search: PlacesSearchInput, $filter: PlacesFilterInput, $options: PlacesOptionsInput, $first: Int) {
 places(search: $search, filter: $filter, options: $options, first: $first) { __typename ... on AppError { error: message }
  ... on PlaceConnection { edges { node { __typename id name ... on Station { code } ... on City { code } } } } } }"""


def gql(op: str, query: str, variables: dict, retries: int = 1) -> dict:
    for attempt in range(retries + 1):
        try:
            r = S.post(f"{URL}?featureName={op}", json={"query": query, "variables": variables}, timeout=120)
            if r.status_code == 429 or r.status_code >= 500:
                raise RuntimeError(f"{op}: HTTP {r.status_code}")
            d = r.json()  # ValueError on an HTML error/challenge page
            break
        except (requests.RequestException, ValueError, RuntimeError) as e:
            if attempt >= retries:
                raise RuntimeError(f"{op}: {e!r}") from e
            print(f"[kiwi] {op}: {e!r}; retrying in 10 s", file=sys.stderr)
            time.sleep(10)
    if d.get("errors"):
        raise RuntimeError(f"{op}: {d['errors'][0].get('message')}")
    return d["data"]


# ------------------------------------------------------------------ places
_CACHE: dict[str, str] = {}


def resolve(token: str) -> list[str]:
    """'ZAG' | 'TYO' | 'Country:JP' | 'ZAG@400' -> list of Kiwi ids."""
    token = token.strip()
    if ":" in token:
        return [token]
    if "@" in token:
        code, km = token.split("@", 1)
        return [f"Station:airport:{c}" for c, _ in radius_airports(_city_id(code), int(km))]
    code = token.upper()
    if code in _CACHE:
        return [_CACHE[code]]
    d = gql("UmbrellaPlacesQuery", Q_PLACES, {"search": {"term": code}, "options": {"locale": "en"}, "first": 8})
    edges = [e["node"] for e in d["places"].get("edges", []) if e["node"].get("code") == code]
    # Metro codes (TYO, OSA, LON, MIL) rank the City first -> use it (covers all its airports);
    # plain airports (ZAG, VIE) rank the Station first -> use the airport.
    pick = edges[0]["id"] if edges else f"Station:airport:{code}"
    _CACHE[code] = pick
    return [pick]


def _city_id(code: str) -> str:
    """Radius search needs a City (or GPS) anchor; a Station id returns nothing."""
    if ":" in code:
        return code
    d = gql("UmbrellaPlacesQuery", Q_PLACES, {"search": {"term": code.upper()},
                                              "options": {"locale": "en"}, "first": 8})
    nodes = [e["node"] for e in d["places"].get("edges", []) if e["node"].get("code") == code.upper()]
    city = next((n["id"] for n in nodes if n["__typename"] == "City"), None)
    return city or (nodes[0]["id"] if nodes else f"Station:airport:{code.upper()}")


def radius_airports(place_id: str, km: int) -> list[tuple[str, str]]:
    d = gql("UmbrellaPlacesQuery", Q_PLACES, {"search": {"idSlugRadius": {"id": place_id, "radius": km}},
                                              "filter": {"onlyTypes": ["AIRPORT"]},
                                              "options": {"locale": "en"}, "first": 100})
    return [(e["node"]["code"], e["node"]["name"]) for e in d["places"].get("edges", [])]


def ids(tokens) -> list[str]:
    """['ZAG,VIE', 'Country:JP', 'ZAG@400'] -> unique Kiwi ids (raw ids keep their casing)."""
    out: list[str] = []
    for t in ([tokens] if isinstance(tokens, str) else tokens):
        for p in t.split(","):
            p = p.strip()
            if not p:
                continue
            if "@" in p:
                code, km = p.split("@", 1)
                p = f"{code.upper()}@{km}"
            elif ":" not in p:
                p = p.upper()
            out += resolve(p)
    return list(dict.fromkeys(out))


# ---------------------------------------------------------------- variables
def _pax(adults: int, checked: int, hand: int) -> dict:
    return {"adults": adults, "children": 0, "infants": 0,
            "adultsHoldBags": [checked] * adults, "adultsHandBags": [hand] * adults,
            "childrenHoldBags": [], "childrenHandBags": []}


def _filter(a, limit=50) -> dict:
    f = {"allowChangeInboundDestination": True, "allowChangeInboundSource": True,
         "allowDifferentStationConnection": True, "enableSelfTransfer": not a.no_self_transfer,
         "enableThrowAwayTicketing": a.hacks, "enableTrueHiddenCity": a.hacks,
         "transportTypes": ["FLIGHT"], "contentProviders": ["KIWI", "FRESH"],
         "flightsApiLimit": limit, "limit": limit}
    if a.max_stops is not None:
        f["maxStopsCount"] = a.max_stops
    return f


def _options(a) -> dict:
    return {"sortBy": "PRICE", "mergePriceDiffRule": "INCREASED", "currency": a.currency.lower(),
            "locale": "en", "market": a.market, "partner": "skypicker", "partnerMarket": a.market,
            "affilID": "skypicker", "storeSearch": False, "searchStrategy": "REDUCED"}


def _range(d1, d2):
    return {"start": f"{d1}T00:00:00", "end": f"{d2}T23:59:59"}


def _itin(a, src, dst):
    d1, d2 = parse_date_range(a.dates)
    it = {"source": {"ids": src}, "destination": {"ids": dst}, "outboundDepartureDate": _range(d1, d2)}
    ret = False
    if getattr(a, "return_dates", None):
        r1, r2 = parse_date_range(a.return_dates)
        it["inboundDepartureDate"] = _range(r1, r2)
        ret = True
    if getattr(a, "nights", None):
        lo, hi = (a.nights.split("-") + [a.nights])[:2]
        it["nightsCount"] = {"start": int(lo), "end": int(hi)}
        ret = True
    return it, ret


def _sector_txt(sec) -> tuple[str, str, str]:
    segs = sec["sectorSegments"]
    path = "-".join([segs[0]["segment"]["source"]["station"]["code"]] +
                    [s["segment"]["destination"]["station"]["code"] for s in segs])
    dep = segs[0]["segment"]["source"]["localTime"][:16].replace("T", " ")
    arr = segs[-1]["segment"]["destination"]["localTime"][5:16].replace("T", " ")
    al = ",".join(dict.fromkeys(s["segment"]["carrier"]["code"] for s in segs))
    return path, f"{dep}->{arr}", al


def _bag_fee(it, checked: int) -> float:
    """Price of the checked bags Kiwi ADDED to this itinerary's price (query currency).

    With adultsHoldBags > 0 the returned price = fare + the cheapest checkedBagTier, and
    includedCheckedBags then counts the priced-in bags too. A tier price of 0 means the
    fare itself includes the bag (per Kiwi). Kiwi's bag data is missing for some full-service
    carriers (MU: '0 bags' + EUR 334.89 RT for 1x23 kg, while GDS data says 2x23 kg)."""
    if not checked:
        return 0.0
    tiers = (it.get("bagsInfo") or {}).get("checkedBagTiers") or []
    fees = [float(t["tierPrice"]["amount"]) for t in tiers
            if t.get("tierPrice") and len(t.get("bags") or []) >= 1]
    return min(fees) if fees else 0.0


def _row(it, ret: bool, checked: int = 0) -> dict:
    secs = [it["outbound"], it["inbound"]] if ret else [it["sector"]]
    parts = [_sector_txt(s) for s in secs]
    th = it["travelHack"]
    flags = [n for n, v in (("self-transfer", th["isVirtualInterlining"]),
                            ("hidden-city", th["isTrueHiddenCity"]),
                            ("throwaway", th["isThrowawayTicket"])) if v]
    if (it.get("pnrCount") or 1) > 1 and not th["isVirtualInterlining"]:
        flags.append(f"{it['pnrCount']}-tickets")
    url = (it.get("bookingOptions") or {}).get("edges") or []
    price, eur = float(it["price"]["amount"]), round(float(it["priceEur"]["amount"]), 2)
    fee = _bag_fee(it, checked)
    fee_eur = round(fee * eur / price, 2) if price else fee
    first, last = secs[0]["sectorSegments"][0]["segment"], secs[-1]["sectorSegments"][-1]["segment"]
    return {"price": price, "eur": eur,
            "fare_eur": round(eur - fee_eur, 2), "kiwi_bag_eur": fee_eur,
            "route": " | ".join(p[0] for p in parts), "times": " | ".join(p[1] for p in parts),
            "airlines": " | ".join(p[2] for p in parts), "tickets": it.get("pnrCount"),
            "checked_bags": it["bagsInfo"]["includedCheckedBags"], "flags": ",".join(flags),
            "dep_local": first["source"]["localTime"][:16], "arr_local": last["destination"]["localTime"][:16],
            "book": ("https://www.kiwi.com" + url[0]["node"]["bookingUrl"]) if url else None}


def _carriers(row) -> set:
    return {c for part in row["airlines"].split("|") for c in part.strip().split(",") if c}


def _rank_eur(row, fsc: set) -> float:
    """Ranking price: the Kiwi price, except that with --fsc-bags-included the Kiwi bag add-on is
    dropped for itineraries flown only by those carriers (their fares include checked bags)."""
    if fsc and row.get("kiwi_bag_eur") and _carriers(row) <= fsc:
        return row["fare_eur"]
    return row["eur"]


def _check_meta(res, a) -> None:
    md = res.get("metadata") or {}
    if md.get("hasMorePending"):
        print("[kiwi] WARNING: hasMorePending=true - Kiwi had not finished searching; results may be "
              "partial (re-run in a few seconds)", file=sys.stderr)
    bad = [s for s in md.get("statusPerProvider") or [] if s.get("errorHappened") or s.get("pending")]
    for s in bad:
        print(f"[kiwi] WARNING: provider {s['provider']['code']} pending={s.get('pending')} "
              f"error={s.get('errorMessage')}", file=sys.stderr)


def _search_raw(a, src, dst, it, ret) -> list[dict]:
    v = {"search": {"itinerary": it, "passengers": _pax(a.adults, a.checked_bags, a.hand_bags),
                    "cabinClass": {"cabinClass": "ECONOMY", "applyMixedClasses": False}},
         "filter": _filter(a, a.limit_api), "options": _options(a)}
    if ret:
        v["filter"]["allowReturnFromDifferentCity"] = True
    op, q, key = (("SearchReturnItinerariesQuery", Q_RET, "returnItineraries") if ret else
                  ("SearchOneWayItinerariesQuery", Q_OW, "onewayItineraries"))
    res = gql(op, q, v)[key]
    if res["__typename"] != "Itineraries":
        print(f"[kiwi] {res.get('error') or res}", file=sys.stderr)
        return []
    _check_meta(res, a)
    return [_row(x, ret, a.checked_bags) for x in res["itineraries"]]


def _oneway_combos(a, src, dst, top=12) -> list[dict]:
    """Round trip as two separate one-way tickets (out + back). Kiwi's RETURN search does not
    build these for full-service carriers (e.g. CA VIE-PEK-KIX + CZ HND-CAN-BUD = EUR 870 with
    a bag on 2026-10-04, while the return search's best was EUR 927); the Kiwi MCP does."""
    d1, d2 = parse_date_range(a.dates)
    r1, r2 = parse_date_range(a.return_dates)
    out = _search_raw(a, src, dst, {"source": {"ids": src}, "destination": {"ids": dst},
                                    "outboundDepartureDate": _range(d1, d2)}, False)
    back = _search_raw(a, dst, src, {"source": {"ids": dst}, "destination": {"ids": src},
                                     "outboundDepartureDate": _range(r1, r2)}, False)
    combos = []
    for o in out[:top]:
        for b in back[:top]:
            if b["dep_local"] <= o["arr_local"]:
                continue
            flags = ",".join(x for x in ("2-tickets(OW+OW)", o["flags"], b["flags"]) if x)
            combos.append({"price": round(o["price"] + b["price"], 2), "eur": round(o["eur"] + b["eur"], 2),
                           "fare_eur": round(o["fare_eur"] + b["fare_eur"], 2),
                           "kiwi_bag_eur": round(o["kiwi_bag_eur"] + b["kiwi_bag_eur"], 2),
                           "route": f"{o['route']} | {b['route']}", "times": f"{o['times']} | {b['times']}",
                           "airlines": f"{o['airlines']} | {b['airlines']}",
                           "tickets": (o["tickets"] or 1) + (b["tickets"] or 1),
                           "checked_bags": min(o["checked_bags"], b["checked_bags"]), "flags": flags,
                           "dep_local": o["dep_local"], "arr_local": b["arr_local"],
                           "book": f"{o['book']} + {b['book']}"})
    return combos


# ----------------------------------------------------------------- commands
def run_search(a, src=None, quiet=False) -> list[dict]:
    src = src or ids(a.origins)
    dst = ids(a.dests)
    it, ret = _itin(a, src, dst)
    if a.limit_api > 50 and not quiet:
        print("[kiwi] note: the API returns at most 50 itineraries per query (--limit-api > 50 is ignored)",
              file=sys.stderr)
    rows = _search_raw(a, src, dst, it, ret)
    if ret and getattr(a, "combine_oneways", False) and getattr(a, "return_dates", None):
        seen = {(r["route"], r["times"]) for r in rows}
        rows += [c for c in _oneway_combos(a, src, dst) if (c["route"], c["times"]) not in seen]
    fsc = set(split_codes(getattr(a, "fsc_bags_included", None) or ""))
    for r in rows:
        r["rank_eur"] = _rank_eur(r, fsc)
    rows.sort(key=lambda r: (r["rank_eur"], r["eur"]))
    if not quiet:
        print(f"[kiwi] {len(rows)} itineraries; sources={src[:6]}{'...' if len(src) > 6 else ''} "
              f"dest={dst}", file=sys.stderr)
        cols = [("eur", "EUR"), ("price", f"PRICE({a.currency.upper()})")]
        if a.checked_bags:
            cols += [("fare_eur", "FARE€"), ("kiwi_bag_eur", "KIWI-BAG€")]
        if fsc:
            cols += [("rank_eur", "RANK€")]
        print_table(rows, cols + [("route", "ROUTE"), ("times", "TIMES"), ("airlines", "AIRLINES"),
                                  ("tickets", "PNRs"), ("checked_bags", "BAGS"), ("flags", "FLAGS")],
                    limit=a.limit, maxw=90)
        heavy = sorted({c for r in rows[: a.limit or len(rows)] if r.get("kiwi_bag_eur", 0) >= 150
                        for c in _carriers(r)} - fsc)
        if heavy:
            print(f"[kiwi] WARNING: Kiwi added >= EUR 150 of bag fees on itineraries with {','.join(heavy)}. "
                  "Kiwi's bag data is unreliable for full-service carriers (MU said 0 bags; OTAs/GDS say 2x23 kg). "
                  "Compare FARE€ with OTAs' bag-inclusive prices, or pass --fsc-bags-included MU,CA,CZ,...",
                  file=sys.stderr)
    return rows


def cmd_per_city(a) -> list[dict]:
    it, ret = _itin(a, ids(a.origins), ids(a.dests))
    v = {"search": {"itinerary": it, "passengers": _pax(a.adults, a.checked_bags, a.hand_bags),
                    "cabinClass": {"cabinClass": "ECONOMY", "applyMixedClasses": False}},
         "filter": _filter(a, a.limit_api), "options": _options(a)}
    op, q, key = (("ReturnOnePerCity", Q_OPC_RET, "returnOnePerCityItineraries") if ret else
                  ("OnewayOnePerCity", Q_OPC_OW, "onewayOnePerCityItineraries"))
    res = gql(op, q, v)[key]
    rows = [{"eur": round(float(x["priceEur"]["amount"]), 2), "price": float(x["price"]["amount"]),
             "from": x["source"]["station"]["code"], "to": x["destination"]["station"]["code"],
             "city": x["destination"]["station"]["city"]["name"],
             "country": x["destination"]["station"]["country"]["code"],
             "date": (x.get("departureDate") or "")[:10]} for x in res.get("itineraries") or []]
    rows.sort(key=lambda r: r["eur"])
    print_table(rows, [("eur", "EUR"), ("from", "FROM"), ("to", "TO"), ("city", "CITY"),
                       ("country", "CC"), ("date", "DATE")], limit=a.limit)
    return rows


def cmd_origin_scan(a) -> list[dict]:
    out = []
    for o in split_codes(a.scan_origins):
        try:
            rows = run_search(a, src=resolve(o), quiet=True)
        except Exception as e:  # keep scanning
            print(f"[kiwi] {o}: {e}", file=sys.stderr)
            continue
        best = rows[0] if rows else None
        print(f"[kiwi] {o}: {best['eur'] if best else '-'} EUR {best['route'] if best else ''}",
              file=sys.stderr)
        if best:
            no_st = next((r for r in rows if (r.get("tickets") or 1) == 1), None)
            out.append({"origin": o, **best,
                        "best_single_ticket_eur": no_st["eur"] if no_st else None,
                        "single_ticket_route": no_st["route"] if no_st else None})
    out.sort(key=lambda r: r["eur"])
    print_table(out, [("origin", "ORIGIN"), ("eur", "BEST EUR"), ("route", "ROUTE"),
                      ("times", "TIMES"), ("flags", "FLAGS"),
                      ("best_single_ticket_eur", "1-TICKET EUR"),
                      ("single_ticket_route", "1-TICKET ROUTE")], maxw=70)
    return out


def cmd_calendar(a) -> list[dict]:
    d1, d2 = parse_date_range(a.dates)
    v = {"search": {"source": {"ids": ids(a.origins)}, "destination": {"ids": ids(a.dests)},
                    "dates": _range(d1, d2), "passengers": _pax(a.adults, a.checked_bags, a.hand_bags),
                    "cabinClass": {"cabinClass": "ECONOMY", "applyMixedClasses": False}},
         "filter": _filter(a), "options": _options(a)}
    res = gql("PriceCalendarQuery", Q_CAL, v)["itineraryPricesCalendar"]
    rows = [{"date": c["date"][:10], "price": float(c["ratedPrice"]["price"]["amount"]),
             "rating": c["ratedPrice"].get("rating")}
            for c in res.get("calendar") or [] if c.get("ratedPrice") and c["ratedPrice"].get("price")]
    print_table(rows, [("date", "DATE"), ("price", a.currency.upper()), ("rating", "RATING")])
    if rows:
        b = min(rows, key=lambda r: r["price"])
        print(f"cheapest day: {b['date']} {b['price']} {a.currency.upper()}")
    return rows


def cmd_places(a) -> list[dict]:
    base = _city_id(a.near)
    rows = [{"code": c, "name": n} for c, n in radius_airports(base, a.radius)]
    print(f"{len(rows)} airports within {a.radius} km of {a.near} ({base}):")
    print(" ".join(r["code"] for r in rows))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, need_from=True):
        if need_from:
            p.add_argument("--from", dest="origins", nargs="+", required=True)
        p.add_argument("--to", dest="dests", nargs="+", required=True)
        p.add_argument("--dates", required=True, help="2027-03-01..2027-03-15 or 2027-03-10+-3")
        p.add_argument("--return-dates", help="return window -> round trip")
        p.add_argument("--nights", help="e.g. 14-21 -> round trip with that stay length")
        p.add_argument("--currency", default="EUR")
        p.add_argument("--market", default="hr")
        p.add_argument("--adults", type=int, default=1)
        p.add_argument("--checked-bags", type=int, default=0, help="price in N checked bags")
        p.add_argument("--hand-bags", type=int, default=0, help="price in N cabin bags")
        p.add_argument("--max-stops", type=int)
        p.add_argument("--no-self-transfer", action="store_true",
                       help="exclude Kiwi self-transfer (virtual interlining) combos")
        p.add_argument("--hacks", action="store_true",
                       help="also allow hidden-city / throwaway results (risky; off by default)")
        p.add_argument("--combine-oneways", action="store_true",
                       help="round trip: also price out + back as two one-way tickets (2 extra queries); "
                            "Kiwi's return search omits these for full-service carriers")
        p.add_argument("--fsc-bags-included", metavar="CARRIERS",
                       help="with --checked-bags: rank itineraries flown only by these carriers WITHOUT "
                            "Kiwi's bag add-on (their fares include bags), e.g. MU,CA,CZ")
        p.add_argument("--limit", type=int, default=30, help="rows to print")
        p.add_argument("--limit-api", type=int, default=50, help="itineraries requested (API max 50)")
        p.add_argument("--json")

    common(sub.add_parser("search", help="itinerary search (multi-origin/region/radius)"))
    common(sub.add_parser("per-city", help="cheapest fare per destination city"))
    p = sub.add_parser("origin-scan", help="query each origin separately; rank origins")
    common(p, need_from=False)
    p.add_argument("--origins", dest="scan_origins", nargs="+", required=True)
    common(sub.add_parser("calendar", help="cheapest one-way price per day"))
    p = sub.add_parser("places", help="airports within a radius")
    p.add_argument("--near", required=True)
    p.add_argument("--radius", type=int, default=400)
    p.add_argument("--json")

    a = ap.parse_args()
    fn = {"search": run_search, "per-city": cmd_per_city, "origin-scan": cmd_origin_scan,
          "calendar": cmd_calendar, "places": cmd_places}[a.cmd]
    dump_json(fn(a), a.json)


if __name__ == "__main__":
    main()
