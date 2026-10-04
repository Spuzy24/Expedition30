# Fare-lowering techniques: what works, what's a myth, what's risky

> Living summary. Evidence and sources: `research/02-fare-tricks.md` (snapshot 2026-10-04, incl.
> live Google Flights tests) + `research/00-orchestrator-notes.md`. Risk scale:
> **Safe → Low → Moderate → Risky → ToS** (violates the airline's conditions of carriage).
> **Never use a Risky/ToS technique without the user's explicit opt-in** (see `profile.md`).

## A. Proven for Zagreb → Japan (do these every hunt)

| # | Technique | Evidence (2026-10-04 tests) | Risk |
|---|---|---|---|
| 1 | **Start from a nearby hub ("ex-" fares) reached by ground** (VIE, BUD, BEG, MUC, VCE, LJU, GRZ) | Same dates (10–24 Feb 2027) on Google Flights: VIE **€688–787**, IST €788, MXP €867, MUC €874, BUD €908 vs **ZAG €1,018**. Kiwi Jan 2027: BUD best (MU OW €443; KE RT €734). Add ground cost from `searches/ground.json`. | Low |
| 2 | **Europe-wide long-haul origin + low-cost positioning flight** (separate tickets) | Fly4free benchmark: Ryanair GDN→ARN + Air China ARN–PEK–HND = ~€457 RT incl. 23 kg. MXP Air China €551; BRU Hainan €635; IST Asiana €618. | Moderate (separate tickets; use a buffer night) |
| 3 | **Chinese & Korean carriers, checked directly and per carrier** | Air China €551 MXP fare was on airchina.com only (not GF/ITA). Kiwi hides Air China ZAG unless filtered `--only-airlines CA`. CA EU sites: up to 6% off when booking **Fri–Sun**. | Safe |
| 4 | **Price return AND 2× one-way AND open-jaw**, every time | ZAG: RT €1,018 vs 2×OW €1,323. VIE: RT €688 < a single OW €704. But China Eastern priced RT ≈ 2×OW (€891 vs €443 OW). Mixed carriers can win (B1: MU out + CZ back €686 was the cheapest). Open-jaw TYO/OSA ≈ RT on Chinese carriers, +28% on a Star Alliance fare (B2). | Safe |
| 5 | **Catch the sale dip: track + book fast** | GF history ZAG–TYO: €776 for **2 days** (20–21 Sep 2026), €866 for 6 days, then back to €1,018. Set up monitoring (playbook §6). | Safe |
| 6 | **Flexible dates: date grid / calendars / ±3 days** | Mon–Wed departures ~13% cheaper than Fri–Sun (Google data). Kiwi `--flex`, Skiplagged `skcal`, Matrix calendar, GF date grid. | Safe |
| 7 | **Rank by TOTAL cost** (bags, ground, hotel night, fees, card FX) | KLM €608 → €723 with a bag. ANA 1×23 kg only (since Nov 2024), JAL 2×23 kg, Chinese carriers 23 kg (MU often 2×23), KE 23 kg. → `quotes.py`. | Safe |
| 8 | **Deal feeds for flash sales / error fares** | `deals.py` (20 feeds). Regional Japan floor seen: €440–560 RT. Book error fares within minutes; no non-refundable extras for ~2 weeks. | Low |
| 9 | **Cheapest seller for a fixed itinerary** | Momondo (#1 in Frommer's 2025 & 2026 tests), Skyscanner, Trip.com (strong for Chinese carriers), airline direct. Book direct if within ~€20–40. | Safe → Moderate (OTA risk) |

## B. Situational (check if the profile allows)
- **Student/youth fares:** Turkish (age 12–34): 10–15% off + 40 kg. Qatar Student Club (18–30): 10–20% off 4 tickets. StudentUniverse is gone (closed Jun 2025).
- **Free holds:** Turkish refunds in full within 24 h if bought on turkishairlines.com and departure ≥ 7 days away. Emirates/Qatar sell paid holds. **No EU-wide 24 h rule** (the US DOT rule doesn't apply).
- **Stopovers for free:** Turkish Stopover (20 h–7 days, 1 free hotel night in economy, return on one booking, apply 72 h ahead); Touristanbul (6–24 h); Finnair (up to 5 days); ANA "Stopover & Add-on Free Fare" (2 free Japan domestic flights; booking window was 24 Nov 2025–31 Jan 2026, so watch for a repeat); China (30 days visa-free until 31 Dec 2026).
- **Sale calendar:** Qatar Black Friday ex-Europe (late Nov; 2025 included Croatia→Osaka, up to 20% off); Air China weekend discount (Fri–Sun, ≤6%); Chinese carrier promos posted year-round on travel-dealz.
- **Pay smart:** pay in the ticket's currency on a zero-FX card (Revolut €1,000/month free, then 1%, +1% at weekends; Wise 0.35–1.5%), decline DCC. EU law bans card surcharges (PSD2), so OTAs dress them up as "discounts". Compare final prices.
- **Book on another EU country's airline site:** legally protected (Reg. 1008/2008 Art. 23: no discrimination by residence). Safe.
- **Lufthansa-group/AF-KL tickets via GDS-based OTAs** carry €18–23 distribution surcharges → their own site is often cheaper.

## C. Myths: don't waste time (tested or well-evidenced)
1. **Changing Google Flights country/currency:** 7 markets (EUR/TRY/HUF/JPY/INR/USD/PLN) were identical within 0.5%. Google converts one fare. (Airline-site non-EU POS still untested: one manual check on TK/QR is OK if a candidate exists. Low–Moderate risk, rarely pays.)
2. **VPN / incognito / cookies:** independent tests found ~nothing; CNIL/DGCCRF found no IP pricing.
3. **"Book on Tuesday" / fixed weeks-ahead rules:** the booking-day effect is ~1–3%. The sale dip matters more.
4. **Fuel (YQ) dumping:** dead.
5. **Hidden-city via Tokyo:** no pattern found (Japan is an end point from Europe).
6. **Kiwi protects every self-transfer:** its Guarantee is now an optional paid add-on. Kiwi may cancel or ask for more money if the fare rises before ticketing (T&C 6.3.2); €30 pp per flight is deducted from refunds.
7. **Miles for economy without existing points:** e.g. 30k Avios + £244 one-way HEL–TYO. Not cheaper than cash.
8. **Google price guarantee / Flight Deals AI:** US-only / not for ZAG departures. **LLM-quoted prices:** hallucinated in tests. Always fetch live.

## D. Risky: only with explicit user consent
| Technique | Danger | Rating |
|---|---|---|
| Self-transfer on separate tickets (Kiwi, GF "Cheapest" tab, DIY via ICN/TPE/PEK + LCC) | No protection on a missed connection; re-check bags; landside entry needed (K-ETA for Korea, UK ETA, etc.) | Moderate |
| Airport change inside an itinerary (ICN→GMP, STN→LHR, CRL→BRU, BGY→MXP, WMI→WAW) | Cross-city transfer + entry formalities. Avoid with ITA Matrix `-change`; `mcp_flights.py` marks it with `~` | Moderate |
| Positioning flight on a separate ticket | You absorb delays → travel the day before or keep ≥ 4–6 h | Moderate |
| Non-EU point of sale with an EU card | Fare rule may require local issuance; card checks at airport | Low–Moderate |
| Hidden-city / throwaway | Breaks coupon sequence: later segments cancelled, bags go to the final destination, miles can be confiscated. EU 261 reform (agreed 2026, applies ~H2 2027) bans cancelling a **return** after a skipped outbound, but not skipping onward segments on a one-way. One-way + cabin bag only. | ToS / Risky |
| Mistake fares | ~10–50% get cancelled; worst case is a refund | Low |

## E. ITA Matrix quick reference (research tool; you can't book on it)
- **Routing** (per leg): `N` nonstop · `X:IST` connect at IST · `IST,DOH,AUH` any of these · `X? X?` ≤ 2 connections · `C:TK` / `TK+` carrier · `O:TK` operated by · `~SU+` exclude carrier · `~SVO` exclude airport · `F* TK F*` at least one TK flight.
- **Extension**: `-change` (no airport change) · `padconnect 30` · `minconnect 90; maxconnect 360` · `maxdur 1800` · `-overnight; -redeye` · `alliance star-alliance` · `-airlines SU MU` · `maxstops 1` · `f bc=w|v` (booking class).
- Starter for ZAG→Japan: routing `X? X?`, extension `-change; padconnect 30; maxdur 1800`, then run per hub: `IST`, `DOH`, `AUH`, `DXB`, `WAW`, `HEL`, `PEK,PKX`, `PVG`, `ICN`.
- Matrix misses LCCs, many airline web-only fares (e.g. Air China promos) and NDC-only fares. Use it as a map of fare construction, then book via the airline (multi-city with the same booking class) or find a seller on momondo/Skyscanner.
