# dryrun-tyo-2027-05: cheapest-ticket report (2026-10-04)

> **This is a DRY RUN** by a test agent following the skill unaided, to validate the toolkit. The
> brief was invented, not the user's real request. Prices were real and live on 2026-10-04 but are
> long stale by the time you read this. The friction log is in `skill-feedback.md` next to this file.

Brief: 1 adult, Zagreb → Tokyo or Osaka, out about 12 May 2027 (±3), back about 2 weeks later, 1 checked bag.
Bus to VIE/BUD is OK. Self-transfer only if it saves > €100. No hidden-city.
All prices were fetched live 18:17–18:53 UTC. None were taken to a checkout page.

## Recommendation
**China Eastern out / China Southern back, Budapest ⇄ Osaka KIX (or Tokyo NRT/HND), Wed 12 May → Wed 26 May 2027.**
- **Fare €684** (OPODO via momondo), one ticket, **2×23 kg included**.
- Out: MU BUD 12:30 → PVG → KIX 13 May 12:10. Back: CZ KIX 26 May 16:00 → CAN → BUD 27 May 06:30.
- **Total ≈ €804:** fare €684 + FlixBus ≈ €70 + one Budapest night ≈ €50. There is no direct bus on 11–12 May, so no same-day arrival makes the 12:30 flight. If a morning train arrives by 09:30, the total is ≈ €754.
- **Where to book:** check **ceair.com** first. Matrix prices MU's own fare at €715, within the "book direct if within €20–40" rule. Otherwise OPODO at €684: decline Prime and add-ons. Gotogate (€699) and Booking (€741) are High-risk sellers.
- **Risk: low.** One ticket, airside transit in China (no visa needed). 17–20 h out, 23 h back.
- The same fare showed up at 6 sources (€684–741).

## Top options
| # | Total € pp | Total € party | Fare € | Bags | Route & times | Carriers | Ticket type | Seller | Risk | Checked at checkout? | Link |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ≈ 804 (≈ 754 with a train) | same | 684 | 2×23 | BUD 12 May 12:30 → PVG → KIX 13 May 12:10 · KIX 26 May 16:00 → CAN → BUD 27 May 06:30 | MU/CZ | 1 ticket | OPODO; MU direct ≈ 715 | low | no | https://www.momondo.de/flight-search/BUD-TYO,OSA/2027-05-12/2027-05-26?sort=price_a |
| 2 | ≈ 774 | same | 708 | 1 checked | VIE 11 May 20:30 → DEL → HND 13 May 07:55 · HND 25 May 11:50 → DEL → VIE 26 May 19:00 (38 h) | AI | 1 PNR | Kiwi | low–moderate | no | https://kiwi.com/u/bkk6zjm |
| 3 | ≈ 812 | same | 692 | 2×23 | BUD → PVG → NRT · HND 26 May 20:00 → PVG → BUD | MU | 1 ticket | OPODO | low | no | momondo link above |
| 4 | ≈ 743 + bag fee | same | 675–687 | bag probably not included | VIE 11 May 12:10 → SIN → HND 13 May 01:05 · HND 26 May 02:20 → SIN → VIE 27 May 08:55 | Scoot | 1 ticket | Scoot / Gotogate / Booking | moderate | no | https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDUtMTFqBRIDVklFcgUSA0hORBoaEgoyMDI3LTA1LTI2agUSA0hORHIFEgNWSUVCAQFIAZgBAQ&hl=en&gl=HR&curr=EUR |
| 5 | ≈ 914 | same | 794 / 812 | 1 checked | BUD 12 May 10:00 → DOH → HND | QR | 1 ticket | OPODO / Qatar | low (Gulf caveat) | no | https://www.google.com/travel/flights/search?tfs=GhoSCjIwMjctMDUtMTJqBRIDQlVEcgUSA0hORBoaEgoyMDI3LTA1LTI2agUSA0hORHIFEgNCVURCAQFIAZgBAQ&hl=en&gl=HR&curr=EUR |

## Cheapest at any risk
- **Air India from Vienna** (≈ €774) is €30 cheaper in total but has a 38 h return.
- The €627 split (Scoot + CZ, separate tickets) saves under €100 before the bag fee, so it is rejected.
- Flying to Istanbul or Athens first costs about €1,000 all-in.

## Timing verdict
€684 with bags from BUD is the bottom of the "Normal" band and near BUD's average of about €650. Google's typical range was unavailable. The trip is 7 months away, so **monitor** with a threshold of €600 (`watch.json`) and a Google Flights alert.

## Manual checks for you
1. https://www.ceair.com/ (BUD → TYO/OSA, 12 / 26 May)
2. https://www.skyscanner.net/transport/flights/bud/tyoa/270512/270526/ and https://www.skyscanner.net/transport/flights/vie/tyoa/270511/270525/
3. https://www.trip.com/flights/showfarefirst?dcity=bud&acity=tyo&ddate=2027-05-12&rdate=2027-05-26&triptype=rt&class=y&quantity=1&locale=en-XX&curr=EUR
4. https://www.airindia.com/ (VIE ⇄ HND, 11 → 25 May)
5. https://www.flyscoot.com/ (add a bag each way and note the total)
6. Google Flights in your browser: the "Cheapest" tab and a multi-city BUD→TYO / OSA→BUD search
7. https://www.secretflying.com/ (Budapest, Vienna, Zagreb)
8. hzpp.hr / mavcsoport.hu: a morning train Zagreb → Budapest on 12 May

## Assumptions & not covered
- 23 kg bag each way, 12–16 nights, max 2 stops and 30 h each way.
- The hotel and airport-bus costs are estimates. The FlixBus fares are live.
- Open-jaw was not reliably priced (Matrix `--slice` bug, since fixed: see skill-feedback F17).
- Skyscanner, Trip.com and airline sites block bots, so they are left as manual checks.
- Nagoya (BUD→NGO €599 one-way) was not explored.
