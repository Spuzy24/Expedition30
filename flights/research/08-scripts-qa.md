# 08: QA of `flights/scripts/` (2026-10-04)

> QA run 2026-10-04 18:15–19:00 UTC, cloud container, agent proxy. Base: commit `a407406` (scripts
> identical to `2ab02e2`, reviewed at the start). Another agent was searching with the same tools at
> the same time, so I stayed within the call budget: `gflights` 2 calls (1 search + 1 calendar via
> `gflights_calendar.py`), `matrix` 2, `kayak` 1, `aviasales` 1, `booking_flights` 1. Kiwi,
> Skiplagged, Ryanair and Wizz were used moderately. Scripts were NOT modified in place. Fixes are
> unified diffs in `research/patches/` (§5). Nothing committed.
>
> Severity: **P0** = wrong price or ranking · **P1** = crash or major usability · **P2** = minor.

**Top findings**
1. **Kiwi anomaly (§3):** the €1,135 is not reproducible. The same command now gives **€925–927**
   (CA VIE–PEK–HND RT), exactly what the Kiwi MCP gave. The script's query is not the cause. Kiwi
   prices the MU fare as "0 bags" and adds a **€334.89 bag** to it. The same fare is sold by
   Opodo/eDreams/Gotogate/Booking at €692–741 *with 2×23 kg*, which GDS data identifies as MU
   "ECONOMY STANDARD". Kiwi is **not** selling a cheaper no-bag fare. It lacks the bag data and
   upsells a bag the ticket very likely already includes. Separately, Kiwi's web GraphQL return search
   never builds **two-one-way pairs with full-service carriers** (CZ), which the MCP does
   (€871 vs €927 at 18:24).
2. Eight **P0** ranking/price bugs (Kiwi bag ranking, missing OW+OW pairs, Skiplagged RT parsing and
   logging, two `quotes.py` ground-cost errors, positioning bags and time zones, `gflights` sweep cache
   reusing prices from a different query). All have tested patches.
3. `setup.sh` is idempotent here but **fails silently in a fresh container**: it reports "done", exit 0,
   while `certutil` is missing or the proxy CA is stale, and every browser script then fails.
4. `gflights.py search` returned **0 itineraries with exit 0** for the benchmark query (1.0 s), while
   the calendar endpoint worked 15 s later. The other agent got 300 rows for the same query shape
   10 minutes earlier.

---

## 1. Smoke tests

`setup.sh` was run first (exit 0, 3.4 s). All 16 scripts plus 6 sub-command `--help` pages: **exit 0,
0.1–0.3 s each**. P2: `flixbus_ground.py --help` has no description or examples. Real queries used
May 2027 dates and ZAG/VIE/BUD origins, as asked.

| Script | Test (real query) | Exit | Time | Verdict |
|---|---|---|---|---|
| setup.sh | run twice (idempotency) | 0 / 0 | 3.4 s / 3.2 s | **PASS here**. Fresh-container simulation: silent failure (§4) |
| gflights.py | `search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26` | 0 | 1.2 s | **FAIL (silent)**: 0 itineraries, exit 0, no warning (B9) |
| gflights_calendar.py | `--from BUD --to TYO --start 2027-05-01 --end 2027-05-31 --stay 14 --heatmap` | 0 | 0.7 s | PASS: 12→26 May €812 (B1 had GF €811 QR); heatmap OK |
| matrix.py | `search BUD→TYO RT --route "MU+" --route-ret "MU+"` | 0 | 35.3 s | PASS: €715.27 MU602/MU523 ‖ MU272/MU601, 90 solutions; RT slices parsed correctly |
| matrix.py | `calendar BUD→TYO 2027-05-10..16 --stay 14` | 0 | 33.7 s | PASS (runs). Data caveat: pruned default answer, 12 May **€5,132** (CA/KE only) vs €715 when MU is forced |
| mcp_flights.py | `kiwi ZAG,VIE,BUD TYO,OSA 2027-05-12 --ret 2027-05-26 --bags 1 --no-self-transfer` | 0 | 1.9 s | PASS: 15 rows; €871 CA\|CZ at 18:24, €927 CA RT at 18:53 |
| mcp_flights.py | same without bags | 0 | 2.8 s | PASS: €748 MU BUD–PVG–NRT RT, bags 1/1/0 |
| mcp_flights.py | `sk BUD TYO 2027-05-12 --ret 2027-05-26 --no-hidden-city` | 0 | 5.1 s | Runs, **BUG**: RT route concatenated with a false `~`, outbound-only carriers (B3) |
| mcp_flights.py | `skcal BUD TYO …` / `sksweep ZAG …` | 0 / 0 | 3.5 / 3.9 s | PASS. Doc: `skcal` is a *flexible-return* calendar (prices same-day returns, $1,488), not "fixed stay" (B24) |
| kiwi_graphql.py | **benchmark**: `search --from ZAG,VIE,BUD --to TYO,OSA --dates 2027-05-12 --return-dates 2027-05-26 --checked-bags 1` | 0 | 14.7 s | PASS: **€925** CA VIE–PEK–HND RT (not €1,135); ~10 s of it is place resolution |
| kiwi_graphql.py | `search --from TYO --to BUD --dates 2027-05-26` (OW) | 0 | 7.3 s | PASS: €308 CZ HND–CAN–BUD (2 bags) at 18:33 |
| kiwi_graphql.py | `per-city --from ZAG,VIE,BUD --to Country:JP --dates 2027-05-10..14` | 0 | 9.6 s | PASS: VIE→KIX €363 |
| kiwi_graphql.py | `origin-scan --origins ZAG,VIE,BUD … RT --checked-bags 1` | 0 | 18.6 s | PASS. "1-TICKET" column uses flags only (B23) |
| kiwi_graphql.py | `calendar BUD→TYO May` / `places --near ZAG --radius 200` | 0 / 0 | 6.1 / 2.5 s | PASS (9 airports) |
| kayak.py | `--from ZAG,VIE,BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26` (momondo.de) | 0 | 40.8 s | PASS: **€688** MU\|CZ Opodo, 2 bags; 4,576 total. `bookingOptions[0]` is the cheapest in 50/50 results |
| aviasales.py | `--from BUD --to TYO --depart 2027-05-12 --return 2027-05-26` | 0 | 31.4 s | PASS: €700.75 MU\|CZ Turna.com; 16 of 1,513 tickets parsed (by design); BAGS from cheapest seller only (B16) |
| booking_flights.py | same | 0 | 23.9 s | PASS: €741.27 MU RT, 2 bags, 1,445 offers |
| flightconnections.py | `to NRT --filter-country Austria,Hungary,Croatia,…` | 0 | 22.2 s | PASS: VIE, 18/month |
| flightconnections.py | `from VIE --filter-country JP,CN,KR,AE,QA,TR` (the docstring example) | 0 | 20.2 s | **FAIL**: 0 rows (country names give 15). B11 |
| ryanair_wizz.py | `routes --from ZAG,BUD,VIE` | 0 | 4.9 s | PASS: FR 28/70/70, W6 0/97/0 |
| ryanair_wizz.py | `anywhere --from ZAG,BUD --dates 2027-05-08..11` | 0 | 16.4 s | PASS (Wizz rows have an empty CITY, cosmetic). Ryanair farfnd is complete (`nextPage: null`) |
| ryanair_wizz.py | `calendar --from BUD --to BGY,STN …` / Wizz RT `anywhere --return …` | 0 / 0 | 8.1 / 6.6 s | PASS (both Wizz RT legs in HUF, no currency mixing) |
| positioning.py | `--home ZAG,BUD --to TYO --dates 2027-05-11..12 --hubs BGY,STN,IST --checked-bags 1` | 0 | 64.6 s | Runs, **BUG**: positioning bag not costed, Wizz arrival time zone wrong (B6, B7) |
| azair.py | `--from ZAG,VIE,BUD --to IST,SAW,BGY --dates 2027-05-08..12` | 0 | 1.4 s | PASS ("no results" beyond the ~4-month horizon, as documented) |
| azair.py | `--from ZAG,LJU --anywhere --dates 2026-11-02..05` | 0 | 2.0 s | PASS: 65 results, but AGE_H 5,800–6,166 h (8 months stale) |
| deals.py | `--days 60` (table and `--json`) | 0 | 35 s | PASS: 21 hits, 22 feeds; `travelpirates.com` returns 0 items but shows "ok 0" (B19) |
| flixbus_ground.py | `--date 2027-05-11 --to "Vienna Airport" "Budapest Airport"` | 0 | 0.8 s | PASS: €21.48 / €32.47 |
| fx.py | `2350 PLN --card-fee 1.5` / `100 XYZ` | 0 / **1** | 0.1 s | PASS €544.89 / **traceback** KeyError (B20) |
| quotes.py | add/list/best in a sandbox copy (repo log untouched) | 0 | <0.2 s | Runs, **maths bugs** (B4, B5, B14) |

---

## 2. Bugs found

### P0: wrong price or ranking

| ID | Script | Bug | Evidence | Patch |
|---|---|---|---|---|
| B1 | kiwi_graphql.py | `--checked-bags N` ranks by Kiwi's price **including its own bag add-on** and shows `BAGS 1` as if the bag were included. Kiwi has no bag data for MU (48 of 50 itineraries say "0 included"), so the MU fare gets **+€334.89 RT** and drops from #1 (€748) to €1,082.89, below CA €927. | GraphQL `checkedBagTiers` for MU: one tier, 1×23 kg, €334.89. §3.3 | 01 |
| B2 | kiwi_graphql.py | The return search never builds **two separate one-way tickets** with full-service carriers. A CZ-only RT filter returns 0 rows in every market (hr/hu/at/gb/us), although the one-way endpoint has CZ. The MCP builds these pairs. | 18:24: MCP €871 (CA VIE–PEK–KIX + CZ HND–CAN–BUD); GraphQL RT €927; GraphQL OW €562 + OW €308 = **€870** | 01 |
| B3 | mcp_flights.py | Skiplagged RT: `_route` concatenates both directions (`BUD-PVG-HND~NRT-DOH-BUD`). `~` falsely flags an airport change: it is only HND arrival vs NRT return 2 weeks later. `carriers` = outbound only (QR return hidden). `--log` writes **dest = route[-3:] = BUD** (`BUD->BUD`) with no return airports, so `quotes.py best` groups it wrongly. | live `sk BUD TYO … --ret …`; sandbox log test | 03 |
| B4 | quotes.py | Origin missing from `ground.json` → ground = 0 → the quote **ranks first** (LJU €760 above BUD €810 in the test). | sandbox | 02 |
| B5 | quotes.py | Open-jaw on the home side halves the `hotel` night and adds half of the *return* airport's hotel. The hotel is only needed before the outbound flight. | BUD out/VIE back: €103 instead of €108 | 02 |
| B6 | positioning.py | `--checked-bags` prices the bag into the long-haul only. FR/W6 positioning fares are fare-only, so every positioning combo is understated by €25–60 per bag per leg against home departures. | top combo €401.25, → €430.96 with a €40 bag | 04 |
| B7 | positioning.py | Wizz arrival = origin-local departure + `--wizz-block` hours, compared with **hub-local** Kiwi times. It ignores time zones: BUD→IST +1 h, BUD→AUH/DXB +2 h, westbound errors are conservative. This can accept impossible connections or reject valid ones. | BUD→AUH 10:00 + 5.5 h = 17:30 Dubai time, script said 15:30; BUD→IST 05:30 gap was 31.0 h, really 30.0 h | 04 |
| B8 | gflights.py | `sweep` resumable cache: the signature omits `--via/--bags/--carry-on/--max-price/--exclude-basic/--no-self-transfer`, so a rerun with `--bags 1` **reuses bag-less prices** with 0 requests. A changed signature also *discards* the old cache. | offline demo: `--bags 1` rerun printed the cached €807 with "0 requests" | 05 |

### P1: crash or major usability

| ID | Script | Bug | Patch |
|---|---|---|---|
| B9 | gflights.py | `search` printed "0 itineraries" with exit 0 for a valid query (1.0 s answer). Only the **first** `wrb.fr` payload is parsed, with no warning and no distinction between "no flights" and an empty or throttled answer. Root cause not confirmed (Google budget spent). | 05: tries every payload, warns, exits 3 on zero results |
| B10 | setup.sh | Fresh container: no `apt-get update` before installing `libnss3-tools`, so `certutil: command not found` ×2 yet it prints "== done", exit 0. `pip … \| tail -2` masks pip failures (exit 0 for a missing requirements file). It checks the CA **by nickname**: with a stale CA it says "already trusted" while Chromium fails ERR_CERT_AUTHORITY_INVALID (demonstrated). No browser smoke test. | 06 |
| B11 | flightconnections.py | ISO2 `--filter-country` (the docstring example `JP,CN,KR,AE,QA,TR`) returns 0 rows: it compared against href suffixes. The ISO2 code is in the flag URL `/flags/24/JP.png`. | 07 |
| B12 | kiwi_graphql.py | Ignores `metadata.hasMorePending` and provider errors (partial answers look final). A non-JSON or 5xx response gives a traceback. `--limit-api` > 50 is silently capped at 50 (tested 200 → 50). | 01 |
| B13 | mcp_flights.py | `rpc()` retries deterministic JSON-RPC errors (bad arguments) 3× with 3+6+9 s sleeps, including a sleep after the last attempt. | 03 |
| B14 | quotes.py | `--per total` without `--pax` silently divides by 1 (€1,416 "per person" for a 2-pax €1,400 fare). The `fare€` column shows the N-pax total next to a per-person total. | 02 |
| B15 | mcp_flights.py `--log` / quotes | Kiwi quotes logged from a no-bag search carry `bag_cost 0`, so they outrank OTA bag-inclusive fares for a traveller with a bag. Kiwi's MCP also gives no PNR count, so MU\|CZ OW+OW pairs look like one ticket even with `--no-self-transfer`. | not patched: log with `--bags 1` or set `--bag-cost`; document |

### P2: minor

| ID | Script | Bug | Patch |
|---|---|---|---|
| B16 | aviasales.py | BAGS comes from the cheapest seller only, which hides that the same ticket has a bag-inclusive seller a few euros up (Kiwi.com €735/0 bags vs Trip.com €780/2×23 kg). | 08 (`EUR+BAG` column) |
| B17 | booking_flights.py | Checked bags are **summed over travellers** (2 adults → "4"). The fare brand is not shown. | 09 |
| B18 | matrix.py | `--carriers` + `--route`: the route overrides the forced carrier, giving N identical queries. The same solution is listed once per forced carrier (duplicates). | 10 |
| B19 | deals.py | Undated items bypass `--days`. Dedupe uses raw links (`utm_*` parameters). An empty feed shows as "ok 0". Cross-language duplicates (travel-dealz .de/.com) and Japan→elsewhere noise are not filtered (not patched). | 11 |
| B20 | fx.py, quotes.py | Unknown currency gives a KeyError traceback. | 12, 02 |
| B21 | gflights.py | `grid` ignores `--bags/--via/--max-price/--exclude-basic`. | 05 |
| B22 | gflights_calendar.py | `--quiet --gl HR …` puts `--gl` after the subcommand, which argparse rejects. | 05 |
| B23 | kiwi_graphql.py | `origin-scan` "1-TICKET" = first row without the self-transfer flag, even if it has 2 PNRs (two one-ways). | 01 (`pnrCount == 1`) |
| B24 | tools.md (doc) | `skcal` is described as "price per date pair (fixed stay)". It is a fixed-departure, flexible-return calendar. | doc only |
| B25 | _common.py / fx.py | Two FX sources (ECB XML vs open.er-api + frankfurter). If the ECB fetch fails, `to_eur` returns None and kayak/aviasales sort on the raw price in another currency. | not patched |
| B26 | positioning.py | `rw.fr_routes()` is re-fetched for every (home, hub, sibling) pair. With a cache the test run took 29 s instead of 64.6 s. | 04 |
| B27 | matrix.py calendar | The default answer is pruned (12 May €5,132 vs €715 with `MU+`). Known; use `--route` in calendars too. | doc |
| B28 | kayak.py | `--nearby` silently ignores every origin after the first. | not patched |
| B29 | mcp_flights.py `kiwi` | The `bags(p/c/h)` column means "bags in the price" when `--bags` is set, not bags included in the fare. | doc |

**Checked and OK:**
- Kayak: `bookingOptions[0]` is always the cheapest, and momondo.de returns EUR.
- Ryanair farfnd is not paginated.
- Wizz RT legs share one currency.
- Matrix RT slices and `price_num` parse correctly.
- Kiwi GraphQL: the server sorts by bag-inclusive price and the client re-sort agrees; `per-city`/`calendar` are fine.
- GF calendar splits TYO and OSA correctly.
- deals: time-zone handling of ages is fine.
- quotes: plain RT ground and USD→EUR conversion are correct.
- `setup.sh` is idempotent in this container (identical output, one NSS entry, CA fingerprint matches).

**Not tested (budget):**
- `--adults > 1` per-person vs total on GF/Kayak/Aviasales/Matrix. In the code, Booking, Kiwi and Matrix report the total for all passengers and no table labels it.
- GF `html`/`browser` backends, `explore` and live `sweep`.
- Matrix `--carriers`/`--slice`; Kayak `--pages/--flex/--nearby`.
- `monitor.py` (added mid-review; it reads the `eur` key, so it stays compatible with patch 01).

---

## 3. Anomaly: `kiwi_graphql` bag search €1,135 vs Kiwi MCP €925

### 3.1 Reproduction (all 2026-10-04, UTC)

| Time | Query | Cheapest |
|---|---|---|
| 18:19 | `kiwi_graphql.py search … --checked-bags 1` (benchmark command) | **€925** CA VIE–PEK–HND RT (1 PNR, Kiwi: bag included) · MU RT €1,082.89 |
| 18:20–18:30 | 20 GraphQL variants (below) | €927, identical in every variant |
| 18:24 | MCP `--bags 1 --no-self-transfer` | **€871** CA VIE–PEK–KIX + CZ HND–CAN–BUD · €924 MU+CZ · €927 CA RT |
| 18:24 | MCP no bags | €748 MU BUD–PVG–NRT RT, checked 0 |
| 18:33 | GraphQL OW TYO→BUD | €308 CZ HND–CAN–BUD (2 bags) |
| 18:50 | GraphQL OW TYO,OSA→ZAG,VIE,BUD | CZ HND–CAN–BUD now **€806** |
| 18:53 | MCP `--bags 1 --no-self-transfer` | **€927** CA RT, the same as GraphQL; CZ OW €804/806 |

### 3.2 Query construction, sorting, limit, or missing results?

- **Query construction: not the cause.** Every variant returned the same €927:
  - `searchStrategy` REDUCED vs REGULAR, and `mergePriceDiffRule` INCREASED vs STANDARD.
  - `showNoCheckedBags`.
  - `contentProviders` + KAYAK/NDC/AMADEUS (only KIWI ever answered).
  - `allowReturnToDifferentCity`.
  - `market` hr/hu/at/gb/us.
  - `--no-self-transfer`.
  - Repeated cold and warm calls: deterministic, `hasMorePending=false`, provider KIWI 200.
- **Sorting: not the cause.** The server list is already sorted by bag-inclusive price and the script's re-sort agrees.
- **Limit: a cap, not a truncation bug.** The API returns at most 50 itineraries (`limit 200` → 50). The bag search does re-rank over a wider pool: 16 of 50 itineraries differ between the bag and no-bag searches. Itineraries are not cut by base fare first.
- **Missing results: yes, structurally (B2).** The GraphQL *return* endpoint does not combine two one-way tickets on full-service carriers:
  - A CZ-only RT search gives 0 rows, while the one-way endpoint has the CZ flight.
  - Two GraphQL one-way searches gave €562 + €308 = **€870**, matching the MCP's €871.
  - The MCP exposes Tequila-style parameters (`adults_hold_bags`, `select_airlines`, `one_for_city`), so it sits on a different Kiwi backend that builds these pairs.
- **Volatility: yes.** In 30 minutes the CZ leg went €308 → €806 and the MCP's best bag RT went €871 → €927. The script printed no metadata, so a transient answer looks final.
- **Verdict on €1,135:** not reproducible. The benchmark's description ("CA/MU out + TR back combos") matches the 2-PNR rows that still sit at €1,078–1,113 today. So at that moment the single-ticket CA and MU RTs were missing from Kiwi's GraphQL answer, a Kiwi-side transient state. The *systematic* differences are B1 (bag pricing), B2 (no OW+OW pairs) and volatility without diagnostics (B12).

### 3.3 Is Kiwi's MU/CA bag data wrong, or is Kiwi selling a fare without bags?

The same flights are BUD–PVG–NRT MU602/MU523 out, MU RT back, 12→26 May 2027:

| Seller / source | Price | Checked bags | Fare label |
|---|---|---|---|
| Kiwi GraphQL, no bags | €748 | `includedCheckedBags 0`; bag tier 1×23 kg = **€334.89** | provider KIWI-BASIC |
| Kiwi GraphQL, `--checked-bags 1` | €1,082.89 = 748 + 334.89 | 1 (paid add-on) | |
| Aviasales: agent Kiwi.com | €735 / €1,069.89 | 0 / 1×23 kg (+€334.89 again) | |
| Kayak: SKYPICKER (= Kiwi) | €706–737 / €1,041–1,070 | **UNKNOWN** / "+1 Gepäckstück" (+€335) | "Economy Class Light" |
| Kayak: Opodo, eDreams, Gotogate, Booking (BOOKINGFLIGHTS) | **€692–703** | **2 included** | "Economy Class Light" (same label as Kiwi's) |
| Booking.com (Etraveli, GDS branded-fare data) | €741.27 (base €294.58 + tax €410.38) | **2×23 kg, piece-based** | **`ECONOMY STANDARD`** |
| Aviasales: Gotogate / Trip.com | €717.99 / €780 | 2 / 2×23 kg | |
| ITA Matrix `MU+` | €715.27 | (fare only) | |
| ceair.com baggage page | | Europe-touching itineraries: **Basic 0 pc**, Standard/Flexible **1 pc** ×23 kg. Japan routes: Basic 1, Standard 2 | |

**Conclusion:**
- **Kiwi is not selling a cheaper no-bag fare.** Its no-bag price (€706–748) is *above* the bag-inclusive Standard fare at other sellers (€692–741). Kayak tags Kiwi's offer with the same fare label as the OTAs'.
- **Kiwi's bag data for MU is missing, not "0".** Kayak marks it UNKNOWN. Kiwi upsells a **€335 bag** that the ticketed fare very likely already includes: GDS says 2×23 kg, and MU's own site says at least 1 piece for Standard.
- **Residual risk:** MU now has a **Basic** brand with 0 bags on Europe itineraries. A MU price clearly *below* the Standard level (≈ €690–740 here) should be treated as Basic/0 bags. The GDS (2 pc) and ceair.com (1 pc on Europe routes) disagree on the count, so check the allowance on the e-ticket or in "manage booking" right after purchase.
- **CA:** Kiwi's data is usable. It reports 1 included bag with a €0 tier, so the CA RT keeps €927 with a bag. Real CA allowance is 2×23 kg; Kiwi undercounts, which is harmless for 1 bag.

### 3.4 Fix

- **Code (patch 01, tested live):**
  - Every row shows `FARE€` and `KIWI-BAG€` (Kiwi's add-on) next to `EUR`. A warning fires when ≥ €150 of bag fees land on an itinerary.
  - `--fsc-bags-included MU,FM,CA,CZ` ranks those carriers by fare: MU moves back to #1 at €748 (`RANK€`).
  - `--combine-oneways` adds OW+OW pairs (2 extra queries, flagged `2-tickets(OW+OW)`). The €870 pair had vanished by the time the patch was ready (the CZ leg moved to €806), so the live test could only confirm that pairs are built and checked, not reproduce €870.
  - `hasMorePending` and provider errors print warnings.
  - `origin-scan` "1-TICKET" now means `pnrCount == 1`.
- **Process (suggested text for `tools.md` §4 and `playbook.md`):**
  - Replace "Bag data is wrong for Chinese carriers (says 0 checked; the MU fare includes 2×23 kg)" with: "Kiwi has no bag data for MU (shows 0 and sells a ≈ €335 RT bag add-on). The same fare is MU ECONOMY STANDARD with 2×23 kg at OTAs (GDS). Rank MU/CA/CZ on Kiwi's no-bag price against OTAs' bag-inclusive prices, or use `--fsc-bags-included`. Never buy Kiwi's bag add-on for MU without checking the fare."
  - Replace "`--checked-bags 1` gave odd, high results in B1" with: "Bag search = Kiwi price + Kiwi bag add-on; see `KIWI-BAG€`. Use `--combine-oneways` for RTs; the return endpoint misses two-one-way pairs that the MCP finds."
  - Always run both Kiwi paths (MCP + GraphQL) and note the query time: prices moved by €500 on one leg within 30 minutes.

---

## 4. `setup.sh`

**Idempotency:** OK in this container. Two runs (3.4 s / 3.2 s) gave identical output, the NSS store keeps exactly one `ccr-agent-proxy` entry, and its SHA-256 fingerprint equals `/root/.ccr/agent-proxy-ca.crt`.

**Fresh-container correctness: FAIL (silent).** Simulated with `env -i`, a PATH without `certutil`, and an `apt-get` that fails like an image with empty package lists:
```
  ! could not install libnss3-tools
setup.sh: line 24: certutil: command not found
setup.sh: line 28: certutil: command not found
...
== done            (exit 0)
```

| Issue | Effect |
|---|---|
| No `apt-get update` before `apt-get install libnss3-tools` | Fails on images with empty apt lists ("Unable to locate package") |
| `certutil` used even after the install failed; no `set -e`/`pipefail`; always exits 0 | "== done" while browser scripts will hit ERR_CERT_AUTHORITY_INVALID |
| `pip install … 2>&1 \| tail -2` | pip failures (including PEP 668 "externally-managed-environment" on Debian 12/Ubuntu 24.04 system Python; `/usr/lib/python3.12/EXTERNALLY-MANAGED` exists here) are hidden, exit 0 |
| `pip` instead of `python3 -m pip` | May install for a different interpreter than `python3` (same here: both are 3.11) |
| CA checked by **nickname** only | Demonstrated with a stale CA stored as `ccr-agent-proxy`: the original prints "already trusted", exit 0, and Chromium then fails ERR_CERT_AUTHORITY_INVALID |
| No browser smoke test | The most fragile dependency (Chromium + TLS via the proxy) is never exercised |
| `PLAYWRIGHT_BROWSERS_PATH` not checked | Set here (`/opt/pw-browsers`); a fresh shell without it fails with "Executable doesn't exist" |

**Patch 06 (tested):**
- `pipefail`, a failure counter and a non-zero exit when a step fails.
- `python3 -m pip`, with a `--break-system-packages` fallback **only** in the managed cloud env (`/root/.ccr` present) when PEP 668 blocks the install.
- `apt-get update` before installing; a hard failure if `certutil` is still missing.
- CA compared by fingerprint, so a stale CA is replaced.
- `PLAYWRIGHT_BROWSERS_PATH` defaulted to `/opt/pw-browsers`.
- A headless-Chromium HTTPS smoke test.

Results:
- Real container: exit 0 twice (4.3 s / 4.2 s), "chromium: HTTP 200 via proxy".
- Fresh-container simulation: **exit 1, "done WITH ERRORS"**, and the Chromium test reports the exact ERR_CERT_AUTHORITY_INVALID.
- Stale-CA test: the CA is replaced and Chromium gets HTTP 200.

---

## 5. Patches (`research/patches/`)

Apply from the repo root with `git apply flights/research/patches/*.diff`. Each patch and the full set pass `git apply --check` against `a407406`.

| File | Fixes | How it was tested |
|---|---|---|
| `01-P0-kiwi_graphql-bags-oneway-combos.diff` | B1, B2, B12, B23 | live: default, `--combine-oneways`, `--fsc-bags-included`, `origin-scan`, OW; `positioning.longhaul()` still works |
| `02-P0-quotes-ground-hotel-missing.diff` | B4, B5, B14, B20 | sandbox: 808 (was 803), LJU `60?` (was 0), `--per total` without `--pax` → error; real quote log ranks identically |
| `03-P0-mcp_flights-skiplagged-roundtrip.diff` | B3, B13 | offline on the saved raw response + live RT/OW; `--log` → BUD→NRT, return NRT→BUD |
| `04-P0-positioning-bags-timezones.diff` | B6, B7, B26 | live: +€40/bag, TZ-correct gaps, 64.6 s → 29 s |
| `05-P1-gflights-sweep-cache-empty-results-grid.diff` | B8, B9, B21, B22 | offline (mocked RPC): multi-payload, warning, grid filters, cache compatibility (old caches still resume for default options; a different query is backed up, not overwritten), wrapper argv |
| `06-P1-setup-sh-fresh-container.diff` | B10 | real run ×2, fresh-container simulation, stale-CA simulation |
| `07-P1-flightconnections-iso2-filter.diff` | B11 | offline on captured HTML (`/flags/24/JP.png` → JP) |
| `08-P2-aviasales-cheapest-with-bag.diff` | B16 | saved raw: Kiwi.com €735/0 bags → EUR+BAG €780 |
| `09-P2-booking-bags-per-traveller-brand.diff` | B17 | saved raw: 2 bags, brand ECONOMY STANDARD |
| `10-P2-matrix-carriers-route-dedupe.diff` | B18 | offline (mocked search): conflict → exit 1; duplicate CA/MU solution collapsed |
| `11-P2-deals-undated-utm-empty-feeds.diff` | B19 | live: 21 hits, travelpirates flagged EMPTY |
| `12-P2-fx-unknown-currency.diff` | B20 | `fx.py 1 XYZ` → clean usage error |

**Notes on the patches:**
- Patch 05 changes the sweep cache signature. Existing caches still resume when the new options are at their defaults.
- Patch 01 adds JSON keys (`fare_eur`, `kiwi_bag_eur`, `rank_eur`, `dep_local`, `arr_local`) and keeps `eur` as Kiwi's real price, so `monitor.py`'s minimum-price extraction is unchanged.
- Patch 04 defaults `--pos-bag-eur` to €40 when `--checked-bags` is set, and says so on stderr. Set the real Ryanair/Wizz fee per route.
