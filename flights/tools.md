# Tools reference (`flights/scripts/`)

> All tested live from the cloud container on 2026-10-04 (after QA + a full dry run). Deep notes:
> `research/05-tools-google-matrix.md` (Google Flights, ITA Matrix), `research/06-tools-ota-meta.md` (the rest),
> `research/08-scripts-qa.md` (QA, bag anomaly), `research/09-review-resolution.md` (what was fixed).

**Conventions**
- **Working directory.** Commands below are written **from `flights/scripts/`** (`cd` there). From the repo root, use `S=flights/scripts; python3 $S/<script>`. Paths that start with `flights/` are repo-root paths.
- **Output.** Every script has `--help` with examples and prints a price-sorted table. JSON goes to `--json PATH|-` for most scripts, `--out PATH` / `--json-only` for gflights and matrix, and `--json` (a flag that prints to stdout) for mcp_flights. Parent directories are created automatically.
- **Dates.** `YYYY-MM-DD`; ranges are `A..B` (Kiwi also accepts `D+-3`).
- **Stay length is counted differently by different tools.**
  - gflights/matrix `--stay` = days between the two departure dates.
  - Kiwi `--nights` = nights at the destination. Europe→Japan lands +1 day, so `--stay 14` ≈ `--nights 13`.
  - Return dates are LOCAL departure dates from Japan.
  - Compare tools on exact dates, not on stay lengths.

**Passengers: per person or party total? (tested with `--adults 2` on 2026-10-04)**

| Script | `--adults 2` price is… | Table header |
|---|---|---|
| `kayak.py` (momondo/Kayak) | **per person** | `EUR/pp` |
| `kiwi_graphql.py` (search, calendar, per-city, origin-scan) | **party total** (the cheapest fare may not have 2 seats) | `EUR total (N pax)` + `EUR/pp` |
| `mcp_flights.py kiwi` / `sk` | party total | (logged with `--pax N --per total`) |
| `aviasales.py`, `booking_flights.py` | party total | `EUR total` + `EUR/pp` |
| `gflights.py search` (insights double too) | party total | `EUR total` + `EUR/pp`; calendar/grid/explore "assumed total" (not verified) |
| `matrix.py search` rows | party total | `EUR total` + `EUR/pp` (the min/carrier lines and the calendar are per person) |
| `positioning.py` | Kiwi total + N × FR/W6 fare | `TOTAL EUR total` + `EUR/pp` |
| `ryanair_wizz.py` | per person, 1 adult | n/a |

No script prices children or infants: check those on the seller's site. The cheapest bucket can have **one seat left**. For 2 travellers, Skiplagged's cheapest MU fare went from $806 to $2,516.

## 0. Setup
```bash
bash setup.sh            # pip deps, Playwright 1.56 pin, Chromium NSS proxy-CA, smoke tests incl. headless Chromium (~5 s)
bash setup.sh --full     # + one tiny LIVE request per core scraper with OK/FAIL (~30–90 s); scraper failures don't change the exit code
```
- **Requirements.**
  - Core scripts need only `requests`; AZair also needs `beautifulsoup4`/`lxml`.
  - Browser scripts need `playwright==1.56.0`, which matches Chromium build 1194 preinstalled in `/opt/pw-browsers`. **Never run `playwright install`.**
- **NSS trust store.** Chromium's NSS store may start empty, giving ERR_CERT_AUTHORITY_INVALID. `setup.sh` adds the agent-proxy CA (matched by fingerprint; verification stays on).
- **Exit code.** Non-zero means a required step failed. See §12.

## 1. Which tool for which job
| Job | Tool(s), best first |
|---|---|
| Cheapest single tickets from the home catchment | `kayak.py` (momondo.de), `kiwi_graphql.py origin-scan` / `search`, `mcp_flights.py kiwi`, `aviasales.py`, `booking_flights.py`, `mcp_flights.py sk`, `gflights.py search`, `matrix.py --carriers` |
| Which European city has the cheapest long-haul | `kiwi_graphql.py origin-scan` (RT with `--return-dates`), `per-city`, `gflights.py sweep --origins europe` (heavy) |
| Positioning (home → hub on Ryanair/Wizz) + long-haul | `positioning.py` (RT mode `--return-dates`), `ryanair_wizz.py anywhere/calendar` |
| Cheapest dates | `kiwi_graphql.py calendar --nights` (RT), `gflights.py calendar/grid`, `matrix.py calendar --route "MU+"`, `mcp_flights.py skcal` (return-flex only) |
| Fare construction, routing control, open-jaw, fare levels | `matrix.py` (routing/ext codes, `--slice O:D:DATE[:ROUTE]`, `--no-avail` = leads) |
| Cheapest *seller* of a known itinerary | `kayak.py --show-links`, `booking_flights.py`, `aviasales.py` (+ manual Trip.com/Skyscanner/airline) |
| Deals / error fares | `deals.py` |
| Route discovery (who flies where) | `flightconnections.py`, `ryanair_wizz.py routes` |
| Ground cost/time to departure airports | `flixbus_ground.py` |
| Price log, total-cost ranking, FX, monitoring | `quotes.py`, `fx.py`, `monitor.py` |

**Airport changes are marked everywhere.** Every route printer (kayak, kiwi_graphql, aviasales, booking, mcp_flights sk) marks a change of airport with `~`, e.g. `ZAG-CRL~BRU-PVG-KIX` means a bus from CRL to BRU. Round trips print as `out | back`. JSON has `airport_change: true/false`.

## 2. Google Flights: `gflights.py` (no browser; internal RPC)
Global options go before the subcommand (`--max-wait` also works after it): `--gl HR --curr EUR --hl en --sleep 3 --max-wait 60 --quiet`.

Codes and presets:
- `TYO` = NRT, HND
- `OSA` = KIX, ITM. UKB is excluded because it breaks calendars; add UKB explicitly to `search` if needed.
- `JPN` = 8 Japanese airports
- presets `zagreb` (20 airports) and `europe` (60 airports)

```bash
python3 gflights.py search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26 --bags 1 [--expand 3]
python3 gflights.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26      # single origin → price insights ("typical" range)
python3 gflights.py search --from BUD --to OSA --date 2027-02-09 --stops 1 --via IST,DOH --bags 1 --adults 2
python3 gflights.py calendar --from VIE --to TYO --start 2027-02-01 --end 2027-03-31 --stay 14 --bags 1 [--heatmap]
python3 gflights.py grid --from VIE --to NRT --depart 2027-03-01..2027-03-07 --return 2027-03-15..2027-03-21
python3 gflights.py explore --from ZAG --region japan --month 2 --duration 2weeks
python3 gflights.py sweep --origins europe --to TYO,OSA --start 2027-02-01 --end 2027-03-31 --stay 14 \
        --cache flights/searches/<trip>/gf_sweep.json --details 5      # ~20–25 min, resumable; optional (heavy)
```
- **Search options:**
  - `--bags N`, `--carry-on`, `--exclude-basic`, `--stops`, `--via`, `--sort cheapest|best|…`, `--top`;
  - `--no-self-transfer`, `--per-origin`, `--batch 7`, `--backend rpc|html|browser|auto`.
  - Up to ~300 itineraries per query, 0.5–4 s each. `grid` honours `--bags/--via/--max-price/--exclude-basic`.
- **Blind spot:** Google carries **no China Eastern, Air China or China Southern** on Europe→Japan (B1: `--via PVG` gives 0 results). Never use it alone.
- **Bags:** with `--bags 1`, prices are unreliable for LCCs (Scoot, ZIPAIR). Verify them on the airline site.
- **Cached prices:** calendar, explore and sweep show Google's cache. Re-check with `search`. One `--stay` length is 1–2 requests; a range like `12-16` loops 5× per city group, so avoid it.
- **Price insights** (the "typical" range and 60-day history) print under the table for **single-origin** searches only. Multi-origin batches return `{}`.
- **Rate limits:**
  - ≥ 3 s between calls (default), 6 s in sweeps.
  - Every back-off prints to stderr.
  - When total back-off would exceed `--max-wait` (60 s by default; 315 s in sweeps), it prints "rate-limited: stop using Google for this session" and **exits 4**.
  - **Exit 4 → don't call Google again this session.**
- **Point of sale:** `gl`/`curr` never changed a price (10 countries tested).
- **Shortcut:** `gflights_calendar.py` wraps calendar/grid and passes `--max-wait` through.

## 3. ITA Matrix: `matrix.py` (no browser; JSON API)
```bash
python3 matrix.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --carriers MU,CA,QR
python3 matrix.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --route "MU+" --route-ret "MU+" [--no-avail]
python3 matrix.py search --slice BUD:TYO:2027-05-12 --slice OSA:BUD:2027-05-26 --carriers MU   # open-jaw, MU forced on BOTH slices (€819 vs €4,241 when broken)
python3 matrix.py search --slice "BUD:TYO:2027-05-12:MU+" --slice "OSA:BUD:2027-05-26:CA+"      # per-slice routing
python3 matrix.py search --from VIE --to TYO --date 2027-03-10 --ext "-REDEYES" --minus 1 --plus 1
python3 matrix.py calendar --from BUD --to TYO --start 2027-05-01 --end 2027-05-31 --stay 14 --route "MU+" --route-ret "MU+"
```
- **The default answer is pruned** (6–17 solutions from 4–5 carriers, varying between runs). In B1 the default gave €1,083 against €715 with `MU+`.
  - **Always use `--carriers`** (~40 s per carrier; start with `MU,CA,QR`, then add carriers seen elsewhere) or routing codes.
  - The same applies to `calendar`: use `--route`.
- **`--slice` mode:**
  - Later slices use `--route-ret`/`--ext-ret`, falling back to `--route`/`--ext`.
  - `--carriers` forces every slice.
  - A per-slice `:ROUTE` cannot be combined with `--carriers`.
- **`--no-avail`** shows fare levels without confirmed seats (e.g. CA €574 one-way ex-VIE). These are **leads**: log them with `quotes.py add --lead`.
- **`--no-airport-change`** drops itineraries that change airport (ITA's `-change`).
- **Routing codes** (per slice):

  | Code | Meaning |
  |---|---|
  | `CA+` | at least one CA flight |
  | `C:CA` / `O:EK` | exactly one segment, marketed / operated by that carrier |
  | `X:IST` | connect at IST |
  | `N` | nonstop, per Google's docs. It returned 0 on a date without a nonstop; `--max-stops 0` or `C:OS` also work |

- **Extension codes (verified):** `MAXSTOPS 1`, `MINCONNECT 120`, `MAXCONNECT 240`, `-AIRLINES TK`, `ALLIANCE STAR-ALLIANCE`, `-CODESHARE`, `-REDEYES` (this shows a totally different set!), `-OVERNIGHTS`, `-PROPS`, `F BC=K`.
- **Sales city** made no difference (8 cities, all €1,123).
- **Speed:** 15–60 s per query; default pacing 5 s.
- **Coverage gaps:** no LCCs, no self-transfer, no NDC or web-only fares.

## 4. Kiwi.com
### 4a. `mcp_flights.py kiwi` (public MCP, `https://mcp.kiwi.com`)
```bash
python3 mcp_flights.py kiwi ZAG,VIE,BUD TYO,OSA 2027-05-12 --flex 3 --ret 2027-05-26 --ret-flex 3 --adults 1
python3 mcp_flights.py kiwi BUD TYO 2027-05-01 --date-to 2027-05-31 --nights 12-16
python3 mcp_flights.py kiwi ZAG TYO,OSA 2027-01-18 --date-to 2027-01-29 --only-airlines CA --log tyo-2027-01
python3 mcp_flights.py kiwi ZAG,VIE,BUD TYO,OSA 2027-05-12 --ret 2027-05-26 --exclude-airlines MU    # surface the next carrier
```
**Options:**
- dates: `--flex/--ret-flex` (≤10 days), `--date-to/--ret-to`, `--nights A-B`;
- bags: `--bags N`, `--cabin-bag`;
- routing: `--no-self-transfer`, `--max-stops`, `--max-hours`, `--only-airlines`, `--exclude-airlines`, `--via`, `--not-via`, `--not-via-countries`;
- output: `--sort`, `--adults`, `--json`, `--log TRIP [--log-top 3]`.

**Behaviour:**
- **About 15 results per call,** so carriers get crowded out. Run per-carrier passes (`--only-airlines`, `--exclude-airlines`).
- **The `bags(pers/cabin/HOLD)` column is per adult.** HOLD = checked bags in the price.
  - **Kiwi has no bag data for MU/CA/CZ/FM fares,** so 0 there means *unknown*.
  - With `--bags`, prices include Kiwi's bag add-on (~€335 round trip on MU). **Never rank on that.**
- **`tkt` column** (inferred from Kiwi's itinerary id):
  - `1` = one ticket;
  - `N OW+OW` = separately priced one-ways (e.g. MU out + CZ back);
  - `N self-tr` = self-transfer.

  The MCP builds OW+OW pairs that the GraphQL round-trip endpoint misses.
- **`--adults N`** gives party totals. `--log` then passes `--pax N --per total` and handles the rest:
  - inferred self-transfers are flagged;
  - HOLD 0 on MU/CA/CZ/FM is logged as `bags unknown`.
- **Air China ex-ZAG round trips** priced implausibly (€1,500+ against a €625 one-way). Cross-check them.
- **Native MCP:** the same server is registered in `.mcp.json` as `kiwi` (tool `search-flight`, dates dd/mm/yyyy).

### 4b. `kiwi_graphql.py` (Kiwi website GraphQL, no key)
```bash
python3 kiwi_graphql.py origin-scan --origins ZAG,LJU,GRZ,VIE,BUD,BEG,VCE,TRS,MUC --to TYO,OSA --dates 2027-05-09..2027-05-15 --return-dates 2027-05-23..2027-05-29
python3 kiwi_graphql.py search --from ZAG,VIE,BUD --to TYO,OSA --dates 2027-05-10..2027-05-14 --return-dates 2027-05-24..2027-05-28
python3 kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates 2027-05-10..2027-05-16      # one-way, radius
python3 kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates 2027-05-10..2027-05-16
python3 kiwi_graphql.py calendar --from BUD --to TYO,OSA --dates 2027-05-01..2027-05-31 --nights 12-16    # round-trip calendar
python3 kiwi_graphql.py places --near ZAG --radius 400
```
- **Location forms:** `ZAG`, `ZAG,VIE`, `ZAG@400` (radius in km), `City:tokyo_jp`, `Country:JP`, `Continent:europe`.
- **`search` with several origins** runs **one query per origin** and merges the results.
  - Multi-origin answers are not a global price sort: the old single query missed Air India VIE €708.
  - Round trips add one combined query, which finds cross-airport returns (out VIE, back BUD, €673).
  - `--no-per-origin` restores the old single query.
  - **Read the return leg:** it can land at another home airport. Log it with `--return-to`.
- **`origin-scan`** runs one query per hub (~5 s each). It's the fair way to rank hubs, and it was the only sweep that found AI €708. Pass `--return-dates` for round trips; without it, it's one-way.
- **`per-city`** gives the cheapest origin per Japanese city in one call. It's low value, because it shows only one origin per city.
- **`calendar`** is one-way, or round-trip with `--nights` / `--return-dates` (giving both is an error).
- **Bags:**
  - `--checked-bags N` ranks by Kiwi's price **plus Kiwi's bag add-on** and prints a warning.
  - Columns `FARE€` and `KIWI-BAG€` show the split.
  - `--fsc-bags-included MU,FM,CA,CZ` ranks those carriers by fare.
  - `--combine-oneways` adds OW+OW pairs.
- **Other flags:** `--no-self-transfer`, `--max-stops`, `--hand-bags`, `--nights`, `--hacks` (hidden-city/throwaway; off by default and needs user consent).
- **Prices are volatile:** one leg went €308 → €806 within 30 minutes. Note the query time, and the warnings on `hasMorePending` or provider errors.

## 5. `mcp_flights.py sk|skcal|sksweep` (Skiplagged public MCP)
```bash
python3 mcp_flights.py sk ZAG TYO 2027-05-12 --ret 2027-05-26 --limit 30 [--no-vi] [--hidden-city]
python3 mcp_flights.py skcal BUD TYO 2027-05-12 --ret 2027-05-26      # FIXED departure, flexible RETURN date (USD); low value
python3 mcp_flights.py sksweep ZAG 2027-05-12 --ret 2027-05-26        # cheapest destinations "anywhere"
python3 mcp_flights.py tools sk                                       # raw tool schemas
```
- **Hidden-city is OFF by default.** `--hidden-city` is an explicit opt-in (ToS risk; one-way, cabin bag only). `--no-hidden-city` is now a no-op.
- **Prices** come in USD, with an added **EUR** column (an `eur` key in JSON, so `monitor.py` can track `sk` checks).
- **Round trips** print as `out | back`, with all carriers, and the logged destination is correct. Every RT deep link contains `#trip=OUT,RET`, but that does NOT mean two separate one-way tickets.
- **Passengers:** `--adults N` gives party totals.
- **Round trips can come back unpriced.** In the final check on 2026-10-04 the server returned no price ("—") for every RT row; earlier the same day RT prices worked. The script shows `n/a` and warns. Then search each direction as a one-way `sk` (those still priced).

## 6. momondo / Kayak: `kayak.py` (no browser; poll API)
```bash
python3 kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26 --flex 3 --pages 2
python3 kayak.py --site www.kayak.de --from ZAG,BUD --nearby --to TYO,OSA --depart 2027-03-10 --flex 3 --show-links
python3 kayak.py --from VIE --to TYO --depart 2027-03-08,2027-03-10 --return 2027-03-24 --pages 2 --json out.json
```
- **Best performer in B1 and B4:** €684–686, MU+CZ with 2 bags via Opodo. 15–45 s per search; keep calls ≥ 3 s apart.
- **Prices are per person.** Use momondo.de or kayak.de for EUR.
- **Columns:**
  - `TICKET`: 1, self-transfer, or hacker. Self-transfer is shown for SKYPICKER/KIWIVI/KIWIVILCC, virtual-interline flags and `SELF_TRANSFER` warnings.
  - `EUR+BAG`.
  - `BAGS`: included checked bags, or FEE/UNKNOWN.
- **`--dedupe`** is on by default with `--flex`, several origins or `--nearby`. It keeps the cheapest row per (carriers, airports, provider), so the page isn't 50 copies of one fare on different dates. `--no-dedupe` shows every row. `--json` keeps all rows from all pages.
- **`--nearby` with several origins** runs one search per origin and merges.
- **Provider codes:**
  - `KIWIVI` / `KIWIVILCC` / `SKYPICKER` = Kiwi (self-transfer)
  - `CTRIPAIR` = Trip.com
  - `OPODO` / `EDREAMS`
  - `BOOKINGFLIGHTS`, `JUSTFLY`, and airline codes
- **Single ticket?** A mixed-carrier "one booking" (e.g. MU out + CZ back) may be 2 tickets. Confirm at checkout.

## 7. Browser-based OTAs (Playwright, ~25–45 s each; prices = party TOTAL)
```bash
python3 aviasales.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26 [--show-urls]
python3 booking_flights.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26
```
- **Aviasales** covers many small OTAs and packaged self-transfers (Mytrip FR+MU, Lucky2Go).
  - Its summary line `cheapest=… cheapest_with_baggage=…` is the **best bag signal**; it is repeated at the end of the output.
  - The `EUR+BAG` column shows the cheapest seller of the same ticket that includes a bag.
- **Booking.com Flights** is Etraveli inventory: Gotogate, Mytrip and Flightnetwork, which block bots directly. It's the high-risk seller tier.
  - It shows bags per traveller and the fare brand (e.g. ECONOMY STANDARD).

## 8. Positioning: `ryanair_wizz.py` and `positioning.py`
```bash
python3 ryanair_wizz.py anywhere --from ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --dates 2027-05-01..2027-05-10
python3 ryanair_wizz.py anywhere --from ZAG,BUD,VIE --to IST,SAW,BGY,MXP,STN,CRL,BRU,WAW,HEL,ARN --dates … --return …
python3 ryanair_wizz.py calendar --from ZAG --to BGY --dates 2027-05-01..2027-05-31
python3 ryanair_wizz.py routes --from ZAG,BUD,LJU
python3 positioning.py --home ZAG,VIE,BUD --hubs BRU,IST,MXP,ATH --to TYO,OSA --dates 2027-05-08..2027-05-14 \
        --return-dates 2027-05-22..2027-05-28 --adults 1 --checked-bags 1 --pos-bag-eur 40 --compare-home-rt 717
python3 positioning.py --home ZAG,VIE,BUD --hubs BRU,IST --to TYO,OSA --dates 2027-05-08..2027-05-14     # one-way out
python3 positioning.py --direction back --home ZAG,VIE,BUD --to TYO,OSA --dates 2027-05-24..2027-05-28
```
- **Ryanair/Wizz fares are fare only:** a small personal item, no cabin or checked bag, 1 adult.
  - Wizz fares come in local currency and are converted.
  - **Wizz has no ZAG or VIE routes; Ryanair has none from LJU or GRZ.**
- **`positioning.py` RT mode (`--return-dates`):** total = hub⇄Japan RT (Kiwi) + positioning out and back + `--pos-bag-eur` per positioning leg.
  - The return may land at a different home airport.
  - **`--compare-home-rt EUR`** with **`--min-saving 150`** prints skip lines for hubs that can't beat the home RT.
- **Connections:**
  - Buffer defaults to 4 h, plus 3 h for sibling airports (CRL↔BRU, BGY↔MXP, SAW↔IST, WMI↔WAW, NYO↔ARN, …).
  - `--max-gap 30` allows an overnight.
  - Wizz arrival times are time-zone-correct.
  - Ground transfer between sibling airports is **not** costed (CRL→BRU is about 1 h by bus).
- **Speed:** 1–8 min. Run it only for the top 2–4 hubs.
- **Coverage:** FR/W6 positioning only. For TK/PC→IST, LO→WAW, OU/JU legs, use `mcp_flights.py kiwi ZAG IST <date>`.

## 9. Others
```bash
python3 azair.py --from ZAG,LJU,GRZ --anywhere --dates 2026-11-01..2026-11-08     # LCC route IDEAS only
python3 flightconnections.py to NRT --filter-country AT,HU,HR,TR,QA                # ISO2 or names
python3 flightconnections.py from ZAG LJU VIE
python3 flixbus_ground.py --date 2027-05-11 [--from Ljubljana] [--to "Vienna Airport" Budapest]
python3 flixbus_ground.py --drive --home 15.9819,45.8150
python3 deals.py --days 60 [--region] [--any-asia] [--keywords seoul,korea,ICN] [--region-words wien,vienna,VIE] [--json]
python3 fx.py 2350 PLN [--card-fee 1.5]
```
- **AZair:** prices are months old, and it has no results beyond ~3 months ahead. Re-price on `ryanair_wizz.py`.
- **`flixbus_ground.py`:** returns city stops, not airports, and doesn't cover trains (the ZAG–BUD and ZAG–VIE trains exist: hzpp.hr / oebb.at / mavcsoport.hu).
  - Times vary by date: in May 2027 there was no direct ZAG→BUD bus.
- **`deals.py`** reads 22 RSS feeds (fly4free.pl Japan tag, travel-dealz Japan, utazomajom.hu…).
  - `--keywords` replaces the Japan word list, and `--region-words` replaces the Zagreb-region list. Three-letter uppercase words are matched as IATA codes.
  - Secret Flying and Jack's Flight Club need a browser or email.

## 10. Quote log: `quotes.py`
```bash
python3 quotes.py add --trip tyo-2027-05 --source momondo --seller Opodo --origin BUD --dest KIX \
   --return-from KIX --out 2027-05-12 --ret 2027-05-26 --price 684 --carriers MU,CZ --stops 1 --via PVG/CAN \
   --bags-included 2x23 --extras 50 --risk low --link "<url>" --notes "MU out, CZ back; hotel night BUD"
python3 quotes.py add … --price 1368 --per total --pax 2          # party-total prices
python3 quotes.py add … --lead                                     # Matrix --no-avail fare level (not bookable)
python3 quotes.py add … --supersedes 7                             # re-price replaces row #7
python3 quotes.py list --trip tyo-2027-05 --latest --need-bag 70   # per-person totals, newest row per itinerary
python3 quotes.py list --trip tyo-2027-05 --rt-only | --ow-only | --include-leads | --include-superseded
python3 quotes.py best --trip tyo-2027-05                          # best per origin→destination (never leads)
python3 quotes.py ground-init --trip <trip>                        # per-trip ground.json (other home base)
```
- **Total formula** (all per person): fare × (1 + card fee) + bag cost + extras + ground.
- **Ground:**
  - Round trip: the round-trip figure from `ground.json`. Open-jaw on the home side: half of each.
  - **One-way rows:** half of the round-trip figure (`OW` in dates; `--leg out|ret` forces the direction).
  - The hotel night counts once, before the outbound flight.
  - **An origin missing from `ground.json` gets a conservative default, shown as `?`.** Pass `--ground €` for those.
  - `hotel_if` notes trigger a warning on `add`; add the night with `--extras`.
  - `flights/searches/<trip>/ground.json` overrides the shared file for that trip. `--ground-file` overrides both.
- **Columns:**
  - `#` (row number, used by `--supersedes`) and `extra€`.
  - Bag `0?` = the checked bag isn't clearly included. `--need-bag 70` adds €70 to those rows and lists them.
  - `LEAD` = non-bookable; hidden by default.
- **Japan-side differences** aren't automatic. Add them with `--extras`:
  - ~€80 Shinkansen backtrack on a plain return when the trip goes Tokyo→Osaka;
  - ~€5–15 for NRT vs HND city transfer.
- **Other flags:** `--live` marks a price re-checked on the seller's checkout; `--self-transfer` marks separate tickets.
- **Automatic logging:** `mcp_flights.py --log TRIP` adds quotes for you (party totals and unknown bags handled).

## 10b. Price monitoring: `monitor.py`
```bash
python3 monitor.py flights/searches/<trip>/watch.json            # run all checks, print summary + ALERT lines
python3 monitor.py flights/searches/<trip>/watch.json --history  # stored history per check
```
- **Watch file:** checks are normal toolkit commands, plus how to get JSON:
  - `"json": "file:--json"` for kayak, kiwi_graphql, aviasales, booking and positioning;
  - `"file:--out"` for gflights and matrix;
  - `"stdout:--json"` for mcp_flights.

  Optional per-check `"note"` and `"threshold_eur"`.
- **What it compares:** the **fare-only minimum** per check (no ground or bags; per-person for kayak, the party total for the others). Build checks like-for-like:
  - one origin;
  - no Kiwi bag flags;
  - `--no-self-transfer` if needed;
  - never `--no-avail`.
- **Alerts:**
  - a new all-time low;
  - the **first** time a check goes ≤ threshold, or a further drop below the last alerted price.
  - Re-armed when the price rises again.
- **Tested** 2026-10-04: 4 checks in 77 s. The Routine prompt is in playbook §9.

## 11. Manual-only sources (give the user exact URLs)
- **Skyscanner:** `https://www.skyscanner.net/transport/flights/bud/tyoa/270512/270526/` (whole month: `?oym=2705&iym=2705`; Everywhere: `/transport/flights-from/zag/`)
- **Trip.com:** `https://www.trip.com/flights/showfarefirst?dcity=bud&acity=tyo&ddate=2027-05-12&rdate=2027-05-26&triptype=rt&class=y&quantity=1&locale=en-XX&curr=EUR` (also try `ja-JP` / `zh-HK` locales)
- **Google Flights in the user's browser:** the "Cheapest" tab (self-transfer combos the script never returns) and multi-city (open-jaw)
- **Airlines:**
  - Air China: `https://www.airchina.at/AT/GB/Home` (airchina.com blocks cloud IPs); book Fri–Sun for up to 6% off.
  - China Eastern: `https://www.ceair.com/` (check Basic vs Standard bags)
  - Air India: `https://www.airindia.com/`
  - Scoot: `https://www.flyscoot.com/` (add bags)
  - Turkish, Qatar, LOT, Finnair, Korean Air: their own sites.
- **Japan-origin OTAs** for Japan→Europe one-ways: skyticket.jp, Trip.com `locale=ja-JP`
- **Secret Flying** origin pages: Zagreb, Ljubljana, Vienna, Budapest, Belgrade
- **Trains to the departure airport:** hzpp.hr, oebb.at, mavcsoport.hu

## 12. When things break
| Symptom | Fix |
|---|---|
| `setup.sh` exits non-zero | Read its `!` lines. Fresh containers need `apt-get update` for certutil (it does this). On a PEP 668 Python, the script retries pip with `--break-system-packages` (cloud container only) |
| Browser pages fail with ERR_CERT_AUTHORITY_INVALID | `bash setup.sh` (NSS proxy CA, fingerprint-checked) |
| Playwright "Executable doesn't exist" | `pip install playwright==1.56.0` (match the /opt/pw-browsers build); set `CHROMIUM_PATH` if needed; never run `playwright install` |
| `gflights.py` exit 4 / "rate-limited" | Stop using Google for this session; continue with other sources |
| Google JS bundles blocked in headless (ERR_BLOCKED_BY_ORB) | `gflights.py --backend browser` already routes them via requests |
| `gflights.py` "0 itineraries" warning (exit 3) | Empty or throttled answer: wait, retry once with `--backend html`, then move on |
| Matrix returns few or odd solutions | Pruning: use `--carriers` / `--route "XX+"` / `--ext -REDEYES` variants |
| Kiwi MCP / Skiplagged MCP errors | Retry once; check `python3 mcp_flights.py tools kiwi` (the schema may have changed) and adapt the args |
| Wizz `400 InvalidProtocol` | Token echo is handled in the script; if the API version changed, it's re-scraped from wizzair.com. Re-run |
| AZair "busy" | The script retries with back-off; space queries ≥ 10 s |
| A site starts returning 403 / a captcha | Treat it as manual-only; note it in `sources.md` with the date |
| An internal API changes shape | Capture the site's own XHR with Playwright (`_browser.py` response capture), update the script, and note the date in the research file |
