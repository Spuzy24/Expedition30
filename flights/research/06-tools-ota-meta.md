# 06 — OTA / meta-search / LCC tools: what is programmatically usable (tested 2026-10-04)

Scope: everything except Google Flights & ITA Matrix (see 05). Goal: tools a future agent can
run to find the absolute cheapest bookable Europe(home)→Japan ticket, including the
"positioning flight + cheap long-haul from another European hub" construction.
All tests were run live from the sandbox on 2026-10-04 with modest request rates (2–10 s
between calls). Example dates: Feb–Mar 2027. Prices quoted are what the tools returned that day.

## TL;DR

* **Works with plain HTTPS (fast, scriptable, no key):**
  **Kiwi web GraphQL** (multi-origin, country/continent/radius origins, per-city cheapest,
  price calendar), **Kayak / momondo poll API** (live meta-search, ~60 results/page, EUR on
  .de sites), **Ryanair farfnd** and **Wizz timetable** (positioning fares), **AZair**
  (works but stale cache and short horizon).
* **Works with headless Chromium (Playwright) only:** **Aviasales** (AWS-WAF token),
  **Booking.com Flights** (= Etraveli/Gotogate/Mytrip inventory; AWS-WAF JS challenge),
  **FlightConnections** (route network; AWS-WAF).
* **Blocked, so check manually in a normal browser:** **Skyscanner** (PerimeterX
  press-and-hold captcha, APIs 403), **Trip.com** (verification wall on flight pages), Wego
  (403), Expedia (429), Gotogate/Mytrip direct (403, but covered via Booking.com),
  Skiplagged web (403; its MCP works, see orchestrator), Qatar (Akamai "Access Denied"),
  Turkish Airlines (edge tarpit/502), LOT (JS shell), Finnair (loads but not automated),
  Dohop (JS app; not automated). Travelpayouts/Aviasales Data API and Kiwi Tequila need API
  keys (account signup is out of scope).
* **Best combo found today (one-way, Mar 2027):** Ryanair **ZAG→CRL €33.99** (4 Mar) + ground
  CRL→BRU + **Juneyao BRU–PVG–NRT €327** (single ticket, 5 Mar) = **≈€361** + bus. Same
  hub from TSF €353, BUD (Wizz) €358, VIE €364. Direct searches from home: VIE–SIN–HND
  Scoot €360 (2/9 Mar), BUD–PVG–NRT MU €443, ZAG best €385 (Kiwi self-transfer).
  Round trip with 1 checked bag: VIE–XIY–PVG–NRT MU **€712**, BUD–PVG–HND MU €748,
  BUD–PEK–HND CA €757 (Kiwi, 8–12 Mar out / 22–26 Mar back).

## Summary matrix

| Source | Programmatic? | Method | Reliability | Notes |
|---|---|---|---|---|
| **Kiwi.com** (web GraphQL) | **Yes** | `POST api.skypicker.com/umbrella/v2/graphql` (plain requests, no key/cookies) → `kiwi_graphql.py` | High (≈1–3 s/query, no throttling seen in ~50 calls) | Live Kiwi prices incl. self-transfer "virtual interlining", bag pricing, multi-origin, `Country:`/`Continent:`/radius, per-city, calendar. Complements Kiwi MCP (`mcp_flights.py`). |
| Kiwi Tequila API | No | `tequila-api.kiwi.com` → 403 "'apikey' header is required" | n/a | Partner key required (not self-serve for us); web GraphQL and MCP make it unnecessary. |
| **Kayak / momondo** | **Yes** | GET search page → CSRF `formtoken` → `POST /i/api/search/dynamic/flights/poll` → `kayak.py` | High (≈10 searches, no captcha) | Live meta-search, all OTAs + airlines + Kiwi combos ("KIWIVI…"). EUR on momondo.de/kayak.de; multi-origin, nearby, ±1–3 days; pagination. |
| **Ryanair** | **Yes** | `services-api.ryanair.com/farfnd/v4/oneWayFares` / `roundTripFares`, `/api/farfnd/v4/oneWayFares/{O}/{D}/cheapestPerDay`, routes API → `ryanair_wizz.py` | High | Fare-finder cache (fare only, no bags); anywhere-from-origin in 1 call. Booking `availability` API declines without browser session (409). |
| **Wizz Air** | **Yes** | `be.wizzair.com/<ver>/Api/search/timetable` (+ `/asset/map`), version scraped from homepage → `ryanair_wizz.py` | High (needs `X-RequestVerificationToken` header echo) | Cheapest fare/day, ≤31-day window per call, local currency (HUF…) → EUR via ECB. |
| **AZair.eu** | Yes (HTML) | `GET azfin.php?…` + BeautifulSoup → `azair.py` | **Low–medium** | Works, but prices often **months old** (age 649–6 190 h), frequent "busy" answers, no results beyond ~2–3 months (Feb–Mar 2027: none). Discovery only. |
| **Aviasales** | Browser only | Playwright; page calls `tickets-api…/search/v2/start` (AWS-WAF token) + `/search/v3.2/results` → `aviasales.py` | Medium (≈45 s/search; works after cookie banner) | Live; strong at OTA self-transfer combos (Mytrip FR+MU). Old public endpoints (min-prices, map.aviasales) 404/302; Travelpayouts API 401 without token. |
| **Booking.com Flights** | Browser only | Playwright; page calls `flights.booking.com/api/flights/?…` → `booking_flights.py` | Medium-high | Live Etraveli inventory (≈ Gotogate/Mytrip/Flightnetwork), full price breakdown, bags, totalCount, min by stops. curl → 202 challenge. |
| **FlightConnections** | Browser only | Playwright; airport pages + `/airports_url.php`, `/airlines_url.php` → `flightconnections.py` | Medium-high | Route discovery (nonstop routes, flights/month, airlines). No prices. curl → 202 empty (AWS-WAF). |
| **Skyscanner** | **No** | curl → 307 to PerimeterX captcha; headless → captcha page, `/g/radar/api/v2/web-unified-search` & `/g/search-intent/v1/pricecalendar` **403** | — | Check manually (user's browser). Do not try to defeat the captcha. |
| **Trip.com** | **No** | curl → "Challenge Validation" page; headless → `verify.trip.com` "complete the verification test" | — | Manual only. Homepage itself loads. |
| Wego | No | 403 (bot block) | — | Manual. |
| Expedia | No | 429 on search URL | — | Manual. |
| eDreams / Opodo | Not built | Homepages 200 (JS app) | — | Their fares already appear in Kayak/momondo (provider OPODO/EDREAMS). |
| Gotogate / Mytrip | No (direct) | 403 | — | Same Etraveli inventory via Booking.com Flights and Aviasales/Kayak providers. |
| Skiplagged | Web: No | 403 (Cloudflare) | — | Use its public MCP (orchestrator's `mcp_flights.py`). |
| Dohop | Not built | JS app; guessed URLs 404 | — | Manual if wanted (self-transfer specialist). |
| Turkish Airlines | No | curl HTTP/2 INTERNAL_ERROR / timeout; headless 502 | — | Manual. |
| Qatar Airways | No | headless → "Access Denied" (Akamai) | — | Manual. |
| LOT | No | 3 KB JS shell (bot manager) | — | Manual. |
| Finnair | Partially | homepage loads in headless | — | Not automated; Kayak/Kiwi show AY fares. |
| Travelpayouts Data API | No | 401 "Unauthorized" without token | — | Needs partner token. |

## Environment notes (important for the next agent)

1. **Playwright:** `pip install playwright==1.56.0` (matches preinstalled Chromium build 1194
   in `/opt/pw-browsers`). Never `playwright install`.
2. **Chromium TLS through the proxy:** Chromium uses the NSS store, which was **empty**, so
   every page failed with `ERR_CERT_AUTHORITY_INVALID`. Fix (adds trust for the proxy CA; does
   not disable verification):
   ```
   apt-get install -y libnss3-tools
   certutil -A -d sql:$HOME/.pki/nssdb -n ccr-agent-proxy -t "C,," -i /root/.ccr/agent-proxy-ca.crt
   ```
3. **Playwright sync-API gotcha:** `time.sleep()` blocks event dispatch, so `page.on("response")`
   handlers never fire. Wait with `page.wait_for_timeout()` instead (`_browser.wait_until(..., page=page)`).
4. Python `requests` honours `HTTPS_PROXY`/`REQUESTS_CA_BUNDLE` automatically.
5. Shared helpers: `_common.py` (polite per-host rate limiter, ECB FX → EUR, table/JSON
   output, date ranges like `2027-03-01..2027-03-10` or `2027-03-05+-3`) and `_browser.py`
   (Playwright launcher with proxy, UA, cookie-consent clicking, response capture).

## Scripts (all in `flights/scripts/`, deps in `requirements-ota.txt`)

| Script | Source | Needs browser | Typical runtime |
|---|---|---|---|
| `kiwi_graphql.py` | Kiwi web GraphQL | no | 1–3 s/query |
| `kayak.py` | Kayak / momondo poll API | no | 15–25 s/search |
| `ryanair_wizz.py` | Ryanair farfnd + Wizz timetable | no | 2–3 s/call |
| `positioning.py` | Kiwi long-haul from hubs + FR/W6 positioning, buffer-aware | no | 1–4 min |
| `azair.py` | AZair HTML | no | 2–60 s (retries) |
| `aviasales.py` | Aviasales | yes | ~45 s/search |
| `booking_flights.py` | Booking.com Flights | yes | ~25 s/search |
| `flightconnections.py` | FlightConnections | yes | ~10 s/airport |

Every script has `--help` with examples, prints a sorted table, and accepts `--json PATH|-`.

---

## 1. Kiwi.com — web GraphQL (`kiwi_graphql.py`)

**Method.** Captured the kiwi.com search page with Playwright. The site calls
`POST https://api.skypicker.com/umbrella/v2/graphql?featureName=SearchReturnItinerariesQuery`
(or `SearchOneWayItinerariesQuery`) with a 44 KB query. Replaying it with plain `requests`
(no cookies, no `kw-umbrella-token`) **works**, and so does a hand-written slim query.
**Introspection is enabled**, so the full schema can be read. Useful root fields:
`onewayItineraries`, `returnItineraries`, `onewayOnePerCityItineraries`,
`returnOnePerCityItineraries`, `itineraryPricesCalendar`, `returnItineraryPricesCalendar`,
`itineraryPricesMap`, `places`.

**Website URL patterns (verified):**
`https://www.kiwi.com/en/search/results/zagreb-croatia/tokyo-japan/2027-03-10/2027-03-24`
(return); multi-origin + date range + one-way:
`…/results/zagreb-croatia,vienna-austria/tokyo-japan/2027-03-01_2027-03-15/no-return`.

**Location IDs** (`search.itinerary.source.ids`): `Station:airport:ZAG`, `City:tokyo_jp`,
`Country:JP`, `Continent:europe`, `Region:central-europe`. A radius isn't accepted as a source
directly; expand it with `places(search:{idSlugRadius:{id:"City:zagreb_hr",radius:400}},
filter:{onlyTypes:[AIRPORT]})`. The anchor must be a **City** id: a Station id returns 0.
400 km around Zagreb gives 27 airports (BNX BEG BLQ BZO BWK BTS BRQ BUD RMI FRL GRZ INN KLU
LNZ LJU AOI OMO OSI PUY RJK SZG SJJ SPU TSF TRS TZL VCE).

**Other inputs:** `sortBy: PRICE`; `searchStrategy` ∈ REGULAR / REDUCED (+_WITH_MRP);
`filter.flightsApiLimit` and `limit` (up to ~50 returned); `passengers.adultsHoldBags:[1]`
prices in a checked bag; return search supports `nightsCount:{start,end}`;
`enableSelfTransfer`, `enableTrueHiddenCity`, `enableThrowAwayTicketing`, `maxStopsCount`,
`excludeCarriers`, `stopoverCountries`. Each itinerary has `travelHack.isVirtualInterlining`
(self-transfer), `pnrCount`, `bagsInfo.includedCheckedBags`, `priceEur`, and
`bookingOptions…bookingUrl`.

**Region search (coordinator question).**
* `Continent:europe → Country:JP` in a normal search **works but is thin**: 25 results, all
  WAW/FCO, cheapest €698. Not reliable for finding the cheapest origin.
* A list of 6 whole countries returned **0**; 2 countries worked. A list of 22 airports worked
  (2.7 s), but results are dominated by one origin (BUD).
* **What works:** `onewayOnePerCityItineraries` with `Continent:europe → Country:JP` gives the
  cheapest fare per Japanese city with its European origin:
  BRU→NRT €327, BRU→KIX €327, DUB→NGO/FUK €395, OSL→OKA €436, MXP→CTS €544…
  Also `origin-scan` (one query per hub) ranks hubs fairly:

```
$ python3 kiwi_graphql.py origin-scan --to TYO,OSA --dates 2027-03-05..2027-03-12 \
    --origins ZAG,VIE,BUD,MUC,IST,WAW,HEL,MXP,BRU,AMS,FRA,PRG
ORIGIN  BEST EUR  ROUTE                FLAGS          1-TICKET EUR  1-TICKET ROUTE
BRU     327.0     BRU-PVG-NRT                         327.0         BRU-PVG-NRT
IST     373.0     IST-TAS-ICN-KIX      self-transfer  390.0         IST-CAN-HND
ZAG     385.0     ZAG-CRL-PVG-NRT      self-transfer
MXP     388.0     MXP-BCN-BRU-PVG-NRT  self-transfer  550.0         MXP-TPE-KIX
VIE     403.0     VIE-SIN-HND                         403.0         VIE-SIN-HND
PRG     413.0     PRG-BCN-BRU-PVG-NRT  self-transfer  589.0         PRG-PEK-KIX
WAW     433.0     WAW-NYO-PVG-HND      self-transfer  542.0         WAW-PEK-HND
BUD     437.0     BUD-BRU-PVG-NRT      self-transfer  443.0         BUD-PVG-NRT
FRA     481.0     FRA-LIN-BRU-PVG-KIX  self-transfer  542.0         FRA-PVG-HND
```

`per-city` also covers **positioning**: `--from ZAG,LJU,GRZ --to Continent:europe` returns
93 cities, e.g. ZAG→MLA €30, BSL €33, BGY €35, STN €35, CRL €38, FCO €45, WMI €45.

**Data quality.** Live Kiwi prices. Many of the cheapest results are Kiwi self-transfer combos
(separate tickets, Kiwi Guarantee). The flag and PNR count show this. Prices default to
cabin-bag-only unless `--checked-bags 1`. The price calendar (`itineraryPricesCalendar`) gives
the cheapest price per day with a CHEAP/AVERAGE/EXPENSIVE rating (ZAG→TYO, 1–10 Mar 2027:
€379–€509).

**Rate limits.** About 50 calls at 2–3 s spacing with no throttling. Each call takes 0.6–3 s.

**Usage**
```
python3 kiwi_graphql.py places --near ZAG --radius 400
python3 kiwi_graphql.py search --from ZAG@300 --to Country:JP --dates 2027-03-01..2027-03-15
python3 kiwi_graphql.py search --from ZAG,VIE,BUD --to TYO,OSA --dates 2027-03-08..2027-03-12 \
        --return-dates 2027-03-22..2027-03-26 --checked-bags 1
python3 kiwi_graphql.py search --from VIE --to TYO --dates 2027-03-01..2027-03-10 --nights 14-18
python3 kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates 2027-03-01..2027-03-15
python3 kiwi_graphql.py origin-scan --to TYO,OSA --dates 2027-03-05..2027-03-12 --origins BRU,IST,...
python3 kiwi_graphql.py calendar --from ZAG --to TYO --dates 2027-02-01..2027-03-31
```
Options: `--no-self-transfer`, `--max-stops`, `--hacks` (allow hidden-city/throwaway; off by
default), `--currency`, `--market`, `--json`.

Sample (`search --from ZAG@300 --to Country:JP --dates 2027-03-01..2027-03-15`, one-way):
```
EUR    ROUTE            TIMES                          AIRLINES  PNRs  BAGS  FLAGS
360.0  VIE-SIN-HND      2027-03-02 10:00->03-04 01:00  TR        1     0
407.0  VCE-BRU-PVG-NRT  2027-03-05 06:40->03-06 12:00  AZ,HO     2     0     self-transfer
414.0  VIE-SIN-TPE-OKA  2027-03-02 10:00->03-03 18:30  TR,SL     2     0     self-transfer
420.0  GRZ-MUC-ICN-KIX  2027-03-09 13:50->03-10 16:35  LH,WE     2     0     self-transfer
```
Round trip with 1 checked bag (`--from ZAG,VIE,BUD --to TYO,OSA`, out 8–12 Mar, back 22–26 Mar):
```
712.0  VIE-XIY-PVG-NRT | NRT-PVG-XIY-VIE   MU | MU   1 PNR  1 bag
748.0  BUD-PVG-HND | HND-PVG-BUD           MU | MU   1      1
757.0  BUD-PEK-HND | HND-PEK-BUD           CA | CA   1      1
864.0  VIE-PEK-KIX | KIX-PEK-VIE           CA | CA   1      1
```

**Tequila API:** `tequila-api.kiwi.com/v2/search` → `403 {"message":"'apikey' header is required"}`.
A partner key would require account signup (out of scope). Not needed.

## 2. Kayak / momondo — poll API (`kayak.py`)

**Method.** Captured momondo with Playwright: results arrive through
`POST /i/api/search/dynamic/flights/poll`. A plain-HTTP replay **works**:
1. `GET https://<site>/flight-search/<ORIG>-<DEST>/<date>[/<ret>]?sort=price_a`. The HTML
   contains `"formtoken":"…"` and sets session cookies.
2. `POST /i/api/search/dynamic/flights/poll` with headers `x-csrf: <formtoken>`,
   `x-requested-with: XMLHttpRequest` and body
   `{"userSearchParams":{"legs":[{"origin":{"airports":["ZAG","VIE"],"locationType":"airports"},
   "destination":{"airports":["TYO"],"locationType":"airports"},"date":"2027-03-10","flex":"exact"}],
   "passengers":["ADT"],"passengerDetails":[{"ptc":"ADT"}],"sortMode":"price_a"},
   "searchMetaData":{"pageNumber":1}}`. Repeat with the returned `searchId` until
   `status=="complete"` (3–7 polls). After that, `pageNumber=2…` gives more pages.

Nearby airports use `{"airport":"ZAG","locationType":"nearbyAirports"}` (URL `ZAG,nearby-TYO`).
Flexible dates use `"flex":"plusminusthree"` (URL `2027-03-10-flexible-3days`); also
`plusminusone` and `plusminustwo`.

**Sites/currency:** www.momondo.de, www.kayak.de and similar are EUR; kayak.com and
momondo.com are USD. All tested: kayak.com, momondo.com, momondo.de, kayak.de.

**Data:** live. Each result has providers (OPODO, BOOKINGFLIGHTS, KIWIVI/KIWIVILCC = Kiwi
self-transfer, CTRIPAIR = Trip.com, JUSTFLY…), `fareAmenities` (carry-on/checked
INCLUDED/FEE and count), legs/segments, a share URL and a booking redirect URL. `totalCount`
was 700–2 700 itineraries per search, with ~50–65 returned per page.

**Bot behaviour.** About 10 searches across 4 domains: no captcha, no 429. Keep ≥3 s between
calls (the script enforces this).

**Usage / samples**
```
$ python3 kayak.py --from ZAG,VIE,BUD --to TYO --depart 2027-03-10 --return 2027-03-24
== www.momondo.de ZAG,VIE,BUD -> TYO 2027-03-10 / 2027-03-24  (50 results, 2678 total)
EUR    PROVIDER        BAGS  ITINERARY
660.0  OPODO           2     BUD-PVG-NRT 03-10 11:30->03-11 12:50 MU | HND-PVG-BUD 03-24 ...
669.0  BOOKINGFLIGHTS  2     BUD-PVG-NRT 03-10 11:30->03-11 12:50 MU | NRT-PVG-BUD 03-24 ...

$ python3 kayak.py --site www.kayak.de --from ZAG --nearby --to TYO,OSA --depart 2027-03-10 --flex 3
EUR    PROVIDER   BAGS     ITINERARY
356.0  KIWIVILCC  FEE      ZAG-CRL-PVG-KIX 03-13 18:05->03-15 12:30 FR,HO
389.0  KIWIVILCC  FEE      ZAG-CRL-PVG-NRT 03-11 17:50->03-13 12:00 FR,HO
427.0  KIWIVI     UNKNOWN  ZAG-BEG-BRU-PVG-NRT 03-11 11:30->03-13 12:00 JU,HO
```
Options: `--site`, `--nearby`, `--flex 0-3`, `--pages N`, comma lists in `--depart/--return`
(it loops over every combination), `--show-links`, `--json`.

## 3. Ryanair + Wizz Air (`ryanair_wizz.py`), the positioning finder

**Ryanair (plain HTTPS, no key):**
* `GET https://services-api.ryanair.com/farfnd/v4/oneWayFares?departureAirportIataCode=ZAG&outboundDepartureDateFrom=2027-03-01&outboundDepartureDateTo=2027-03-10&currency=EUR&market=en-gb`
  returns the **cheapest fare to every destination** in the window (BUD: 54 destinations).
  Add `arrivalAirportIataCode` to restrict it. `www.ryanair.com/api/farfnd/v4/…` and
  `services-api…/farfnd/3/…` behave the same. Passing `limit=` → 400 InvalidLimit; omit it.
* `…/farfnd/v4/roundTripFares?…&inboundDepartureDateFrom=…&inboundDepartureDateTo=…`
  gives the cheapest RT per destination.
* `https://www.ryanair.com/api/farfnd/v4/oneWayFares/ZAG/BGY/cheapestPerDay?outboundMonthOfDate=2027-03-01&currency=EUR`
  gives a daily calendar with departure and arrival times.
* Routes: `https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/ZAG`
  (ZAG has 28; LJU and GRZ have 0).
* The booking availability API (`/api/booking/v4/en-gb/availability`) → `409 {"message":"Availability declined"}`
  without a browser session. Not needed.
* Data: cached fare-finder prices (`priceUpdated` timestamp). These are fares only, with
  a small personal item and no cabin or checked bag. Fares are bookable on ryanair.com. They
  are consistent with live checks (ZAG–STN 6 Nov €67.34 vs AZair's stale €36.99).

**Wizz Air (plain HTTPS):**
* API version: GET `https://www.wizzair.com/en-gb` and regex `apiUrl:"https://be.wizzair.com/29.19.0/Api"`.
  The old `/buildnumber` endpoint now returns HTML.
* Routes: `GET https://be.wizzair.com/29.19.0/Api/asset/map?languageCode=en-gb` (city
  `connections`). BUD has 97 destinations, BTS 39, VCE 36, TSF 9, LJU 2 (SKP, TGD). **No ZAG,
  no VIE** (Wizz left Vienna).
* Fares: `POST …/Api/search/timetable` with body `{"flightList":[{"departureStation":"BUD",
  "arrivalStation":"IST","from":"2027-03-01","to":"2027-03-31"},{return leg optional}],
  "priceType":"regular","adultCount":1,"childCount":0,"infantCount":0}`. It returns the
  cheapest fare per day plus all departure times, in the **origin's currency** (HUF for BUD).
  Max window is about 31 days (45 days → 400). Only 2 legs per call (outbound + return).
* **Gotcha:** after the first call the server sets `RequestVerificationToken`. Later calls on
  the same session fail with `400 {"handlerError":"InvalidProtocol"}` unless the token is
  echoed in the `X-RequestVerificationToken` header. The script handles this.
* `smartSearchCheapestFlights` (an old "anywhere" endpoint) → 404. Kasada (`x-kpsdk`) protects
  the website, but not these API calls.
* Data: regular (non-Discount-Club) fare, no bags, no arrival time.

**Usage / samples**
```
$ python3 ryanair_wizz.py anywhere --from ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --airlines FR \
      --dates 2027-03-01..2027-03-10
AL  FROM  TO   CITY        DEPART            ARR    FLIGHT  PRICE  CUR  EUR
FR  VIE   BNX  Banja Luka  2027-03-08 14:15  15:10  FR9753  18.99  EUR  18.99
FR  BTS   MXP  Milan       2027-03-08 06:55  08:30  FR5733  18.99  EUR  18.99
FR  ZAG   BSL  Basel       2027-03-05 15:10  16:45  FR5862  22.99  EUR  22.99
FR  VIE   BGY  Bergamo     2027-03-07 08:55  10:20  FR7360  23.99  EUR  23.99 ...

$ python3 ryanair_wizz.py anywhere --from BUD,BTS --airlines W6 --to IST,SAW,BGY,MXP,LTN,WAW,AUH,DXB,BCN,ARN,CPH,OSL \
      --dates 2027-03-01..2027-03-05 --return 2027-03-20..2027-03-25
W6  BTS  WAW  2027-03-04 07:50  RETURN 2027-03-21 13:00   45.98 EUR    45.98
W6  BUD  WAW  2027-03-01 06:20  RETURN 2027-03-20 08:10   17380 HUF    47.08
W6  BUD  MXP  2027-03-01 08:25  RETURN 2027-03-21 06:10   20480 HUF    55.47
W6  BUD  IST  2027-03-02 05:00  RETURN 2027-03-23 09:55   37080 HUF   100.44
W6  BUD  AUH  2027-03-01 13:05  RETURN 2027-03-21 21:55  141180 HUF   382.41

$ python3 ryanair_wizz.py calendar --from BUD --to IST --airlines W6 --dates 2027-03-01..2027-03-07
$ python3 ryanair_wizz.py routes --from ZAG,BUD,LJU
```
Round-trip mode (`--return`) uses Ryanair `roundTripFares` (1 call per origin) and Wizz
outbound+return in one call. Other options: `--per-day`, `--max-price`, `--wizz-max-dests`.

### 3b. `positioning.py`: positioning + long-haul combiner (coordinator priority)

For each hub it pulls the cheapest Kiwi long-haul (hub→Japan, up to 40 itineraries). For each
home airport it pulls Ryanair/Wizz daily fares home→hub, **including same-city sibling
airports** (CRL↔BRU, BGY/LIN↔MXP, SAW↔IST, WMI↔WAW, BVA/ORY↔CDG, STN/LTN/LGW↔LHR,
NYO↔ARN, GRO↔BCN, CIA↔FCO, HHN↔FRA, FMM↔MUC, BTS↔VIE, EIN↔AMS, TRF↔OSL, MMX↔CPH). It
keeps pairs with a connection gap of `--buffer` (4 h, +3 h when a sibling airport is
involved) to `--max-gap` (30 h, which allows an overnight at the hub), then ranks by total.
`--direction back` does the mirror (Japan→hub→home). Use `--single-ticket` for a one-PNR
long-haul and `--checked-bags 1` to price a bag into the long-haul.

```
$ python3 positioning.py --home ZAG,VIE,BUD,TSF --to TYO,OSA --dates 2027-03-05..2027-03-12 --hubs BRU,IST,MXP
TOTAL EUR  HOME  HUB  POSITIONING                     POS DEP      POS EUR  GAP H  LONG-HAUL            LH EUR  LH FLAGS
352.99     TSF   BRU  FR TSF-CRL (+ground CRL<->BRU)  03-11 08:45  25.99    24.8   BRU-PVG-NRT          327.0
358.39     BUD   BRU  W6 BUD-CRL (+ground CRL<->BRU)  03-11 06:15  31.39    25.9   BRU-PVG-NRT          327.0
360.99     ZAG   BRU  FR ZAG-CRL (+ground CRL<->BRU)  03-04 17:50  33.99    15.3   BRU-PVG-NRT          327.0
363.99     VIE   BRU  FR VIE-CRL (+ground CRL<->BRU)  03-11 09:35  36.99    23.8   BRU-PVG-NRT          327.0
417.99     VIE   MXP  FR VIE-MXP                      03-09 06:00  23.99    13.2   MXP-BCN-BRU-PVG-NRT  394.0   self-transfer
442.04     BUD   IST  W6 BUD-IST                      03-10 05:00  69.04    26.2   IST-TAS-ICN-KIX      373.0   self-transfer
```
(8 hubs and 5 home airports took ≈4 min.) Caveats: ground transfer cost and time are not
included (CRL→BRU is about 1 h by bus). Positioning fares exclude bags. Wizz arrival time is
estimated (`--wizz-block 3` h).

## 4. AZair.eu (`azair.py`)

**Method.** `GET https://www.azair.eu/azfin.php?searchtype=flexi&isOneway=oneway|return&srcAirport=Zagreb [ZAG] (+LJU,GRZ)&srcap0=LJU&srcap1=GRZ&dstAirport=Anywhere [XXX]&anywhere=true&depdate=…&arrdate=…&minDaysStay=…&maxDaysStay=…&maxChng=0-3&currency=EUR&lang=en&…`
(full parameter set in the script). Airport labels must match AZair's names
(`static*.azair.us/www-azair-eu-assets/js/airports_array.js`, e.g. `London (Stansted) [STN]`).
The script downloads and caches that list. Results are parsed from `div.result` (legs,
airline, flight number, leg price, `span.checked[data-age]` = hours since the price was
checked, total). The always-present strings "Letiště neexistuje / nespravne datum" are hidden
form-validation templates, not errors.

**Findings (important):**
* **Stale data:** price ages of 649 h and **≈6 160–6 190 h (≈8.5 months)** for Nov 2026
  flights. Example: AZair had ZAG→STN 6 Nov 19:50 €36.99, while Ryanair live shows
  19:05 €67.34 (both time and price changed).
* **Horizon:** the form only offers months up to 2027-01. Queries for Feb–Mar 2027 and even
  Dec 2026 returned "No results".
* **Throttling:** about half the queries answer "Our search engine is not able to answer your
  query in a timely manner" instantly. The script retries with back-off (20 s, 40 s) and
  usually succeeds on attempt 2–3. Space queries ≥10 s apart.
* Value: discovering LCC routes and self-transfer LCC combos (it builds 1-change combos like
  ZAG–BGY–NRN). **Re-price everything** with `ryanair_wizz.py` or the airline site.

```
$ python3 azair.py --from ZAG,LJU,GRZ --anywhere --dates 2026-11-01..2026-11-08
FROM  TO   DATE        DEP    DURATION/CHANGES    AIRLINES         FLIGHTS        EUR    AGE_H
ZAG   STN  2026-11-06  19:50  2:30 h / no change  Ryanair          FR3104         36.99  6161
LJU   LGW  2026-11-07  17:10  2:25 h / no change  easyJet          U28842         50.49  5811
ZAG   AMS  2026-11-08  06:10  4:50 h / 1 change   Ryanair,easyJet  FR2189 U27840  72.14  6161
$ python3 azair.py --from ZAG,VIE,BUD --to BGY,MXP,CRL,STN --dates 2026-11-05..2026-11-25 --return --min-days 5 --max-days 10 --max-changes 0
```

## 5. Aviasales (`aviasales.py`)

* Public cached endpoints are **gone**: `min-prices.aviasales.ru/calendar_preload` and
  `/price_matrix` → 404; `map.aviasales.ru/prices.json` → 302. `api.travelpayouts.com/v2/prices/latest`
  and `/aviasales/v3/prices_for_dates` → **401 Unauthorized** (token required).
* The website (`https://www.aviasales.com/search/VIE1003TYO1`; RT `ZAG1003TYO24031`, i.e.
  origin + DDMM + dest + [DDMM] + pax) calls `POST tickets-api.aviasales.com/search/v2/start`
  with **`x-aws-waf-token`**, then polls `POST tickets-api.us-east-2.aviasales.com/search/v3.2/results`.
  So it is **browser-only**.
* **The search only starts after the cookie banner is answered.** The script keeps clicking
  "OK". Each results chunk carries the 10 "best" tickets plus `cheapest_ticket` and
  `meta` (`total_tickets_count`, `first_ticket_price`, `cheapest_baggage_ticket_price`).
  Rewriting the request to raise `limit` broke the search (WAF), so it isn't done.
* There's also a cached nearby-dates ribbon: `GET tickets-api.aviasales.com/search/prices/ribbon?origin=VIE&origin_type=city&destination=TYO…`.
* Data: live OTA offers. Strong on OTA self-transfer packages (Mytrip/Flightnetwork sell
  FR+MU; Lucky2Go DE+AI).

```
$ python3 aviasales.py --from VIE --to TYO --depart 2027-03-10
[aviasales] total tickets=612 cheapest=466 cheapest_with_baggage=510 (EUR)
EUR     SELLER         BAGS  SELF-TR  AIRLINES  ITINERARY
465.66  Mytrip.com           True     FR,MU     VIE-MAD-PVG-HND 03-10 06:00->03-11 15:50
469.57  Lucky2Go             False    DE,AI     VIE-FRA-DEL-HND 03-10 17:10->03-13 05:55
470.0   Kiwi.com       0     True     OS,LH,MM  VIE-FRA-ICN-NRT 03-10 11:20->03-11 15:15
550.84  Turna.com      1     False    CA        VIE-PEK-HND 03-10 13:00->03-11 14:25
568.13  Ubfly          2     False    CA        VIE-PEK-HND 03-10 13:00->03-11 12:50
```
Rate behaviour: about 8 page loads, no block. One run occasionally didn't start the search
(the consent banner hadn't been clicked yet); the retry/consent loop fixes this.

## 6. Booking.com Flights (`booking_flights.py`)

* `curl https://flights.booking.com/flights/…` → **202** (AWS-WAF JS challenge page). In
  Playwright the challenge auto-solves (`&chal_t=…`) and the page calls
  `GET https://flights.booking.com/api/flights/?type=ONEWAY|ROUNDTRIP&adults=1&cabinClass=ECONOMY&from=VIE.AIRPORT&to=TYO.CITY&depart=2027-03-10[&return=…]&sort=CHEAPEST&currency=EUR&locale=en-gb…`.
* JSON: `flightOffers` (15/page, sorted cheapest), `priceBreakdown` (total/base/tax/fee),
  `segments[].legs[]` (carriers, flight numbers), `travellerCheckedLuggage`,
  `isVirtualInterlining`, and `aggregation` (totalCount, min price per stops / airline).
* Inventory is Etraveli's (the same engine as Gotogate/Mytrip, which block scripts directly).
* Samples: VIE→TYO OW 10 Mar: €510.87 (OS/LH + Peach via ICN, self-transfer), €511.91
  (FR+MU via MAD). ZAG→TYO RT 10/24 Mar: 1 571 offers, cheapest €1 211.73 (OU+EVA via
  VIE–TPE, 2 bags). ZAG-origin round trips are expensive.

```
$ python3 booking_flights.py --from ZAG --to TYO --depart 2027-03-10 --return 2027-03-24
== Booking.com ZAG->TYO 2027-03-10 / 2027-03-24: 1571 offers; min price by stops {1: 1255.51, 2: 1211.73, 3: 1211.73}
EUR      BAGS  SELF-TR  AIRLINES          ITINERARY
1211.73  2     False    OU,BR | BR,OU     ZAG-VIE-TPE-NRT 03-10 08:10->03-11 19:20 | NRT-TPE-VIE-ZAG ...
1255.51  1     False    LX,NH | LH        ZAG-ZRH-NRT 03-10 08:45->03-11 10:20 | HND-MUC-ZAG ...
1268.52  0     True     OU,HO | ZE,KL,FR  ZAG-BRU-PVG-NRT ... | NRT-ICN-AMS-FCO-ZAG ...
```

## 7. FlightConnections (`flightconnections.py`)

* curl → 202 with an empty body (AWS-WAF). It works in Playwright.
* Airport page `https://www.flightconnections.com/flights-from-zagreb-zag` (the slug comes
  from `/airports_url.php?lang=en&iata=zag` → `{"a":"Zagreb (ZAG)","c":334}`). Parse
  `#popular-destinations a.popular-destination` (`data-a`, "N flights / month", flag alt =
  country). The airlines list is in `/airlines_url.php?lang=en&depAps=334&desAps=`. Destination
  coordinates/ids are in `/rt334.json?...`. No prices.
* `to NRT` gives NRT's nonstop partners (filtered to Europe/Middle East): DOH 62/month, IST 45,
  WAW 41, DXB 37, AUH 31, FRA 31, HEL 28, VIE 18.
* `from ZAG` lists 66 nonstop destinations (FRA 142/month, MUC 112, … IST 80, DOH 18, DXB 17,
  SAW 12) and 24 airlines. Air China is listed, but the ZAG–PEK route page says "no direct
  flights", and Kiwi finds no nonstop ZAG→China in Mar 2027.
* The `route` mode's airline list comes from `airlines_url.php` with depAps+desAps, which
  includes 1-stop carriers, not only nonstop ones.

```
$ python3 flightconnections.py to NRT --filter-country Austria,Germany,Italy,Hungary,Croatia,Slovenia,Czechia,Poland,Finland,Turkey,"United Arab Emirates",Qatar
$ python3 flightconnections.py from ZAG LJU VIE
$ python3 flightconnections.py route VIE NRT
```

## 8. Skyscanner (blocked, so check manually)

* `curl https://www.skyscanner.net/transport/flights/zag/tyoa/270310/270324/` → **307 to
  `/sttc/px/captcha-v2/…`** (PerimeterX).
* Headless Chromium (realistic UA, locale, consent clicked) also lands on the captcha page.
  The in-page APIs `POST /g/radar/api/v2/web-unified-search/`, `/g/search-intent/v1/pricecalendar`
  and `/pricecalendar/month` return **403**. Only a hotel cross-sell endpoint
  (`/g/michelin/api/search/v1`) answered 200.
* No captcha-solving was attempted. **Use the user's own browser.** Useful manual URL
  patterns (Skyscanner's usual formats; could not be re-verified from here because of the
  captcha): day view `…/transport/flights/zag/tyoa/270310/270324/`;
  whole-month view `…/transport/flights/zag/tyoa/?oym=2703&iym=2703` (or pick "Cheapest
  month" in the date picker); "Everywhere" `…/transport/flights-from/zag/`. Try
  `tyoa`/`osaa` city codes and nearby origins (`vie`, `bud`).

## 9. Trip.com (blocked, so check manually)

* `https://www.trip.com/flights/showfarefirst?dcity=vie&acity=tyo&ddate=2027-03-10&triptype=ow&class=y&quantity=1&locale=en-XX&curr=EUR`:
  curl gets a "Challenge Validation" HTML (1.8 KB). Headless Chromium is redirected to
  `verify.trip.com/static/tripVerify.html` ("please complete the verification test"). The
  homepage and its config APIs load fine, so only flight search is gated.
* Locale/currency price differences could not be tested. Manual tip: compare
  `locale=en-XX&curr=EUR` with other locales (e.g. `ja-JP`, `zh-HK`) in a browser. Trip.com
  fares also show in Kayak/momondo as provider **CTRIPAIR** (e.g. VIE–BRU–PVG–NRT €471).

## 10. Others (quick probes)

* **Wego** search URL → 403. **Expedia** search URL → 429. **lastminute.com** → 403.
  **fly4free.com** homepage → 403 (its RSS works; see orchestrator `deals.py`).
* **eDreams / Opodo** homepages → 200 (JS apps). Not built, because their fares already come
  through Kayak/momondo (provider OPODO / EDREAMS, e.g. BUD–PVG–NRT MU RT €660 via Opodo).
* **Gotogate / Mytrip** → 403. Use Booking.com Flights (same Etraveli engine) or the
  Aviasales/Kayak providers ("Mytrip.com").
* **Skiplagged** web → 403. Its MCP works (orchestrator).
* **Dohop** → JS app; `/flights/VIE/TYO/2027-03-10` → 404. Not pursued.
* **Airlines:** Turkish (HTTP/2 INTERNAL_ERROR / 20 s timeout / 502), Qatar (Akamai "Access
  Denied"), LOT (3 KB JS shell), Finnair (loads in headless; not automated), Air China
  (`airchina.com.cn` 200 HTML; not automated), China Eastern (`us.ceair.com` → /en/; not
  automated), Emirates (307 to /us/english/; not automated). Their fares are visible through
  Kiwi/Kayak/Aviasales/Booking, which is enough for price discovery. **Book direct with the
  airline when it's the same price** (better protection for disruptions).

## Recommended workflow for the future agent

1. **Discover the cheap long-haul origin:**
   `kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates <window>` plus
   `kiwi_graphql.py origin-scan --to TYO,OSA --origins <20–25 hubs>` (both directions, and
   with `--checked-bags 1`). Cross-check the top 3 hubs with `kayak.py` (momondo.de),
   `aviasales.py`, `booking_flights.py`, and the orchestrator's MCP (Kiwi/Skiplagged) and
   Google/Matrix (05).
2. **Price positioning:** `positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS
   --hubs <top hubs> --dates <window>` (and `--direction back`). For single legs use
   `ryanair_wizz.py anywhere/calendar`. Use AZair only for route ideas (stale).
3. **Compare with single-ticket options from VIE/BUD** (`kayak.py --from ZAG,VIE,BUD …`,
   `kiwi_graphql.py search --from ZAG@300 …`), including bags. Self-transfer savings of
   €50–100 may not be worth the missed-connection risk.
4. **Manual checks in the user's browser:** Skyscanner (incl. "whole month" and
   "Everywhere"), Trip.com (with a couple of locales), Google Flights (05), and the airline
   sites of the winning carrier (Air China, China Eastern, Juneyao, Turkish, Qatar, LOT,
   Finnair) before buying.

## Caveats

* Self-transfer / virtual interlining (Kiwi KIWIVI*, Mytrip FR+MU, Booking `isVirtualInterlining`)
  means separate tickets: bags must be rechecked, landside transit/visa rules apply at the
  connecting airport (check current China/Korea/Gulf entry & transit rules for the passport),
  and a missed connection is the traveller's risk unless the seller guarantees it.
* LCC fares (Ryanair/Wizz/AZair) are fare-only; add the bag fees per leg (check the airline's
  current price for the date; they vary by route and day).
* Kiwi/Kayak "cheapest" sometimes relies on very long layovers (e.g. arriving 01:00).
  Inspect the times.
* All prices were observed on 2026-10-04 and change constantly; re-run before deciding.
