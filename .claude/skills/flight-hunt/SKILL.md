---
name: flight-hunt
description: Find the user the cheapest real, bookable flight ticket (built for home region Zagreb/Central Europe → Japan, works for any route). Searches every nearby departure airport and Europe-wide hubs with positioning flights, across Google Flights, ITA Matrix, Kiwi, Skiplagged, momondo/Kayak, Aviasales, Booking.com, Ryanair/Wizz and deal feeds, compares RT / one-ways / open-jaw / self-transfer, ranks by true total cost, and reports or monitors. Use when the user asks to find, compare, check or monitor flight prices, or to plan buying a ticket.
---

# Flight hunt: operational checklist

Full reasoning: `flights/playbook.md`. Context: `CLAUDE.md`. Work from the repo root.
Every command below was tested on 2026-10-04 (see `flights/tools.md` for all options).
`S=flights/scripts`

## 0. Setup (fresh container, ~1 min)
```bash
bash flights/scripts/setup.sh          # deps, Playwright pin, Chromium proxy-CA, smoke tests
```
If a script breaks, check `flights/tools.md` ("When things break") before debugging.

## 1. Intake
- Read `flights/profile.md`. Ask the user every `TBD` in ONE message: home base (assumed Zagreb), pax/ages/student, Japan airports + open-jaw OK?, date window/trip length/flex, bags, risk appetite (self-transfer, positioning flights, hidden-city default NO), payment card, budget.
- Trip id like `tyo-2027-05`: `cp -r flights/searches/_template flights/searches/<trip>`. Log every search in its `notes.md`.
- If the user's home isn't Zagreb: re-derive `flights/searches/ground.json` with `$S/flixbus_ground.py --from "<City>"` and update `flights/origins.md`.

## 2. Recon
```bash
python3 $S/deals.py --days 60                       # live sales / error fares (22 feeds)
python3 $S/gflights.py calendar --from VIE --to TYO --start D1 --end D2 --stay 12-16
python3 $S/kiwi_graphql.py calendar --from ZAG --to TYO --dates D1..D2
python3 $S/mcp_flights.py skcal BUD TYO D --ret R
```
Benchmarks in `flights/japan.md` §1 (great < €500 RT with bag, normal €650–950). Note Google's "typical" range. Pick the 1–3 cheapest date pairs that fit the user's window.

## 3. Sweep A: home catchment (ZAG, LJU, GRZ, VIE, BUD, BEG, VCE, TRS, MUC)
Run ALL of these; each sees different inventory (benchmark B1: momondo €686 vs Google €811 vs Matrix €1,083):
```bash
python3 $S/kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart D --return R   # + --flex 3, --nearby, --site www.kayak.de
python3 $S/mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD,BEG,VCE,TRS,MUC TYO,OSA D --flex 3 --ret R --ret-flex 3
python3 $S/kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates D1..D2 --return-dates R1..R2
python3 $S/mcp_flights.py sk BUD TYO D --ret R          # repeat for ZAG, VIE
python3 $S/aviasales.py --from BUD --to TYO --depart D --return R      # per origin, ~45 s
python3 $S/booking_flights.py --from BUD --to TYO --depart D --return R
python3 $S/gflights.py search --from ZAG,LJU,GRZ,VIE,BUD,BEG,VCE --to TYO,OSA --date D --return R   # airline baseline; MISSES Chinese carriers
python3 $S/matrix.py search --from VIE --to TYO --date D --return R    # fare rules; misses MU/CA/QR
```
Per-carrier passes (top-N lists hide carriers): `mcp_flights.py kiwi ... --only-airlines CA` then MU,FM / CZ / HU / KE,OZ / TK / QR / EY / LO / AY / NH.

## 4. Sweep B: Europe-wide hubs + positioning
```bash
python3 $S/kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates D1..D2
python3 $S/kiwi_graphql.py origin-scan --to TYO,OSA --dates D1..D2 --origins ZAG,VIE,BUD,BEG,MUC,VCE,MXP,FCO,BRU,AMS,CDG,FRA,IST,WAW,HEL,ARN,CPH,DUB,LHR,MAD,ATH,PRG
python3 $S/gflights.py sweep --origins europe --to TYO,OSA --start D1 --end D2 --stay N --cache flights/searches/<trip>/gf_sweep.json
python3 $S/positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --hubs <top hubs> --to TYO,OSA --dates D1..D2   # + --direction back
```
The cheapest hub changes with dates (BRU in Mar 2027, IST in May 2027). Add sibling-airport transfers and a buffer night for separate tickets.

## 5. Sweep C: constructions
For the top 3–5: RT vs 2× one-way (price the return direction separately), open-jaw TYO⇄OSA (`matrix.py search --slice ZAG:TYO:D --slice OSA:ZAG:R`; Kiwi with `TYO,OSA` mixes automatically), secondary Japanese airports, ±3 days, Asian-hub self-transfer (only if it saves ≥ €150), free stopovers.

## 6. Seller + validation
- Cheapest trustworthy seller for each finalist: `kayak.py ... --show-links`, `booking_flights.py`, `aviasales.py`. Airline direct if within ~€20–40 (`flights/sources.md` §2 seller tiers).
- Validate (playbook §7): live today; bags on every leg (Kiwi bag data is wrong for Chinese carriers); single vs separate tickets; connection ≥ 2 h (one ticket) / ≥ 4–6 h or overnight (separate); airport changes (`~`); transit/entry rules (China, Korea K-ETA, UK ETA); ground plan on that weekday; total cost; risk.
- Log: `python3 $S/quotes.py add --trip <trip> ...` then `python3 $S/quotes.py list --trip <trip>`.

## 7. Report
Write `flights/searches/<trip>/report.md`, then commit and push.
- **Recommendation:** itinerary, total € pp incl. bags/ground, where to book, risk.
- **Top-5 table:** total | fare | bags | route/times | carriers | ticket type | seller | risk | link.
- Cheapest-at-any-risk alternative, timing verdict (vs "typical" range).
- **Manual checks for the user** with exact URLs: Skyscanner, Trip.com, the airline site (Air China: airchina.at, book Fri–Sun for ≤6% off), Secret Flying. These sites block bots, so never try to bypass captchas.
- Assumptions and what wasn't checked.

## 8. Monitor (if not buying now)
Offer a scheduled re-check (Routine: `create_trigger`, or `send_later` for one-offs) that re-runs the 2–3 winning queries + `deals.py --days 3`, appends quotes, and only reports on a drop below threshold. Suggest Google Flights price tracking to the user.

## Guardrails
- Never book, pay, create accounts or enter personal data. The user buys.
- Never present a price not fetched live this session. LLM-remembered fares are worthless.
- Hidden-city / throwaway only with explicit user opt-in; one-way, cabin bag only.
- Gulf routings: mention the 2026 Middle East disruption caveat.
- Keep pacing (scripts enforce it). On 429 / captcha: stop that source and move on.
