# Trip dryrun-tyo-2027-05: search log

## Brief (from profile.md + user message, 2026-10-04)
- Travelers / bags: 1 adult. 1 checked bag (assume 23 kg) + cabin bag, each way (profile default; user said "1 checked bag").
- Home / allowed origins: Zagreb (confirmed by user). Bus to VIE or BUD OK. Other catchment airports (LJU, GRZ, BEG, VCE, TRS, MUC) not mentioned, so checked but flagged. Positioning flights treated as self-transfer.
- Japan airports / open-jaw: Tokyo (TYO = NRT+HND) or Osaka (OSA = KIX+ITM). Open-jaw TYO<->OSA not mentioned: ASSUMED OK, shown separately.
- Date window / flexibility / trip length: out 2027-05-12 +/-3 (09-15 May), back "about two weeks later" = ~2027-05-26, assumed +/-3 (23-29 May), stay 12-16 nights.
- Risk appetite: self-transfer OK only if it saves > EUR 100 (user's number; overrides profile default EUR 80 and skill §5 EUR 150). Positioning flights = self-transfer, same rule. Hidden-city: NO (explicit).
- Budget / buy-now threshold: TBD (not given). Benchmarks: great < EUR 500 RT with bag, normal 650-950 (japan.md §1).

### Questions I would have asked (not asked: dry run, defaults used)
1. Open-jaw OK (into Tokyo, out of Osaka or vice versa)?
2. Exact trip length / hard return date? "About two weeks" read as 12-16 nights.
3. Checked bag weight: 23 kg assumed. Cabin bag too?
4. Any student status / age < 30 (Turkish/Qatar student fares)?
5. Payment card with no FX fee (Revolut/Wise)? Decides foreign-currency OTAs.
6. Budget / threshold to buy now vs monitor?
7. Other origins OK: LJU, GRZ, BEG, VCE, TRS, MUC? Positioning flights (e.g. to IST/BRU)?
8. Max stops / max travel time / overnight layovers (defaults used: 2 stops, 30 h, overnight OK if saves >= EUR 100)?
9. Transit visa situations: OK to route via China (visa-free transit until 31 Dec 2026 only - trip is May 2027!)?

## Log
<!-- date-time (UTC, 2026-10-04) | tool + args | result | best EUR | notes -->
- 18:16 | `setup.sh` | all smoke tests OK | - | 4 s (skill says ~1 min)
- 18:17 | `deals.py --days 60` | 21 deals; none from ZAG/VIE/BUD for May; Hainan BRU EUR 635 w/ bag (Sep post), PL Qatar sales | - | 37 s
- 18:18 | `kiwi_graphql.py calendar --from ZAG --to TYO --dates 2027-05-09..2027-05-15` | ONE-WAY only: 12 May EUR 456, 10 May 464 | 456 OW | 7 s
- 18:18 | `gflights.py calendar --from VIE --to TYO,OSA --start 2027-05-09 --end 2027-05-15 --stay 12-16 --bags 1` | ~10 RPCs, 2x HTTP 429, OSA cache sparse; VIE 11->26 May EUR 675 | 675 | 2 m 50 s
- 18:19 | `mcp_flights.py skcal BUD TYO 2027-05-12 --ret 2027-05-26` | return-date flex only (incl. same-day return), USD 1,398+ | - | 4 s, low value
- 18:21 | `kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26 --flex 3` | 8,116 results; top-50 page all MU from BUD: split TR+CZ 627 (hacker), Kiwi/SKYPICKER MU 678, OPODO MU/CZ 684 (2 bags) | 684 single | 44 s
- 18:22 | `mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD,BEG,VCE,TRS,MUC TYO,OSA 2027-05-12 --flex 3 --ret 2027-05-26 --ret-flex 3` | 15 rows, all MU BUD 717-748 (hold bags 0) | 717 | 4 s. Missed AI VIE 708 (see 18:41)
- 18:22 | `kiwi_graphql.py search --from ZAG@400 --to Country:JP --dates 2027-05-09..2027-05-15 --return-dates 2027-05-23..2027-05-29` | 50 rows, all MU BUD 717+, BAGS 0 | 717 | 8 s. Also missed AI VIE 708
- 18:23 | `mcp_flights.py sk {BUD,ZAG,VIE} TYO 2027-05-12 --ret 2027-05-26 --no-hidden-city` | BUD USD 775 (MU out + QR back, 2 one-ways); ZAG USD 1,126; VIE USD 1,092 | ~690 EUR | ~10 s
- 18:24 | `aviasales.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26` | Turna 700.75 MU/CZ 1 bag; Kiwi 706; Gotogate 717.56 MU 2 bags | 700.75 | 35 s
- 18:24 | `booking_flights.py --from BUD --to TYO --depart 2027-05-12 --return 2027-05-26` | MU 741.27, 2 bags | 741 | 24 s
- 18:25 | `gflights.py search --from ZAG,LJU,GRZ,VIE,BUD,BEG,VCE --to TYO,OSA --date 2027-05-12 --return 2027-05-26 --bags 1` | BUD QR 812, VIE AY 949, ZAG 1000; no MU/CA/CZ (as documented) | 812 | 24 s, 1 request
- 18:26 | `matrix.py search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26 --carriers MU,CA,CZ,TK,QR` | MU 678.76 (VIE 06:20 via CDG out, back to BUD); MU BUD-BUD 715.27; QR 819; CA 1,144; TK 1,632; CZ none | 678.76 | ~3.5 min, 5 Matrix calls
- 18:26 | Kiwi MCP per-carrier `--only-airlines` CA / CZ / HU / KE,OZ / TK / QR / EY / LO / AY / NH,JL | CA 885 VIE, QR 832 BUD, EY 961, CZ 966, LO 1004, AY 1005, NH 1081, KE/OZ 1155, TK 1214, HU none | - | ~60 s
- 18:30 | `kiwi_graphql.py per-city --from Continent:europe --to Country:JP --dates 2027-05-09..2027-05-15` (as in skill) | ONE-WAY: VIE-KIX 363 (Scoot), ARN-HND 381 | - | 3 s
- 18:30 | same + `--return-dates 2027-05-23..2027-05-29` | RT: MAD-KIX 662, BCN-NRT 680 (one origin per JP city only) | - | 3 s
- 18:31 | `kiwi_graphql.py origin-scan --to TYO,OSA --dates 2027-05-09..2027-05-15 --return-dates 2027-05-23..2027-05-29 --origins <22>` | ATH 588 (ET via ADD/ICN), MAD 659 (CA), FRA 698, LHR 705, **VIE 708 (Air India, 1 ticket)**, BUD 717 (MU) ... ZAG 900 | 708 home | 2 min. Only run that surfaced AI VIE
- 18:32 | `positioning.py --home ZAG,LJU,GRZ,VIE,BUD,TSF,VCE,TRS,BTS --hubs ATH,MAD,BCN,FRA,LHR,IST,BRU,MXP --to TYO,OSA --dates 2027-05-09..2027-05-15 --single-ticket --checked-bags 1` | OW out: W6 BUD-ATH 33.56 + ATH-ADD-ICN-NRT 364 = 397.56; W6 BUD-IST 52.25 + IST-PKX-HND 349 = 401.25 | - | **8 min 19 s**
- 18:38 | `positioning.py --direction back --home ZAG,VIE,BUD,BTS,VCE --hubs ATH,IST,BCN,MAD --to TYO,OSA --dates 2027-05-23..2027-05-29 --single-ticket --checked-bags 1` | NRT-UBN-IST 398 + W6 IST-BUD 59.99 (22 h gap) = 457.99 | RT combo ~859 + Wizz bags + night | 2 min. Loses by > EUR 150
- 18:38 | `gflights.py search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-11 --return 2027-05-26 --bags 1` | Scoot VIE-SIN-HND 675 (TR61/TR882, lands HND 01:05), QR BUD 810 | 675 | 23 s. price_insights empty
- 18:39 | Kiwi MCP one-ways out/back flex 3 (+ `--no-self-transfer`) | out: Scoot VIE-SIN-KIX 363, MU BUD 443; back: Scoot HND-SIN-VIE 378, MU NRT-PVG-BUD 498 | 2xOW 741 | 2xOW loses to RT
- 18:39 | `matrix.py search --slice "VIE/BUD:TYO:2027-05-12" --slice "OSA:VIE/BUD:2027-05-26" --carriers MU` | EUR 4,241: MU+ applied to slice 1 only, return priced NH+TK | invalid | 36 s, 6th Matrix call
- 18:41 | `kayak.py --site www.momondo.de --from VIE --to TYO,OSA --depart 2027-05-11 --return 2027-05-25,2027-05-26` | Scoot RT: Gotogate 678, Bookingflights 687; CA Expedia 827 (2 bags) | 678 | 62 s
- 18:41 | Kiwi MCP ZAG `--only-airlines CA` / AI / TR / `--exclude-airlines MU,FM` | CA ZAG-OTP-PEK 1,415; **AI VIE 708 (11->25 May, 1 hold bag)**; Scoot RT 838; ex-MU best QR 853 | 708 | ~15 s
- 18:43 | `flixbus_ground.py --from Zagreb --to Budapest Vienna --date 2027-05-11` / `-12`, back 27 May | ZAG->BUD: only 8.5-12 h transfers (no direct; ground.json says 5.3 h); fastest same-day arrives 12:25, too late for MU 12:30, so 11 May 13:00->21:30 + night. ZAG->VIE 01:45 -> 07:05 EUR 23.48. BUD->ZAG 27 May 12:45 EUR 35.97; VIE->ZAG 35.98 | - | 2 s
- 18:46 | `kayak.py --site www.momondo.de --from BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26` | OPODO 684 MU/CZ BUD-PVG-KIX / KIX-CAN-BUD 2 bags; OPODO 692 MU/MU; Gotogate 699 | 684 | ~45 s (re-verification)
- 18:46 | `aviasales.py --from VIE --to TYO --depart 2027-05-11 --return 2027-05-26` | cheapest 716 (Scoot, no bag), **cheapest_with_baggage 856** | - | 36 s (ran twice: `tail` cut the header)
- 18:47 | `gflights.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --bags 1` | hung > 5 min (429 back-off 45/90/180 s); killed; Google stopped for the session | - | 5 min wasted
- 18:50 | `kiwi_graphql.py search --from VIE --to TYO --dates 2027-05-11..2027-05-11 --return-dates 2027-05-25..2027-05-26 --checked-bags 1` | AI 708, 1 PNR, 1 bag incl.; Scoot RT gone from top 12 | 708 | 7 s
- 18:52 | `monitor.py watch.json --only kiwi` | works; exposed two Kiwi traps below | - | 19 s
- 18:53 | Kiwi probes | `--checked-bags 1` turns MU 717 into **1,051.89** (Kiwi adds a bag fee to a fare that includes 2x23); multi-origin `--from VIE BUD` hides AI VIE 708 even with `--limit-api 250` | - | 30 s

Correction: an earlier quote row says "1 checked per MCP" for MU. That is wrong: the MCP column is personal/cabin/hold, so `1/1/0` = 0 hold bags. quotes.py cannot edit rows.

Budget used: Google 4 invocations (~13 RPCs, 2x 429 + 1 stuck), Matrix 6 calls.

## Shortlist (true total per person = fare + ground + extras)
1. **MU/CZ BUD <-> KIX (or NRT/HND), 12 -> 26 May**, OPODO EUR 684, 2x23 kg, one ticket. Ground 70 + Budapest night 50 = **~EUR 804**. MU direct fare level EUR 715 (Matrix). Same fare family at 6 sources (684-741).
2. **Air India VIE <-> HND, 11 -> 25 May**, Kiwi EUR 708, 1 hold bag, 1 PNR. Ground 66 = **~EUR 774**. Return 38 h (over the 30 h default).
3. **Scoot VIE <-> HND, 11 -> 26 May (dep 02:20 = night of 25th)**, Google 675 / Gotogate 678 / Booking 687, checked bag almost certainly NOT included. Ground 68 = EUR 743 + bag fee (not fetched).
4. QR BUD <-> HND 12 -> 26 May, OPODO 794 (1 bag) / Google 812; 10:00 dep also needs a BUD night: ~EUR 914.
5. CA VIE <-> KIX/HND 11 -> 25 May, Expedia 827 (2 bags) / Kiwi 861-885: ~EUR 893+.
Losers: positioning via IST/ATH (~EUR 1,000 all-in), 2x one-way, open-jaw (not reliably priced).

## Manual checks requested from the user
- Skyscanner BUD/VIE, Trip.com BUD, ceair.com, airindia.com, flyscoot.com (bag fee), Secret Flying, Google Flights "Cheapest" tab + multi-city open-jaw, ZAG->BUD morning train. URLs in report.md. Nothing reported back yet (dry run).
