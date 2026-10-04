# 05 – Tools: Google Flights & ITA Matrix (tested 2026-10-04)

Goal: give a future agent a **reliable, scriptable** way to query the two most important
fare engines – Google Flights (GF) and ITA Matrix – for the cheapest Zagreb-region / Europe →
Japan tickets (dates tested: Feb–Mar 2027), and document what works, what fails and why.

Everything below was **actually run** from this container (Python 3.11, Playwright 1.56 +
pre-installed Chromium 141 build 1194, egress through the agent proxy). Egress IP geolocates to
**Chicago, US (AS396982 Google LLC)** – relevant for consent pages and point-of-sale tests.

---

## TL;DR

| Method | Works (Oct 2026)? | Notes |
|---|---|---|
| **GF internal RPC** `FlightsFrontendService/GetShoppingResults` (own client in `gflights.py`) | **YES – best** | plain `requests`, 0.5–4 s/query, up to ~300 itineraries, multi-airport origins *and* destinations in one call, gl/curr/hl params, self-transfer flag, layovers |
| GF RPC `GetCalendarGraph` (cheapest per day) | **YES** | 61 days per call, one-way or round-trip with **one fixed** stay length per call |
| GF RPC `GetCalendarGrid` (dep × ret matrix) | **YES** | ≤200 cells per call |
| GF results page HTML (`/travel/flights/search?tfs=…`) parsed for `ds:1` | YES (fallback) | only ~10–15 "top" itineraries; `tfs` protobuf hand-encoded, multi-airport OK |
| GF in headless Chromium (Playwright) | PARTIAL | server-rendered results parse fine (fallback backend works); the app's JS bundles fail with `ERR_BLOCKED_BY_ORB` through this proxy, so interactive widgets (Cheapest tab, date grid, price graph, Explore) do not work here |
| `flights` (punitarani/**fli**) 0.9.0 | YES | good library + CLI (`fli flights`, `fli dates`); defaults are too aggressive (10 req/s, parallel threads) |
| `fast-flights` 3.1.0 (AWeirdDev) | **NO (parser bug)** | fetch works (primp, 0.7 s) but `get_flights()` crashes with `IndexError` on rows without price |
| `gflights` 0.3.1 (Rust, nas-/google-flights-rs) | YES (bursty) | search/price_graph/date_grid/cheapest_dates/explore/offer; one `cheapest_dates`+`explore` burst earned an HTTP 429 |
| **ITA Matrix v5 JSON API** (`content-alkalimatrix-pa.googleapis.com/v1/search`) | **YES** (`matrix.py`) | direct HTTP works **without** the BotGuard token today; 15–60 s per query; specific dates, calendar, routing & extension codes, sales city, currency |
| Matrix via Playwright | YES (fallback) | deep links don't auto-run in headless; fallback drives the form and swaps the request body (keeps BotGuard token) |

**Point of sale:** changing `gl` (HR, AT, DE, HU, US, GB, JP, IN, TR, SE) **did not change a single
GF price** – all 82 itineraries of a ZAG–TYO round trip were identical in EUR; other currencies
differed only by FX conversion (+0.07 … +0.44 %). No POS arbitrage is visible through Google Flights.
Matrix sales-city results: see §5.3.

**Coverage warning:** a default Matrix v5 query returns only a *small, pruned, run-to-run varying*
solution set (6–17 solutions, 4–5 carriers) – e.g. VIE–NRT 10 Mar 2027 one-way: Matrix min **€1034**
(KE) vs GF **€772**; ZAG–TYO RT 10–24 Mar: Matrix **€1554** (AF/KL) vs GF **€1186** (LOT). Other
carriers (EK €789, QR €878, CA €770 …) only appear when the query is narrowed with routing/extension
codes (see §5.2–5.3). Use GF for "cheapest", Matrix for fare construction / routing tricks, and run
several narrowed Matrix variants rather than trusting one default query.

---

## 1. Environment notes (for the next agent)

* `pip install -r flights/scripts/requirements.txt` – core needs only `requests`; Playwright is
  optional (browser fallbacks). Use a **venv**: on this Debian Python, `pip install flights` fails
  building its dependency `ratelimit` (`AttributeError: install_layout`) – inside a venv it installs fine.
* Playwright: install **`playwright==1.56.0`** (matches the pre-installed Chromium build 1194 under
  `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`; never run `playwright install` here).
  Binary: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (headless shell:
  `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`). Set
  `CHROMIUM_PATH` to force a binary in the scripts.
* Chromium must be launched with `proxy={"server": os.environ["HTTPS_PROXY"]}`; TLS trust is already
  configured (NSS store). Python `requests`, `primp`, `curl_cffi` and the Rust `gflights` all worked
  through the proxy without extra settings.
* No Google consent wall appeared (US egress). The browser code pre-seeds the `SOCS` consent cookie
  and clicks "Reject all"/"Accept all" if it lands on `consent.google.com` (untested from an EU IP).

---

## 2. Python libraries for Google Flights

### 2.1 `fast-flights` 3.1.0 (released 2026-08-18) – **broken parser**

```
pip install fast-flights          # pulls primp 2.0.1, protobuf 7, selectolax 1.0
python - <<'EOF'
from fast_flights import FlightQuery, Passengers, create_query, get_flights
q = create_query(flights=[FlightQuery(date="2027-03-10", from_airport="VIE", to_airport="NRT")],
                 trip="one-way", passengers=Passengers(adults=1), language="en", currency="EUR")
print(q.url())   # https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDMtMTBqBRIDVklFcgUSA05SVEIBAUgBmAEC&hl=en&curr=EUR
get_flights(q)   # -> IndexError: list index out of range  (parser.py line 77: price = k[1][0][1])
EOF
```

* Fetch mode: `primp.Client(impersonate="chrome_145")` GET of the `tfs=` URL – **works** (0.7 s,
  2.3 MB HTML). v3 replaced the old `fetch_mode` ("common"/"fallback"/"local" Playwright) with
  `integrations` (Bright Data, SearchAPI – paid). No `gl` support in the URL builder.
* Parser reads only `payload[3]` ("other flights", not `payload[2]` "best") and crashes on any row
  whose price list is empty (Google includes priceless rows, e.g. KE+OZ combos). Fields when it
  works: price, airline names, legs (airports, times, duration, aircraft), CO2. **No self-transfer
  flag, no layover detail, no currency.**
* Useful anyway: its `tfs` protobuf schema (Info{3:FlightData, 8:passengers, 9:seat, 19:trip},
  FlightData{2:date, 13:from, 14:to}). `gflights.py` hand-encodes the same and verified that
  **repeated** 13/14 entries give multi-airport searches.

### 2.2 `flights` = punitarani/**fli** 0.9.0 (2026-05-21) – **works**

```
python3 -m venv .venv && .venv/bin/pip install flights click     # click is a missing dependency of the CLI
.venv/bin/fli flights VIE NRT 2027-03-10 --currency EUR --country HR --language en --format json
.venv/bin/fli dates   VIE NRT --from 2027-02-01 --to 2027-03-31 --currency EUR --country HR --format json
```

| Test | Result |
|---|---|
| `fli flights VIE NRT 2027-03-10` (OW) | 110 itineraries in **1.4 s**; cheapest €772 QR+PR via DOH/MNL; €801 OS+CX; €878 QR |
| `fli flights VIE NRT 2027-02-09` | cheapest **€418** Scoot TR61/TR894 via SIN |
| `fli dates VIE NRT` Feb–Mar 2027 (OW) | 59 dates in **0.9 s**; cheapest €418 (9/16/23 Feb) |
| Python API, 7 origins × 3 dests one call | 300 itineraries, 14 s; cheapest **€368** VIE–SIN–HND (Scoot) |
| Python API RT VIE–NRT 10→24 Mar, `top_n=3` | 1+3 requests, 10 s; cheapest RT €949 (AY via HEL) |

Fields: price, currency, duration, stops, legs (airports, times, flight no., airline, aircraft,
legroom, amenities), layovers, **self_transfer**, mixed_cabin, CO2, booking_token. Currency/country
via `curr=`/`gl=`/`hl=` URL params. Multi-airport via `FlightSegment(departure_airport=[[A,0],[B,0]])`.
Caveats: client rate limiter allows **10 req/s** and `parallel_map` threads – far too aggressive
here; Airport enum (7,900 entries) does not accept city codes/MIDs; RT expansion costs 1+N calls.

### 2.3 `gflights` 0.3.1 (2026-07-23; Rust core) – works, but bursts get 429

```python
import asyncio; from gflights import Client
c = Client(currency="EUR", country="HR", lang="en")
asyncio.run(c.search(origin="ZAG", destination="Tokyo", date="2027-02-09"))      # 13 results, 0.5 s
asyncio.run(c.price_graph(origin="VIE", destination="NRT", date="2027-02-01", months=2))   # 60 days, 0.3 s
asyncio.run(c.date_grid(origin="VIE", destination="NRT", dep_start="2027-03-01", dep_end="2027-03-07",
                        ret_start="2027-03-15", ret_end="2027-03-21"))            # 49 cells, 0.1 s, min €907
asyncio.run(c.cheapest_dates(origin="VIE", destination="NRT", date="2027-02-01", months=2,
                             trip_duration_days=14))                               # 37.7 s (many calls)
asyncio.run(c.explore(origin="ZAG", month=3, duration="2weeks"))                   # 67 destinations, 25 s, no Japan
asyncio.run(c.offer(origin="VIE", destination="NRT", date="2027-02-09"))           # HTTP 429 (after the burst above)
```

Accepts city names ("Tokyo"). `search` returns only the first ~12 rows. After a 429 the client
refuses all further calls until `reset_rate_limit()`. Its source (github.com/nas-/google-flights-rs)
documents the `GetCalendarGrid` (≤200 cells) and `GetExploreDestinations` wire formats.

### 2.4 Others checked
`google-flights-scraper` 0.1.0 (2024, abandoned), `pyflights` (2018, dead QPX API). SerpApi /
SearchAPI / Bright Data are paid – not used.

---

## 3. Google Flights – direct RPC (what `gflights.py` uses)

Endpoint (same as the web app; no cookies, no token, plain `requests` with a desktop UA):

```
POST https://www.google.com/_/FlightsFrontendUi/data/travel.frontend.flights.FlightsFrontendService/<Method>?hl=en&gl=HR&curr=EUR
content-type: application/x-www-form-urlencoded;charset=UTF-8
body: f.req=<urlencoded JSON: [null, "<JSON string of the request>"]>
```

Request ("flat" format, field map from fli + own tests):

```
segment = [[[[ "VIE",0],["ZAG",0]]],          # 0 origins   (type 0 = airport, 5 = city MID e.g. "/m/07dfk" Tokyo)
           [[[ "NRT",0],["HND",0]]],          # 1 destinations
           null, stops(0 any|1 nonstop|2 ≤1|3 ≤2), airlines_incl, airlines_excl,
           "2027-02-09", [max_minutes]|null, selected_flights|null, via_airports|null,
           null, min_layover, max_layover, emissions, 3 (outbound) | 1 (return)]
main    = [null,null, trip(1 RT|2 OW|3 multi), null, [], cabin(1-4), [adults,children,inf_lap,inf_seat],
           [null,max_price]|null, null,null, [checked_bags,carry_on]|null, null,null, [segments...],
           null,null,null, 1, null×10, exclude_basic(0/1)]
GetShoppingResults : [[], main, sort(2=cheapest), 1, 0, 1]
GetCalendarGraph   : [null, main, ["2027-02-01","2027-03-31"]]                    # OW, ≤61 days
                     [null, main, [start,end], null, [14,14]]                      # RT, fixed stay (ranges ⇒ empty)
GetCalendarGrid    : [null, main(trip=1), [dep_start,dep_end], [ret_start,ret_end]] # ≤200 cells
```

Response: `)]}'` + length-prefixed `wrb.fr` chunks; inner JSON `[2][0]` = "best" rows, `[3][0]` =
"other" rows, `[5]` = price insights (`[1][1]` lowest, `[4][1]..[5][1]` typical range).
Row: `row[0]` itinerary (`[0]` airline code, `[1]` names, `[2]` legs, `[3]/[6]` orig/dest,
`[9]` minutes, `[12]` **self-transfer**, `[13]` layovers `[min, arr_apt, dep_apt,…]`),
`row[1][0][1]` price, `row[1][1]` token (currency inside: `\x1a\x03EUR`). Leg: `[3]/[6]` airports,
`[8]/[10]` times, `[20]/[21]` dates, `[11]` minutes, `[17]` aircraft, `[22]` `[carrier, number, _, name]`.
Calendar rows: `inner[-1][i] = [dep, ret, [[null, price], token]]`.

Verified behaviour:
* **Multi-airport works on both sides** (7 origins × 4 destinations → 300 rows, 4 s). Results are
  capped (~300 rows), so for per-origin completeness query origins separately (`--per-origin`/`sweep`).
* **Round trip:** the price on each outbound row is the cheapest *total* RT price with that
  outbound; the return list needs one extra call per outbound (`--expand N`), filled via
  `segment[8] = [[from, date, to, null, carrier, number], …]`.
* Calendar Graph honours **one** stay length per call (a range `[12,16]` returns nothing) – the
  script loops lengths. Including **UKB** (Kobe, domestic only) in the destination list makes the
  calendar return a single date – removed from the `OSA` group; the script warns on such results.
  Calendar values are Google's cached lowest prices: some dates are missing (e.g. ARN only 36/59
  days) and must be re-checked with a specific search.
* `q=` natural-language URLs do **not** accept comma lists ("Flights to NRT,HND from ZAG,VIE…" → 0
  results); the `tfs=` protobuf URL does.
* No self-transfer itinerary was returned in any test (fli notes the self-transfer toggle only
  exists in the browser's "wrapper" request format). Kiwi-style virtual interlining must be
  searched on Kiwi etc. (other agent's report).

### 3.1 Rate limiting (observed)
* gflights/fli-style bursts (dozens of calls at ≤10/s): **HTTP 429** on `GetBookingResults`, and
  minutes later the browser got the **reCAPTCHA "unusual traffic" page** (`/sorry/`). The RPC
  endpoint worked again ~15 min later.
* With the IP still "warm", ~4.5 s spacing gave 429s on 5 of the first 10 calls; the 30–60 s
  back-off recovered each time.
* **6–7.5 s spacing (default for `sweep`): no 429** over the full 60-origin sweep (§4.4).
* `gflights.py` therefore: ≥3 s (+0–1.5 s jitter) between calls by default (`--sleep`), 6 s in
  sweeps (`--pace`), back-off 45→90→180 s on 429/captcha, then stops cleanly (sweep progress is
  cached).

### 3.2 Playwright (headless Chromium) on Google Flights
* `https://www.google.com/travel/flights?q=Flights%20to%20NRT%20from%20ZAG%20on%202027-03-10%20through%202027-03-24&hl=en&gl=HR&curr=EUR`
  loads in ~1.4 s; the first ~10 results are **server-rendered** (and present as `ds:1` JSON), so the
  `browser` backend of `gflights.py` simply renders the page and parses `ds:1` (works, ~6 s).
* The app's lazily loaded JS modules (`www.gstatic.com/_/mss/boq-travel/...`, URLs 2.7–4 KB long)
  fail in Chromium with **`net::ERR_BLOCKED_BY_ORB`** through this proxy, although `curl` fetches
  the same URLs fine (200, `text/javascript`). Consequence: the "Cheapest" tab spinner never
  resolves, and "Date grid"/"Price graph" buttons and `/travel/explore` don't work in this
  environment. Disabling ORB features didn't help; routing those JS URLs through `requests` loaded
  the page but at that moment Google served the captcha (rate-limit episode) – not pursued since the
  RPC endpoints deliver the same data (calendar = price graph, grid = date grid).
{{PW_EXTRA}}

---

## 4. `gflights.py` – usage

Location: `flights/scripts/gflights.py` (+ `gflights_calendar.py` shortcut). Global options go
**before** the subcommand: `--gl HR --curr EUR --hl en --sleep 3 --quiet`.

Code groups: `TYO`=NRT,HND · `OSA`=KIX,ITM · `JPN`=NRT,HND,KIX,ITM,NGO,FUK,CTS,OKA · `LON`, `PAR`,
`MIL`, `ROM`, `STO`, `VEN`(VCE,TSF)…; presets `zagreb` (20 airports within ~1 day of Zagreb) and
`europe` (60 long-haul-relevant airports); or a file with codes.

```
# specific dates; origins batched 7 per request; table + JSON
python gflights.py search --from zagreb --to TYO,OSA --date 2027-02-09 --out results.json
python gflights.py search --from ZAG,VIE --to TYO --date 2027-03-10 --return 2027-03-24 --expand 3
python gflights.py search --from VIE --to JPN --date 2027-02-08..2027-02-12 --stay 14
python gflights.py search --from BUD --to OSA --date 2027-02-09 --stops 1 --via IST,DOH --bags 1
python gflights.py search --backend auto ...      # rpc → html → browser fallbacks

# cheapest price per day (OW; RT with --stay N or N-M)
python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --heatmap
python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 13-15
python gflights.py calendar --from zagreb --to TYO --start 2027-02-01 --end 2027-03-31 --stay 14 --per-origin

# RT departure × return grid
python gflights.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21

# Europe-wide origin sweep (resumable): 1 calendar call per origin, then itinerary details for best N
python gflights.py sweep --origins europe --to TYO,OSA --start 2027-02-01 --end 2027-03-31 --stay 14 \
       --cache sweep_cache.json --details 5 --out sweep.json
python gflights.py sweep --origins europe --to TYO --date 2027-02-09 --return 2027-02-23   # specific-date mode
```

Options: `--adults`, `--cabin economy|premium|business|first`, `--stops any|0|1|2`, `--via`,
`--max-price`, `--bags N`, `--carry-on`, `--exclude-basic`, `--no-self-transfer`, `--sort`,
`--top`, `--out`, `--json-only`, `--per-origin`, `--batch 7`.
JSON per itinerary: `price, currency, airline, airlines, origin, destination, depart, arrive,
duration_min, stops, layovers, layover_detail[{minutes, airport, airport_change}], self_transfer,
flights, legs[{from,to,dep,arr,flight,carrier,duration_min,aircraft}], query_date, query_return,
trip, google_flights_url` (+ `return_leg` with `--expand`).

### 4.1 Sample: multi-origin one-way (1 request, 4.1 s)
```
$ python gflights.py search --from ZAG,LJU,GRZ,VIE,BUD,VCE,MUC --to TYO,OSA --date 2027-02-09 --top 8
  #    price cur from>to   depart              dur st via          ST airline / flights
  1      368 EUR VIE >HND  2027-02-09 10:00  31h00  1 SIN             Scoot | TR61 TR804
  2      418 EUR VIE >NRT  2027-02-09 10:00  37h10  1 SIN             Scoot | TR61 TR894
  3      418 EUR VIE >KIX  2027-02-09 10:00  40h15  1 SIN             Scoot | TR61 TR880
  4      498 EUR VIE >NRT  2027-02-09 10:00  24h30  2 SIN,TPE         Scoot | TR61 TR874 TR874
  5      514 EUR VCE >KIX  2027-02-09 09:35  25h35  1 IST             Turkish Airlines | TK1868 TK86
  8      521 EUR BUD >KIX  2027-02-09 09:10  26h00  1 IST             Turkish Airlines | TK1036 TK86
cheapest per origin: VIE 368, VCE 514, BUD 521, MUC 579, ZAG 621, LJU 712, GRZ 785
(300 itineraries, 1 requests, 4.1 s)
```

### 4.2 Sample: round trip with return expansion
```
$ python gflights.py search --from ZAG --to TYO --date 2027-03-10 --return 2027-03-24 --expand 2 --top 3
  1     1186 EUR ZAG >NRT  2027-03-10 12:45  46h55  1 WAW             LOT | LO612 LO79
             return: NRT>ZAG 2027-03-24 23:00 via WAW | LO80 LO613 (total 1186)
  2     1197 EUR ZAG >NRT  2027-03-10 17:50  41h50  2 VIE,WAW         Croatia, LOT | OU442 LO222 LO79
             return: NRT>ZAG 2027-03-24 23:00 via WAW | LO80 LO613 (total 1197)
  3     1297 EUR ZAG >HND  2027-03-10 06:00  20h45  1 FRA             Lufthansa | LH1407 LH716
```
(price insights for this route: lowest now €1186, typical €1100–1600)

### 4.3 Sample: calendar (OW, heatmap) and grid
```
$ python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --heatmap
    328 EUR VIE  2027-03-02
    368 EUR VIE  2027-02-09   (also 23 Feb, 28 Feb, 9 Mar, 16 Mar)
      Mon    Tue    Wed    Thu    Fri    Sat    Sun
2027-02 01:694  02:418  03:704  04:478  05:718  06:555  07:418
2027-02 08:712  09:368  10:704  11:418  12:654  13:478  14:418
...
$ python gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 14
    688 EUR VIE  2027-02-10 2027-02-24      (690 on 8/15/17/21 Feb)
$ python gflights.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21
depart \ return   03-15  03-16  03-17  03-18  03-19  03-20  03-21
2027-03-01         1001    935   1003    935   1033   1056   1008
2027-03-02          912    916    907    933    969    958    958
...
cheapest: 907 EUR  2027-03-02 -> 2027-03-17
```

### 4.4 Europe-wide sweep (TYO+OSA, RT 14 nights, departures 1 Feb–31 Mar 2027)
{{SWEEP}}

---

## 5. ITA Matrix

### 5.1 How the Matrix v5 web app talks to its backend
Captured with Playwright (UI search VIE→NRT, 10 Mar 2027, sales city ZAG, EUR):

* Location lookups: `GET /v1/locationTypes/airportOrMultiAirportCity/locationCodes/NRT?key=…`
* Search: gapi **batch** POST to `https://content-alkalimatrix-pa.googleapis.com/batch` wrapping
  `POST /v1/search?key=AIzaSyBH1mte6BdKzvf0c2mYprkyvfHCRWmfX7g&alt=json` with headers
  `x-alkali-application-key: applications/matrix`, `x-alkali-auth-apps-namespace: alkali_v2`,
  `x-alkali-auth-entities-namespace: alkali_v2` and a BotGuard `bgProgramResponse` in the body.
* **Direct POST to `/v1/search` (no batch, no BotGuard token) works** (200, same JSON). Exact body:

```json
{"summarizers":["carrierStopMatrix","currencyNotice","solutionList","itineraryPriceSlider","itineraryCarrierList"],
 "inputs":{"filter":{},"page":{"current":1,"size":25},"pax":{"adults":1},
   "slices":[{"origins":["VIE"],"destinations":["NRT"],"date":"2027-03-10","dateModifier":{"minus":0,"plus":0},
              "isArrivalDate":false,"routeLanguage":"C:CA X:PEK C:CA","commandLine":"MAXSTOPS 1",
              "filter":{"warnings":{"values":[]}},"selected":false}],
   "firstDayOfWeek":"SUNDAY","internalUser":false,"sliceIndex":0,"sorts":"default","cabin":"COACH",
   "maxLegsRelativeToMin":1,"maxStopCount":1,"changeOfAirport":true,"checkAvailability":true,
   "currency":"EUR","salesCity":"ZAG"},
 "summarizerSet":"wholeTrip","name":"specificDatesSlice"}
```
  Calendar of lowest fares: `"name":"calendar"`, `"summarizerSet":"calendarRoundTrip"` (or
  `calendarOneWay`), summarizers `["calendar","overnightFlightsCalendar","itineraryStopCountList",
  "itineraryCarrierList","currencyNotice"]`, slices **without** `date`, plus
  `"startDate":"2027-03-01","endDate":"2027-04-01"` and for RT `"layover":{"min":12,"max":14}`
  (stay nights; a range is fine – one call returns the best length per day).
* Errors come back as `{"error":{"message":"QPX Warning. SLICE-PROHIBITED-CABINS: \"BUSINESS\" is not a Bc Bin","type":"input"}}`.
* Response: `solutionList.solutions[]` (`displayTotal` "EUR1033.09", `itinerary.slices[]` with
  flights, stops, departure/arrival, duration; carriers), `carrierStopMatrix`,
  `itineraryCarrierList.groups[]` (min price per carrier), `calendar.months[].weeks[].days[]`
  (`minPrice`, `tripDuration.options[].tripLength`).
* UI state URL: `https://matrix.itasoftware.com/flights?search=<base64 JSON>` (type, slices with
  origin/dest/routing/ext/dates, options cabin/stops/extraStops/currency/salesCity, pax). In headless
  Chromium such deep links render but **do not start the search** (console `{error: Object}`), so
  the browser fallback drives the form and swaps the request body instead.
* Timing: **15–60 s per query** (server-side). Never saw a rate limit in ~25 queries at ≥5 s spacing.

### 5.2 Results & coverage
| Query | Matrix | Google Flights |
|---|---|---|
| VIE→NRT OW 10 Mar 2027 (avail. check on) | 6 solutions, min **€1033** KE/OZ; TK €1891 (sometimes CA €770 VIE–PEK–HND appears – results vary between identical calls) | 110 rows, min **€772** (QR+PR), €801 OS+CX, €878 QR, €935 KL, €940 EY, €942 AY |
| ZAG⇄TYO RT 10–24 Mar | 17 solutions, min **€1554** AF/KL | 82 rows, min **€1186** LOT |
| ARN⇄TYO RT 9–23 Feb, avail. on | min €905 (NH nonstop); CA only €2298 | min **€746** AY; no CA at all |
| same, `--no-avail` | **€655 Air China** ARN–PEK–HND (CA912/CA167, CA184/CA911) | – |
| ARN→TYO OW calendar Feb–Mar, `--route "CA+" --no-avail` | **€486** every day | – |
| VIE⇄TYO RT calendar Feb, stay 12–14, sales ZAG | min €896 (KE, 10 Feb, 13 n) | €688 (14 n) |

Take-aways: Matrix sees a **subset of carriers** (no LO, QR, EY, AY, TR, KL-direct… in these
tests), and with `checkAvailability=false` it exposes **published fares without confirmed seats**
(e.g. Air China €655 RT ex-ARN) – that's a lead to check on airchina.com / OTAs, not a bookable
price. Identical queries can return different (pruned) solution sets; vary routing codes
(`CA+`, `X:IST`, `MAXSTOPS 1`) to surface alternatives.

### 5.3 Routing / extension codes (tested on VIE→TYO 10 Mar OW)
Baseline (no codes) varied between runs: 6 solutions, min €1033 KE/OZ – or 7 incl. CA €770.

| Code | Result | Verdict |
|---|---|---|
| `--route "X:IST"` | 4 solutions, all TK via IST (€1891) | works |
| `--route "CA+"` / `"C:CA X:PEK C:CA"` (ARN⇄TYO) | only CA via PEK (€655 RT, no-avail) | works |
| `--route "C:CA"` | 0 solutions | works – `C:xx`/`O:xx` = exactly **one** segment |
| `--route "O:KE"` | 0 solutions (no single KE-operated VIE–TYO flight) | as above |
| `--route "N"` | 0 solutions | not a valid "nonstop" shortcut (use `C:OS` or `--max-stops 0`) |
| `--ext "MAXSTOPS 1"` | CA €770, KE €1033, TK… | works |
| `--ext "MINCONNECT 120"` / `"MAXCONNECT 240"` | sets change (AF €1167 appears with MAXCONNECT) | works |
| `--ext "-AIRLINES TK"` | TK disappears | works |
| `--ext "ALLIANCE STAR-ALLIANCE"` | KE (SkyTeam) disappears; CA/TK/NH/OS/AC only | works |
| `--ext "-PROPS"` | normal result | accepted |
| `--ext "F BC=K"` | 0 solutions | accepted, no K-class fare found (inconclusive) |
| `--ext "-CABIN BUSINESS"` | error `SLICE-PROHIBITED-CABINS: "BUSINESS" is not a Bc Bin` | invalid code ⇒ error JSON |
| `--ext "-CODESHARE"` (needs the argv fix; plain argparse rejects "-…" values) | 8 solutions, LH €1090 newly visible | works |
| `--ext "-REDEYES"` | **completely different set: EK €789 (VIE–DXB–HND), QR €878, JL €1086** | works – and shows how pruned the default set is |
| `--ext "-OVERNIGHTS"` | CA €770, KE, AF €1167, TK | accepted |
| `--minus 1 --plus 1` (date ±1) | 10 solutions incl. 9 Mar OS/NH nonstop VIE–HND €1313/€1389 | works |
{{MATRIX_DET}}

### 5.4 Sales city / currency experiment (VIE⇄TYO RT 10–24 Mar 2027, currency EUR)
`matrix.py search --from VIE --to TYO --date 2027-03-10 --return 2027-03-24 --curr EUR --sales-city X`
(direct API, 6 s between calls, all with availability check):

| sales city | min price | solutions | carrier minimums |
|---|---|---|---|
| default (= VIE) | EUR 1123.00 | 17 | KE 1123, CA 2255, AC 5109, OS 10873, multi 7027 |
| ZAG | EUR 1123.00 | 17 | identical |
| BUD | EUR 1123.00 | 17 | identical |
| LON | EUR 1123.00 | 17 | identical |
| TYO | EUR 1123.00 | 17 | identical |
| DEL | EUR 1123.00 | 17 | identical |
| IST | EUR 1123.00 | 17 | identical |
| NYC | EUR 1123.00 | 17 | identical |

No difference at all: either the fares used are not sales-city restricted, or the v5 API ignores
`salesCity` (the UI sends exactly this field, so the former is likely for these carriers). Combined
with §6 (Google Flights), **no point-of-sale arbitrage was observable through either engine** for
Europe→Japan. (For reference, GF's cheapest for the same RT was €949 AY, Matrix doesn't even show AY.)

### 5.5 `matrix.py` usage
```
python matrix.py search --from VIE --to TYO --date 2027-03-10 [--return 2027-03-24] \
     [--route "CA+" --route-ret "CA+"] [--ext "MAXSTOPS 1"] [--sales-city ZAG] [--curr EUR] \
     [--no-avail] [--minus 1 --plus 1] [--extra-stops 1] [--max-stops 1] [--cabin economy] \
     [--backend http|browser|auto] [--out m.json]
python matrix.py search --slice ZAG:NRT:2027-03-10 --slice KIX:ZAG:2027-03-24        # open jaw
python matrix.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 [--stay 12-14]
```
Values starting with "-" are accepted (`--ext -CODESHARE`). Output: sorted table, carrier minimums,
and a `matrix.itasoftware.com/flights?search=…` URL to open the same search in a normal browser
(deep links do work in a real desktop browser).

Sample:
```
$ python matrix.py search --from ARN --to TYO --date 2027-02-09 --return 2027-02-23 --route "CA+" --route-ret "CA+" --no-avail --sales-city STO --top 2
carriers: CA EUR655.00
  1     EUR654.63  CA   ARN-PEK-HND 2027-02-09T18:10 CA912 CA167 || HND-PEK-ARN 2027-02-23T08:30 CA184 CA911
  2     EUR654.63  CA   ARN-PEK-HND 2027-02-09T18:10 CA912 CA167 || HND-PEK-ARN 2027-02-23T08:30 CA184 CA731
$ python matrix.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-02-28 --stay 12-14 --sales-city ZAG
chunk 2027-02-01..2027-02-28: 52 day(s) priced; carriers [('CA','EUR1172.00'),('NH','EUR1150.00'),('KE','EUR896.00'),('*','EUR1225.00')]
EUR896.00  2027-02-10 13
EUR1097.00 2027-02-17 13
(33.9 s)
```

---

## 6. Point-of-sale / currency experiment on Google Flights

Method: identical RPC query, only `gl`/`curr` changed; ≥4 s between calls; converted with **ECB
reference rates of 2026-10-02**: USD 1.1225, JPY 176.99, GBP 0.85033, HUF 369.18, TRY 55.165,
INR 108.1245, SEK 11.29 per EUR. Also repeated through the HTML page (`/travel/flights/search?tfs=`).

**A) VIE→TYO one-way 9 Feb 2027 (cheapest = Scoot TR61/TR804 via SIN, 162–163 rows each)**

| gl | curr | cheapest | in EUR | Δ vs HR/EUR |
|---|---|---|---|---|
| HR | EUR | 368 | 368.0 | – |
| AT / DE / HU / US / JP / IN / TR | EUR | 368 | 368.0 | 0 % |
| HU | HUF | 135 409 | 366.8 | −0.3 % |
| US | USD | 414 | 368.8 | +0.2 % |
| HR | USD | 414 | 368.8 | +0.2 % |
| GB | GBP | 314 | 369.3 | +0.4 % |
| JP | JPY | 65 284 | 368.9 | +0.2 % |
| IN | INR | 39 835 | 368.4 | +0.1 % |
| TR | TRY | 20 317 | 368.3 | +0.1 % |
| SE | SEK | 4 152 | 367.8 | −0.1 % |

**B) ZAG⇄TYO RT 10–24 Mar 2027 (cheapest = LOT LO612/LO79 + LO80/LO613, 82 rows each)**

| gl | curr | cheapest | in EUR | all 82 itineraries vs HR/EUR |
|---|---|---|---|---|
| HR / AT / DE / US / JP / IN / TR | EUR | 1 186 | 1 186.0 | identical (ratio 1.0000) |
| US | USD | 1 335 | 1 189.3 | +0.27 … +0.38 % |
| GB | GBP | 1 011 | 1 189.0 | +0.19 … +0.31 % |
| JP | JPY | 210 664 | 1 190.3 | +0.36 … +0.44 % |
| IN | INR | 128 542 | 1 188.8 | +0.24 … +0.32 % |
| TR | TRY | 65 559 | 1 188.4 | +0.20 … +0.29 % |
| HU | HUF | 436 953 | 1 183.6 | −0.2 % |
| SE | SEK | 13 399 | 1 186.8 | +0.07 … +0.15 % |
| HR | USD | 1 335 | 1 189.3 | +0.3 % |

Conclusion: on Google Flights the `gl` country **does not change prices at all**; the currency only
adds Google's FX rounding (±0.4 %). Google prices each itinerary once (origin-market fare) and
converts. So "use a VPN / other country" brings nothing *on Google Flights*; any real POS
arbitrage would have to be found on airline/OTA sites selling in other markets (and Matrix's
sales-city option, §5.4). Caveat: the egress IP is US; `gl` was the only POS signal varied.

---

## 7. Recommendations for the future agent

1. **Broad search:** `gflights.py sweep --origins europe` (or `zagreb`) `--to TYO,OSA` with
   `--start/--end` and `--stay`, then `--details N`. ~10–12 s/origin, no 429 at 6 s pacing.
2. **Specific dates / many origins:** `gflights.py search --from zagreb --to TYO,OSA --date … [--return …]`
   (7 origins per call). Add `--per-origin` when you need every origin's own cheapest.
3. **Flexible dates:** `calendar` (OW or fixed stay; loop stays with `--stay 12-16`), `grid` for RT
   date pairs. Re-check calendar minima with `search` (calendar = cached prices, some days missing).
4. **Fare engineering:** `matrix.py` for routing/extension codes, sales city, open-jaw and fares
   without availability (`--no-avail` = leads only). Don't trust Matrix for "cheapest overall".
5. **Verify before reporting a price:** open `google_flights_url` / Matrix URL in a real browser,
   or book-site check; GF prices exclude bags unless `--bags`.
6. Keep ≥3 s between GF calls (≥6 s for long runs); on 429/captcha stop for 15+ min.
7. Self-transfer combos (Ryanair/Wizz positioning + long-haul) are **not** built by these engines:
   combine a GF/Matrix long-haul from a hub (sweep output) with a separate short-haul search.

## 8. Files
* `flights/scripts/gflights.py` – GF search/calendar/grid/sweep (rpc/html/browser backends)
* `flights/scripts/gflights_calendar.py` – shortcut for calendar/grid
* `flights/scripts/matrix.py` – ITA Matrix search/calendar (http/browser backends)
* `flights/scripts/requirements.txt`
{{FILES_EXTRA}}
