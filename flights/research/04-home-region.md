# 04 — Home region: every departure airport worth considering from Zagreb

Researched **2026-10-04** (Sunday). Home base assumed **Zagreb, Croatia** (consistent with the repo's earlier trip, which flew Zagreb→Basel). Not yet confirmed by the user.

**Tags used:**
- `[verified: how]` means checked today on a primary or near-primary source (operator API, official airport page or PDF, airline/airport press).
- `[claimed: source]` means secondary (Wikipedia, aggregators, news, blogs, or the snippets from my searches). Treat these as leads to re-check before relying on them.
- `[estimate]` means my own approximation.

**Swapping the home base:**
- Re-run `flights/scripts/flixbus_ground.py --from "<City>" --date YYYY-MM-DD` to get bus/train prices and times from the new city to every airport.
- Run `... --drive --home <lon,lat>` to get driving distance and time.
- The long-haul and deal sections (§3–§6) depend on the region, not on Zagreb, so they still apply.

---

## 0. 2026 context that changes the usual advice (read first)

1. **Middle East war (Iran) since late Feb 2026.** Gulf hubs shut down or shrank in March–May 2026.
   - UAE lifted all restrictions on 2 May 2026 [claimed: Al Jazeera via search].
   - Emirates was back to about 96% of its network by May. Qatar resumed **Zagreb and Belgrade on 16–17 Jun 2026** at 4×/week on an A320 ([exyuaviation 2026-06-17](https://www.exyuaviation.com/2026/06/qatar-airways-returns-to-zagreb-and.html?m=1)). Qatar resumed Tokyo Haneda on 15 Jul 2026 [claimed: search].
   - As of **28 Sep 2026** the risk is still "elevated". Iranian airspace is only usable above FL285, and airlines cancel and reroute at short notice ([Wego, Sep 2026](https://blog.wego.com/middle-east-travel-update-iran-israel-conflict-what-wego-travelers-need-to-know-right-now/)) [claimed].
   - **Rule:** a Gulf-hub itinerary is real and bookable, but needs a reliability caveat and a check of the carrier's latest schedule.
2. **Air China Beijing–Bucharest–Zagreb started 4 Sep 2026.**
   - 3×/week (Mon/Wed/Fri), A330-200, with about 3 h on the ground in Bucharest.
   - It is the first ever scheduled China–Croatia link. Zagreb Airport's official timetable now lists "BEIJING CAPITAL" and "BUCHAREST" [verified: zagreb-airport.hr timetable dropdown, 2026-10-04].
   - Air China says Bucharest–Zagreb-only tickets can be sold ([exyuaviation 2026-08-16](https://www.exyuaviation.com/2026/08/air-china-readies-for-zagreb-launch.html), [migflug 2026-09-03](https://migflug.com/afterburner/air-china-beijing-bucharest-zagreb-route-launch-2026/)).
   - **This is the single most important new option from ZAG:** a Chinese carrier at the home airport, connecting in PEK to NRT, HND, KIX and more.
   - **Warning:** travel-dealz reports that Air China promo fares often **don't appear in Google Flights or ITA Matrix**. Search airchina.com's flexible search, Trip.com or Skyscanner directly ([travel-dealz 2026-07-17](https://travel-dealz.com/ticker/121404/)).
3. **Emirates does NOT fly to Zagreb.** It last flew there in Oct 2019. **flydubai** serves ZAG:
   - 3×/week (Wed/Fri/Sun) until 1 Oct 2026, with "hopes" of going daily after October ([travelradar 2026-06-22](https://travelradar.aero/flydubai-reduces-operations-due-to-conflict/)).
   - flydubai is listed among ZAG airlines [verified: zagreb-airport.hr carrier list].
4. **T'way Air Zagreb–Seoul (ICN)** ran **nonstop** in summer 2026: from 27 Jun, 3×/week, A330-200, TW409/410, return departures from ZAG on Tue and Sun ([AeroRoutes 2026-02-10](https://www.aeroroutes.com/eng/260210-twns26zag)).
   - Promo sales mentioned travel up to 24 Oct 2026.
   - "SEOUL" is **not** in ZAG's timetable dropdown today, so treat it as summer-only. Re-check for summer 2027.
5. **European carriers still avoid Russian airspace,** so Europe–Japan nonstops are long. Chinese carriers keep their price edge via PEK, PVG, CAN, XIY and other Chinese hubs.

---

## 1. Ready-to-use master table

Notes on the table:
- "Ground" is one-way, per person, by public transport, from central Zagreb to the terminal.
- FlixBus prices come from FlixBus's own search API for Tue 10 Nov 2026, Fri 13 Nov 2026 and Tue 19 Jan 2027, including the platform fee [verified: global.api.flixbus.com, 2026-10-04].
- Drive times are OSRM free-flow times from Zagreb centre. Add border queues for BiH and Serbia (outside Schengen) [verified: router.project-osrm.org].
- Carrier lists say "Japan-relevant" when the carrier flies nonstop to Japan or feeds a hub that does.

| IATA | City | Tier | Ground time from ZAG | Typical ground cost EUR (1-way) | How | Long-haul/hub carriers relevant to Japan | Notes |
|---|---|---|---|---|---|---|---|
| **ZAG** | Zagreb | 1 (home) | 25–45 min (15 km) | **8** (Pleso shuttle) · ~1 (ZET bus 290) · 20–30 taxi/Bolt [estimate] | Pleso prijevoz bus from main bus station every 30 min (€8 [claimed]); ZET 290 | **Air China** (PEK via OTP, 3×/wk); **Turkish** (IST); Pegasus (SAW); **Qatar** (DOH); flydubai (DXB); LH/Air Dolomiti/Croatia (FRA, MUC); Austrian (VIE); Swiss/Croatia (ZRH); KLM (AMS); Air France (CDG); LOT (WAW); Iberia (MAD); BA (LHR); SAS/others (CPH, ARN); Ryanair (FCO, BGY, STN, WMI…); T'way ICN in summer only | Official destination list verified 2026-10-04. Parking €24 first day + €13/day (→ ~€193 for 14 days) [verified: zagreb-airport.hr price list valid from 1.10.2026] |
| **LJU** | Ljubljana (Brnik) | 1 | 2h10–2h50 bus to Ljubljana + ~45 min airport bus ≈ 3–3.5 h; car 2h00 (169 km) | **15–25** (Flix €9.98–11.48 + airport bus ~€4 or GoOpti) | FlixBus (11–18/day), HŽ/SŽ train ~2h10–2h30, GoOpti door-to-door | **Turkish** (IST, 14/wk), Pegasus (SAW, since Jan 2026), flydubai (DXB, 2/wk; suspended Mar–May 2026), LH (FRA, MUC), Swiss (ZRH), KLM (AMS), LOT (WAW 6/wk), Finnair (HEL, summer), Transavia (ORY), BA (LHR) | [claimed: Fraport Slovenija news 2026; slovenia.info 2026-02-19]. The airport site blocks scripts (403). |
| **GRZ** | Graz | 1 | 2h40–3h15 bus + ~20 min local; car 2h05 (175 km) | **15** (Flix €11.48–14.98 + ~€3 local) | FlixBus (9–12/day incl. 01:45→04:30), EC train (Zagreb–Graz direct, ~2/day [claimed]) | **LH/Air Dolomiti** FRA (≤20/wk) & MUC (≤19/wk), **Swiss** ZRH daily, **Pegasus** SAW (Mon/Sat) | Winter 26/27 list [verified: graz-airport.at PDF "Stand 02.09.2026"]. Turkish has left GRZ. |
| **TRS** | Trieste (Ronchi) | 1 | 4h50 Flix direct to airport (14:05→18:55); city 4h00 + train | **14–18** | FlixBus direct to airport (1–2/day) or to Trieste city + regional train | Air Dolomiti FRA (winter suspension being discussed), Ryanair (STN, BVA, CRL, DUB, BCN, BER, PRG, ARN, KRK, NAP, MLA) | Ryanair list [verified: ryanair.com routes API]. Weak long-haul feed. |
| RJK | Rijeka (Krk) | 1 | 2h15–3h to Rijeka (€5.98) + transfer | ~10–15 | FlixBus; Pleso prijevoz Rijeka–ZAG airport line | Summer only: LH FRA/MUC, Ryanair STN/CRL/HHN/ARN | Summer-only positioning [verified: Ryanair API; LH claimed: Wikipedia] |
| MBX | Maribor | 1 | 1h40–2h10 (€10.48) | — | FlixBus | No meaningful scheduled service [claimed] | Ignore |
| PUY | Pula | 1–2 | car 3–4 h (271 km) | — | bus/car | Summer Ryanair (CRL, FMM, KTW, NRN, STN, VIE) | Summer-only positioning [verified: Ryanair API] |
| KLU | Klagenfurt | 1–2 | car 2h55 (229 km); no Flix direct | — | car / train via Ljubljana–Villach | Ryanair STN; Sky Alps FCO/VIE | Ignore for Japan |
| BNX | Banja Luka | 1–2 | 2h45–3h20 (€30.99) + border | ~35 | FlixBus; car 2h06 + BiH border | Ryanair: ARN, FMM, VIE (+others) | Positioning only |
| ZAD | Zadar | 2 | 3h30 (€11.48–15.48) + airport bus | ~17 | FlixBus 12/day | Ryanair base, ~50 routes incl. **HEL, ARN, CPH**, VIE, BUD, PRG, OTP, STN… (mostly summer) | [verified: Ryanair API]. Summer positioning hub. |
| OSI | Osijek | 2 | car 3h15 (297 km) | — | car/bus | Ryanair STN only | Ignore |
| **VIE** | Vienna | **2** | Flix **direct to airport 06:30→11:55** (5h25); to Vienna city 5h00–5h50 (+25 min train); EC train 07:25→Wien Hbf 14:07; car 4h19 (378 km) | **22–40** (Flix airport €21.48 Tue / €37.98 Fri / €23.97 Jan; city €19.98–25.98 + ~€5 train) | FlixBus (12–14/day to city incl. 01:45→07:05 & 23:30→04:35); EC "Croatia" from €29.90 [claimed: seat61]; BlaBlaCar; car + parking | **ANA** HND (nonstop); **Austrian** NRT (seasonal) & PVG (paused 30 Nov–20 Feb); **Air China** PEK; **China Eastern** XIY; **Hainan** CTU/SZX; **Korean** ICN; **EVA, China Airlines** TPE; Emirates, Qatar, Etihad, Turkish, AJet/Pegasus, Air Arabia (SHJ), Scoot SIN [claimed], Air India; Ryanair (HEL, ARN, CPH, WAW, STN, MXP, BGY, FCO, MAD, OTP, SOF…) | **Strongest regional Japan origin.** ANA/OS [verified: AeroRoutes]; others [claimed: Wikipedia + deal posts]. Parking C €104.90/week; off-site from ~€119 for 14 days [claimed: autorevue.at] |
| **BUD** | Budapest | **2** | Flix to city 3h55–5h50 + ~45 min bus 100E; **Fri overnight Flix direct 23:59→airport 04:50**; car 4h05 (374 km) | **26–42** (city €20.48 Tue / €35.98 Fri + ~€6 bus; airport direct €25.98 Fri; airport via transfer €35–41) | FlixBus (4–15/day); IC "Agram" train 16:30→Déli 22:24 from ~€17 [claimed: seat61; check 2026 works]; car | **Air China** PEK & CKG; **China Eastern/Shanghai Airlines** PVG, NGB, XIY; **China Southern** CAN; **Hainan** SZX; **Korean** & **Asiana** ICN (Asiana since 3 Apr 2026); Emirates (daily from Jun 2026), flydubai, Qatar?, Turkish, Pegasus/AJet, Finnair HEL, LOT, Qanot Sharq TAS; Wizz base (JED, AUH? [unverified]); Ryanair (ARN, CPH, STN, MXP, BGY, MAD, PRG, SOF…) | **Second-strongest; 8 Far-East routes** [claimed: BUD press 2024 + Wikipedia 2026]. Parking from ~HUF 11,900/week (~€32) [claimed] |
| BTS | Bratislava | 2 | 6h20–9h via Vienna/Budapest; car 5h00 (428 km) | ~28 (city €23.98–27.48 + bus) | FlixBus (Express 01:45→08:25) | No long-haul (Smartwings seasonal DXB/DOH charters [claimed]); Ryanair (STN, DUB, BCN, MXP, WMI, EIN…) | LCC positioning only. Vienna Airport is 1 h away anyway. |
| **BEG** | Belgrade | 2 | 5h30–5h55 (4/day, incl. 22:15→04:10) + border; car 4h02 + border | **~28** (Flix €23.98–25.98 + airport bus ~€3–4 [estimate]) | FlixBus; Zagreb–Belgrade train **still suspended in 2026** [claimed: seat61]; Air Serbia ZAG–BEG flight | **Air Serbia** CAN & PVG (with China Southern codeshare); **China Southern** CAN; **Hainan** PEK; **Qatar** DOH (4/wk); flydubai DXB (14/wk); Turkish, Pegasus/AJet; SCAT (NQZ); LH, KLM, LOT | Non-Schengen (expect border queues). Air Serbia China routes [verified: Air Serbia press 2026-01-11]; others [claimed] |
| **VCE** | Venice Marco Polo | 2 | Flix **direct to airport**: 07:30→13:45, 14:05→20:20, 18:00→23:55 (~6 h); car 4h03 (368 km) | **18–25** | FlixBus direct; GoOpti; car (Italian tolls) | **Emirates** DXB (daily again since Jun 2026), **Qatar** DOH, **Turkish** IST, **China Eastern** PVG (5/wk in summer 2026), LH, KLM, AF, LOT, Finnair (summer) | Emirates/Qatar were suspended until 28 Mar 2026 [claimed: italiavola.com] |
| TSF | Treviso | 2 | 6h30–8h30 (transfer) | ~32–45 | Flix transfer, or via Mestre + local bus | None; Ryanair base (LTN, BVA, CRL, EIN, BER, BUD, PRG, OTP, SOF, LIS, WMI, VIE…) | Positioning only [verified: Ryanair API] |
| SJJ | Sarajevo | 2 | 7h10–8h25 (€46.99–47.99) | ~55 | FlixBus; Croatia Airlines flight | Turkish IST, AJet SAW, flydubai DXB, LH FRA, Austrian VIE, Flynas, Ryanair (STN, BGY, BVA, CRL, FMM, NRN, ARN) | Occasional cheap Asia deals ex-SJJ (see §5). Too far by bus for regular use. |
| TZL | Tuzla | 2 | 5h30–5h45 (€50.99) | ~55 | FlixBus | Wizz base (positioning) [claimed] | Positioning only |
| SPU | Split | 2 | 7h50 (transfer, €20.48), or bus to Split city ~5 h; car 4h23 | ~25 | FlixBus; HŽ train | Summer hub feeds (Ryanair FCO, DUB…) | Summer only |
| BLQ | Bologna | 2–3 | 8h45–9h40 bus to city (€24.48) | ~35 | FlixBus direct | Emirates (DXB), Turkish, LH | Marginal |
| **MUC** | Munich | **3** | Flix to Munich ZOB 8h20–9h40 (incl. 22:30→06:55) + 40 min S-Bahn; **night train "Lisinski" 19:39→Munich ~06:01** [claimed: HŽPP]; car 6h18 (588 km) | **40–50** (Flix €26.48–36.98 + ~€14 S-Bahn); night train couchette from ~€50 [claimed: seat61] | FlixBus (6–12/day), EN Lisinski (seat/couchette/sleeper), EC via Villach 08:40→17:41 from €37.99 [claimed] | **Lufthansa HND daily + KIX 3/wk** (W26/27); **ANA HND** (5 of 7 weekly Dec–Feb); plus the whole LH long-haul network (PVG, ICN, SIN, BKK…) | Best nonstop-to-Japan option that's reachable overnight by land [verified: AeroRoutes LH NW26 filing & ANA NW26] |
| MXP / BGY / LIN | Milan | 3 | Flix ~9h50 to Milan (07:30→17:25, 20:45→06:35); airports 10.5–17 h; car 6–7 h | 28–50 by bus; **better: Ryanair ZAG–BGY flight** | Ryanair ZAG–BGY [verified: Ryanair API] | **Air China** (MXP–PEK; deal €551 to Tokyo, Dec 2026), **ANA** MXP–HND (since Dec 2024, 3/wk [claimed]), Emirates, Qatar, Etihad, Turkish, Cathay?, etc. | Use as a "virtual origin" reached by a positioning flight |
| PRG | Prague | 3 | ~10 h bus (23:30→09:10; €29.98–31.98); car 7h49 (664 km) | ~35 + hotel | FlixBus direct to city | China Airlines TPE, Korean ICN, **VietJet HAN from 10 Oct 2026** (~€500 return), Emirates, Qatar, Etihad, Turkish | Rarely worth it from ZAG |
| FCO | Rome | 3 | car 9h54; no sensible bus | — | **Ryanair ZAG–FCO** / Croatia Airlines / ITA flights | **ITA HND daily** (ITA joins the LH/ANA Japan JV in Oct 2026) [claimed] | Virtual origin via positioning flight |
| ZRH | Zurich | 3 | **Night train Lisinski 19:39→Zürich 09:20** (11:36 during works 14 Jun–14 Oct 2026); car 9h42 | couchette from €49.90 [claimed: seat61] | EN Lisinski; Swiss/Croatia flights | **Swiss NRT** (daily Apr/May/Oct, 5/wk otherwise) [claimed: AeroRoutes] | Usually reached by flight |
| FRA | Frankfurt | 3 | car 9h23; fly | — | LH/Croatia ZAG–FRA flights | LH HND & KIX?, JAL, ANA; huge network | Fly-feeder only |
| OTP | Bucharest | 3 | car 12h34 | — | **Air China ZAG–OTP leg** (local sales announced) | Air China PEK; plus Wizz/Turkish etc. | Only via the Air China flight |
| IST/SAW, WAW, HEL | (hubs) | virtual | flight only | — | TK/PC from ZAG; LO ZAG–WAW, Ryanair ZAG–WMI; Ryanair ZAD/VIE–HEL | TK NRT/HND/KIX; ANA IST–HND; Asiana IST–ICN deals; LOT WAW–NRT (up to 11/wk Sep 2026); Finnair HEL–NRT/HND/KIX | "Virtual origins" for separate-ticket combos |

---

## 2. Ground access in detail, by tier

### 2.1 FlixBus timetables and prices (verified)

**Source:** FlixBus public search API, queried 2026-10-04 [verified].
**Script:** `flights/scripts/flixbus_ground.py`.
**Sample dates:** Tue 10 Nov 2026 (most results), Fri 13 Nov 2026, Tue 19 Jan 2027.
**January caveat:** the January timetables were only partly on sale, so fewer options showed up.

| From Zagreb to… | Sample departures → arrivals (Tue 10 Nov unless noted) | Cheapest EUR (incl. fee) | Direct? |
|---|---|---|---|
| Ljubljana (city) | 07:15→09:36, 07:30→09:40, …, 20:45→23:20, 22:30→00:55 (11/day; 18 on Fri) | 10.48 (Tue) · 11.48 (Fri) · 9.98 (Jan) | direct |
| Graz (city) | **01:45→04:30**, 06:30→09:15, 09:15→11:55 … 19:15→22:20 (9/day) | 11.98 · 14.98 Fri · 11.48 Jan | direct |
| Trieste Airport | 14:05→18:55 | 13.98 · 17.48 Fri · 13.48 Jan | direct |
| Trieste (city) | 07:30→11:30, 14:05→18:10, 18:00→22:05 | 15.98 | direct |
| **Venice Airport (VCE)** | 07:30→13:45, 14:05→20:20, **18:00→23:55** | 20.98 · 24.48 Fri · 18.48 Jan | direct |
| Treviso Airport | 07:30→14:00, 22:30→07:00 (+1) | 44.98 | transfer |
| **Vienna Airport (VIE)** | **06:30→11:55** (Fri also 17:30→00:15 and 18:30→02:05 via transfer) | 21.48 · 37.98 Fri · 23.97 Jan | direct |
| Vienna (city) | **01:45→07:05**, 06:30→11:30 … 18:30→23:35, **23:30→04:35** (12–14/day) | 21.48 · 25.98 Fri · 19.98 Jan | direct |
| Bratislava (city) | **01:45→08:25**, 06:30→12:50, plus many via Vienna | 24.48 · 27.48 Fri · 23.98 Jan | direct/transfer |
| Bratislava Airport | 01:45→10:55 … (all transfers) | 31.47 | transfer |
| **Budapest (city)** | 11:05→15:00, 14:10→18:05 (Tue); Fri: 07:30, 08:30, 11:05, 14:10, 17:05, 18:50, **23:59→05:15** | 20.48 Tue · 35.98 Fri · 27.97 Jan | direct |
| **Budapest Airport (BUD)** | Tue: transfers only (11:05→18:45 …); **Fri: 23:59→04:50 direct** | 34.97 Tue · **25.98 Fri** · 30.97 Jan | Fri direct |
| **Belgrade** | 09:00→14:30, 14:00→19:30, 16:45→22:15, **22:15→04:10** | 23.98 · 25.98 Fri | direct |
| Sarajevo | 12:30→20:55, 16:45→23:55, 22:00→06:00 | 46.99 | direct |
| Banja Luka | 12:30→15:50, 22:00→00:45 | 30.99 | direct |
| Tuzla | 12:00→17:30, 23:45→05:30 | 50.99 | direct |
| Zadar | 12/day, 3h30 | 11.48 | direct |
| Split Airport | 07:45→15:35 | 20.48 | transfer |
| **Munich (city ZOB)** | 07:15→16:00 … **22:30→06:55** (8/day; 12 Fri) | 30.98 · 36.98 Fri · 26.48 Jan | direct |
| Munich Airport | 08:35→02:25 (+1) etc. (16–18 h) | 44.47 | transfer (useless) |
| Memmingen Airport | 22:30→09:40 | 43.97 | transfer |
| Milan (city) | 07:30→17:25, 20:45→06:35 | 27.98 | direct |
| Bergamo Airport | 18:00→04:35, 20:45→09:30 | 42.97 | transfer |
| Milan Malpensa | 12–17 h | 45.46 | transfer |
| Bologna | 14:05→23:45, 18:00→02:45 | 24.48 | direct |
| Prague (city) | 08:35→18:40 … 23:30→09:10 | 29.98 | direct |
| Rijeka · Maribor | ~2h30 · ~1h45 | 5.98 · 10.48 | direct |

**Key takeaways from the timetables:**
- Friday buses cost noticeably more (e.g. Budapest €20→€36, VIE airport €21→€38). Price ground legs for the actual weekday.
- Direct-to-airport FlixBus services exist for **VCE, VIE, TRS, and BUD (some days)**.
- For MUC, Milan airports, BTS and PRG, go to the city and then use the local airport train/bus.

### 2.2 Trains (status 2026)

- **Zagreb–Vienna:** EC "Croatia" 07:25 → Wien Hbf 14:07, from €29.90 [claimed: seat61, 2026 page].
  - HŽPP says the Dec-2025 timetable has *two* ZAG–Vienna trains and two ZAG–Munich trains [claimed: HŽPP via search snippet].
  - Wien Hbf → VIE airport is about 15–25 min by Railjet or S7 [estimate ~€5].
- **Zagreb–Budapest:** IC "Agram" 16:30 → Budapest Déli 22:24, from about €17, booked on jegy.mav.hu [claimed: seat61].
  - HŽ plans works on Dugo Selo–Koprivnica–Botovo in 2026 [verified: HŽPP 2026 financial plan PDF lists these sections]. There were bus replacements Gyékényes–Koprivnica in Sep 2025 [claimed: MÁV notice].
  - **Verify on jegy.mav.hu for the actual date.** The bus is simpler anyway.
- **Zagreb–Belgrade:** train **still suspended in 2026** [claimed: seat61]. Use FlixBus.
- **Zagreb–Munich/Stuttgart/Zurich night train "Lisinski"** (EuroNight/ÖBB-HŽ), departs Zagreb 19:39 [claimed: seat61, HŽPP snippet]:
  - Arrivals: Munich about 06:01, Stuttgart 08:38, Zürich 09:20. During works (14 Jun–14 Oct 2026) Zürich arrival is 11:36.
  - Fares: couchette from €49.90 (6-berth), single sleeper from €129.90; ordinary seats also exist.
  - **The Munich arrival makes MUC midday departures feasible with no hotel.**
- **Zagreb–Munich day train:** EC 08:40 → (change at Villach) → Munich Hbf 17:41, from €37.99 [claimed: seat61].
- **Zagreb–Ljubljana:** 08:40, 10:34, 12:50, 19:39, 20:38; 2h07–2h31 [claimed: seat61].
- **Split–Vienna summer night train:** ran until 26 Sep 2026 [claimed: croatiaweek]. Not relevant for winter.

### 2.3 Shuttles, rideshare and car

- **GoOpti** (Ljubljana-based shared door-to-door van) covers ZAG, LJU, VCE, TSF, TRS, GRZ and VIE. Shared rides start "from €9–10" when booked early [claimed: goopti.com]. Mainly useful for LJU or VCE with early or late flights.
- **BlaBlaCar:** Zagreb–Vienna and Zagreb–Budapest are common at about €15–25 [estimate, unverified].
- **Car economics.** Only worth it for 2 or more people:
  - Fuel is about €0.10/km [estimate].
  - **Vignettes** [claimed: 2026 price lists]: Austria 1-day €9.60, 10-day €12.80. Slovenia 7-day €16. Hungary 10-day HUF 6,910 (≈€18.70 at ECB 369.18 HUF/EUR on 2026-10-02).
  - Croatian motorway tolls are about €2–8 each way [estimate].
  - **Parking:**
    - ZAG: €24 for the first day + €13/day after (≈ €193 for 14 days) [verified: zagreb-airport.hr, valid from 1.10.2026].
    - VIE: Parking C €104.90/week, garages €185.90/week, off-site (Panda) €119 for 14 days [claimed: autorevue.at].
    - BUD: official Holiday Parking about HUF 11,900/week (~€32); off-site BUDCAR from €17.57/week [claimed: free2move/blog].
  - **Example:** VIE by car for 14 days ≈ €76 fuel + ~€40 vignettes/tolls + €119–210 parking = **€235–325 per car**, versus 2 × (2 × ~€28) = **~€112 by bus for two people**.
  - **Example:** BUD by car ≈ €75 fuel + ~€25 tolls/vignette + ~€65 parking = **~€165 per car**. That beats the bus for 2 or more people when the bus is the Friday fare.

### 2.4 Early-morning departures: how to be there in time

| Airport | Earliest same-day public-transport arrival (from timetables above) | If flight departs before… | Then |
|---|---|---|---|
| ZAG | Pleso shuttle from early morning; taxi 24/7 | — | No problem |
| LJU | Bus to Ljubljana 09:36 + airport bus → about 10:30 | ~12:30 | Take the 22:30→00:55 bus and stay at a hotel (LJU budget ~€50–70 [estimate]), or book a GoOpti pickup |
| GRZ | 01:45 bus → Graz 04:30 → airport about 05:15 | ~07:00 | Fine for almost any flight |
| TRS | Airport bus arrives 18:55; city 11:30 → airport about 12:15 | ~14:00 | Hotel or GoOpti |
| VCE | 18:00 bus → **airport 23:55** (sleep airside/landside) or 07:30→13:45 | ~15:30 | Late-evening bus + airport night, or hotel |
| VIE | 01:45 bus → Vienna 07:05 → airport about 07:45; or 23:30→04:35 | ~09:45 | Night bus; no hotel needed |
| BUD | Fri 23:59 bus → **airport 04:50**; other days city 15:00/18:05 | ~07:00 (Fri) / evening (other days) | Otherwise one hotel night (~€40–60 [estimate]) |
| BEG | 22:15 bus → 04:10 → airport about 05:00 | ~07:00 | Night bus |
| MUC | 22:30 bus → ZOB 06:55 → airport about 07:45; night train → Hbf ~06:01 → airport about 06:50 | ~09:30 | Night bus or train |
| PRG / BTS | 23:30 → PRG 09:10; 01:45 → BTS 08:25 | ~11:00 | Night bus |

---

## 3. Long-haul relevance: who gets you to Japan from each airport

**Japan nonstops reachable within 1 transfer of the region** (status for winter 2026/27 where known):

| Hub | Carrier → Japan | Status / source |
|---|---|---|
| VIE | ANA → HND | Daily in summer 2026; 787-8 3×/week from 3 Dec 2026 (gap 26 Dec–11 Jan) [verified: [AeroRoutes 2026-09-14](https://www.aeroroutes.com/eng/260914-nhnw26hnd)] |
| VIE | Austrian → NRT | Summer 2026: 7/wk Jun–Aug, 6/wk to 11 Oct [verified: [AeroRoutes NS26](https://www.aeroroutes.com/eng/260330-osns26inc)]; winter 26/27 not in the NW26 filing → **check** |
| MUC | Lufthansa → HND (daily), → KIX (3 of 7 weekly) | Eff. 25 Oct 2026 [verified: [AeroRoutes LH NW26](https://www.aeroroutes.com/eng/260520-lhnw26inc)] |
| MUC | ANA → HND | 5 of 7 weekly, 2 Dec 2026–7 Feb 2027 [verified: AeroRoutes 2026-09-14] |
| FRA | LH, ANA, JAL → HND (LH also KIX?) | [claimed] |
| ZRH | Swiss → NRT | Daily in Apr/May/Oct 2026, otherwise 5/wk [claimed: AeroRoutes snippet] |
| FCO | ITA → HND daily; ITA joins the LH/ANA JV Oct 2026 | [claimed: theflightclub.it 2026-06] |
| MXP | ANA → HND (3/wk, launched 3 Dec 2024) | [claimed: 2024 press; re-check 2026] |
| IST | Turkish → NRT/HND/KIX; ANA → HND (from Feb 2025) | [claimed] |
| WAW | LOT → NRT, up to 11/wk in Sep 2026 | [claimed: twocontinents/AeroRoutes 2Q27 note] |
| HEL / AMS / CDG / CPH / ARN / MAD / LHR | Finnair / KLM / AF / SAS / ANA / Iberia / BA, JAL, ANA | [claimed, standard] |
| DOH / DXB / AUH | Qatar (HND back from 15 Jul 2026) / Emirates / Etihad | Conflict caveat (§0) |
| PEK / PVG / CAN / XIY / SZX / CTU / CKG / NGB | Air China / China Eastern / China Southern / Hainan / Sichuan, many daily flights to NRT/HND/KIX/NGO/FUK… | [claimed] Usually the cheapest economy fares with a 23 kg bag |
| ICN | Korean / Asiana / LCCs to all Japan | Seasonal T'way ZAG–ICN; KE/OZ from BUD, VIE, PRG |
| TPE | EVA, China Airlines, Starlux → Japan | From VIE (BR, CI), PRG (CI) |

**What each origin offers, in practice:**
- **ZAG:**
  - One-stop routings via IST (TK), DOH (QR), FRA/MUC/VIE/ZRH (LH group, incl. LH/NH nonstops), AMS (KL), CDG (AF), WAW (LO), MAD (IB), and, new since September, **PEK (CA via OTP)**. CPH and ARN on the ZAG list open SAS CPH–HND and ANA ARN–HND.
  - No Chinese carriers until Sep 2026. No ex-ZAG Japan deals found in deal feeds 2024–2026 (§5). Usually priced as "fare from the hub + Croatian add-on".
- **VIE:** the densest Asia network within 5 h of Zagreb (ANA, OS, CA, MU, HU, KE, BR, CI, EK, QR, EY, TK). Recurring cheap China Eastern / Air China promos (§5).
- **BUD:** Chinese carriers (CA, MU/FM, CZ, HU) + KE/OZ + EK/QR/TK. Recurring BUD–Tokyo promos (§5).
- **BEG:** Air Serbia/China Southern to CAN and PVG, Hainan to PEK, QR, FZ, TK. Recurring cheap China Southern fares (§5).
- **LJU / GRZ / TRS:** feeders only (LH group, TK, LO, KL). Fares are typically "VIE/MUC/FRA/IST fare + small add-on". Worth including in multi-airport searches because LH-group pricing sometimes undercuts ZAG.
- **VCE:** EK/QR/TK + China Eastern PVG. A good Gulf alternative if ZAG–DOH is expensive.
- **MUC:** nonstop LH/NH to HND/KIX. Rarely the cheapest, but the best "nonstop" option.

---

## 4. Positioning flights (low-cost feeders to long-haul hubs)

**Ryanair networks from the region, verified today** via the public routes endpoint (`https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/<IATA>`). Only hub/positioning-relevant destinations are shown:

| From | Ryanair to hubs/positioning points |
|---|---|
| **ZAG** | BGY, BSL, BVA, CRL, DUB, EIN, **FCO**, FMM, MLA, NAP, NRN, **STN**, **WMI** |
| ZAD (mostly summer) | **ARN, HEL, CPH**, BCN, BER, BGY, BLQ, BTS, BUD, BVA, CGN, CRL, DUB, EIN, FCO, FMM, HHN, KRK, KTW, MXP, NRN, NUE, OTP, PRG, PSA, STN, VIE, WMI |
| VIE | **ARN, HEL, CPH, WAW**, ATH, BCN, BGY, BLQ, BVA, CGN, CRL, DUB, EIN, FCO, KRK, LIS, MAD, MLA, MXP, NAP, OTP, SOF, STN, TSF, VCE |
| BUD | ARN, CPH, ATH, BCN, BER, BGY, BLQ, BVA, CIA, CRL, DUB, KRK, KTW, LIS, MAD, MLA, MXP, NAP, NUE, PRG, PSA, SOF, STN, TSF, VCE, WMI |
| TRS | ARN, BCN, BER, BVA, CRL, DUB, KRK, MLA, NAP, PRG, STN |
| TSF | BER, BUD, BVA, CRL, EIN, KRK, KTW, LIS, LTN, MLA, OTP, PRG, SOF, VIE, WMI |
| VCE | ATH, BCN, BER, BUD, CPH, DUB, HEL, KRK, LIS, LTN, MAD, NAP, STN, VIE, WAW |
| BTS | ATH, BCN, CIA, CRL, DUB, EIN, MLA, MXP, NAP, PSA, STN, WMI |
| SJJ | ARN, BGY, BVA, CRL, FMM, NRN, STN |
| BNX | ARN, FMM, VIE |
| PUY · RJK · OSI · KLU | CRL, FMM, KTW, NRN, STN, VIE · ARN, CRL, HHN, STN · STN · STN |

**Useful feeder → Japan pairings:**
- ZAG–FCO (Ryanair) → ITA FCO–HND.
- ZAG–BGY (Ryanair) → Air China / ANA ex-MXP. BGY→MXP is about 1h15 by bus [estimate].
- ZAG–WMI (Ryanair) → LOT WAW–NRT. Modlin→Chopin is about 1h15.
- ZAG–STN → cheap Chinese/Gulf fares ex-LHR/LGW (e.g. Shenzhen Airlines London £417 to SE Asia, Oct 2026 [claimed: travel-dealz]).
- ZAG/VIE–CRL/BVA/EIN → Hainan/Air China/KLM ex-BRU/CDG/AMS.
- VIE/BUD–ARN → ANA/Air China ex-ARN (fly4free: Gdańsk–ARN Ryanair + Air China ARN–Tokyo = 2,002 PLN ≈ €457 return, Nov–Dec 2026).
- VIE/ZAD/VCE–HEL → Finnair.
- ZAG–IST/SAW (Turkish/Pegasus) → TK, ANA or Asiana ex-IST.

**Wizz Air** could not be queried; its API needs a build token. It has a large BUD base and Balkan bases (TZL, SJJ?, BEG?, SKP). Its BUD–AUH route after Wizz Air Abu Dhabi closed in 2025 is **unverified**.

**Tools to find these combinations:**
- **Azair.eu:** low-cost carrier combinations from "airports within X km". Set the radius to about 400 km around Zagreb to catch VIE, BUD, VCE, TSF and BEG.
- **Kiwi.com:** nearby-airport radius plus virtual interlining. It books self-transfers.
- **Google Flights:** enter up to 7 origin airports at once (e.g. ZAG, LJU, GRZ, VIE, BUD, VCE, BEG) and use Explore/date grid.
- **Skyscanner:** "add nearby airports" and "whole month".
- **Airline sites directly for Chinese carriers** (airchina.com flexible search, ceair.com, csair.com, Trip.com), because their promo fares are often missing from Google Flights and ITA (travel-dealz 2026-07-17).
- Always add the ground cost (§7) and, for separate tickets, a buffer night or at least 4–6 h plus a checked-bag re-check.

---

## 5. Regional price phenomena: evidence (2024–2026)

Conversions use ECB rates for 2026-10-02 (HUF 369.18, PLN 4.3775). All fares below are return, economy.

| Posted | Origin → Japan/Asia | Fare | Carrier / routing | Travel window | Source |
|---|---|---|---|---|---|
| 2026-02-14 | **Vienna → Osaka** | 1,968 PLN ≈ **€450**, incl. 23 kg bag | China Eastern via Xi'an + Shanghai | May–Jun 2026 | [verified: read post] [fly4free.pl](https://www.fly4free.pl/mega-tanie-loty-do-japonii-1968pln/) |
| 2026-07-17 | **Milan → Tokyo / Osaka** | **€551 / €558** | Air China via PEK. Only bookable on airchina.com (not Google Flights or ITA) | Dec 2026 | [verified: read post] [travel-dealz](https://travel-dealz.com/ticker/121404/) |
| 2026-09-17 | Vienna → Hong Kong (benchmark) | €440 incl. 23 kg | China Eastern via XIY (VIE–XIY A330 about 10 h) | Oct–Dec 2026 | [verified: read post] [travel-dealz](https://travel-dealz.com/deal/china-eastern-vienna-hong-kong/) |
| 2026-08-07 / 07-20 | Vienna → Bangkok (benchmark) | €455 return / €247 one-way | Air China via PEK | Aug–Dec 2026 | [claimed: travel-dealz feed titles] |
| 2026-09-26 | Vienna & Warsaw → Asia (Tokyo from Warsaw) | from 891 PLN (the Tokyo fare is higher) | Etihad via AUH | Sep–Dec 2026 | [verified: read post] [fly4free.pl](https://www.fly4free.pl/mega-hit-azja-tanio-od-915-pln/) |
| 2025-12-22 | **Budapest → Tokyo** | 194,700 HUF ≈ **€527** | (carrier not shown) | 16 Feb–3 Mar 2026 | [verified: read post] [utazomajom.hu](https://utazomajom.hu/ajanlatok/retur-repulojegy-tokioba-4/) |
| 2025-09-15 | Budapest → Tokyo | 210,900 HUF ≈ €571, with bag | — | 30 Nov–10 Dec 2025 | [verified] [utazomajom.hu](https://utazomajom.hu/ajanlatok/retur-repulojegy-tokioba-3/) |
| 2024-10-26 | Budapest → Tokyo | 159,950 HUF ≈ €433 today (≈ €400 at the 2024 rate), with bag | — | 21 Nov–3 Dec 2024 | [verified] [utazomajom.hu](https://utazomajom.hu/ajanlatok/tokio-repulojegy-2/) |
| 2026-07-09 | Budapest → Tokyo (cherry-blossom season) | 250,600 HUF ≈ €679 | — | 11–21 Mar 2027 | [verified] [utazomajom.hu](https://utazomajom.hu/ajanlatok/retur-repulojegy-japanba-tavasszal/) |
| ~2024 | **Belgrade → Tokyo** | **€439** | China Southern via CAN | Oct 2024–Mar 2025 | [claimed: Secret Flying via search snippet; page blocked by Cloudflare] |
| ? (Christmas deal) | Sarajevo → Tokyo | €367 | ? | Christmas | [claimed: Secret Flying snippet, undated] |
| 2026-05-27 | Istanbul → Tokyo / Osaka | €618–624 incl. 23 kg | Asiana via ICN (long layovers) | to Oct 2026 | [verified: read post] [travel-dealz](https://travel-dealz.com/ticker/118492/) |
| 2026-09-02 | Brussels → Tokyo / Osaka | €635 incl. bag | Hainan | — | [claimed: feed title] |
| 2026-09-27 | Dublin → Tokyo | from 2,010 PLN ≈ €459 incl. 23 kg | China Eastern via PVG | Nov 2026–Mar 2027 | [verified: read post] [fly4free.pl](https://www.fly4free.pl/dalekie-podroze-azja-australia-od-2010pln/) |
| 2026-08-12 | Stockholm → Tokyo (+ Ryanair feeder from Gdańsk) | 2,002 PLN ≈ €457 total | Air China via PEK | Nov–Dec 2026 | [verified: read post] [fly4free.pl](https://www.fly4free.pl/japonia-w-supercenie-od-2002-pln/) |
| Nov 2025–Oct 2026 | Poland → Japan (benchmark) | 1,968–2,934 PLN ≈ €450–670 | Etihad, Qatar, LOT, Chinese carriers | various | [verified: fly4free.pl Japan tag feed, 60 posts] |
| 2026-07-09 | Prague → Hanoi (LCC chain idea) | about €500 | VietJet, from 10 Oct 2026, 2/wk, technical stop in ALA | — | [verified: read post] [fly4free.pl](https://www.fly4free.pl/tuz-przy-naszej-granicy-rosnie-brama-do-azji-takiej-trasy-nie-ma-nikt-w-europie/) |
| 2024–2026 | **Zagreb / Ljubljana → Japan** | **no deal posts found** | — | — | travel-dealz.com search for "Zagreb" (2 items) and "Ljubljana" (4 items): none to Asia. fly4free: none. |

**Interpretation** (my synthesis; the evidence is suggestive, not proof):
- **The regional floor for Japan return economy with a bag is about €440–560.** It is almost always on **Chinese carriers** (China Eastern, Air China, China Southern, Hainan) from **VIE, BUD, BEG, MXP** (and Western hubs). Gulf-carrier sales (Etihad, Qatar) run about €550–700.
- **Vienna and Budapest show up repeatedly** as origins of such deals. **Belgrade** shows up via China Southern / Air Serbia. **Zagreb never did**, mainly because it had no Chinese carrier before Sep 2026. Expect ZAG to start matching Vienna/Budapest fares if Air China discounts the new route. **Test this first.**
- **Cherry-blossom (late Mar–early Apr) and Golden Week fares are about 25–40% higher** (e.g. BUD 250k HUF in March vs 160–210k in Nov/Dec).
- **Nov–early Dec and mid-Jan to Feb are the cheap windows** in all the evidence above.

---

## 6. Deal sources and communities: status checked 2026-10-04

| Source | Country / lang | Covers our region? | Status today | Machine-readable feed |
|---|---|---|---|---|
| **fly4free.pl** | PL | Often VIE, PRG, BUD departures; frequent Japan posts | Active (posts today) [verified] | `https://www.fly4free.pl/feed/`, **Japan tag:** `https://www.fly4free.pl/tag/japonia/feed/` (`?paged=2` for more) [verified 200, latest 2026-10-02] |
| fly4free.com | EN | Europe-wide | Active [verified] | `https://www.fly4free.com/feed/` ok; search/tag pages return 403 to scripts |
| **travel-dealz.com** / travel-dealz.de | EN / DE | **Often VIE, MXP, BUD, PRG; Chinese-carrier promos** | Active [verified] | `https://travel-dealz.com/feed/`. **Search feeds work:** `https://travel-dealz.com/?s=Tokyo&feed=rss2`, `...?s=Vienna&feed=rss2` [verified] |
| urlaubspiraten.at (HolidayPirates AT) | DE | VIE / Austria departures (mostly packages) | Active [verified] | `https://www.urlaubspiraten.at/feed` [verified 200] |
| piratinviaggio.it | IT | VCE/MXP/BGY departures | Active [verified] | `https://www.piratinviaggio.it/feed` [verified 200] |
| wakacyjnipiraci.pl, urlaubspiraten.de | PL, DE | Partial | Active [verified] | `/feed` [verified 200] |
| **utazomajom.hu** | HU | **BUD-origin Japan deals** (8+ posts 2024–26) | Active (latest 2026-10-03) [verified] | `https://www.utazomajom.hu/feed/`. **Search feed:** `https://www.utazomajom.hu/?s=Tokió&feed=rss2` [verified] |
| Secret Flying | EN | Has origin pages for Zagreb, Ljubljana, Belgrade, Sarajevo, Budapest, Vienna | Live, but **Cloudflare 403** to curl and WebFetch | Use manually or by email alert; not scriptable here |
| Pelikan.cz "akční letenky" | CZ | PRG/VIE OTA promos | Updated 2026-10-01 [verified] | No feed |
| akcniletenky.com | CZ | PRG/VIE | Alive (dates to Sep 2026) [verified] | No feed found |
| Letuška.cz | CZ | OTA | Alive [verified] | No feed |
| poceniletalskekarte.si | SI | SEO blog (Venice/Vienna/Zagreb guides) | Last post Apr 2026, low value [verified] | `/feed/` |
| jeftinoputovanje.com | HR | Package tours, not flight deals | Alive [verified] | No feed |
| Croatian / Serbian Facebook groups ("jeftini letovi"-type) | HR / RS | Probably the main HR/RS deal channel | **Not verifiable** (needs login; my search budget ran out) | — |

**Recommendation for the agent:** poll these three, filtered for `Tokio|Tokyo|Osaka|Japan|Japon|Japán`:
- `fly4free.pl/tag/japonia/feed/`
- `travel-dealz.com/?s=Tokyo&feed=rss2`
- `utazomajom.hu/?s=Tokió&feed=rss2`

Treat any VIE, BUD, BEG, MXP, ZAG or LJU origin as directly actionable.

---

## 7. Ground-cost assumptions to add to fares (per person, EUR)

Add the **return** figure to every fare from that origin. These are public transport, mid-week booking ~5 weeks out. Add about 50% on Fridays/Sundays and for late bookings.

| Origin | One-way | **Return (add)** | + hotel night? | Ground time one-way |
|---|---|---|---|---|
| ZAG | 8 | **16** | no | 0.5 h |
| LJU | 15 | **30** (GoOpti: ~50) | if departure before ~12:30 → +€60 | 3–3.5 h |
| GRZ | 15 | **30** | no (01:45 bus) | 3–3.5 h |
| TRS | 16 | **32** | if departure before ~14:00 → +€60 | 4–5 h |
| VCE | 22 | **45** | departure before ~15:30 → overnight on the 18:00 bus (free) or +€60 hotel | 6 h |
| TSF | 32 | **65** | likely | 6.5–8.5 h |
| VIE | 28 | **56** (Fri: ~75) | no (01:45 or 23:30 bus) | 5.5–6 h |
| BTS | 28 | **56** | usually no | 7–8 h |
| BUD | 30 | **60** (Fri: ~80) | morning departure (non-Fri) → +€50 | 4.5–6 h |
| BEG | 28 | **56** | no (22:15 bus) | 6–6.5 h + border |
| SJJ | 55 | **110** | maybe | 8 h |
| MUC | 45 (bus + S-Bahn) / ~65 (couchette + S-Bahn) | **90–130** | no (night bus or train) | 9–10 h |
| MXP/BGY | positioning flight ZAG–BGY (€20–60 + bag) + ~€10 bus | **60–140** | often | flight |
| FCO, WAW/WMI, IST/SAW, HEL, ARN, STN | positioning flight | **€40–150** + buffer night | self-transfer buffer recommended | flight |
| PRG | 35 | **70** + likely hotel | yes | 10 h |

**Rule of thumb for comparing:** a non-ZAG origin must beat the best ZAG fare by more than this threshold:

`(return ground cost − €16) + hotel + about €6 per extra hour of ground travel (both directions)`

The €6 per hour is my own "time and risk" allowance [estimate]. Resulting thresholds:
- LJU / GRZ: about €45–50
- VIE: about €100
- BEG: about €105, plus border hassle
- BUD: about €100–170
- MUC: about €180–220

---

## 8. Recommended origin set (priority order)

1. **ZAG.** Home airport. Search everything, especially **Air China via OTP/PEK** (check airchina.com directly) plus TK, QR, LH group, AF/KL, LO, IB, SAS, flydubai.
2. **VIE.** Best Japan network in reach (ANA/OS nonstops, CA, MU, HU, KE, BR, CI, Gulf carriers, TK). Strongest deal evidence. Ground about €56 return; overnight bus means no hotel.
3. **BUD.** Chinese-carrier hub of the region (8 Far-East routes) plus KE/OZ. Deal evidence. Ground about €60–80.
4. **BEG.** China Southern / Air Serbia to CAN and PVG, Hainan to PEK. Deal evidence. Ground about €56 with an overnight bus.
5. **LJU and GRZ.** Cheap to reach (about €30). Same LH-group/TK products as ZAG at sometimes lower fares. Include them in every multi-airport query.
6. **MUC.** Nonstop LH/NH to HND, LH to KIX. Reachable overnight. Include if "nonstop" matters, or when LH-group sales hit.
7. **VCE (+TRS).** Gulf carriers plus China Eastern PVG. About €45 ground.
8. **Virtual origins via positioning flights:** MXP/BGY (Air China, ANA), FCO (ITA), WAW (LOT), IST (TK/Asiana/ANA), HEL (Finnair), ARN (ANA/Air China), BRU (Hainan), STN/LGW/LHR (Chinese carriers). Use only if the total beats options 1–7 by more than about €100. These are separate tickets, so add a buffer night.
9. Skip for long-haul (positioning only): TSF, BTS, SJJ, TZL, BNX, ZAD, SPU, RJK, PUY, OSI, KLU, MBX, PRG.

---

## 9. Open questions and stale-info flags

1. **Confirm the home base** (Zagreb?). Also: number of travellers (car economics flip at 2+), dates and flexibility, and checked bag (needed? It matters for low-cost positioning).
2. **Air China ZAG fares.** Price ZAG–PEK–NRT/HND/KIX for the target dates on airchina.com. Check whether the ZAG–OTP local leg is really sold, since fifth-freedom rights were "pursued".
3. **Gulf-carrier risk appetite.** The conflict is unresolved (late-Sep 2026 risk "elevated"). Also check flydubai ZAG frequency after 1 Oct 2026 (daily was "hoped").
4. **Austrian VIE–NRT in winter 26/27** and **ANA VIE** frequency (daily → 3/wk from 3 Dec 2026). Re-check the airline schedules.
5. **Zagreb–Budapest "Agram" train** 2026 operation during the HŽ works. Check jegy.mav.hu.
6. **Lisinski night train** exact Munich arrival and seat/couchette fare for the date. Check oebb.at or thetrainline.
7. **Wizz Air 2026 network** (Vienna presence, BUD–AUH/JED/Asia-adjacent) could not be queried.
8. **T'way ZAG–ICN** summer-2027 schedule (it was nonstop in summer 2026). It could be a summer bargain combined with ICN→Japan low-cost carriers.
9. **Croatian / Serbian deal communities** (Facebook groups) need a manual check.
10. **Wikipedia-sourced route lists** are `[claimed]`, e.g. Scoot VIE–SIN, Qatar BUD, ANA MXP 2026. Verify the routes that actually end up in a winning itinerary.
11. FlixBus "direct-to-airport" runs vary by weekday (the BUD 23:59 runs Fri, VIE airport 06:30 daily?). **Re-run `flixbus_ground.py` for the real dates.**

---

## 10. Tooling added

**Script:** `flights/scripts/flixbus_ground.py`, standard library only.

```
python3 flights/scripts/flixbus_ground.py --date 2026-11-10                      # Zagreb → 21 default airports/cities
python3 flights/scripts/flixbus_ground.py --date 2026-11-13 --to "Vienna Airport" Budapest
python3 flights/scripts/flixbus_ground.py --from Ljubljana --date 2026-11-10     # other home base
python3 flights/scripts/flixbus_ground.py --drive --home 15.9819,45.8150          # OSRM km/time to airports
python3 flights/scripts/flixbus_ground.py --cities "Debrecen"                     # resolve new FlixBus city ids
```

- Prices include the FlixBus platform fee. Rail legs that FlixBus sells are included.
- OSRM times are free-flow: add 10–20% and any border queues.

**Other endpoints confirmed working today** (handy for the agent):
- Ryanair routes: `https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/<IATA>`
- ECB FX: `https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml`
- Zagreb Airport timetable / destination list: `https://www.zagreb-airport.hr/putnici/informacije-o-letovima/red-letenja/54`
- Graz winter schedule PDF: `https://graz-airport.at/media/2026/08/Vorschau-Winterflugplan_26_27.pdf`

**Blocked to scripts:** secretflying.com, flightconnections.com, flightsfrom.com, lju-airport.si, bahn.de API, Wizz API (needs build token), v6.db.transport.rest (TLS fail).
