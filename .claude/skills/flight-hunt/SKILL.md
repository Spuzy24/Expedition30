---
name: flight-hunt
description: Find the user the cheapest real, bookable flight ticket (cheap flights, airfare, plane tickets), built for home region Zagreb/Central Europe → Japan (Tokyo, Osaka…); other routes need the adaptations in §1. Searches nearby departure airports and Europe-wide hubs with positioning flights, across momondo/Kayak, Kiwi, Skiplagged, Aviasales, Booking.com, Google Flights, ITA Matrix, Ryanair/Wizz and deal/error-fare feeds; compares return / one-ways / open-jaw / self-transfer, ranks by true total cost (bags, ground, hotel), and reports or sets up price monitoring. Use when the user asks to find, compare, check or monitor flight prices or deals, or to plan buying a ticket.
---

# Flight hunt: operational checklist

- **Context:** `CLAUDE.md`. **Reasoning:** `flights/playbook.md`. **Every flag:** `flights/tools.md`.
- **Working directory:** run from the repo root with `S=flights/scripts`.
- **Status:** commands verified 2026-10-04 after a full dry run and QA (`flights/searches/dryrun-tyo-2027-05/`).
- **Long sessions:** re-read this file before reporting (the docs may have changed).

## 0. Setup
```bash
bash $S/setup.sh            # deps, Playwright pin, Chromium proxy-CA, smoke tests (~5 s; exit≠0 → tools.md §12)
bash $S/setup.sh --full     # + one live request per core scraper (~30–90 s) if anything looks broken
```

## 1. Intake
- **Ask in ONE message.** Read `flights/profile.md`, then ask the user every `TBD` at once:
  - home base (assumed Zagreb);
  - **party:** adults / children with ages / infants, and **every passport**;
  - student status;
  - Japan airports, and whether open-jaw is OK;
  - return or one-way;
  - date window, trip length, flexibility;
  - bags per person;
  - risk appetite: self-transfer, positioning flights (hidden-city defaults to NO);
  - max ground hours to an airport;
  - payment card;
  - budget.
- **If the request already fixes origin, dates, party and bags,** start searching with the profile defaults. List the open questions and assumptions at the top of `notes.md` and of the report. Thresholds the user states override the profile defaults.
- **Disclose once:** several tools use sites' unofficial endpoints at low volume. If the user objects, use only the manual URLs plus the public MCP servers.
- **Trip folder:** `cp -r flights/searches/_template flights/searches/<trip>` (e.g. `tyo-2027-05`). Log every search in its `notes.md`.
- **Party size:**
  - Pass `--adults N` everywhere. The cheapest bucket may hold one seat, so a 1-adult price may not exist for two.
  - Price columns say `EUR/pp` or `EUR total`:
    - **momondo/Kayak** show per person.
    - **Kiwi, Skiplagged, Aviasales, Booking, Google, Matrix rows and positioning** show the party **total**.
  - Children and infants: no script prices them, so check on the seller's site.
  - Log totals with `quotes.py add --per total --pax N`.
- **Home not Zagreb:**
  1. `kiwi_graphql.py places --near <IATA> --radius 400`.
  2. `flixbus_ground.py --from "<City>" --to <cities> --date D` and `--drive --home <lon,lat>`.
  3. `quotes.py ground-init --trip <trip>`, then edit **that** per-trip `ground.json`. Never overwrite the shared one.
  4. Replace ZAG and the catchment in every command.
  5. `deals.py --region-words <city names>`.
  6. Add a dated note to `origins.md`.
- **Destination not Japan:**
  - Swap TYO,OSA / `Country:JP` / `--region japan` for the destination's codes. Use `positioning.py --to <codes>` and `deals.py --keywords <words>`.
  - Build benchmarks from Google's "typical" range (single-origin `gflights.py search`) and the deal feeds.
  - Check entry and transit rules. `japan.md` doesn't transfer.

## 2. Recon (~5 min): what "good" is, and which dates
```bash
python3 $S/deals.py --days 60                                    # live sales / error fares
python3 $S/gflights.py calendar --from VIE --to TYO --start D1 --end D2 --stay N --bags 1   # ONE stay length (1–2 requests); no Chinese carriers
python3 $S/kiwi_graphql.py calendar --from BUD --to TYO,OSA --dates D1..D2 --nights N-M  # round-trip calendar incl. Chinese carriers
python3 $S/matrix.py calendar --from BUD --to TYO --start D1 --end D2 --stay N --route "MU+" --route-ret "MU+"   # fare level (~40 s)
```
- **Benchmarks:** `flights/japan.md` §1. Great is under €500 RT with a bag; normal is €650–950.
- **Pick dates:** take 2–4 date pairs across **all** calendars. Calendar prices are cached, so re-price them in §3.
- Google's "typical" range only appears on single-origin searches.

## 3. Sweep A: home catchment, single tickets (~15 min)
Origins: ZAG, LJU, GRZ, VIE, BUD, BEG, VCE, TRS, MUC (`flights/origins.md`). Run **all** of these; each sees different inventory:
```bash
python3 $S/kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart D --return R --flex 3 --pages 2 --adults N   # best source in B1/B4; auto-dedupe
python3 $S/kiwi_graphql.py origin-scan --origins ZAG,LJU,GRZ,VIE,BUD,BEG,VCE,TRS,MUC --to TYO,OSA --dates D1..D2 --return-dates R1..R2 --adults N
python3 $S/kiwi_graphql.py search --from ZAG,VIE,BUD --to TYO,OSA --dates D1..D2 --return-dates R1..R2 --adults N   # per origin + cross-airport returns
python3 $S/mcp_flights.py kiwi ZAG,VIE,BUD TYO,OSA D --flex 3 --ret R --ret-flex 3 --adults N   # also builds OW+OW pairs (tkt column)
python3 $S/aviasales.py --from BUD --to TYO --depart D --return R --adults N     # read cheapest_with_baggage; repeat per origin
python3 $S/booking_flights.py --from BUD --to TYO --depart D --return R --adults N
python3 $S/mcp_flights.py sk BUD TYO D --ret R --adults N                        # hidden-city OFF by default; EUR column
python3 $S/gflights.py search --from ZAG,LJU,GRZ,VIE,BUD,BEG,VCE --to TYO,OSA --date D --return R --bags 1 --adults N   # airline baseline; NO Chinese carriers
python3 $S/matrix.py search --from BUD --to TYO --date D --return R --carriers MU,CA,QR --adults N   # + carriers seen elsewhere; ~40 s each
```
- **Bags:**
  - **Never rank on Kiwi's `--bags` / `--checked-bags` prices.** Kiwi has no bag data for MU/CA/CZ and adds a ~€335 RT bag fee.
  - Google's bag-inclusive prices are unreliable for LCCs (Scoot, ZIPAIR).
  - Use the OTA bag columns and Aviasales' `cheapest_with_baggage`.
  - A MU price clearly below the Standard level is probably **Basic** (0 bags on Europe routes).
- **Carrier passes** (top-N lists hide carriers):
  1. Take every carrier in the top results, plus CA, MU/FM, CZ, HU/HO, AI, ET, TR/SQ, CX, KE/OZ, TK, QR, EY, EK, LO, AY, NH/JL.
  2. For each, run `mcp_flights.py kiwi … --only-airlines XX` and `matrix.py … --carriers XX`.
  3. Then repeat `--exclude-airlines <current top carrier>` until no new carrier appears.
- **Google exit 4 means rate-limited:** stop using Google for this session.

## 4. Sweep B: Europe-wide hubs + positioning (~10–20 min)
```bash
python3 $S/kiwi_graphql.py origin-scan --to TYO,OSA --dates D1..D2 --return-dates R1..R2 --origins BRU,IST,MXP,FCO,ATH,AMS,CDG,FRA,WAW,HEL,ARN,CPH,DUB,LHR,MAD,PRG,OTP
python3 $S/positioning.py --home ZAG,VIE,BUD --hubs <top 2–4 hubs> --to TYO,OSA --dates D1..D2 --return-dates R1..R2 \
        --adults N --checked-bags 1 --pos-bag-eur 40 --compare-home-rt <best home RT €>
```
- **Skip positioning** unless (best home RT − best hub RT) ≥ ~€150–200. `--compare-home-rt` prints skip lines.
- **Separate tickets** add sibling-airport transfers (CRL→BRU, BGY→MXP…) and a buffer night.
- **Optional:** `gflights.py sweep --origins europe … --cache flights/searches/<trip>/gf_sweep.json`, only with ≥ 30 min of Google budget and no 429 so far.

## 5. Sweep C: constructions
- **RT vs 2× one-way.** Discover the return direction:
  ```bash
  kiwi_graphql.py per-city --from TYO,OSA --to Continent:europe --dates R1..R2
  kiwi_graphql.py search --from TYO,OSA --to ZAG@400 --dates R1..R2
  kayak.py --from TYO,OSA --to ZAG,VIE,BUD --depart R
  mcp_flights.py kiwi TYO,OSA ZAG,VIE,BUD R --flex 3
  ```
  Log a 2× one-way construction as ONE combined row.
- **Open-jaw:**
  - Matrix: `matrix.py search --slice BUD:TYO:D --slice OSA:BUD:R --carriers MU,CA,QR` forces every slice. Per-slice routes use `--slice O:D:DATE:ROUTE`.
  - Kiwi and momondo mix cities on their own when given `TYO,OSA`, so read the legs.
  - Manual: Google Flights multi-city, Trip.com, the airline.
  - Add the Japan-side backtrack (~€80 Shinkansen) to the plain RT's total with `--extras`.
- **Other constructions:**
  - secondary Japanese airports;
  - ±3 days;
  - Asian-hub self-transfer, only if it saves ≥ €150 (Korea needs a K-ETA);
  - free stopovers (Turkish, Finnair, China 240 h).

## 6. Seller + validation
- **Seller:**
  - Run `kayak.py … --show-links`, `booking_flights.py` and `aviasales.py`.
  - Book with the airline directly if it's within ~€20–40 (seller tiers: `flights/sources.md` §2).
  - Air China: book Fri–Sun for up to 6% off.
- **Validate each finalist** (playbook §7):
  - **Price:** live today for the real party size; not a lead (Matrix `--no-avail`).
  - **Bags:** checked on **every** leg, including positioning legs.
  - **Ticket type:** single vs separate tickets (`TICKET` / `tkt` / `pnr` columns).
  - **Connections:** ≥ 2 h on one ticket; ≥ 4–6 h or overnight on separate tickets.
  - **Airport change:** a **`~`** in any tool's route string means you change airports.
  - **Return airport:** must be the departure airport. Multi-origin round trips may not be.
  - **Entry/transit rules** for every passport (China, Korea K-ETA, UK ETA).
  - **Ground:** `flixbus_ground.py --date <day before/of flight>`; hotel night needed? (BUD often.)
  - **Seat fees** for the party.
  - **Total cost and risk.**
- **Log, then rank:**
  ```bash
  python3 $S/quotes.py add --trip <trip> --source … --seller … --origin … --dest … --out D --ret R --price … --carriers … \
      [--per total --pax N] [--bags-included 2x23 | --bag-cost €] [--ground € for origins not in ground.json] [--extras € hotel/backtrack] \
      [--self-transfer --risk moderate] [--lead] [--supersedes #] [--live]
  python3 $S/quotes.py list --trip <trip> --latest --need-bag 70     # per-person totals; '?'=ground unknown, '0?'=bag unknown
  ```

## 7. Report
Write `flights/searches/<trip>/report.md` from the template, then commit and push. If file writes are blocked (e.g. in a subagent), return the report text to the caller.
- **Recommendation:** the itinerary, total € per person (and for the party) including bags, ground and hotel, where to book, and the risk.
- **Top-5 table:** total | fare | bags | route/times | carriers | ticket type | seller | risk | checked at checkout? | link.
- **Cheapest option at any risk,** and a **timing verdict** against the benchmarks and Google's "typical" range.
- **Manual checks for the user,** with exact URLs (templates in `flights/tools.md` §11):
  - Skyscanner and Trip.com;
  - the winning airline's site (airchina.at, ceair.com, airindia.com, flyscoot.com…);
  - Google Flights in their own browser: the **"Cheapest" tab** and **multi-city**;
  - Secret Flying.

  Never try to bypass a captcha.
- **Assumptions,** and what wasn't checked.

## 8. Monitor (if not buying now)
- Write `flights/searches/<trip>/watch.json` with 3–6 **like-for-like** checks:
  - one origin per check, with the real `--adults`;
  - no Kiwi bag flags;
  - `--no-self-transfer` if the user wants single tickets;
  - never `--no-avail`;
  - include one carrier-forced Matrix check and one momondo check.
- Commit and push the file, then test it with `python3 $S/monitor.py <watch.json>`. It prints `ALERT` on a new low, or the first time a check goes under the threshold. Prices are fare-only minimums.
- With the user's OK, create a daily Routine from the prompt in playbook §9 (`send_later` for one-offs). Disable it when the user buys or travel is ≤ 14 days away.
- Also suggest Google Flights price tracking to the user.

## Guardrails
- Never book, pay, log in, create accounts or enter personal data. The user buys.
- Never present a price you didn't fetch live this session. LLM-remembered fares are worthless.
- Hidden-city and throwaway tickets need explicit opt-in, and are for one-way trips with a cabin bag only. Skiplagged `--hidden-city` and Kiwi `--hacks` are off by default.
- Gulf routings: mention the 2026 Middle East disruption caveat.
- Keep the scripts' pacing, and run one search per site at a time. On a 429, a captcha or "verify you are human", stop that source. Never rotate IPs or user agents.
