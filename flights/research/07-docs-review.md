# 07: Review of the flight-hunt living docs (2026-10-04)

**Reviewed at:** commit `2ab02e2` on `claude/nice-albattani-0rz6ea`. Two commits (`70743f3`, `2ab02e2`: `monitor.py`, benchmark B3, the monitoring Routine, fact 4 rewrite) landed while this review ran, and the review covers them. Line numbers are for that commit.

**Scope:**
- Reviewed files: `CLAUDE.md`, `.claude/skills/flight-hunt/SKILL.md`, `flights/{README,profile,playbook,sources,tools,tricks,japan,origins,benchmarks}.md` and `flights/searches/ground.json`.
- Evidence used:
  - research snapshots `00`–`06`;
  - the `--help` of every script;
  - the source of `quotes.py`, `mcp_flights.py`, `kayak.py`, `kiwi_graphql.py`, `matrix.py`, `positioning.py`, `gflights.py`, `deals.py`, `monitor.py`, `aviasales.py`, `booking_flights.py` and `ryanair_wizz.py`;
  - the dry-run quote log that the load-testing agent was writing at the same time (`flights/searches/quotes.jsonl`, untracked).
- No flight searches were run.
- One web check: Turkish Airlines' student fare is for ages 12–34, which matches `profile.md`. Source: [turkishairlines.com student page](https://www.turkishairlines.com/en-int/student-flight-discount/).

**Priority key:**
- **P0:** would cause a wrong or missed result, or a wrong ranking.
- **P1:** important. It contradicts the evidence, gives unsafe defaults, or leaves a gap a future session will fall into.
- **P2:** polish.

**How to use this file.** Each item gives the file and line, the exact current text, the problem, and the exact replacement text. Where several items touch the same line, the replacement given once already includes all of them, and the other items say so.

| Priority | Count | Themes |
|---|---|---|
| P0 | 3 | passenger count; €0 ground for unlisted origins; bag fees never added for bagless fares |
| P1 | 18 | hidden-city default, hidden airport changes, return to another airport, open-jaw evidence and tooling, fact 4/B3 overclaim, OW/RT ranking, recon bias, buffer contradictions, China entry for 2027, Wizz contradiction, non-Zagreb home, non-Japan destination, monitor semantics, Google Flights "Cheapest" tab, single-ticket claim, automated-access disclosure, Japan-side costs, `--log` bugs |
| P2 | 20 | cross-references, counts, `N` routing code, cwd conventions, missing flags, date semantics, templates, drift |

**Commands that are correct.** Every command in `SKILL.md`, the `CLAUDE.md` quick commands and the `tools.md` code blocks was checked against `--help`. Flags, subcommands and argument order all exist and parse. The problems are about **behaviour** (defaults, hidden semantics, cwd), not syntax:
- P1-1: the `sk` command includes hidden-city fares by default.
- P1-4: `--slice` ignores `--route-ret`, and `gflights` has no multi-city search.
- P1-7: `kiwi_graphql.py calendar` is one-way only.
- P2-7: working-directory mix-ups.

---

## P0: would cause a wrong or missed result

### P0-1. Party size is never threaded through the hunt (every command and the quote log assume 1 adult)

**Files:** `SKILL.md` L19, `tools.md` L6, `CLAUDE.md` L44.

**Current text (`SKILL.md` L19):**
~~~text
- Read `flights/profile.md`. Ask the user every `TBD` in ONE message: home base (assumed Zagreb), pax/ages/student, Japan airports + open-jaw OK?, date window/trip length/flex, bags, risk appetite (self-transfer, positioning flights, hidden-city default NO), payment card, budget.
~~~
**Current text (`tools.md` L6):**
~~~text
> Dates: `YYYY-MM-DD`; ranges `A..B` (Kiwi also `D+-3`). Prices are 1 adult, EUR, unless set.
~~~
**Current text (`CLAUDE.md` L44):**
~~~text
  The earlier trip was for 2 travelers (Sebastijan & Mia), so ask whether this one is too (car/ground economics change at 2+).
~~~
**Problem.** The last trip in this repo was 2 adults (`progress.md`), so a 2-person hunt is likely. Party size never reaches the search commands, and part of the toolkit cannot handle it:
- **The commands are all 1-adult.** Not one command in `SKILL.md`, `CLAUDE.md` or `playbook.md` passes `--adults`.
- **Two tools ignore party size entirely:**
  - `positioning.py` hard-codes `adults=1` (L59).
  - `ryanair_wizz.py` hard-codes `"adultCount": 1` (L188).
- **`mcp_flights.py --log` never passes `--pax`/`--per total`.** A Kiwi price for `--adults 2` is most likely the party total, and it would be logged and ranked as a per-person fare.
- **No tool searches child or infant fares.** `kiwi_graphql` and `gflights` send 0 children.
- **A 1-adult price may not exist for two.** The cheapest booking class often has a single seat left, so the second seat sells at a higher price.
- **Display conventions differ by site.** Some sites show the per-person price and some show the party total. This was never tested in this toolkit.
- **The intake list omits key questions.** It does not ask for the passport(s), one-way vs return, or children. The passport is needed for every transit rule in the docs.

**Proposed replacement (`SKILL.md` L19):**
~~~text
- Read `flights/profile.md`. Ask the user every `TBD` in ONE message: home base (assumed Zagreb); **party** (adults / children with ages / infants) and **every passport**; student status; Japan airports + open-jaw OK?; return or one-way; date window / trip length / flex; bags per person; risk appetite (self-transfer, positioning flights, hidden-city default NO); max ground hours to an airport; payment card; budget.
- **Party size:** run every search with the real `--adults N` (the cheapest bucket can have one seat left, so a 1-adult price may not exist for two). Children/infants: no script supports them, so price them on the seller's site and say so. Log party totals with `quotes.py add --per total --pax N`. `positioning.py`, `ryanair_wizz.py` and `mcp_flights.py --log` are 1-adult only (see `tools.md` §Passengers).
~~~
**Proposed replacement (`tools.md` L6):**
~~~text
> Dates: `YYYY-MM-DD`; ranges `A..B` (Kiwi also `D+-3`). Prices are 1 adult, EUR, unless set.
> **Passengers:** pass `--adults N` (gflights, matrix, kayak, mcp_flights kiwi/sk, kiwi_graphql, aviasales, booking_flights). Whether a tool prints the per-person price or the party TOTAL was not verified on 2026-10-04: before the first multi-pax hunt, run one query with `--adults 1` and `--adults 2` per tool and note which ones double. `positioning.py` and `ryanair_wizz.py` are hard-wired to 1 adult, and `mcp_flights.py --log` does not record `--pax`, so log those quotes by hand. No tool prices children or infants.
~~~
**Proposed replacement (`CLAUDE.md` L44):**
~~~text
  The earlier trip was for 2 travelers (Sebastijan & Mia), so ask whether this one is too. Party size changes fares (search with `--adults N`; the cheapest bucket may have one seat) and ground economics (a car wins at 2+).
~~~

### P0-2. `quotes.py` adds €0 ground for any origin missing from `ground.json`, so far-away hubs rank too cheap

**Files:** `tools.md` L155–156, `ground.json` L2 (`_comment`).

**Current text (`tools.md` L155–156):**
~~~text
Total = fare×(1+card fee) + bag cost + extras + ground (round trip from `ground.json`; open-jaw on the
home side = half of each). Everything is per person; `--per total --pax N` divides. `mcp_flights.py --log TRIP` auto-adds.
~~~
**Current text (`ground.json` `_comment`, fragment):**
~~~text
'hotel' = add when the flight time forces a night before (see 'hotel_if'); quotes.py adds 'hotel' automatically, so set it to 0 when the actual flight time doesn't need it (or use --ground).
~~~
**Problem.** The ranking that the report's top-5 table is built from has several silent gaps:

1. **Missing origins get €0 ground with no warning.**
   - In `quotes.py`, `ground_cost()` returns `None` when the origin key is missing, and `total()` then adds `(g_out or 0)`. The `gnd€` column shows `0`.
   - `ground.json` has 23 keys. The Sweep B origin-scan list in `SKILL.md` L49 includes AMS, CDG, FRA, CPH, DUB, MAD and ATH, none of which are keys. The playbook adds OSL, BCN and OTP, which are also missing.
   - The Google Flights Europe sweep's #1 origin (ATH, €555 RT, research 05 §4.4) would therefore rank as if Athens were free to reach from Zagreb.
2. **The virtual-origin values are placeholders.** BRU (100), IST (120) and the others are guesses that the file itself says to replace. Nothing forces that.
3. **The comment promises behaviour that never happens.** It says "quotes.py adds 'hotel' automatically", but no entry has a positive numeric `hotel` (only PRG has `"hotel": 0`). `hotel_if` is plain text, so the BUD "+50 hotel" is never added.
4. **Other costs are never applied:**
   - `fri_eur` is never read.
   - The €6/h break-even allowance in `origins.md` is not part of the total, so `quotes.py list` and the break-even rule can disagree.

**Proposed replacement (`tools.md` L155–156):**
~~~text
Total = fare×(1+card fee) + bag cost + extras + ground (round trip from `ground.json`; open-jaw on the
home side = half of each). Everything is per person; `--per total --pax N` divides. `mcp_flights.py --log TRIP` auto-adds.
**Check the `gnd€` column of every row before trusting the ranking:**
- An origin that is **not a key in `ground.json` gets €0 ground silently** (e.g. ATH, AMS, CDG, FRA, CPH, DUB, MAD, OSL, BCN, OTP, ZRH, LGW, MAN, SAW, CRL, WMI). Pass `--ground <EUR>` = real round-trip positioning fares + their bag fees + sibling-airport transfers.
- Virtual-origin values (MXP, BGY, FCO, WAW, IST, HEL, ARN, BRU, STN, LHR) are placeholders: override them with `--ground` from the actual `ryanair_wizz.py` / `positioning.py` fares.
- `hotel_if` and `fri_eur` are NOT applied: add a needed hotel night with `--extras` and Friday/Sunday ground with `--ground`.
- The €6/h time allowance (`origins.md` break-even) is not in the total: apply it before recommending a far origin.
~~~
**Proposed replacement (`ground.json` `_comment`, same fragment):**
~~~text
'hotel_if' is a note only: quotes.py adds a numeric 'hotel' key if present (none is set), so add a needed hotel night per quote with --extras. 'fri_eur' is also not read by quotes.py: pass --ground. Origins missing from this file get 0 ground in quotes.py, so always pass --ground for them.
~~~
*(Code follow-up: make `quotes.py` print `?` and a warning for unknown origins. See the end of this file.)*

### P0-3. Bag fees are never added for fares without bags, so bagless constructions rise to the top

**Files:** `SKILL.md` L53 and L60, `tools.md` L131.

**Current text (`SKILL.md` L53):**
~~~text
The cheapest hub changes with dates (BRU in Mar 2027, IST in May 2027). Add sibling-airport transfers and a buffer night for separate tickets.
~~~
**Current text (`tools.md` L131):**
~~~text
- `positioning.py`: buffer default 4 h (+3 h for sibling airports CRL↔BRU, BGY↔MXP, SAW↔IST, WMI↔WAW, NYO↔ARN, …), `--max-gap 30` h allows an overnight. Ground transfer between sibling airports is **not** costed (CRL→BRU ~1 h bus). Wizz arrival time is estimated (`--wizz-block 3`). ~1–4 min.
~~~
**Problem.** `profile.md` defaults to 1 cabin bag + 1 × 23 kg each way, but nothing in the toolkit adds the cost of that bag:
- `positioning.py --checked-bags` prices the bag into the long-haul only. The Ryanair/Wizz leg is fare-only, in both directions.
- `ryanair_wizz.py` is fare-only.
- `quotes.py --bag-cost` defaults to 0, and `mcp_flights.py --log` never sets it.
- **positioning.py is also one-way and 1 adult** (`return_dates=None`, `adults=1`). Its totals are not round-trip totals. A hub⇄Japan round trip is often far below 2 × one-way (VIE: RT €688 < OW €704, tricks A4).
- **Evidence from today's dry run:** the quote log ranks first `VIE-KIX/NRT-BUD TR,CZ momondo/splitbookingow`, total €685 with **bag€ 0**. The brief in `dryrun-tyo-2027-05/notes.md` says the user needs a checked bag, and Scoot's cheapest fares exclude hold bags (B0: "Scoot VIE–SIN–KIX (no bags)"). The top of the ranking is therefore likely understated.

**Proposed replacement (`SKILL.md` L53):**
~~~text
The cheapest hub changes with dates (Kiwi one-way origin-scan: BRU in Mar 2027, IST in May 2027). `positioning.py` totals are ONE-WAY, 1 adult, and fare-only on the Ryanair/Wizz leg. Before comparing, add: (a) cabin and checked-bag fees for EACH positioning leg the traveller needs (price them on the airline site for that date), (b) sibling-airport transfers (CRL→BRU, BGY→MXP…), (c) a buffer night, (d) the return direction (`--direction back`), or better a hub⇄Japan round trip priced with `kiwi_graphql.py search --from <HUB> --return-dates …` / `kayak.py` + `ryanair_wizz.py anywhere --to <HUB> --return …`. Log as `quotes.py add --origin <HUB> --ground <positioning RT + transfers> --bag-cost <all bag fees> --extras <hotel>`.
~~~
**Proposed replacement (`tools.md` L131):** keep the current line, then add:
~~~text
- `positioning.py` is **one-way and 1 adult** (the long-haul is a Kiwi one-way; `--checked-bags` prices bags into the long-haul only, never into the FR/W6 leg). For a round trip, price hub⇄Japan as a return and add both positioning legs + their bag fees.
~~~
**For `SKILL.md` L60** (bags on every leg), see the consolidated replacement in P1-2.

---

## P1: important

### P1-1. The skill's Skiplagged commands include hidden-city fares by default

**Files:** `SKILL.md` L38, `playbook.md` L56.

**Current text (`SKILL.md` L38):**
~~~text
python3 $S/mcp_flights.py sk BUD TYO D --ret R          # repeat for ZAG, VIE
~~~
**Current text (`playbook.md` L56):**
~~~text
- `mcp_flights.py sk ZAG TYO D [--ret R]`, then repeat for VIE and BUD
~~~
**Problem.**
- `mcp_flights.py` sends `"includeHiddenCity": not a.no_hidden_city`, so hidden-city results are **on** unless `--no-hidden-city` is passed.
- `tools.md` L100 says to use `--no-hidden-city` by default, but the skill and the playbook don't.
- With `--ret`, these are round-trip hidden-city results. Those are the riskiest kind: later segments are cancelled after a skip, and bags go to the ticketed destination.
- With `--log`, they reach the quote log, flagged only as `risk tos`.
- The native `skiplagged` MCP tool in `.mcp.json` has the same toggle.

**Proposed replacement (`SKILL.md` L38):**
~~~text
python3 $S/mcp_flights.py sk BUD TYO D --ret R --no-hidden-city   # repeat for ZAG, VIE; hidden-city only with explicit opt-in (one-way, cabin bag only). Native MCP tool: pass includeHiddenCity=false
~~~
**Proposed replacement (`playbook.md` L56):**
~~~text
- `mcp_flights.py sk ZAG TYO D [--ret R] --no-hidden-city`, then repeat for VIE and BUD (drop `--no-hidden-city` only after an explicit opt-in, and only for one-way, cabin-bag-only trips)
~~~

### P1-2. Airport changes are invisible in four tools' route strings, but validation relies on a `~` marker only one tool prints

**Files:** `SKILL.md` L60, `playbook.md` L99.

**Current text (`SKILL.md` L60):**
~~~text
- Validate (playbook §7): live today; bags on every leg (Kiwi bag data is wrong for Chinese carriers); single vs separate tickets; connection ≥ 2 h (one ticket) / ≥ 4–6 h or overnight (separate); airport changes (`~`); transit/entry rules (China, Korea K-ETA, UK ETA); ground plan on that weekday; total cost; risk.
~~~
**Current text (`playbook.md` L99):**
~~~text
- [ ] Airport changes (`~` in `mcp_flights.py` routes, CRL→BRU, ICN→GMP…); overnight layovers; arrival at 01:00?
~~~
**Problem.**
- Four tools build the path as "first origin + each segment's destination":
  - `kayak.py` (`flatten`);
  - `kiwi_graphql.py` (`_sector_txt`);
  - `aviasales.py` (L99);
  - `booking_flights.py` (L77).
- Because of that, a change of airport disappears from the route string. Research 06's own sample `ZAG-CRL-PVG-KIX FR,HO` is really Ryanair ZAG→CRL, a ground transfer to BRU, then Juneyao BRU→PVG→KIX. The origin-scan's `ZAG-CRL-PVG-NRT` is the same.
- Only Skiplagged's output in `mcp_flights.py` marks changes with `~`.
- A session that follows the checklist will see no `~` and pass the itinerary.
- Return legs can also land at a different home airport, or leave from a different Japanese city (P1-3).
- This replacement also carries the P0-3 bag point.

**Proposed replacement (`SKILL.md` L60):**
~~~text
- Validate (playbook §7): live today, for the real party size; bags on every leg incl. positioning legs (Kiwi bag data is wrong for Chinese carriers; add `--bag-cost` for any fare without the needed bag); single vs separate tickets (momondo "hacker"/KIWIVI*/splitbooking = separate); connection ≥ 2 h (one ticket) / ≥ 4–6 h or overnight (separate); **airport changes: only Skiplagged marks them (`~`); `kayak.py`, `kiwi_graphql.py`, `aviasales.py` and `booking_flights.py` route strings HIDE them (e.g. `ZAG-CRL-PVG-KIX` = CRL→BRU by bus), so open the booking link or check whether a segment departs from a different airport than the previous one landed at**; return lands at the same home airport (multi-origin Kayak/Kiwi round trips may not: log with `--return-to`); transit/entry rules for every passport (China, Korea K-ETA, UK ETA); ground plan on that weekday; total cost; risk.
~~~
**Proposed replacement (`playbook.md` L99):**
~~~text
- [ ] Airport changes: `~` in Skiplagged routes only. `kayak.py`, `kiwi_graphql.py`, `aviasales.py` and `booking_flights.py` route strings hide them (`ZAG-CRL-PVG-KIX` is FR ZAG–CRL + bus + HO BRU–PVG–KIX), so check the segment airports on the booking link. Also: return airport = departure airport? overnight layovers; arrival at 01:00?
~~~

### P1-3. Round trips can come back to a different home airport, and nothing tells the agent to check

**Files:** `SKILL.md` L60 (covered by the P1-2 replacement) and `tools.md` §4b. Add after L87 (`- Location forms: …`).

**Current text (`tools.md`):** there is none; the behaviour is undocumented.

**Problem.**
- `kiwi_graphql.py` sets `allowChangeInboundSource`, `allowChangeInboundDestination` and `allowReturnFromDifferentCity` to `True`.
- `kayak.py` builds the return leg from the destination list back to the **origin list**.
- So `--from ZAG,VIE,BUD` or `--from ZAG@400` round trips can go out of one airport and back to another. The dry-run log already has one: `VIE-KIX/NRT-BUD`.
- `quotes.py` costs this correctly only if `--return-to` is given. `mcp_flights --log` passes it; manual `quotes.py add` calls must too.

**Proposed addition (`tools.md`, new bullet after L87):**
~~~text
- Round trips may return to a DIFFERENT home airport or leave from a different Japanese city (`kiwi_graphql.py` enables Kiwi's change-inbound flags; `kayak.py` returns to any airport in `--from`). Read the return leg and log it with `quotes.py add --return-from <JP airport> --return-to <home-side airport>` so ground is costed for both ends.
~~~

### P1-4. Open-jaw: the "≈ free on Chinese carriers" evidence is not valid, and the tooling is weaker than the docs imply

**Files:**
- `benchmarks.md` L49, L52–54;
- `CLAUDE.md` L38;
- `japan.md` L43;
- `playbook.md` L80;
- `SKILL.md` L56;
- `tools.md` L53.

**Current text (`benchmarks.md` L49):**
~~~text
| momondo BUD (MU out / CZ back) | €688 (NRT/HND both ways) | €686 (out PVG–KIX, back KIX–CAN) | ≈ 0 |
~~~
**Current text (`CLAUDE.md` L38):**
~~~text
7. Return vs 2× one-way vs open-jaw: no fixed winner (open-jaw is ≈ free on Chinese carriers, +28% on a Star Alliance fare). Price all of them.
~~~
**Current text (`japan.md` L43):**
~~~text
- **Open-jaw** (into TYO, out of OSA or vice versa): ≈ free on Chinese carriers (MU/CZ/CA), but **+28% on a Star Alliance VIE fare in benchmark B2**. Always price it explicitly. It saves a ¥14,000 Shinkansen or a ≥¥3,990 Peach flight.
~~~
**Current text (`playbook.md` L80):**
~~~text
- **Open-jaw:** in TYO, out OSA (and the reverse): `matrix.py search --slice ZAG:TYO:D1 --slice OSA:ZAG:D2`, `gflights` multi-city if supported, airline multi-city. Usually ≈ RT price and saves a ¥14,000 Shinkansen.
~~~
**Current text (`SKILL.md` L56):**
~~~text
For the top 3–5: RT vs 2× one-way (price the return direction separately), open-jaw TYO⇄OSA (`matrix.py search --slice ZAG:TYO:D --slice OSA:ZAG:R`; Kiwi with `TYO,OSA` mixes automatically), secondary Japanese airports, ±3 days, Asian-hub self-transfer (only if it saves ≥ €150), free stopovers.
~~~
**Problem.**
1. **The B2 momondo "open-jaw" is not an open-jaw.** "out PVG–KIX, back KIX–CAN" flies into KIX and out of KIX. It is the same ticket as B1's €686 row (`MU BUD–PVG–KIX / CZ KIX–CAN–BUD`).
2. **The B2 Kiwi row doesn't support the claim either.**
   - It uses Jan/Feb dates, not the B2 dates.
   - It uses Kiwi's Air China round-trip pricing, which B0 calls "implausible: Kiwi stitching". Stitched one-ways price an open-jaw like a return by construction.
3. **The B2 Matrix row compares two pruned default answers.** Matrix's default answer varies from run to run (research 05 §5.3). So "+28%" is one sample, not a property of Star Alliance fares.
4. **The tooling cannot do what the docs suggest:**
   - **gflights.py:** it has no multi-city at all (trip types 1 and 2 only). "`gflights` multi-city if supported" sends the agent looking for a feature that doesn't exist.
   - **kayak.py:** it has no multi-city either.
   - **matrix.py `--slice`:** it applies `--route`/`--ext` to slice 1 only and **ignores `--route-ret`/`--ext-ret`** (L410–418).
   - **`--carriers` with `--slice`:** only the outbound is forced; the return stays pruned. For an open-jaw on MU or CA, the cheapest construction can be missed.
5. **There is no rule for Japan-side costs** (see P1-17).

**Proposed replacement (`benchmarks.md` L49):**
~~~text
| momondo BUD (MU out / CZ back) | €688 (NRT/HND both ways) | not measured: the €686 row (out PVG–KIX, back KIX–CAN) is in KIX / out KIX, i.e. a plain return, not an open-jaw | n/a |
~~~
**Proposed replacement (`benchmarks.md` L52–54, the conclusion):**
~~~text
**Conclusion:** not established. The only true open-jaw pair with comparable dates is the Matrix VIE one (+28%), and it compares two pruned default answers; the Kiwi Air China pair uses Kiwi's stitched (implausible) RT pricing. Blogs say open-jaw ≈ return on legacy and Chinese carriers; **price it explicitly every time** (Matrix `--slice` with a carrier forced on BOTH slices via `--route`/routing in each slice is not supported by `matrix.py` yet; use the user's browser on Google Flights multi-city / the airline / Trip.com).
~~~
**Proposed replacement (`CLAUDE.md` L38):**
~~~text
7. Return vs 2× one-way vs open-jaw: no fixed winner (one measured open-jaw was +28% on a Star Alliance fare; no clean Chinese-carrier measurement yet). Price all of them, and include Japan-side costs (Shinkansen backtrack vs open-jaw) in the comparison.
~~~
**Proposed replacement (`japan.md` L43):**
~~~text
- **Open-jaw** (into TYO, out of OSA or vice versa): blogs say ≈ a return price; our only clean test was **+28% on a Star Alliance VIE fare** (B2), and the Chinese-carrier "≈ free" rows in B2 turned out not to be open-jaws. Always price it explicitly. When comparing with a plain return, add the backtrack the return forces on you (¥14,000 Shinkansen or a ≥¥3,990 Peach flight plus bag) to the return's total.
~~~
**Proposed replacement (`playbook.md` L80):**
~~~text
- **Open-jaw:** in TYO, out OSA (and the reverse). Tools: `matrix.py search --slice ZAG:TYO:D1 --slice OSA:ZAG:D2` (published fares; `--route`/`--carriers` force only slice 1 and `--route-ret` is ignored with `--slice`, so the return is the pruned default); Kiwi/momondo with `--to TYO,OSA` mix cities on their own (read the legs: the result may not be an open-jaw); `gflights.py` and `kayak.py` have NO multi-city. Manual: Google Flights multi-city, airline multi-city, Trip.com (give the user URLs). Compare totals including the Japan-side backtrack the plain return needs.
~~~
**Proposed replacement (`SKILL.md` L56):**
~~~text
For the top 3–5: RT vs 2× one-way (price the return direction separately, see "Return direction" below), open-jaw TYO⇄OSA (`matrix.py search --slice ZAG:TYO:D --slice OSA:ZAG:R`: only slice 1 is forced by `--route`/`--carriers`; Kiwi/momondo with `TYO,OSA` mix cities but check the legs; no multi-city in gflights/kayak, so add Google Flights multi-city to the user's manual checks), secondary Japanese airports, ±3 days, Asian-hub self-transfer (only if it saves ≥ €150), free stopovers. Add Japan-side costs (backtrack, NRT vs HND transfer) with `--extras`.
~~~
**Proposed replacement (`tools.md` L53):**
~~~text
python3 matrix.py search --slice VIE:TYO:2027-05-12 --slice OSA:VIE:2027-05-26          # open-jaw (--route/--ext/--carriers apply to slice 1 only; --route-ret/--ext-ret are ignored with --slice)
~~~

### P1-5. The new fact 4 and the B3 conclusion misstate benchmark B1

**Files:** `CLAUDE.md` L35 (fact 4), `benchmarks.md` (B3 conclusion, last two lines of the file).

**Current text (`CLAUDE.md` fact 4):**
~~~text
4. **Engines hide carriers:** Kiwi showed Air China's new ZAG→OTP→PEK flight (since Sep 2026) only with `--only-airlines CA`. In B1/B3 the cheapest carrier (China Eastern) appeared only when forced in Matrix (`--route MU+`). **Per-carrier passes are mandatory.**
~~~
**Current text (`benchmarks.md`, B3 conclusion):**
~~~text
Again the cheapest carrier (MU) was absent from Google and from both Kiwi answers, and found only by
forcing the carrier in Matrix. **Per-carrier passes (Matrix `--carriers`, Kiwi `--only-airlines`) are mandatory.**
~~~
**Problem.**
- **In B1, China Eastern was visible almost everywhere.** It showed on momondo (€686, MU+CZ), Aviasales (€706), Booking (€741), Kiwi MCP (€748) and Skiplagged (≈€762). It was missing only from Google Flights and from Matrix's *default* answer.
- **B3 covered just 4 sources** (Matrix, Google Flights, Kiwi MCP, Kiwi GraphQL) and **no momondo, Aviasales or Booking.com.**
- **Today's dry-run log shows MU on momondo, Skiplagged, Aviasales, Kiwi MCP and Booking.com.**
- **The "again" in B3 is wrong.** B1's Kiwi MCP did show MU.
- **Why it matters:** the overstatement could push a session to treat Matrix-forced MU as the sole oracle and skip the OTA and meta sources that found B1's floor.

**Proposed replacement (`CLAUDE.md` fact 4):**
~~~text
4. **Engines hide carriers:** Kiwi showed Air China's new ZAG→OTP→PEK flight (since Sep 2026) only with `--only-airlines CA`. China Eastern (the cheapest carrier in B1/B3) is missing from Google Flights and from Matrix's default answer; in B3 it was also missing from both Kiwi answers and appeared only via Matrix `--route MU+` (momondo/Aviasales/Booking were not run in B3; in B1 they showed it). **Per-carrier passes are mandatory** and do not replace the OTA/meta sweep.
~~~
**Proposed replacement (`benchmarks.md`, B3 conclusion):**
~~~text
The cheapest carrier (MU) was absent from Google and from both Kiwi answers (in B1 Kiwi MCP did show MU), and found among these four sources only by forcing the carrier in Matrix. momondo/Aviasales/Booking were not part of B3. **Per-carrier passes (Matrix `--carriers`, Kiwi `--only-airlines`) are mandatory.**
~~~

### P1-6. One-way and 2 × one-way quotes double-count ground and are ranked against round trips, and there are no return-direction discovery commands

**Files:** `tools.md` §10 (add after the P0-2 block), `SKILL.md` L56 (the P1-4 replacement points here).

**Current text.** None. `tools.md` §10 doesn't mention it, and the `SKILL.md` L56 text "price the return direction separately" gives no commands.

**Problem.**
1. **Round-trip ground is added to every quote.** `quotes.py total()` adds the round-trip ground from `ground.json` even when `--ret` is omitted.
   - A "2 × one-way" construction logged as two rows counts ground twice.
   - A single one-way row (e.g. €356 FR+HO) sits in the same ranked list as round trips, so the top of `quotes.py list` can be a one-way.
2. **There are no return-direction discovery commands.** `origin-scan` varies origins only. For Japan→Europe, the agent needs to vary the European destination.

**Proposed addition (`tools.md` §10, after the P0-2 block):**
~~~text
- `quotes.py` adds ROUND-TRIP ground to every row, one-ways included, and ranks one-ways next to returns. Log a "2× one-way" or "positioning + long-haul" construction as ONE combined row (sum of fares, `--ret` set, `--notes "OW+OW: …"`), or log the second one-way with `--ground 0`. Never present a one-way row as the cheapest round trip.
- Return-direction discovery (Japan → Europe): `kiwi_graphql.py per-city --from TYO,OSA --to Continent:europe --dates R1..R2` (cheapest European landing city), `kiwi_graphql.py search --from TYO,OSA --to ZAG@400 --dates R1..R2`, `kayak.py --from TYO,OSA --to ZAG,VIE,BUD --depart R`, `mcp_flights.py kiwi TYO,OSA ZAG,VIE,BUD R --flex 3`, `positioning.py --direction back …`.
~~~

### P1-7. The recon step picks the date pairs from calendars that miss the cheapest carriers

**File:** `SKILL.md` L26–30.

**Current text:**
~~~text
python3 $S/gflights.py calendar --from VIE --to TYO --start D1 --end D2 --stay 12-16
python3 $S/kiwi_graphql.py calendar --from ZAG --to TYO --dates D1..D2
python3 $S/mcp_flights.py skcal BUD TYO D --ret R
```
Benchmarks in `flights/japan.md` §1 (great < €500 RT with bag, normal €650–950). Note Google's "typical" range. Pick the 1–3 cheapest date pairs that fit the user's window.
~~~
**Problem.** Every later sweep is narrowed to "the 1–3 cheapest date pairs", and the three calendars that choose them are each blind in some way:
- The Google calendar has no MU, CA or CZ fares (fact 1).
- `kiwi_graphql.py calendar` is **one-way only**. `cmd_calendar` queries `itineraryPricesCalendar` and ignores `--return-dates`/`--nights`, even though it accepts them.
- `skcal` covers one origin and a fixed stay.

As a result, the BUD China Eastern date that is cheapest overall can be filtered out before Sweep A.

**Proposed replacement:**
~~~text
python3 $S/gflights.py calendar --from VIE --to TYO --start D1 --end D2 --stay 12-16      # no Chinese carriers
python3 $S/mcp_flights.py kiwi ZAG,VIE,BUD TYO,OSA D1 --date-to D2 --nights 12-16         # RT over the whole window, incl. Chinese carriers
python3 $S/matrix.py calendar --from BUD --to TYO --start D1 --end D2 --stay 12-16 --route "MU+" --route-ret "MU+"   # repeat CA+
python3 $S/kiwi_graphql.py calendar --from ZAG --to TYO --dates D1..D2                    # ONE-WAY prices only
python3 $S/mcp_flights.py skcal BUD TYO D --ret R
```
Benchmarks in `flights/japan.md` §1 (great < €500 RT with bag, normal €650–950). Note Google's "typical" range. Pick the 2–4 cheapest date pairs across ALL calendars (not just Google's) that fit the user's window; calendars are cached, so re-price them in Sweep A.
~~~

### P1-8. The self-transfer buffer and minimum saving contradict each other across files

**File:** `profile.md` L34 (and the threshold mix noted below).

**Current text:**
~~~text
| Self-transfer (separate tickets) OK? | [yes with ≥ 3 h buffer, ≥ €80 saving, no checked-bag issues] |
~~~
**Problem.**
- **The buffer conflicts.** Everywhere else the separate-ticket buffer is ≥ 4–6 h or overnight: `SKILL.md` L60, `playbook.md` §7, `origins.md` §3, `tricks.md` D, and the `positioning.py` default of 4 h + 3 h at sibling airports. The profile default of 3 h is the outlier on a safety parameter.
- **The minimum saving conflicts too.** The profile says €80, while `SKILL.md` L56 and `playbook.md` §5 say €150 for Asian-hub self-transfer. Today's dry-run brief had to reconcile three numbers.

**Proposed replacement:**
~~~text
| Self-transfer (separate tickets) OK? | [yes with ≥ 4–6 h buffer on the same day or an overnight (positioning flights: the day before), ≥ €100 saving after bags/ground/hotel (≥ €150 for an Asian-hub self-transfer), bags re-checked by the traveller] |
~~~

### P1-9. China entry rules are presented in a way that misleads for 2027 trips

**Files:**
- `CLAUDE.md` L45;
- `japan.md` L56;
- `playbook.md` L83;
- `tricks.md` L25.

**Current text (`CLAUDE.md` L45):**
~~~text
- Croatian/EU passport assumed: Japan visa-free 90 d; China visa-free 30 d until 31 Dec 2026; Korea needs K-ETA to enter.
~~~
**Current text (`japan.md` L56):**
~~~text
  - **China:** 30 days visa-free until 31 Dec 2026, then 240 h transit.
~~~
**Problem.**
- Every worked example targets 2027, and the 30-day entry policy ends on 31 Dec 2026 unless it is renewed. Research 03 §2.2 expects a decision around Nov 2026.
- **The dry-run agent drew the wrong conclusion.** It wrote "visa-free transit until 31 Dec 2026 only - trip is May 2027!" (`dryrun-tyo-2027-05/notes.md`) and treated China routings as doubtful.
- **Neither transit option depends on the 30-day policy:**
  - A one-ticket airside connection at PEK/PVG/CAN needs no visa.
  - The 240-h visa-free transit, with an onward ticket to Japan, covers landside self-transfers.
- **The stopover suggestion is also affected.** "China visa-free" as a free stopover (`playbook.md` L83, `tricks.md` L25) only applies to 2026 travel unless renewed.

**Proposed replacement (`CLAUDE.md` L45):**
~~~text
- Croatian/EU passport assumed: Japan visa-free 90 d; Korea needs K-ETA to enter (not for airside transit). China: one-ticket airside transit needs no visa; 240-h visa-free transit covers landside self-transfers/stopovers en route to Japan; the 30-day visa-free entry runs to 31 Dec 2026 (renewal expected to be decided ~Nov 2026: re-check for 2027 travel).
~~~
**Proposed replacement (`japan.md` L56):**
~~~text
  - **China:** airside transit on one ticket: no visa. 240-h visa-free transit (onward ticket to a third country such as Japan, designated ports incl. PEK/PKX/PVG/CAN): fine for landside self-transfers and short stopovers. 30-day visa-free entry: until 31 Dec 2026 unless renewed (re-check for 2027 trips).
~~~
**Proposed replacement (`playbook.md` L83):**
~~~text
- **Stopover value-adds:** Turkish Stopover (free hotel night in economy), Finnair, China (240-h visa-free transit; the 30-day visa-free entry only to 31 Dec 2026 unless renewed).
~~~
**Proposed replacement (`tricks.md` L25), the final clause only:**
~~~text
China (240-h visa-free transit en route to Japan; 30-day visa-free entry until 31 Dec 2026 unless renewed).
~~~

### P1-10. `origins.md` says Wizz Air can't be queried, which contradicts the toolkit

**File:** `origins.md` L63.

**Current text:**
~~~text
Wizz Air network not verified (its API needs a build token). Use Azair/Kiwi, which include Wizz.
~~~
**Problem.**
- Research 06 §3 and `tools.md` §8 show Wizz working: the API version is scraped from wizzair.com and the token echo is handled.
- `ryanair_wizz.py routes/anywhere/calendar` and `positioning.py` include W6 by default.
- AZair is stale and has a horizon of about 3 months, so steering positioning searches to it loses fares.

**Proposed replacement:**
~~~text
Wizz Air works through `ryanair_wizz.py` (routes/anywhere/calendar; verified 2026-10-04: BUD 97 destinations, BTS 39, VCE 36, TSF 9, LJU 2, no ZAG or VIE). Fares are in local currency (HUF…), converted at ECB rates; fare only, no bags.
~~~

### P1-11. A home base other than Zagreb: the recipe is incomplete and would corrupt older trips' totals

**File:** `SKILL.md` L21.

**Current text:**
~~~text
- If the user's home isn't Zagreb: re-derive `flights/searches/ground.json` with `$S/flixbus_ground.py --from "<City>"` and update `flights/origins.md`.
~~~
**Problem.** Several pieces of the toolkit hard-code Zagreb, and the recipe misses most of them:
- `flixbus_ground.py` only **prints**; it doesn't write `ground.json`. Its default target list is the Zagreb airport set.
- `ground.json` is **one global file** that `quotes.py` reads for every trip, so rewriting it changes the totals of older trips.
- These are hard-coded to Zagreb:
  - `deals.py` `REGION` keywords;
  - the `gflights.py` `zagreb` preset;
  - `ZAG@400`;
  - the `--home` lists in positioning;
  - the Sweep A origin list;
  - the break-even constant €16.

**Proposed replacement:**
~~~text
- If the user's home isn't Zagreb: (1) `$S/kiwi_graphql.py places --near <HOME_IATA> --radius 400` for candidate airports; (2) `$S/flixbus_ground.py --from "<City>" --to <airport cities…> --date <date>` (its default targets are Zagreb's) and `--drive --home <lon,lat>`; (3) do NOT overwrite the shared `ground.json` (it re-prices older trips): either save it as `ground.zagreb.json` first, or pass `--ground` on every `quotes.py add`; (4) replace ZAG and the Zagreb catchment in every command (`--from`, `ZAG@400`, `--home`, gflights preset `zagreb`); (5) `deals.py --region` matches Zagreb-region city names only, so run it without `--region` or edit `REGION` in `deals.py`; (6) rewrite the tiers in `flights/origins.md` with a dated note.
~~~

### P1-12. A destination other than Japan: the description promises "any route", but nothing says what to change

**Files:** `SKILL.md` (new paragraph after §1), `SKILL.md` L3 (description).

**Current text (`SKILL.md` L3, fragment):**
~~~text
(built for home region Zagreb/Central Europe → Japan, works for any route)
~~~
**Problem.** Several places hard-code Japan:
- `deals.py` matches only the `JAPAN` keyword list.
- `gflights.py explore` defaults to `--region japan`.
- `positioning.py --to` defaults to `TYO,OSA`.
- `kiwi_graphql` examples use `Country:JP`.
- The benchmarks, carrier notes and entry rules all live in `japan.md`.

A session asked for, say, Seoul or Bangkok gets no guidance.

**Proposed addition (`SKILL.md`, after §1):**
~~~text
**Destination not Japan?** Replace TYO,OSA / `Country:JP` / `--region japan` with the destination's codes (gflights `--region` takes a `/m/` MID); `positioning.py --to <codes>`; `deals.py` only matches Japan keywords (edit `JAPAN` in `deals.py` or read the feeds with `--any-asia`); there is no benchmark file, so build one from Google's "typical" range (`gflights.py search` output) and Kayak route stats, and check entry/transit rules for that country. `japan.md` and the Chinese-carrier facts do not transfer automatically.
~~~

### P1-13. Monitoring is now actionable, but `monitor.py` compares mixed constructions and has no stop rule

**Files:** `playbook.md` §9 (after the Routine prompt, before L125 "Use `send_later`…"), `SKILL.md` L72.

**Current text (`SKILL.md` L72):**
~~~text
Write `flights/searches/<trip>/watch.json` (3–6 winning queries incl. one carrier-forced Matrix + one momondo check) and test `python3 $S/monitor.py <watch.json>` (prints `ALERT` on a new low / ≤ threshold). With the user's OK, create a daily Routine using the prompt template in playbook §9 (`send_later` for one-offs). Suggest Google Flights price tracking to the user too.
~~~
**Problem.** The new `monitor.py` and the Routine prompt are good. Remaining traps:
1. **The "min" is not like-for-like.**
   - `min_eur()` takes the minimum over every row in a check's JSON: self-transfers, fares without bags, hidden airport changes, and Matrix `--no-avail` leads.
   - It is fare-only (no ground or bags), and it follows the tool's party-size convention.
   - So `threshold_eur` (presumably a per-person total) is compared with a different quantity, and a new low can just be a worse construction.
2. **Alerts repeat.** "≤ threshold" alerts fire on every run while the price stays under it.
3. **There is no stop condition.** The Routine keeps firing after purchase or after the travel dates pass.
4. **A fresh-session Routine only sees what is pushed.** `watch.json` must be committed and pushed before the Routine is created.
5. **Pushes can collide.** A Routine that pushes `watch_state.json` while an interactive session is pushing needs `git pull --rebase`.

**Proposed addition (`playbook.md` §9, new bullets after the prompt block):**
~~~text
- Make each check like-for-like: use `--no-self-transfer` / `--single-ticket` / `--no-hidden-city` and bag flags where the user needs them, never `--no-avail`, and the real `--adults`. `monitor.py` takes the cheapest row of each check, fare only (no ground, no bags), so set `threshold_eur` on that basis and still re-verify the full total before reporting.
- Commit and push `watch.json` before creating the Routine (fresh sessions only see what is pushed); the Routine prompt should `git pull --rebase` before pushing `watch_state.json`.
- Stop rule: when the user buys, or the first travel date is ≤ 14 days away, disable the Routine (`update_trigger enabled=false`) and tell the user.
~~~
**Proposed replacement (`SKILL.md` L72):**
~~~text
Write `flights/searches/<trip>/watch.json` (3–6 winning queries incl. one carrier-forced Matrix + one momondo check, with the real `--adults` and like-for-like filters), commit and push it, and test `python3 $S/monitor.py <watch.json>` (prints `ALERT` on a new low / ≤ threshold; fare-only minimum per check). With the user's OK, create a daily Routine using the prompt template in playbook §9 (`send_later` for one-offs) and disable it when the user buys or travel is ≤ 14 days away. Suggest Google Flights price tracking to the user too.
~~~

### P1-14. The manual checks leave out Google Flights' "Cheapest" tab and multi-city search

**File:** `SKILL.md` L68.

**Current text:**
~~~text
- **Manual checks for the user** with exact URLs: Skyscanner, Trip.com, the airline site (Air China: airchina.at, book Fri–Sun for ≤6% off), Secret Flying. These sites block bots, so never try to bypass captchas.
~~~
**Problem.**
- `gflights.py` never returned a self-transfer itinerary (research 05 §3), so Google's own self-transfer combos are unseen.
- Research 01 rates the "Cheapest" tab "must-use".
- Open-jaw has no automated multi-city source except the pruned Matrix query (P1-4).

**Proposed replacement:**
~~~text
- **Manual checks for the user** with exact URLs: Skyscanner, Trip.com, the airline site (Air China: airchina.at, book Fri–Sun for ≤6% off), Secret Flying, and Google Flights in their own browser: the **"Cheapest" tab** (self-transfer combos our script never sees) and **multi-city** for the open-jaw. These sites block bots, so never try to bypass captchas.
~~~

### P1-15. The single-ticket status of momondo results is unverified, but presented as fact

**Files:** `CLAUDE.md` L33, `benchmarks.md` L10.

**Current text (`CLAUDE.md` L33, last sentence):**
~~~text
momondo found a mixed MU+CZ ticket nobody else showed.
~~~
**Current text (`benchmarks.md` L10, fragment):**
~~~text
MU BUD–PVG–KIX / **CZ** KIX–CAN–BUD, one ticket, seller **Opodo**
~~~
**Problem.**
- `kayak.py` reads `hasHackerFares` into the row but never prints it: the column list lacks `hacker`.
- So whether a momondo result is one ticket or a combination of two one-ways (Kayak "Hacker Fare", Opodo-style combined one-ways) was never checked.
- Two separate tickets change disruption protection and refund handling.

**Proposed replacement (`CLAUDE.md` L33, last sentence):**
~~~text
momondo found a mixed MU+CZ combination nobody else showed (one ticket or two combined one-ways: not verified; `kayak.py` doesn't print the hacker-fare flag, so check at checkout).
~~~
**Proposed replacement (`benchmarks.md` L10, fragment):**
~~~text
MU BUD–PVG–KIX / **CZ** KIX–CAN–BUD, one booking (single ticket not verified), seller **Opodo**
~~~

### P1-16. Automated access: tell the user what the toolkit does, and draw the line clearly

**File:** `CLAUDE.md` L51 (Rules).

**Current text:**
~~~text
- Respect sites: keep the scripts' pacing; on 429/captcha stop that source.
~~~
**Problem.** The toolkit relies on undocumented, unofficial endpoints:
- Google Flights' internal RPC;
- the Matrix search API called without its BotGuard token;
- Kiwi's website GraphQL;
- Kayak/momondo's poll API with a scraped CSRF token.

It also uses headless Chromium to pass AWS-WAF JavaScript challenges on Booking.com, Aviasales and FlightConnections. Research 02 §1.1 itself warns that scraping Matrix "may break or violate Google's terms".

This is low-volume, read-only and arguably fine, but:
- The user is never told about it.
- The rules ban "captcha" bypass but say nothing about the grey zone: silent JS challenges, rotating UAs/IPs, or parallel runs.

**Proposed replacement:**
~~~text
- Respect sites: keep the scripts' pacing, run one search per site at a time, never rotate IPs/user agents or use proxies to get around a block, and on 429 / captcha / "verify you are human" / press-and-hold stop that source for the session (a JS challenge that a normal browser passes silently is the limit; anything interactive is manual-only). Several tools use sites' unofficial internal endpoints at low volume: say so once at intake, and if the user objects, use only the manual URLs plus the public MCP servers.
~~~

### P1-17. Japan-side costs (backtrack, NRT vs HND) are not part of the total

**File:** `tools.md` §10 (add one line after the P0-2 block). Related: `japan.md` L39 ("Take NRT if it's ≥ €15–20 cheaper").

**Problem.**
- `japan.md` has rules for these costs, but `quotes.py` totals ignore them.
- So round trip vs open-jaw, and NRT vs HND, are compared on fare alone.

**Proposed addition (`tools.md` §10):**
~~~text
- Japan-side differences are not automatic: add them with `--extras` (per person): ~€80 (¥14,000) Shinkansen backtrack to a plain return when the itinerary is Tokyo→Osaka (none for the open-jaw), and ~€5–15 extra city transfer for NRT vs HND (¥1,260–3,140 vs ¥300–500).
~~~

### P1-18. Quotes logged with `mcp_flights.py --log` can be mislabelled

**File:** `tools.md` §4a. Add after L77 (`- Same server is registered in .mcp.json …`).

**Problem.** `log_rows()` has three defects:
- **Kiwi self-transfers are never flagged.** Kiwi rows never get `--self-transfer`, so the `ST` column stays empty for Kiwi virtual-interlining combos.
- **Kiwi bag data is wrong for Chinese carriers.** It writes Kiwi's bag field, which P0-3 and fact 5 both describe as unreliable.
- **Skiplagged round trips get the wrong destination.** It takes the destination as `route[-3:]`. For round trips the route string concatenates both directions, so the logged destination equals the origin.

**Proposed addition (`tools.md` §4a):**
~~~text
- `--log` caveats: Kiwi rows are logged without the self-transfer flag and with Kiwi's (unreliable) bag field; Skiplagged round-trip rows get `dest` = the origin (route strings concatenate both directions). Fix the logged row by hand (`quotes.py add … --self-transfer --dest <JP> --bag-cost …`) for anything that reaches the shortlist.
~~~

---

## P2: polish

| # | File / line | Current text | Problem | Proposed replacement |
|---|---|---|---|---|
| P2-1 | `tricks.md` L16 | `Set up monitoring (playbook §6).` | Monitoring is playbook §9. | `Set up monitoring (playbook §9).` |
| P2-2 | `tricks.md` L19 | `` `deals.py` (20 feeds). `` | `deals.py` has 22 feeds (also stated in `sources.md`/`SKILL.md`). | `` `deals.py` (22 feeds). `` |
| P2-3 | `tools.md` L59 | `` `N` is not valid; use `--max-stops 0`. `` | The conclusion probably comes from a date with no nonstop. Research 05: `--route "N"` gave 0 on VIE→TYO 10 Mar, but `--minus 1 --plus 1` found an OS/NH nonstop on 9 Mar. Google's help (research 02 §1.2) documents `N`. It also contradicts `tricks.md` L52 and `matrix.py --help`. | `` `N` = nonstop per Google's docs (returned 0 on a date without a nonstop; confirm on a date with one). `--max-stops 0` or `C:OS` also work. `` |
| P2-4 | `CLAUDE.md` L34; `playbook.md` L10 | `€200–650 below ZAG` / `€230–650 below ZAG` | The two ranges disagree, and no research row supports €650. They mix one-way and return results. | CLAUDE: `run €230–330 below ZAG on the same RT dates in the Google test (10–24 Feb 2027), and one-way hub fares from BRU/IST undercut ZAG single tickets in the Kiwi origin-scans.` Playbook: same wording. |
| P2-5 | `CLAUDE.md` L34; `SKILL.md` L53 | `(BRU in Mar 2027, IST in May 2027)` | These come from a Kiwi one-way origin-scan. The Google round-trip sweep for Feb–Mar ranked ATH first. | `(Kiwi one-way origin-scan: BRU in Mar 2027, IST in May 2027; Google's RT sweep for Feb–Mar ranked ATH first)` (`SKILL.md` L53 is covered by the P0-3 replacement). |
| P2-6 | `sources.md` L45 | `- **No engine finds everything.** Same trip, different winners:` | The Kayak €356 row is a 10 Mar query. The others are 20 Jan. | `- **No engine finds everything.** Similar ZAG→TYO one-way queries, different winners (20 Jan unless noted):` and L49 → `` - Kayak `--nearby --flex 3` (10 Mar ±3): €356 FR+HO via CRL→BRU. `` |
| P2-7 | `tools.md` L5 (header) | `> Every script has --help …` | The working directory changes between files. The SKILL runs from the repo root (`$S`), the playbook from `flights/` (`scripts/deals.py`, `--cache searches/…`), and tools.md from `flights/scripts/`. Yet tools.md L40 passes `--cache flights/searches/<trip>/gf_sweep.json`, and `gflights.py` writes the cache without creating its folder. From `flights/scripts/` that path doesn't exist, so the sweep crashes on its first save. | Insert before L5: `> Commands below are shown from flights/scripts/ (cd there) except paths starting with flights/, which are repo-root paths: from the repo root use S=flights/scripts and python3 $S/<script>. Create flights/searches/<trip>/ before --cache/--out into it.` and change playbook L37/L70 to `python3 flights/scripts/deals.py …` / `--cache flights/searches/<trip>/gf_sweep.json`. |
| P2-8 | `tools.md` §3, §4b, §10 | (absent) | These options exist but are undocumented: `matrix.py --no-airport-change` (= ITA `-change`); `quotes.py add --live` (sets `verified_live`), `--self-transfer`, `--pax/--per`; and `kiwi_graphql.py calendar` is one-way only. Also, `--json` is a boolean on `mcp_flights.py` while `gflights`/`matrix` use `--out`/`--json-only`. | §3 add: `` - `--no-airport-change` drops itineraries with an airport change (ITA `-change`). `` §4b add: `` - `calendar` is ONE-WAY only (it ignores `--return-dates`/`--nights`). `` §10 add: `` - Mark a quote re-checked on the seller's checkout with `--live`; flag separate tickets with `--self-transfer`; party totals with `--per total --pax N`. `` Header L5 → `…and accept --json PATH|- (mcp_flights: --json flag to stdout; gflights/matrix: --out PATH / --json-only).` |
| P2-9 | `tools.md` (new, after L6) | (absent) | Date and stay semantics differ between tools:<br>• Kiwi `--nights` counts nights in Japan.<br>• Google's `--stay` counts the days between departure dates.<br>• Europe→Japan arrives +1 day.<br>• `--ret`/`--return` are local departure dates from Japan.<br>Comparing "14 nights" across tools is off by one. | `> Stay semantics: gflights/matrix --stay = days between the two departure dates; Kiwi --nights = nights in the destination (arrival is usually +1 day, so --stay 14 ≈ --nights 13). Return dates are LOCAL departure dates from Japan; via China, arrival home can be the next day. Compare tools on exact dates, not stay lengths.` |
| P2-10 | `japan.md` L33 | `ANA VIE–HND (3/wk winter)` | Research 04 §3 records a 26 Dec–11 Jan gap. | `ANA VIE–HND (3/wk from 3 Dec 2026, no flights 26 Dec–11 Jan)` |
| P2-11 | `japan.md` L27 | `**Air Serbia (JU):** BEG–PVG/CAN.` | Juneyao (HO) BRU/ATH–PVG is missing, though it set the €327 one-way floor in B0 and research 06. | `**Air Serbia (JU):** BEG–PVG/CAN. **Juneyao (HO):** BRU and ATH to PVG (BRU–PVG–NRT €327 OW, Mar 2027, the cheapest hub fare in B0; sold as one ticket with OU from ZAG on Skiplagged).` |
| P2-12 | `origins.md` L47 | `Proven feeder → Japan pairings:` | Only GDN–ARN + CA (fly4free) and ZAG–CRL + HO BRU (Kiwi) were seen priced. The rest are route-map ideas. | `Candidate feeder → Japan pairings (priced examples: Ryanair GDN–ARN + CA ARN–PEK–HND ≈ €457 RT; FR ZAG–CRL + HO BRU–PVG–NRT ≈ €361 OW):` |
| P2-13 | `tools.md` L31 | `` `OSA`=KIX,ITM `` | UKB has had international flights since 2025 (`japan.md` L40). The `gflights.py` comment "UKB (Kobe, domestic only)" is stale. UKB is excluded because it breaks calendars. | `` `OSA`=KIX,ITM (UKB excluded because it breaks calendars; add UKB explicitly to `search` for ICN/TPE feeds) `` |
| P2-14 | `SKILL.md` L42 vs `playbook.md` L57 | `--carriers MU,CA,CZ,KE,TK,QR,EK,LO` vs `--carriers MU,CA,CZ,HU,KE,TK,QR,EK,EY,LO,AY` | The two lists drift apart (so do the origin-scan lists). Two places hold the same commands. | Keep the canonical command lists only in `SKILL.md`. In the playbook, replace command lines with "see SKILL §N" plus the reasoning. At minimum, make both lists `MU,CA,CZ,HU,KE,TK,QR,EK,EY,LO,AY`. |
| P2-15 | `playbook.md` L61 | `` with `--sales-city` set to the origin city `` | Redundant: the default sales city is the departure city, and 8 sales cities priced the same (research 05 §5.4). | `` (sales city defaults to the departure city; changing it made no difference in tests) `` |
| P2-16 | `playbook.md` L67 | `€327 BRU–PVG–NRT on Juneyao in Mar 2027` | This is a one-way fare, listed next to a round-trip figure. | `€327 one-way BRU–PVG–NRT on Juneyao in Mar 2027` |
| P2-17 | `playbook.md` L129–130 | `Stop when 4+ independent inventories agree on the floor` | "Independent" is undefined. Kayak = momondo. Kiwi MCP = Kiwi GraphQL. Booking.com ≈ Etraveli ≈ Aviasales' Mytrip/Gotogate sellers. Google Flights and Matrix share the QPX engine. | `Stop when 4+ independent inventories (count each group once: Google Flights/Matrix · Kiwi MCP/GraphQL · Kayak/momondo · Skiplagged · Aviasales · Booking/Etraveli) agree on the floor` |
| P2-18 | `searches/_template/notes.md` L4; `report.md` L7 | `- Travelers / bags:` | Passports and party size are missing. The report has no party total and doesn't show whether the price was checked at checkout. | notes: `- Travelers (adults/children/infants, passports) / bags per person:`; report: add a `Total € party` column and a `Checked at checkout (--live)?` column. |
| P2-19 | `playbook.md` §7 (new checkbox) | (absent) | Some fees are never checked:<br>• Seat fees for travellers who want to sit together.<br>• On a mixed-carrier ticket (e.g. OU + HO), the bag allowance follows the "most significant carrier", so check it per ticket. | `- [ ] Party extras: seats together (fees on many fares); mixed-carrier tickets: bag allowance per the most significant carrier, so read it at checkout.` |
| P2-20 | `sources.md` §1 (new row) | (absent) | Research 01 §5 lists Japan-origin OTAs (skyticket.jp, Trip.com JP locale) for a Japan→Europe one-way and domestic legs. The weak yen (¥177/€) makes this worth one check when 2 × one-way is in play. | `` | Japan-origin OTAs (skyticket.jp, Trip.com `locale=ja-JP`) | **Manual** | user's browser | Japan→Europe one-ways and domestic legs priced in JPY | Check the card FX fee; one-way only | `` |

**SKILL frontmatter (`SKILL.md` L3), polish.**
- The description triggers well on "find, compare, check or monitor flight prices".
- It would also catch "cheap flights / airfare / plane tickets / Tokyo / Osaka / error fare / price alert" phrasings if those words were added.
- Suggested description:
~~~text
Find the user the cheapest real, bookable flight ticket (cheap flights, airfare, plane tickets), built for home region Zagreb/Central Europe → Japan (Tokyo, Osaka…); other routes need the adaptations in the skill. Searches nearby departure airports and Europe-wide hubs with positioning flights, across Google Flights, ITA Matrix, Kiwi, Skiplagged, momondo/Kayak, Aviasales, Booking.com, Ryanair/Wizz and deal/error-fare feeds, compares RT / one-ways / open-jaw / self-transfer, ranks by true total cost, and reports or sets up price monitoring. Use when the user asks to find, compare, check or monitor flight prices or deals, or to plan buying a ticket.
~~~

**Progressive disclosure (assessment, no change required).** `CLAUDE.md` (68 lines) and `SKILL.md` (79 lines) are the right size and order:
- `CLAUDE.md` holds the facts that change the search.
- `SKILL.md` holds the commands.
- The other files are references.

The main debt is that `playbook.md` repeats about 60% of `SKILL.md`'s commands, and they drift (P2-14).

---

## Stale-risk register (facts the docs state flatly that will change)

| Fact as stated | Where | Why it will go stale | Re-check |
|---|---|---|---|
| Air China ZAG–OTP–PEK Mon/Wed/Fri since 4 Sep 2026 | CLAUDE #4, japan §2, origins §1 | New route with a fifth-freedom leg; often trimmed in the first winter | Zagreb Airport timetable, before each hunt |
| China 30-day visa-free entry until 31 Dec 2026 | CLAUDE, japan §5, playbook §5, tricks B | Renewal decision expected ~Nov 2026 | Nov 2026 (P1-9) |
| K-ETA exemption list (Croatia not on it; exemptions to 31 Dec 2026) | japan §5, research 03 | Temporary exemptions get extended or ended at year end | k-eta.go.kr, Jan 2027 |
| Qatar ZAG 4/wk A320; Gulf "elevated risk" | japan §2, origins | Post-conflict network still recovering | Each hunt (caveat already in SKILL) |
| Austrian VIE–NRT summer only (back ~29 Mar 2027); LH MUC–KIX 3/wk NW26; ANA VIE 3/wk | japan §2 | Seasonal schedules | At the NS27 / NW27 filings |
| Trinity (ex-T'way) ZAG–ICN summer-only, 2027 unknown | japan §2 | The airline is in "emergency management" | Spring 2027 |
| Google Flights lacks MU/CA/CZ on Europe→Japan | CLAUDE #1, sources, tools | Distribution deals change without notice | Re-run the B1 control (`--via PVG`) every few hunts |
| Matrix API works without the BotGuard token; GF RPC, Kiwi GraphQL and Kayak poll formats | tools §2–6 | Unofficial endpoints | Smoke-test in `setup.sh` (it currently checks only fx and the two MCP servers) |
| AZair has no results beyond ~Jan 2027 | sources, tools §9 | Rolling horizon | Phrase as "≈3 months ahead" (tools already does) |
| Wizz "no ZAG / no VIE"; Ryanair route lists | sources, origins §3, tools §8 | Seasonal network changes | `ryanair_wizz.py routes` each hunt |
| Trustpilot scores; AGCM fine; Kiwi Guarantee terms; Kiwi T&C 6.3.2 | sources §2, tricks C | Ratings and terms drift | Yearly |
| Frommer's 2025/2026 and Which? Oct 2025 rankings | sources §3, tricks A9 | Annual tests | Next edition (~Nov 2026) |
| ANA "Stopover & Add-on Free Fare" window; Qatar Black Friday | tricks B, playbook §9 | Annual promotions | Late Nov 2026 |
| EU261 reform "applies ~H2 2027" | tricks D | Depends on the publication date | When it is published in the OJ |
| Japan departure tax ¥3,000 (tickets bought from 1 Jul 2026); JESTA FY2028 | japan §5 | Policy | Yearly |
| FlixBus prices/times, ZAG parking €193/14 d | origins, ground.json | Timetables and price lists | `flixbus_ground.py --date` each hunt |
| Revolut €1,000/month free FX, +1% weekends | tricks B | Plan terms | When the user names their card |

Suggested wording for living docs: prefix volatile facts with "(as of 2026-10-04)". Some already are; the airline schedule lines in `japan.md` §2 mostly aren't.

---

## Safety and ethics (summary)

- **Hidden-city defaults:**
  - `mcp_flights.py sk` includes hidden-city fares unless `--no-hidden-city` is passed, and the skill's command omits the flag (P1-1).
  - `kiwi_graphql --hacks` is correctly off by default.
  - Hidden-city, throwaway and non-EU point of sale are all gated on opt-in in `tricks.md` D. Good.
- **Captchas and bot walls:** the rule exists. The grey zone (silent JS challenges, UA/IP rotation) and telling the user about the unofficial endpoints need one sentence (P1-16).
- **Accounts, booking, payment:** prohibited in both `CLAUDE.md` and `SKILL.md`. Good.
  - Student fares, Qatar Student Club and Trip.com coupons need accounts. The docs present these as the user's actions, which is correct.
  - Consider adding "(the user creates any account)" next to the student-fare line in `tricks.md` B.
- **Mistake fares:** "book within minutes" is advice for the user, and the agent never books. Fine.
- **Personal data:** `progress.md` (PWA, out of scope) holds booking PINs and confirmation numbers. Not part of this review, but don't copy it into flight reports.

---

## Code follow-ups (outside this doc review; suggested as separate tasks)

1. **`quotes.py`:**
   - warn and show `?` for origins missing from `ground.json`;
   - apply `fri_eur` when `out` is a Friday or Sunday;
   - make `hotel_if` numeric;
   - add `--leg out|ret` so one-way legs get one-way ground;
   - allow a per-trip ground file.
2. **`mcp_flights.py`:**
   - default `sk` to `includeHiddenCity=false` with a `--hidden-city` opt-in;
   - make `--log` pass `--pax/--per total` when `--adults > 1`, and pass `--self-transfer` for Kiwi virtual-interlining rows;
   - fix the Skiplagged round-trip `dest` parsing.
3. **Route strings:** make `kayak.py`, `kiwi_graphql.py`, `aviasales.py` and `booking_flights.py` mark a station change with `~` (as `mcp_flights` does); `kayak.py` should also print the `hacker` column.
4. **`matrix.py`:** apply `--route-ret`/`--ext-ret` (and `--carriers`) to the last slice in `--slice` mode, and allow a per-slice routing syntax.
5. **`positioning.py`:**
   - support `--adults`;
   - support a round-trip mode (hub⇄Japan return + both positioning legs);
   - add an optional `--pos-bag-eur` per leg.
6. **`deals.py`:** add `--keywords` / `--region-words` so other destinations and home bases work without code edits.
7. **`gflights.py`:** create the `--cache` parent directory; consider a multi-city (trip type 3) search for open-jaw.
8. **`kiwi_graphql.py`:** implement a round-trip calendar (`returnItineraryPricesCalendar`), or reject `--return-dates` on `calendar`.
9. **`monitor.py`:** optional per-check filters (`max_stops`, `no_self_transfer`) applied to rows before taking the minimum; under-threshold alerts only on a change.
