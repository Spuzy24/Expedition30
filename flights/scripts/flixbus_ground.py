#!/usr/bin/env python3
"""Price ground legs (home city -> departure airport) on FlixBus's public search API.

Usage:
  python3 flixbus_ground.py --date 2026-11-10                  # all default airports from Zagreb
  python3 flixbus_ground.py --date 2026-11-10 --to "Vienna Airport" "Budapest Airport"
  python3 flixbus_ground.py --from "Ljubljana" --date 2026-11-10   # another home base
  python3 flixbus_ground.py --cities "Graz Airport"                # just resolve city ids

Uses the same endpoints as flixbus.com (no key needed):
  autocomplete: https://global.api.flixbus.com/search/autocomplete/cities?q=...
  search:       https://global.api.flixbus.com/search/service/v4/search?from_city_id=..&to_city_id=..&departure_date=DD.MM.YYYY
Prices are per adult in EUR, *including* the platform fee (total_with_platform_fee).
Results include FlixBus-sold trains (e.g. ÖBB/SŽ legs) where Flix sells them.
"""
import argparse, json, sys, urllib.parse, urllib.request, datetime as dt

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
API = "https://global.api.flixbus.com/search"

# FlixBus city ids (resolved 2026-10-04). Name -> id. Airport "cities" stop at/near the terminal.
CITY_IDS = {
    "Zagreb": "40dea87d-8646-11e6-9066-549f350fcb0c",
    "Zagreb Airport": "27801821-86ad-4b3a-b838-0b9a1c824d83",
    "Ljubljana": "40de8044-8646-11e6-9066-549f350fcb0c",
    "Graz": "40de3c97-8646-11e6-9066-549f350fcb0c",
    "Maribor": "40de835d-8646-11e6-9066-549f350fcb0c",
    "Klagenfurt": "40de7c93-8646-11e6-9066-549f350fcb0c",
    "Rijeka": "40e11860-8646-11e6-9066-549f350fcb0c",
    "Zadar": "40e12563-8646-11e6-9066-549f350fcb0c",
    "Split Airport": "6500bc00-20be-4007-9536-6ad3e13d3476",
    "Trieste Airport": "74fc3496-db2d-4884-89f1-ace2d36469f1",
    "Trieste": "40de9f2f-8646-11e6-9066-549f350fcb0c",
    "Venice Airport": "b2a6981d-00be-40c6-9141-57e4977b409f",
    "Venice": "40dea03b-8646-11e6-9066-549f350fcb0c",
    "Treviso Airport": "0f3e7731-1464-463f-897f-019f79155692",
    "Vienna Airport": "40df34e5-8646-11e6-9066-549f350fcb0c",
    "Vienna": "40de1f31-8646-11e6-9066-549f350fcb0c",
    "Bratislava Airport": "358d7179-0a70-4694-8d26-bd2e084be1ed",
    "Bratislava": "40de54de-8646-11e6-9066-549f350fcb0c",
    "Budapest Airport": "07a78aaa-755f-4071-bb35-739b1fc741e6",
    "Budapest": "40de6527-8646-11e6-9066-549f350fcb0c",
    "Belgrade": "340bdce6-7eb1-4c50-bd1e-fd43485cdfef",
    "Sarajevo": "b4b1c3c9-608f-4920-9dfc-85762cef4b04",
    "Banja Luka": "40e10d0b-8646-11e6-9066-549f350fcb0c",
    "Tuzla": "ec3793d1-f68f-4167-a366-4879f33c6afd",
    "Munich Airport": "40dc4639-8646-11e6-9066-549f350fcb0c",
    "Munich": "40d901a5-8646-11e6-9066-549f350fcb0c",
    "Memmingen Airport": "156ea61d-a431-4acf-81e6-8830f6b9a56e",
    "Bergamo Airport": "e66b26bd-758d-4c59-ad1f-eddf72800f3e",
    "Milan Malpensa Airport": "40e324e7-8646-11e6-9066-549f350fcb0c",
    "Bologna": "40df3653-8646-11e6-9066-549f350fcb0c",
    "Prague Airport": "ffb87aeb-111d-40fd-8f06-b6838da8762e",
    "Prague": "40de1ad1-8646-11e6-9066-549f350fcb0c",
}
DEFAULT_TARGETS = [
    "Zagreb Airport", "Ljubljana", "Graz", "Trieste Airport", "Venice Airport", "Treviso Airport",
    "Vienna Airport", "Bratislava Airport", "Budapest Airport", "Belgrade", "Sarajevo", "Banja Luka",
    "Tuzla", "Zadar", "Split Airport", "Munich Airport", "Memmingen Airport", "Bergamo Airport",
    "Milan Malpensa Airport", "Bologna", "Prague Airport",
]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def resolve(name):
    if name in CITY_IDS:
        return CITY_IDS[name]
    q = urllib.parse.urlencode({"q": name, "lang": "en", "flixbus_cities_only": "false", "stations": "true"})
    res = get(f"{API}/autocomplete/cities?{q}")
    if not res:
        raise SystemExit(f"no FlixBus city for {name!r}")
    return res[0]["id"]


def search(frm, to, date):
    q = urllib.parse.urlencode({
        "from_city_id": frm, "to_city_id": to, "departure_date": date.strftime("%d.%m.%Y"),
        "products": json.dumps({"adult": 1}), "currency": "EUR", "locale": "en",
        "search_by": "cities", "include_after_midnight_rides": 1,
    })
    d = get(f"{API}/service/v4/search?{q}")
    out = []
    for trip in d.get("trips", []):
        for r in trip.get("results", {}).values():
            if r.get("status") != "available":
                continue
            p = r.get("price", {})
            out.append({
                "dep": r["departure"]["date"][:16].replace("T", " "),
                "arr": r["arrival"]["date"][:16].replace("T", " "),
                "dur": f'{r["duration"]["hours"]}h{r["duration"]["minutes"]:02d}',
                "type": r.get("transfer_type", "?"),
                "modes": "+".join(sorted({l.get("means_of_transport", "?") for l in r.get("legs", [])})),
                "eur": p.get("total_with_platform_fee", p.get("total")),
            })
    return sorted(out, key=lambda x: x["dep"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default="Zagreb")
    ap.add_argument("--to", nargs="*", default=None)
    ap.add_argument("--date", default=(dt.date.today() + dt.timedelta(days=30)).isoformat())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cities", nargs="*", help="only resolve these names to FlixBus city ids")
    a = ap.parse_args()
    if a.cities:
        for n in a.cities:
            print(n, resolve(n))
        return
    date = dt.date.fromisoformat(a.date)
    frm = resolve(a.frm)
    allres = {}
    for t in (a.to or DEFAULT_TARGETS):
        try:
            res = search(frm, resolve(t), date)
        except Exception as e:  # network / API change
            res = [{"error": str(e)}]
        allres[t] = res
        if not a.json:
            ok = [r for r in res if "eur" in r]
            cheapest = min((r["eur"] for r in ok), default=None)
            print(f"\n== {a.frm} -> {t} on {date} : {len(ok)} options, cheapest {cheapest} EUR")
            for r in res:
                if "error" in r:
                    print("   ERROR", r["error"]); continue
                print(f'   {r["dep"][11:]} -> {r["arr"][5:]}  {r["dur"]:>6}  {r["type"]:<10} {r["modes"]:<10} {r["eur"]} EUR')
    if a.json:
        json.dump(allres, sys.stdout, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
