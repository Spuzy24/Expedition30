# Tools reference (`flights/scripts/`)

> All tested live from the cloud container on 2026-10-04. Deep notes: `research/05-tools-google-matrix.md`
> (Google Flights, ITA Matrix) and `research/06-tools-ota-meta.md` (everything else).
> Every script has `--help` with examples, prints a price-sorted table, and most accept `--json PATH|-`.
> Dates: `YYYY-MM-DD`; ranges `A..B` (Kiwi also `D+-3`). Prices are 1 adult, EUR, unless set.

## 0. Setup
```bash
bash flights/scripts/setup.sh     # pip deps, Playwright 1.56 pin, Chromium NSS proxy-CA, smoke tests
```
- Core scripts need only `requests` (+ `beautifulsoup4`/`lxml` for AZair). Browser scripts need `playwright==1.56.0`, which matches Chromium build 1194 preinstalled in `/opt/pw-browsers`. **Never run `playwright install`.**
- Chromium's NSS trust store may start empty in a fresh container, causing ERR_CERT_AUTHORITY_INVALID. `setup.sh` adds the agent-proxy CA (trust only; verification stays on).

## 1. Which tool for which job
| Job | Tool(s) |
|---|---|
| Cheapest single tickets from many home-area airports | `kayak.py` (momondo.de), `mcp_flights.py kiwi`, `kiwi_graphql.py search`, `aviasales.py`, `booking_flights.py`, `mcp_flights.py sk`, `gflights.py search`, `matrix.py --carriers` |
| Which European city has the cheapest long-haul to Japan | `kiwi_graphql.py per-city` / `origin-scan`, `gflights.py sweep --origins europe` |
| Positioning (home → hub on Ryanair/Wizz) + long-haul combos | `positioning.py` (both directions), `ryanair_wizz.py anywhere/calendar` |
| Cheapest dates | `gflights.py calendar/grid`, `kiwi_graphql.py calendar`, `matrix.py calendar`, `mcp_flights.py skcal` |
| Fare construction, routing control, open-jaw, fare levels | `matrix.py` (routing/ext codes, `--slice`, `--no-avail`) |
| Cheapest *seller* of a known itinerary | `kayak.py --show-links`, `booking_flights.py`, `aviasales.py` (+ manual Trip.com/Skyscanner/airline) |
| Deals / error fares | `deals.py` |
| Route discovery (who flies where) | `flightconnections.py`, `ryanair_wizz.py routes` |
| Ground cost/time to departure airports | `flixbus_ground.py` |
| Price log, total-cost ranking, FX | `quotes.py`, `fx.py` |

## 2. Google Flights: `gflights.py` (no browser; internal RPC)
Global options go **before** the subcommand: `--gl HR --curr EUR --hl en --sleep 3 --quiet`.
Codes: `TYO`=NRT,HND · `OSA`=KIX,ITM · `JPN`=8 Japanese airports · presets `zagreb` (20 airports) and `europe` (60).
```bash
python3 gflights.py search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26 [--expand 3]
python3 gflights.py search --from zagreb --to TYO,OSA --date 2027-02-09 --per-origin --out r.json
python3 gflights.py search --from BUD --to OSA --date 2027-02-09 --stops 1 --via IST,DOH --bags 1
python3 gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 [--stay 14] [--heatmap]
python3 gflights.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21
python3 gflights.py explore --from ZAG --region japan --month 2 --duration 2weeks
python3 gflights.py sweep --origins europe --to TYO,OSA --start 2027-02-01 --end 2027-03-31 --stay 14 \
        --cache flights/searches/<trip>/gf_sweep.json --details 5      # ~20–25 min, resumable
```
- Search options: `--bags N`, `--carry-on`, `--exclude-basic`, `--stops`, `--via`, `--sort cheapest|best|…`, `--top`, `--no-self-transfer`, `--per-origin`, `--batch 7`, `--backend rpc|html|browser|auto`. Up to ~300 itineraries per query, 0.5–4 s.
- **Blind spot:** carries **no China Eastern / Air China / China Southern** on Europe→Japan (B1: `--via PVG` → 0). Never use it alone.
- Calendar/explore/sweep prices are Google's cache. Re-check with `search`. Query TYO and OSA separately in calendars (the script does). Stay ranges are looped per length.
- Rate limits: ≥3 s between calls (default), 6 s in sweeps. Bursts → HTTP 429 → reCAPTCHA; recovers after ~15 min. The script backs off and stops cleanly.
- `gl`/`curr` (point of sale) never changed a price (10 countries tested).
- `gflights_calendar.py` is a shortcut for calendar/grid.

## 3. ITA Matrix: `matrix.py` (no browser; JSON API)
```bash
python3 matrix.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --carriers MU,CA,CZ,KE,TK,QR,EK,LO,AY
python3 matrix.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --route "MU+" --route-ret "MU+" [--no-avail]
python3 matrix.py search --slice VIE:TYO:2027-05-12 --slice OSA:VIE:2027-05-26          # open-jaw
python3 matrix.py search --from VIE --to TYO --date 2027-03-10 --ext "-REDEYES" --minus 1 --plus 1
python3 matrix.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 12-14 [--sales-city ZAG]
```
- **The default answer is pruned** (6–17 solutions, 4–5 carriers, varies run to run). B1 default €1,083 vs `MU+` €715. **Always use `--carriers`** (~40 s per carrier) or routing codes.
- `--no-avail` shows fare levels without confirmed seats (e.g. CA €574 OW ex-VIE). These are **leads**, not bookable prices.
- Routing (per slice): `CA+` (≥1 CA flight), `C:CA` / `O:EK` = exactly ONE segment marketed/operated, `X:IST` connect at IST. `N` = nonstop per Google's docs (it returned 0 on a date without a nonstop; confirm on a date with one). `--max-stops 0` or `C:OS` also work.
- Extension (verified): `MAXSTOPS 1`, `MINCONNECT 120`, `MAXCONNECT 240`, `-AIRLINES TK`, `ALLIANCE STAR-ALLIANCE`, `-CODESHARE`, `-REDEYES` (shows a totally different set!), `-OVERNIGHTS`, `-PROPS`, `F BC=K`. Values starting with `-` are accepted.
- Sales city made no difference (8 cities, identical €1,123). 15–60 s per query; default pacing 5 s. Browser fallback is flaky; use HTTP.
- No LCCs, no self-transfer, no NDC/web-only fares; often pricier than GF for the same airline.

## 4. Kiwi.com
### 4a. `mcp_flights.py kiwi` (public MCP, `https://mcp.kiwi.com`)
```bash
python3 mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD TYO,OSA 2027-05-12 --flex 3 --ret 2027-05-26 --ret-flex 3
python3 mcp_flights.py kiwi BUD TYO 2027-01-15 --date-to 2027-02-15 --nights 12-16 --bags 1
python3 mcp_flights.py kiwi ZAG TYO,OSA 2027-01-18 --date-to 2027-01-29 --only-airlines CA --log tyo-2027-01
```
Options: `--flex/--ret-flex` (≤10), `--date-to/--ret-to`, `--nights A-B`, `--bags N`, `--cabin-bag`,
`--no-self-transfer`, `--max-stops`, `--max-hours`, `--only-airlines`, `--exclude-airlines`, `--via`,
`--not-via`, `--not-via-countries`, `--sort`, `--json`, `--log TRIP [--log-top 3]`.
- **~15 results per call**, so carriers get crowded out. Run per-carrier passes (`--only-airlines CA`, …).
- **Bag data is wrong for Chinese carriers** (says 0 checked; the MU fare includes 2×23 kg). Don't use `--bags 1` rankings for MU/CA without cross-checking.
- RT pricing for Air China ex-ZAG was implausible (€1,500+ vs €625 OW). Cross-check.
- Same server is registered in `.mcp.json` as MCP server `kiwi` (tool `search-flight`, dates dd/mm/yyyy).

### 4b. `kiwi_graphql.py` (Kiwi website GraphQL, no key)
```bash
python3 kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates 2027-05-10..2027-05-16 [--return-dates …] [--checked-bags 1]
python3 kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates 2027-05-10..2027-05-16
python3 kiwi_graphql.py origin-scan --to TYO,OSA --dates 2027-05-10..2027-05-16 --origins ZAG,VIE,BUD,IST,BRU,MXP,…
python3 kiwi_graphql.py calendar --from ZAG --to TYO --dates 2027-02-01..2027-03-31
python3 kiwi_graphql.py places --near ZAG --radius 400
```
- Location forms: `ZAG`, `ZAG,VIE`, `ZAG@400` (radius km, expanded via `places`), `City:tokyo_jp`, `Country:JP`, `Continent:europe`.
- `origin-scan` = 1 query per hub (~5 s each), the fair way to rank hubs. `per-city` = cheapest European origin per Japanese city in one call. A plain `Continent:europe` search is thin; don't trust it.
- Flags: `--no-self-transfer`, `--max-stops`, `--checked-bags`, `--hand-bags`, `--nights`, `--hacks` (hidden-city/throwaway; off by default, needs user consent).
- `--checked-bags 1` gave odd, high results in B1. Cross-check with the MCP / OTAs.

## 5. `mcp_flights.py sk|skcal|sksweep` (Skiplagged public MCP)
```bash
python3 mcp_flights.py sk ZAG TYO 2027-05-12 --ret 2027-05-26 --limit 30 [--no-hidden-city] [--no-vi]
python3 mcp_flights.py skcal BUD TYO 2027-05-12 --ret 2027-05-26      # price per date pair (fixed stay)
python3 mcp_flights.py sksweep ZAG 2027-05-12 --ret 2027-05-26        # cheapest destinations "anywhere"
python3 mcp_flights.py tools sk                                       # raw tool schemas
```
- Prices are USD. Routes show `~` at an airport change (e.g. `STN~LHR`). Type shows `virtual-interline`/hidden-city.
- RT route strings concatenate both directions. Hidden-city results = ToS risk; use `--no-hidden-city` by default.

## 6. momondo / Kayak: `kayak.py` (no browser; poll API)
```bash
python3 kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26
python3 kayak.py --site www.kayak.de --from ZAG --nearby --to TYO,OSA --depart 2027-03-10 --flex 3 --show-links
python3 kayak.py --from VIE --to TYO --depart 2027-03-08,2027-03-10 --return 2027-03-24 --pages 2 --json out.json
```
- **Best performer in B1** (€686 MU+CZ with 2 bags via Opodo, a combo nobody else showed). 15–30 s/search; keep ≥3 s apart.
- Sites: momondo.de/kayak.de = EUR (use these); .com = USD. Different sites show slightly different seller sets.
- Provider codes: `KIWIVI`/`KIWIVILCC`/`SKYPICKER` = Kiwi (self-transfer), `CTRIPAIR` = Trip.com, `OPODO`/`EDREAMS`, `BOOKINGFLIGHTS`, `JUSTFLY`, airline codes. BAGS column = included checked bags (or FEE/UNKNOWN).

## 7. Browser-based OTAs (Playwright, ~25–45 s each)
```bash
python3 aviasales.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26 [--show-urls]
python3 booking_flights.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26
```
- Aviasales: many small OTAs + packaged self-transfers (Mytrip FR+MU, Lucky2Go). Prints "cheapest_with_baggage".
- Booking.com Flights = Etraveli inventory (Gotogate/Mytrip/Flightnetwork, which block bots directly). High-risk seller tier.

## 8. Positioning: `ryanair_wizz.py` and `positioning.py`
```bash
python3 ryanair_wizz.py anywhere --from ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --dates 2027-05-01..2027-05-10
python3 ryanair_wizz.py anywhere --from ZAG,BUD,VIE --to IST,SAW,BGY,MXP,STN,CRL,BRU,WAW,HEL,ARN --dates … --return …
python3 ryanair_wizz.py calendar --from ZAG --to BGY --dates 2027-05-01..2027-05-31
python3 ryanair_wizz.py routes --from ZAG,BUD,LJU
python3 positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --to TYO,OSA --dates 2027-05-08..2027-05-14 \
        --hubs BRU,IST,MXP,BGY,WAW,HEL,FRA,MUC,BCN,MAD,CDG,AMS,PRG,ARN,CPH,STN,DUB,FCO [--checked-bags 1] [--single-ticket]
python3 positioning.py --direction back --home ZAG,VIE,BUD --to TYO,OSA --dates 2027-05-24..2027-05-28
```
- Ryanair/Wizz = **fare only** (small personal item, no cabin/checked bag). Wizz fares come in local currency (converted). **Wizz has no ZAG/VIE; Ryanair has none from LJU/GRZ.**
- `positioning.py`: buffer default 4 h (+3 h for sibling airports CRL↔BRU, BGY↔MXP, SAW↔IST, WMI↔WAW, NYO↔ARN, …), `--max-gap 30` h allows an overnight. Ground transfer between sibling airports is **not** costed (CRL→BRU ~1 h bus). Wizz arrival time is estimated (`--wizz-block 3`). ~1–4 min.
- Only FR/W6 positioning. For TK/PC→IST, LO→WAW, OU/JU legs use `mcp_flights.py kiwi ZAG IST <date>`.

## 9. Others
```bash
python3 azair.py --from ZAG,LJU,GRZ --anywhere --dates 2026-11-01..2026-11-08     # LCC route IDEAS only
python3 flightconnections.py to NRT --filter-country Austria,Hungary,Croatia,Turkey,Qatar
python3 flightconnections.py from ZAG LJU VIE
python3 flixbus_ground.py --date 2027-05-11 [--from Ljubljana] [--to "Vienna Airport" Budapest]
python3 flixbus_ground.py --drive --home 15.9819,45.8150
python3 deals.py --days 60 [--region] [--any-asia] [--json]
python3 fx.py 2350 PLN [--card-fee 1.5]
```
- AZair prices are months old and it has no results beyond ~3 months ahead. Re-price on ryanair_wizz.py.
- `deals.py` reads 22 RSS feeds (fly4free.pl Japan tag, travel-dealz Japan, utazomajom.hu…). Secret Flying/Jack's need a browser/email.

## 10. Quote log: `quotes.py`
```bash
python3 quotes.py add --trip tyo-2027-05 --source momondo --seller Opodo --origin BUD --dest KIX \
   --return-from KIX --out 2027-05-12 --ret 2027-05-26 --price 686 --carriers MU,CZ --stops 1 --via PVG/CAN \
   --bags-included 2x23 --risk low --link "<url>" --notes "MU out, CZ back, one ticket"
python3 quotes.py list --trip tyo-2027-05 --top 20      # ranked by per-person total incl. ground (searches/ground.json)
python3 quotes.py best --trip tyo-2027-05               # best per origin→destination
```
Total = fare×(1+card fee) + bag cost + extras + ground (round trip from `ground.json`; open-jaw on the
home side = half of each). Everything is per person; `--per total --pax N` divides. `mcp_flights.py --log TRIP` auto-adds.

## 10b. Price monitoring: `monitor.py`
```bash
python3 monitor.py flights/searches/<trip>/watch.json            # run all checks, print summary + ALERT lines
python3 monitor.py flights/searches/<trip>/watch.json --history  # stored history per check
```
Watch file lists checks as normal toolkit commands plus how to get JSON (`"json": "file:--json"` for
kayak/kiwi_graphql/aviasales/booking/positioning, `"file:--out"` for gflights/matrix, `"stdout:--json"`
for mcp_flights). It extracts the min EUR price per check and alerts on a new low or ≤ `threshold_eur`.
Example + Routine prompt: playbook §9. Tested 2026-10-04 (4 checks, 77 s).

## 11. Manual-only sources (give the user exact URLs)
- Skyscanner: `https://www.skyscanner.net/transport/flights/zag/tyoa/270512/270526/` (whole month `?oym=2705&iym=2705`; Everywhere `/transport/flights-from/zag/`)
- Trip.com: `https://www.trip.com/flights/showfarefirst?dcity=bud&acity=tyo&ddate=2027-05-12&rdate=2027-05-26&triptype=rt&class=y&quantity=1&locale=en-XX&curr=EUR` (also try other locales)
- Air China: `https://www.airchina.at/AT/GB/Home` (airchina.com blocks cloud IPs); book Fri–Sun for ≤6% off.
- China Eastern `ceair.com`, Turkish, Qatar, LOT, Finnair, Korean Air: their own sites.
- Secret Flying origin pages (Zagreb/Ljubljana/Vienna/Budapest/Belgrade).

## 12. When things break
| Symptom | Fix |
|---|---|
| Browser pages fail with ERR_CERT_AUTHORITY_INVALID | `bash flights/scripts/setup.sh` (NSS proxy CA) |
| Playwright "Executable doesn't exist" | `pip install playwright==1.56.0` (match /opt/pw-browsers build); set `CHROMIUM_PATH` if needed; never `playwright install` |
| Google Flights 429 / "unusual traffic" | Stop GF for 15+ min; continue with other sources; raise `--sleep` |
| Google JS bundles blocked in headless (ERR_BLOCKED_BY_ORB) | `gflights.py --backend browser` already routes them via requests |
| Matrix returns few/odd solutions | Pruning: use `--carriers` / `--route "XX+"` / `--ext -REDEYES` variants |
| Kiwi MCP/Skiplagged MCP errors | Retry once; check `python3 mcp_flights.py tools kiwi`; schema may have changed. Adapt args |
| Wizz `400 InvalidProtocol` | Token echo handled in script; if the API version changed, it's scraped from wizzair.com; re-run |
| AZair "busy" | Script retries with back-off; space queries ≥10 s |
| A site starts returning 403/captcha | Treat as manual-only; note it in `sources.md` with the date |
| An internal API changes shape | Capture the site's own XHR with Playwright (see `_browser.py` response capture), update the script, note the date in the research file |
