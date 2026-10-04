# Flight-hunt playbook: why we search the way we do

> **The commands live in one place:** the skill `.claude/skills/flight-hunt/SKILL.md` (§ numbers match
> this file). This file explains the **reasoning, decision rules and thresholds** behind each step, so a
> future session can adapt when reality changes. Built and tested 2026-10-04 (benchmarks B0–B4 in
> `benchmarks.md`, dry run in `searches/dryrun-tyo-2027-05/`). Update it when reality disagrees, with a date.

## 0. Golden rules (learned from our own tests, not folklore)

1. **No single engine finds the cheapest fare.**
   - Benchmark B1, same return query: momondo **€686** (MU+CZ, 2 bags), Aviasales €706, Booking €741, Kiwi €748, Skiplagged ≈ €762, Google Flights €811, ITA Matrix default €1,083 (forced MU: €715).
   - In the B4 dry run, momondo found the cheapest single ticket, and only a per-origin Kiwi scan found the #2 option (Air India VIE €708).
   - **Google Flights has no China Eastern / Air China / China Southern** on Europe→Japan, and those are usually the cheapest carriers.
   - Triangulate ≥ 4 independent inventories. Count each group once: Google/Matrix · Kiwi · Kayak/momondo · Skiplagged · Aviasales · Booking/Etraveli.
2. **Where you start matters more than any hack.**
   - Same dates on Google: VIE was €230–330 below ZAG.
   - The B1/B4 floor came from BUD, a €60–80 bus ride (plus a hotel night on some dates).
   - Hub fares (BRU, IST, ATH…) only win if they beat home by more than positioning + bags + nights, which in practice means ≥ €150–200.
3. **The cheapest hub changes with the dates:** BRU in March 2027, IST in May 2027 (Kiwi one-way scans), ATH on Google's Feb–Mar round-trip sweep. Re-scan for every date window.
4. **Engines hide carriers, and top-N lists crowd them out.**
   - Kiwi showed Air China ZAG only when filtered.
   - Matrix showed MU only when forced.
   - Multi-origin Kiwi missed Air India VIE.
   - Run per-carrier passes and the "exclude the current top carrier" loop.
5. **Bags decide rankings, and the data is dirty.**
   - Kiwi has no bag data for MU/CA/CZ: it says 0 and sells a ~€335 add-on, while OTAs show 2×23 kg on the same fare.
   - Google's bag pricing is wrong for LCCs.
   - MU also sells a bagless Basic fare in Europe.
   - So rank with **verified** bag allowances, and treat unknown as unknown (`quotes.py` `0?`).
6. **Price every construction:** return, 2× one-way, open-jaw, mixed carriers, positioning + long-haul, Asian-hub self-transfer. None wins consistently (the B1 floor was mixed MU out + CZ back).
7. **Rank by total per-person cost:** fare + bags + ground/positioning + hotel night + Japan-side backtrack + card FX + seller fees. Use `quotes.py`; it flags unknown ground (`?`) and unknown bags (`0?`).
8. **Never quote a price you haven't fetched live in this session.** LLM memory, cached calendars, AZair and Matrix `--no-avail` are hints or leads, not prices. Prices move fast (one leg went €308 → €806 in 30 min). Re-verify the top options right before reporting.
9. **Safety first, then cheapness.**
   - Separate tickets need buffers.
   - Risky or ToS-violating tricks only with explicit consent.
   - Prefer a trustworthy seller when it is within ~€20–40.
10. **Be polite to sites.**
    - Keep the scripts' pacing and run one search per site at a time.
    - After a Google 429 (gflights exit 4), stop using Google for the session.
    - Never defeat captchas. For blocked sites, give the user exact URLs.
11. **Log everything** (`quotes.py add`, `searches/<trip>/notes.md`), so the next session doesn't redo work.

## 1. Intake: why these questions
| Question | Why it matters |
|---|---|
| Home base | Sets the origin set, the ground costs and the break-even thresholds (`origins.md`) |
| **Party** (adults, children + ages, infants) and **every passport** | Fares are per bucket: the cheapest seat may be alone (Skiplagged MU went $806 → $2,516 for 2). Ground and car economics flip at 2+. Transit rules depend on the passport. Some tools show per-person prices, others party totals (`tools.md` table) |
| Student status | Turkish student fare (12–34): −10–15% + 40 kg. Qatar Student Club (18–30) |
| Japan airports, open-jaw OK? | Open-jaw saves the ~€80 backtrack. Secondary airports often price like Tokyo on KE/MU |
| Return / one-way, dates, flexibility | ±3 days and Mon–Wed departures save ~13%. Avoid CNY on China routings, sakura, Golden Week, Obon |
| Bags per person | Changes the ranking more than anything else (rule 5) |
| Risk appetite | Self-transfer, positioning flights and low-rated OTAs need the user's OK. Hidden-city stays NO unless the user explicitly opts in |
| Max ground hours | Caps how far we go (BUD/VIE/MUC/BEG by bus or night train) |
| Payment card | Foreign-currency sellers are only worth it with a zero-FX card |
| Budget / buy-now threshold | Sets the report verdict and the monitor threshold |

- **If the request already fixes origin, dates, party and bags,** search first with the `profile.md` defaults and list the open questions and assumptions in the notes and the report.
- **Thresholds the user states** override the profile defaults.

## 2. Recon: what "good" looks like, and which dates
- **Benchmarks** (`japan.md` §1):
  - Great: < €500 RT with a bag.
  - Normal: €650–950.
  - Under ~€350 RT is a mistake fare. Book fast; don't buy non-refundable extras for ~2 weeks.
- **Deals feed:** an active sale matching the window may already be the answer.
- **Calendars disagree because each is blind somewhere,** so pick 2–4 date pairs across **all** of them, then re-price live:
  - Google has no Chinese carriers.
  - Kiwi's calendar is the only round-trip calendar that includes MU/CA (`--nights`).
  - Matrix needs a forced carrier.
  - `skcal` only flexes the return date.
- **Google's "typical" range and 60-day history** (single-origin search only) tell you whether today is a dip. The ZAG–TYO history showed a €240 dip that lasted just 2 days.

## 3. Sweep A: home catchment, single tickets
- **Why all the tools:** each sees different inventory (rule 1).
- **Order of value** (B1/B4):
  1. momondo
  2. Kiwi origin-scan and per-origin search
  3. Kiwi MCP, which builds OW+OW pairs
  4. Aviasales, which has the best bag signal
  5. Booking
  6. Skiplagged
  7. Google, as the baseline for TK/QR/EY/LO/LH/AF/KL/KE/AY/Scoot
  8. Matrix with forced carriers, for the airline's own fare level, which drives the "book direct?" decision
- **Per-carrier passes** catch carriers that the top-N lists crowd out.
- **Carriers that mattered in tests:** CA, MU/FM, CZ, HO, AI, ET, TR (Scoot), KE, TK, QR, LO.

## 4. Sweep B: Europe-wide hubs + positioning
- **Goal:** a European city whose long-haul to Japan is so cheap that a positioning leg still wins.
  - Pattern 1: GDN→ARN by Ryanair + Air China ARN–PEK–HND ≈ €457 RT.
  - Pattern 2: Juneyao BRU–PVG–NRT at €327 one-way + Ryanair ZAG–CRL at €34.
- **Decision rule:** (best home RT − best hub RT) must be ≥ ~€150–200. Otherwise skip `positioning.py`; it took 8 min and found nothing in B4.
- **Costs to add for separate tickets:**
  - bag fees on the low-cost leg;
  - the sibling-airport transfer: CRL→BRU bus ~€15–20 / 1 h; BGY→MXP ~€10 / 1 h 15; WMI→WAW; SAW→IST;
  - a **buffer night** (€50–80) unless the gap is ≥ 4–6 h on the same day.
- **Rebuild the winning combination yourself** (separate bookings on the airlines' own sites) and compare it with the packaged self-transfer price from Kiwi or Aviasales. Building it yourself lets you choose a safe buffer.
- **Positioning on TK/PC to IST, LO to WAW or OU/JU** isn't in `positioning.py`. Price those with the Kiwi MCP.

## 5. Sweep C: constructions
- **Return vs 2× one-way:** full-service returns are usually far cheaper (ZAG €1,018 RT vs €1,323 2×OW). But Chinese carriers and mixed carriers can flip that, so price the return direction separately.
- **Open-jaw:** in TYO, out OSA, or the reverse. Our one clean test was +28% on a Star Alliance fare (B2), so always measure it. Add the Japan-side backtrack (~€80 Shinkansen, or Peach ≥ ¥3,990 + bag) to the plain return before comparing.
- **Secondary Japanese airports** (FUK, NGO, CTS, OKA, HIJ…) when the trip starts or ends there.
- **Asian-hub self-transfer** (ICN, TPE, PVG, PEK, HKG, BKK, SIN + a low-cost last leg): only if it saves ≥ €150 or the user wants a stopover. Check entry rules (Korea K-ETA).
- **Stopover add-ons:**
  - Turkish Stopover: a free hotel night in economy.
  - Finnair: up to 5 days.
  - China: 240-h visa-free transit. The 30-day visa-free entry runs only to 31 Dec 2026 unless renewed.

## 6. Seller selection + validation
- **Seller tiers** (`sources.md` §2):
  - Airline direct is preferred within ~€20–40.
  - Trip.com and Kiwi are OK.
  - eDreams/Opodo need caution: decline Prime and add-ons.
  - Etraveli brands (Gotogate, Mytrip, Flightnetwork, Booking.com flights) are high risk.
- **Air China:** book on its EU site Friday–Sunday for up to 6% off.
- **China Eastern:** compare Basic (no bag on Europe routes) vs Standard.

## 7. Validation checklist (never skip; SKILL §6)
- [ ] Price fetched live **today**, for the real party size, with source and timestamp. Not a lead.
- [ ] Bags (cabin and checked) on **every** leg, including positioning legs, and the cost to add any missing.
- [ ] Single ticket vs separate tickets. Connections: ≥ 2 h on one ticket at big hubs; ≥ 4–6 h or overnight on separate tickets.
- [ ] Airport changes (`~` in any route string); return lands at the departure airport; overnight layovers; arrival at 01:00?
- [ ] Transit/entry rules for each connection country and passport: China (airside OK; 240 h), Korea (K-ETA landside), UK (ETA), Schengen.
- [ ] Ground plan feasible on that weekday (`flixbus_ground.py --date`; trains too). Is a hotel night needed?
- [ ] Seller trust tier, fees at checkout, refund/change rules (fare basis via Matrix if relevant).
- [ ] Gulf routing? Add the 2026 conflict reliability caveat.
- [ ] Party extras: seats together. On mixed-carrier tickets the bag allowance follows the most significant carrier, so read it at checkout.
- [ ] Total per person and for the party (`quotes.py list --latest --need-bag …`), plus a risk rating (safe / low / moderate / risky / tos).

## 8. Report
Use the template `searches/_template/report.md`. Keep it skimmable:
1. A recommendation with all-in totals.
2. A top-5 table.
3. The cheapest option at any risk.
4. A timing verdict.
5. **Manual checks for the user** with exact URLs. Ask them to paste back what they see.
6. Assumptions.

Save the report, then commit and push.

## 9. Monitor (if not booking now)
- **Ask the user** to turn on **Google Flights price tracking** for the chosen dates and "any dates", and optionally Skyscanner/Kayak alerts or Secret Flying/Jack's Flight Club e-mails.
- **Watchlist:** `searches/<trip>/watch.json` with 3–6 like-for-like checks (rules in SKILL §8 and `tools.md` §10b). Commit and push it **before** creating a Routine; fresh sessions only see what's pushed.
- **Routine:** with the user's OK, create one with `create_trigger`. Make it recurring (daily, at a jittered morning time in Europe/Zagreb), with a fresh session per fire and push notifications on. Use a standalone prompt like:
  > In repo Spuzy24/Expedition30, branch claude/nice-albattani-0rz6ea: run `bash flights/scripts/setup.sh`, then `python3 flights/scripts/monitor.py flights/searches/<trip>/watch.json` and `python3 flights/scripts/deals.py --days 2`. `git pull --rebase`, then commit and push the updated watch_state.json. If any line starts with ALERT, or a deal mentions Japan from VIE/BUD/ZAG/LJU/BEG/MUC/VCE/MXP, re-verify that fare (playbook §7, live, with bags and ground) and report it with the booking link. If the first travel date is ≤ 14 days away, or the trip folder says BOOKED, disable this Routine (update_trigger enabled=false) and say so. Otherwise reply "no change" in one line.

  Use `send_later` for a one-off check, e.g. before a known sale such as Qatar Black Friday in late November.
- **Cost:** each run takes ~2–5 min. Daily is plenty, because fares move in multi-day steps.
- **Expected sale moments:** Qatar Black Friday (late November), Air China's weekend discount, Chinese carriers' promos (travel-dealz), LOT and Finnair sales.

## 10. Time budget & stopping rule
- **Time:** a full hunt takes ~1–1.5 h of tool time (the B4 dry run took 50 min).
- **Stop when** all three hold:
  - 4+ independent inventories (counted as in rule 1) agree on the floor within ~5%;
  - every construction in §5 has been priced;
  - the top 3 are validated.
- **Report what was NOT checked** (blocked sites) as manual items for the user.
