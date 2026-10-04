# Flight-hunt playbook: cheapest real, bookable ticket (home region → Japan)

> The method, in order. `SKILL.md` (.claude/skills/flight-hunt) is the short operational
> checklist; this file is the full reasoning. Built and tested 2026-10-04; update it when
> reality disagrees (and note the date).

## 0. Golden rules (learned the hard way, not folklore)

1. **No single engine finds the cheapest fare.** Benchmark B1 (`benchmarks.md`), same RT query: momondo **€686** (MU+CZ, 2 bags), Aviasales €706, Booking €741, Kiwi €748, Skiplagged ≈€762, Google Flights €811, ITA Matrix €1,083. **Google Flights did not show China Eastern / Air China at all**, and those are the cheapest carriers to Japan. **ITA Matrix's default answer is pruned**; forced with `--route "MU+"` it found €715 (B1). Always triangulate ≥ 4 independent inventories, and never rely on Google alone.
2. **Where you start matters more than any hack.** In the Google test (RT 10–24 Feb 2027) VIE was €230–330 below ZAG for the same dates, and one-way hub fares from BRU/IST undercut ZAG single tickets in the Kiwi origin-scans. Price the ground or positioning leg and compare totals.
3. **The cheapest hub changes with the dates:** BRU in March 2027, IST in May 2027. Re-run the origin scan for each date window.
4. **Engines hide carriers.** Kiwi only showed Air China ZAG→PEK→HND when filtered by carrier. Air China web promos are often absent from GF/ITA. Run per-carrier queries for the key carriers.
5. **Price every construction:** return, 2× one-way, open-jaw (TYO/OSA), mixed carriers, positioning + long-haul, Asian-hub self-transfer. None wins consistently.
6. **Rank by total per-person cost:** fare + bags + ground/positioning + hotel night + card FX + seller fees. Use `quotes.py`.
7. **Never quote a price you haven't fetched live in this session.** LLM memory, cached calendars and AZair are hints, not prices. Re-verify the top options right before reporting.
8. **Safety first, then cheapness:** separate tickets need buffers. Risky or ToS-violating tricks only with explicit consent. Prefer a trustworthy seller within ~€20–40.
9. **Be polite to sites:** keep the scripts' pacing (≥3 s Google, ≥5 s Matrix). Never defeat captchas. For blocked sites, give the user exact URLs to check.
10. **Log everything** (`quotes.py add`, `searches/<trip>/`). The next session should not redo work.

## 1. Intake (before any searching)
Fill `profile.md`. Ask everything still `TBD` in **one batched message**:
- Home base (assumed Zagreb), number of travelers, ages/student status (TK 12–34, QR 18–30), passport(s).
- Japan airports wanted (TYO = HND+NRT, OSA = KIX(+UKB/ITM), NGO, FUK, CTS, OKA…), and whether open-jaw is OK.
- Date window, trip length, flexibility (± days, blackout days), one-way or return.
- Bags (cabin only? 1×23 kg?), max stops/duration, overnight layovers OK?
- Risk appetite: self-transfer? positioning flights? hidden-city (default NO)? low-rated OTAs?
- Payment card (zero-FX?), existing miles.
- Budget / "buy immediately below €X" threshold.

If the user wants results before answering, proceed with the defaults in `profile.md` and say so.

Create the trip folder: `flights/searches/<trip-id>/` (e.g. `tyo-2027-03`) with `notes.md` (log of
what was searched, when, results), and use `--trip <trip-id>` / `--log <trip-id>` in quote logging.

## 2. Recon (≈10 min): know what "good" looks like and where the cheap dates are
1. **Benchmarks:** `japan.md` §1. Great < €500 RT with bag; normal €650–950. A fare under ~€350 RT is a mistake fare, so book fast.
2. **Deal scan:** `python3 scripts/deals.py --days 60` (+ `--any-asia` for hub ideas). An active sale matching the dates may be the answer already.
3. **Cheap dates:** for 2–3 representative origins (ZAG, VIE, BUD) and the Japan targets:
   - `gflights.py calendar --from VIE --to TYO --start … --end … [--stay 12-16]` (Google's cheapest-per-day)
   - `gflights.py grid …` for return date pairs
   - `kiwi_graphql.py calendar --from ZAG --to TYO --dates …`
   - `matrix.py calendar …` (fare-engine accurate, slow)
   - `mcp_flights.py skcal ZAG TYO <date> --ret <date>`

   Avoid peaks (`japan.md` §4: CNY on China routings, sakura, Golden Week, Obon, holidays).
4. **Price history:** Google's "typical" range and 60-day history (in `gflights.py` output). Tells you whether today is a dip or a peak.

## 3. Sweep A: home catchment, single tickets (≈15 min)
Origins: `origins.md` set 1–7 (ZAG, VIE, BUD, BEG, LJU, GRZ, MUC, VCE, TRS) → all wanted Japan airports.
Run **all** of these (each sees different inventory). Most productive first (per benchmark B1):
- `kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart D [--return R]` (then `--flex 3`, `--nearby`; also `--site www.kayak.de`). **Found the cheapest RT in B1** incl. mixed-carrier tickets.
- `gflights.py search --from ZAG,LJU,GRZ,VIE,BUD,BEG,VCE --to TYO,OSA --date D [--return R]` (airline-direct baseline for TK/QR/EY/LO/LH/AF/KL/KE/AY; misses Chinese carriers)
- `mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD,BEG,VCE,TRS,MUC TYO,OSA D --flex 3 [--ret R --ret-flex 3] [--bags 1]`
- `kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates D1..D2 [--return-dates …] [--checked-bags 1]`
- `aviasales.py --from BUD --to TYO --depart D [--return R]` and `booking_flights.py …` (browser, ~30–45 s each; per origin)
- `mcp_flights.py sk ZAG TYO D [--ret R]`, then repeat for VIE and BUD
- `matrix.py search --from BUD --to TYO --date D [--return R] --carriers MU,CA,CZ,HU,KE,TK,QR,EK,EY,LO,AY` (~40 s per carrier; the default answer is pruned). Add `--no-avail` to see fare levels without confirmed seats (leads only).

Then **per-carrier passes** (each engine's top-15 hides carriers):
- `mcp_flights.py kiwi ZAG,VIE,BUD TYO,OSA D --flex 3 --only-airlines CA`, then repeat with `MU,FM`, `CZ`, `HU`, `KE,OZ`, `TK`, `QR`, `EY`, `LO`, `AY`, `NH`
- `matrix.py search … --route "CA+"` (and MU+, KE+ …) (sales city defaults to the departure city; changing it made no difference in tests)

Log the best 2–3 per source/origin with `quotes.py add` (or the scripts' `--log`).

## 4. Sweep B: Europe-wide long-haul origin + positioning (≈20 min)
Goal: find a European city whose long-haul to Japan is so cheap that a positioning leg still wins
(the ~€457 RT GDN→ARN→PEK→HND pattern; €327 one-way BRU–PVG–NRT on Juneyao in Mar 2027).
1. `kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates …` (cheapest European origin per Japanese city)
2. `kiwi_graphql.py origin-scan --to TYO,OSA --dates … --origins ZAG,VIE,BUD,BEG,MUC,VCE,MXP,FCO,BRU,AMS,CDG,FRA,IST,WAW,HEL,ARN,CPH,OSL,DUB,LHR,MAD,BCN,ATH,PRG,OTP` (+ `--checked-bags 1`)
3. `gflights.py sweep --origins europe --to TYO,OSA --start … --end … --stay N --cache searches/<trip>/gf_sweep.json --details 5` (resumable)
4. For the top 3–5 hubs: `positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --hubs <hubs> --to TYO,OSA --dates …`, and `--direction back` for the return.
   - Positioning on carriers other than FR/W6 (TK/PC to IST, LO to WAW, OU/JU…) isn't covered. Price those with `mcp_flights.py kiwi ZAG <HUB> D` or `gflights.py search`.
   - Add the sibling-airport transfer (CRL→BRU bus ~€15–20/1 h; BGY→MXP ~€10/1h15; WMI→WAW; SAW→IST) and a **buffer night** (€50–80) unless the gap is ≥ 4–6 h on the same day.
5. Rebuild the winning combo **DIY** (separate bookings on the airlines' own sites) and compare with
   the Kiwi/Aviasales packaged self-transfer price. DIY lets you choose a safe buffer.

## 5. Sweep C: constructions (≈15 min)
For the best 3–5 candidates so far:
- **Return vs 2× one-way:** price the reverse one-way separately (`… TYO,OSA ZAG,VIE,BUD D2 --flex 3`). Mixed carriers (e.g. MU out, CA back) can win.
- **Open-jaw:** in TYO, out OSA (and the reverse): `matrix.py search --slice ZAG:TYO:D1 --slice OSA:ZAG:D2`, `gflights` multi-city if supported, airline multi-city. Usually ≈ RT price and saves a ¥14,000 Shinkansen.
- **Secondary Japanese airports** (FUK, NGO, CTS, OKA, HIJ…) when the itinerary starts or ends there. KE/MU often price them like Tokyo.
- **Asian-hub self-transfer:** Europe→ICN/TPE/PVG/PEK/HKG/BKK/SIN + LCC last leg (`japan.md` §6). Only when the Europe→hub fare is ≥ ~€150 below a through ticket, or the user wants a free stopover. Check transit/entry rules (K-ETA for Korea).
- **Stopover value-adds:** Turkish Stopover (free hotel night in economy), Finnair, China (240-h visa-free transit; the 30-day visa-free entry only to 31 Dec 2026 unless renewed).
- **Nearby-date shifts:** ±3 days, Mon–Wed departures.

## 6. Seller selection: cheapest *trustworthy* seller for each finalist (≈10 min)
For each of the top 3 itineraries (same flights):
1. `kayak.py --site www.momondo.de … --show-links` and `kayak.de` (provider list incl. Trip.com = CTRIPAIR, Opodo, Kiwi)
2. `booking_flights.py`, `aviasales.py` (Etraveli/other OTAs)
3. Airline direct: give the user the URL (sites block bots). Air China: book Fri–Sun (≤6% web discount).
4. Trip.com / Skyscanner: give the user the URL (manual).
5. Apply the seller rules in `sources.md` §2. **Airline direct if within ~€20–40.**

## 7. Validate (never skip)
For each finalist, check and write down:
- [ ] Price fetched live **today** in this session, with source + timestamp (quote log `ts`)
- [ ] Bags included (cabin/checked) for **every** leg and the cost to add the needed bags
- [ ] Single ticket vs separate tickets; connection times (≥ 2 h on one ticket at big hubs; ≥ 4–6 h or overnight on separate tickets)
- [ ] Airport changes (`~` in `mcp_flights.py` routes, CRL→BRU, ICN→GMP…); overnight layovers; arrival at 01:00?
- [ ] Transit/entry rules for each connection country (China visa-free/240 h; Korea K-ETA landside; UK ETA; Schengen)
- [ ] Ground/positioning plan feasible on that weekday (`flixbus_ground.py --date`), hotel night needed?
- [ ] Seller trust tier, fees at checkout, refund/change rules (fare basis via Matrix if relevant)
- [ ] Total per-person cost (`quotes.py list --trip …`) and risk rating (safe/low/moderate/risky/tos)
- [ ] Gulf routing? Add the 2026 conflict reliability caveat.
- [ ] Party extras: seats together (fees on many fares); mixed-carrier tickets: bag allowance per the most significant carrier, so read it at checkout.

## 8. Report to the user
Use this structure (keep it skimmable):
1. **Recommendation:** one itinerary, total € pp, what's included, where to book, risk, why.
2. **Top 5 table:** total € | fare € | bags | route & times | carriers | ticket type | seller | risk | link.
3. **Cheapest-at-any-risk** option, if different, with its risks spelled out.
4. **Manual checks for the user** (2–5 min): exact URLs for Skyscanner, Trip.com, the airline site (e.g. airchina.at), Secret Flying origin page. Ask them to paste back what they see.
5. **Verdict on timing:** price vs the "typical" range/history; book now or monitor?
6. What we didn't cover / assumptions.

Save the report to `flights/searches/<trip>/report.md` and commit.

## 9. Monitor (if not booking now)
- Ask the user to turn on **Google Flights price tracking** for the chosen dates and "any dates" (email alerts), and optionally Skyscanner/Kayak alerts or Secret Flying/Jack's Flight Club e-mails.
- Write a watchlist `flights/searches/<trip>/watch.json` with the 3–6 queries that found the best options. Include at least one carrier-forced Matrix query and one momondo query. Format in `scripts/monitor.py --help`. Test it: `python3 flights/scripts/monitor.py flights/searches/<trip>/watch.json`. It tracks the min € per check in `watch_state.json` and prints `ALERT` lines for a new low or ≤ threshold.
- With the user's OK, create a **Routine** (`create_trigger`, recurring, e.g. daily at a jittered morning time in Europe/Zagreb, fresh session per fire, push notification on) with a standalone prompt like:
  > In repo Spuzy24/Expedition30, branch claude/nice-albattani-0rz6ea: run `bash flights/scripts/setup.sh`, then `python3 flights/scripts/monitor.py flights/searches/<trip>/watch.json` and `python3 flights/scripts/deals.py --days 2`. Commit and push the updated watch_state.json. If any line starts with ALERT, or a deal mentions Japan from VIE/BUD/ZAG/LJU/BEG/MUC/VCE/MXP, re-verify that fare (playbook §7) and report it with the booking link. Otherwise reply "no change" in one line.

  Use `send_later` for a one-off check (e.g. before a known sale such as Qatar Black Friday).
- Each run costs ~2–5 min; daily is plenty (fares move in multi-day steps).
- Book on a dip: the ZAG–TYO history showed a €240 drop lasting only 2 days.
- Expected sale moments: Qatar Black Friday (late Nov), Air China weekend discount, Chinese carriers' promos (travel-dealz), LOT/Finnair sales.

## 10. Time budget & stopping rule
A full hunt is ~1.5–2 h of tool time. Stop when 4+ independent inventories (count each group once: Google Flights/Matrix · Kiwi MCP/GraphQL · Kayak/momondo · Skiplagged · Aviasales · Booking/Etraveli) agree on the floor
(within ~5%), every construction in §5 has been priced, and the top 3 are validated. Report what
was NOT checked (blocked sites) as manual items for the user.
