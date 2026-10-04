# 01 — Flight search engines, metasearch & OTAs: the 2026 landscape

*Researched 2026-10-04 for the Zagreb → Japan cheapest-fare hunt. Author: research sub-agent.*

**How to read the tags**
- `[verified: how]` means I checked it myself on 2026-10-04: an HTTP fetch, a live search, or a primary document.
- `[claimed: source]` means a third party reports it and I could not re-check it. Weight it by the source.
- `[knowledge]` means general domain knowledge that I did not re-verify today. Treat it as a hypothesis.

**Research limitations**
- Reddit is not reachable from this sandbox (403, and Anubis/Cloudflare on its mirrors), so Reddit experience reports come only second-hand.
- The session's WebSearch budget (200) ran out partway through. Later facts come from direct fetches of primary pages.
- Trustpilot blocks curl. Its numbers came through WebFetch summaries and are approximate.
- Many top search results for "best flight site 2026" are SEO content farms (examples: truescho.com, flyozo.com, bestflighthoteldeals.com, shopback "is X cheaper" blogs, and auto-generated pages on .edu/.org domains). I treat them as **zero evidentiary weight**.

---

## 1. Key findings (TL;DR)

1. **No engine reliably finds the lowest fare.** Every credible independent test (Frommer's, Which?, Stiftung Warentest, Consumentenbond) gives a different winner. In those tests, the "cheapest" price often comes from an obscure OTA that adds fees at checkout. The robust approach: use Google Flights / ITA Matrix to find the fare and itinerary, use Kiwi/Skiplagged for self-transfer and hidden-city constructions, then use Momondo/Skyscanner to find the cheapest *seller*. Last, compare the **final checkout price** against airline-direct.
2. **For Europe→Japan, the price floor is set by Chinese carriers**, usually reached via a cheap positioning leg on a separate ticket. Examples are Air China via PEK, China Eastern/Juneyao via PVG, China Southern via CAN/PKX, and Sichuan via TFU. My spot-check (ZAG→TYO, one-way, 20 Jan 2027):
   - Kiwi: **€418** self-transfer (JU+MU). With ±3 days, **€373** (Ryanair ZAG→Charleroi, then a ground transfer to Brussels for Air China).
   - Skiplagged: **US$566** single-ticket Croatia Airlines + Juneyao via BRU/PVG.
   - Google Flights' default ("Best") list: **€571** minimum. None of the Chinese-carrier combos appeared in that server-rendered list.

   `[verified: live queries via mcp.kiwi.com, mcp.skiplagged.com and google.com/travel/flights HTML, 2026-10-04]`. This matches the orchestrator's fly4free benchmark: ~€450–480 RT via Air China plus positioning.
3. **Two engines now expose free, no-auth MCP endpoints a future agent can call directly:**
   - **Kiwi.com** (`https://mcp.kiwi.com`, tool `search-flight`): supports ±10-day flex, explicit date ranges and comma-separated multi-origin.
   - **Skiplagged** (`https://mcp.skiplagged.com/mcp`): flight search with hidden-city and virtual-interlining toggles, plus flex calendars and an "anywhere" search.

   **Google Flights results are server-rendered and parseable** (they are in the `aria-label`s). `[verified: 2026-10-04]`. Skyscanner (PerimeterX captcha), Trip.com (challenge page), the Etraveli brands (Akamai 403), Kayak/Momondo (results load by XHR polling) and Skiplagged's website (Cloudflare) are not scriptable with plain curl.
4. **Kiwi.com has changed its model, but it still sells self-transfer:**
   - In 2024 it pivoted to airline partnerships (Ryanair, easyJet, AF-KLM, LH, AA).
   - The Kiwi Guarantee became an **optional, paid add-on**, roughly €5–20.
   - It redirects you to the airline when it can't beat the airline's price.
   - It cut 250 jobs (18%) in Jan 2026, and AI now handles all text-based customer support.
   - Its terms let it **cancel, or ask you to pay the difference, if the fare rises before ticketing**.
5. **ITA Matrix is alive.** `matrix.itasoftware.com` served the Google app shell `[verified: HTTP 200, 2026-10-04]`. Google Flights added a **"Cheapest" tab (Oct 2024)** that includes self-transfer and separate-ticket itineraries. It also added AI "Flight Deals": a beta in Aug 2025 for the US/CA/IN, extended to 200+ countries on 17 Nov 2025.
6. **Red-flag sellers:**
   - **Etraveli brands** (Gotogate 2.5★ with 34% one-star reviews; Mytrip 2.9★ with 50%; Flightnetwork 2.9★ with 32%).
   - **Booking.com flights**, which Etraveli fulfils.
   - **eDreams/Opodo/GO Voyages Prime**: fined €9M by Italy's AGCM on 4 Feb 2026 for dark patterns, and for showing *different prices depending on whether you arrived via a metasearch site or by Prime status*.
   - **Travelgenio** is dead: its domain now redirects to a gambling site.
   - **Jetcost-linked unknown OTAs**: Which? (Oct 2025) says it "wouldn't use some sites it links to".
7. **Brands that are gone or changed:**
   - Dohop no longer offers consumer metasearch (it is B2B only).
   - Trip.ru closed into Gotogate.
   - Seat24.se now goes to Mytrip.
   - Vayama now goes to BudgetAir.
   - StudentUniverse is now "BYOjet for Students".
   - MrJet has ended.
   - Navifare pivoted into Zerolook (B2B).
   - fly.com and surprice.jp fail DNS (SERVFAIL).
   - Hopper paid a US$35M FTC settlement (Jul 2026).
   - Etraveli is still owned by CVC, with KKR taking a minority stake in Jul 2025. Ignore claims that Booking Holdings bought it in 2026: that was the 2021 deal, which the EU blocked in 2023.

---

## 2. Who owns whom (so you know which "comparisons" are really the same backend)

| Group | Brands relevant to flights | Notes |
|---|---|---|
| **Google** | Google Flights, ITA Matrix | Matrix is the QPX fare engine's power-user UI. It shows fares only; you can't book on it. |
| **Booking Holdings** | KAYAK, momondo, Cheapflights, Swoodoo, Priceline, Agoda, Booking.com (flights fulfilled by Etraveli), HotelsCombined | KAYAK/momondo/Cheapflights share a backend. Checking all three is *not* three independent samples `[knowledge]`. In practice momondo surfaces more small OTAs and scored best in tests (§3). |
| **Trip.com Group** | Trip.com/Ctrip, **Skyscanner**, Travix brands (BudgetAir, Vayama → BudgetAir, CheapTickets.nl, Flugladen, Vliegwinkel), part of Qunar | Skyscanner ownership `[knowledge]`. Vayama → budgetair.com redirect `[verified: curl 2026-10-04]`. |
| **Etraveli Group** (CVC majority; KKR minority since Jul 2025) | Gotogate, Mytrip, Flightnetwork, Supersaver, Flygresor.se (metasearch), Seat24 (→Mytrip), Trip.ru (closed → Gotogate), TripStack (virtual interlining tech), Wenrix (bought Jan 2026) | Flight provider behind **Booking.com flights**; that partnership was extended to 2033 in Jun 2025 `[claimed: Wikipedia "Etraveli Group"]`. KKR stake `[claimed: De Brauw/AltexSoft, Jul–Aug 2025]`. trip.ru → `ru.gotogate.com/...closedBrand=trip` `[verified: curl]`. seat24.se → se.mytrip.com `[verified: curl]`. |
| **eDreams ODIGEO** | eDreams, Opodo, GO Voyages, Travellink, Liligo (metasearch) | Subscription ("Prime") model; see §5. |
| **Expedia Group** | Expedia, Orbitz, Travelocity, Hotwire, ebookers, Wotif; MrJet (ended) | mrjet.se → `hotels.com/lp/b/mrjet-ending` `[verified: curl]`. Frommer's says Expedia/Orbitz/Travelocity use Hotwire's air engine `[claimed: Frommer's 2025 test]`. |
| **eSky group** (Katowice, PL) | eSky (incl. **esky.hr**, Croatian site), **Lucky2go** | Lucky2go is run by "lucky2go Sp. z o.o., Katowice" and offers virtual interlining with "Shield Protection" `[verified: WebFetch lucky2go.com]`. |
| **Kiwi.com** (General Atlantic 66.7%) | Kiwi.com; Flightlist.io appears to use Kiwi data | Flightlist pages load airline logos from `images.kiwi.com` and have "include/exclude self-transfer" toggles `[verified: HTML]`. That suggests a Kiwi/Tequila data source (an inference, not confirmed). |
| **Aviasales** | Aviasales (+ Travelpayouts affiliate network) | Founded in Russia; registered in Hong Kong; operations in Phuket `[claimed: Wikipedia]`. |

---

## 3. Evidence: which engines actually surface the lowest prices?

### 3.1 Independent tests (ranked by credibility)

| Test | Date | Scope | Result | Weight |
|---|---|---|---|---|
| **Which? flight comparison sites** ([which.co.uk](https://www.which.co.uk/reviews/travel-agents/article/travel-agents/best-flight-comparison-sites-a60qa3h83bDN)) | **Oct 2025** | 6 metasearch sites (Skyscanner, Google Flights, momondo, Cheapflights, KAYAK, Jetcost) × 30 journeys, plus user testing and click-through price accuracy | **Jetcost** showed the cheapest fare most often, but "many of those low prices were from booking sites we had never heard of". Some of those sites had reviews from customers who paid more than Jetcost advertised. Scores: Skyscanner 81% (Which? Recommended Provider), Google Flights 79% ("most booking options"), Jetcost 49% ("We wouldn't use some sites it links to"). `[claimed: Which?, via WebFetch]` | **High**: independent, recent, checked click-through accuracy. UK routes. |
| **Frommer's "10 Best (and Cheapest) Airfare Search Sites for 2026"** ([frommers.com](https://www.frommers.com/tips/airfare/the-10-best-and-cheapest-airfare-search-sites-for-2026/); page is Cloudflare-blocked for me) | Published ~24 Nov 2025 | 18 sites × 32 itineraries (last-minute and ~3 months out), incl. LA–Hong Kong, NYC–Paris, Chicago–Rome. Weighted score with penalties for the worst prices. | 1 **momondo** ("never served up a bad fare", shows bag fees), 2 Skyscanner, 3 Skiplagged, 4 Google Flights (first time in the top 10), 5 FlightNetwork, 6 Hotwire, 7 Expedia, 8 Booking.com, 9 Priceline, 10 Agoda. `[claimed: iHeart/AIJourn summaries of Frommer's]` | **Medium-high**: a long-running methodology (10th year), but US-origin and price-only. It doesn't check OTA reliability; FlightNetwork's high rank coexists with a 2.9★ Trustpilot. |
| **Frommer's "…for 2025"** ([reidsguides mirror](https://reidsguides.com/rb/the-10-best-and-cheapest-airfare-search-sites-for-2025/)) | Jan 2024–25 | 15 sites × 32 itineraries | 1 momondo/KAYAK, 2 Skyscanner, 3 Skiplagged, … **10 Google Flights**: lowest fare only once, and "$673 more than competitors for Dallas–Dubai". Skiplagged "rounds prices downward", omits bag fees, and some of its OTA referrals cost more at checkout. `[claimed: Frommer's via mirror]` | Medium |
| **Frommer's AI chatbot test** (in the 2026 article) | Nov 2025 | 6 chatbots (ChatGPT, Gemini, Claude, Grok, Perplexity, DeepSeek), NYC–LA | Only **Gemini** hit the actual lowest fare ($226 AA), likely via Google Flights data. The others invented fares (e.g., Frontier quoted at $121–196 when the real fare was $262). `[claimed: Frommer's, via search snippet]` | Medium. **Lesson: never trust LLM-quoted prices. Always fetch live.** |
| **Which? (2018)** ([greenmotion copy](https://greenmotion.com/news/new-research-from-which-reveals-cheapest-flight-comparison-sites)) | 10 Sep 2018 | 5 sites × 10 routes | momondo cheapest on all 10. Cheapflights/KAYAK cheapest on 8. Skyscanner always matched or beaten. Google Flights last. | Low (stale), but the pattern repeats: **momondo is consistently near the top; Google Flights shows fewer small OTAs.** |
| **Stiftung Warentest** ([test.de](https://www.test.de/Preisvergleich-auf-Flugportalen-Fluege-im-Schnitt-ein-Drittel-teurer-als-bei-der-Airline-5482305-0/)) | 13 Jun 2019 | 22 short-haul flights; 6 German OTAs (Bravofly, Opodo, Fluege.de, Flug24, Airline-direct, Billigfluege) vs airline direct, *total* price incl. extras | OTAs were **about one-third more expensive** on average. Opodo was nearly 2× in one case, *even with* its €74.99/yr Prime. 6 portals illegally charged payment-method surcharges. Earlier test.de: momondo, swoodoo and billigflieger.de were the best metasearch sites. `[claimed: test.de]` | Medium. Short-haul + extras is exactly where OTAs lose. |
| **Consumentenbond (NL)** ([consumentenbond.nl](https://www.consumentenbond.nl/nieuws/2024/waarschuwing-consumentenbond-vliegticketwebsites-onnodig-duur)) | 2024 | 11 OTAs: Booking.com, CheapTickets.nl, eDreams, eSky, Expedia, Gotogate, Kiwi, Opodo, Tix.nl, Trip.com, Vliegwinkel | Booking fees **up to €63 pp**. Bags/seats **up to 4×** the airline price. Low-cost carriers often missing. eSky charges **€7 for online check-in**. Booking.com sells a **€97 change package**. Booking.com and Gotogate showed misleading seat maps. Verdict: "book directly with the airline". `[claimed: Consumentenbond via WebFetch]` | **High** for fee behaviour; it doesn't measure base-fare wins on long-haul. |
| SEO "tests" (truescho, flyozo, bestflighthoteldeals, travelwise24 "$12,000 test", shopback "Trip.com is 3–8% cheaper") | 2025–26 | Unverifiable | Various | **Ignore.** No raw data. Several are AI-generated affiliate pages. |

### 3.2 My own spot-check (2026-10-04): ZAG → TYO, one-way, Wed 20 Jan 2027, 1 adult, economy
| Source | Cheapest found | Construction | Notes |
|---|---|---|---|
| Google Flights (server-rendered default list, gl=HR, EUR) | **€571** | LH/Condor/Etihad via FRA+AUH | 13 itineraries in the HTML. No Chinese-carrier options in the default list; the "Cheapest" tab wasn't tested. `[verified: curl + parse aria-labels]` |
| Kiwi.com MCP, exact date | **€418** | JU ZAG–BEG–ARN + MU ARN–PVG–HND (self-transfer, 39.7 h) | €518 for OU ZAG–BRU + CA BRU–PEK–HND. `[verified]` |
| Kiwi.com MCP, ±3 days | **€373** | FR ZAG–CRL, **ground transfer CRL→BRU**, then CA BRU–PEK–HND, overnight | Has an airport change and **0 cabin bags / 0 checked bags**. `[verified]` |
| Kiwi.com MCP, origins ZAG,LJU,VIE,BUD | **€407** | W6 BUD–ATH + ET ATH–ADD–ICN–NRT | Multi-origin works with a comma-separated list. `[verified]` |
| Skiplagged MCP (hidden-city + VI enabled) | **US$566** | OU ZAG–BRU + HO (Juneyao) BRU–PVG–NRT. Not flagged as VI, so it looks like a single ticket. | 274 results. `[verified]` |

**Takeaways:**
- The Google Flights default view **missed ~€50–150 of savings** that the Kiwi and Skiplagged inventory showed. Some of that comes from self-transfer and some from Chinese-carrier single tickets.
- Kiwi's headline prices exclude bags and assume long, risky self-transfers.
- This is **one date and one route**, so it's indicative, not conclusive.

### 3.3 Synthesis
- **For finding the fare / itinerary:**
  - Google Flights is best for speed, calendar and Explore, *and* it gives the airline-direct baseline.
  - ITA Matrix is best for precise control: routing codes, sales city, fare rules.
  - Neither reliably shows the cheapest **seller**.
- **For finding the cheapest seller of a known itinerary:** momondo (tests) and Skyscanner (breadth, OTA star ratings) are the best-evidenced. The cheapest seller is very often a high-risk OTA.
- **For finding cheaper constructions** (self-transfer, LCC positioning, hidden-city): Kiwi, Skiplagged, Azair, plus the Google Flights "Cheapest" tab.
- **On long-haul, OTA "net/consolidator" fares can genuinely undercut the airline**, especially Chinese, Middle-East and Asian carriers on Trip.com `[knowledge; consistent with spot-check and fly4free deals booked via Skyscanner]`. On short-haul and on extras, OTAs lose to direct (Stiftung Warentest, Consumentenbond).

---

## 4. Metasearch & search tools: profiles

### Summary table
| Tool | Status 2026-10-04 | Uniquely good for | Coverage gaps / caveats | Live vs cached | Agent access |
|---|---|---|---|---|---|
| **Google Flights** (google.com/travel/flights) | Up `[verified]` | Fastest discovery. Date grid, price graph, calendar, **Explore** map (`/travel/explore` up `[verified]`), multi-airport origin/destination (up to 7 each `[claimed: widely reported; not verified]`), **Best vs Cheapest tabs** ("Cheapest" since 16 Oct 2024 adds self-transfer, separate tickets and longer layovers, with red warnings `[verified: 9to5google; "Cheapest" string present in page]`), price tracking, "Flight Deals" AI (200+ countries since 17 Nov 2025 `[claimed: BGR]`). Shows the **airline-direct price**. | Shows fewer small OTAs. Booking options depend on which partners pay or are permitted. "Over 300 partners" `[verified: Google help]`. Tested as average or poor on price (Frommer's 2025: 10th; 2026: 4th; Which? 2018: last). | Main results come from the ITA/QPX engine plus partner feeds. Mostly accurate, but OTA prices are partner-reported. Calendar/Explore prices are "lowest found" approximations `[knowledge]`. | **Server-rendered HTML.** Prices are in `aria-label="From N euros…"`, parseable with curl `[verified]`. The natural-language `q=` URL handled one origin; an 8-airport list didn't parse. Use `tfs=` protobuf URLs (e.g., the `fast-flights` library) for multi-airport `[knowledge]`. |
| **ITA Matrix** (matrix.itasoftware.com) | Up `[verified: HTTP 200 app shell]` | Advanced routing/extension codes (force or avoid carriers and connections), **sales-city / currency setting** (point-of-sale arbitrage), a month calendar with length-of-stay ranges, multi-city/open-jaw, full **fare-construction and fare-rule** display. Use it to *understand* why a fare is cheap and then reproduce it elsewhere. `[knowledge]` | You can't book on it. Airline and published fares only: no OTA net fares, no LCCs like Ryanair/Wizz, no self-transfer. | Live computation. | JS app with an internal API. Not trivially scriptable. Tools to get an itinerary to a booking: ITA Matrix Powertools extension (v0.56.1, Jan 2025; makes airline/OTA deep links incl. Gotogate, Seat24, Supersaver, KAYAK, Skyscanner, momondo `[claimed: Edge/Chrome store listing]`) and BookWithMatrix. |
| **Skyscanner** | Up (PerimeterX captcha to curl) `[verified]` | Broadest OTA list incl. tiny OTAs, **star ratings for each seller** (Which? Recommended Provider, Oct 2025), **Everywhere** destination, **Whole month / Cheapest month**, country-level origins, "add nearby airports". Shows self-transfer combos (Kiwi etc.). New: "Explore with AI" (beta, mid-2026), a ChatGPT app (Feb 2026), the "Drops" alerts `[claimed: TTG Asia 6 Jul 2026, Techleap]`. Has a Croatian site, skyscanner.hr `[verified]`. | Mixes sponsored and organic results, omits bag fees (Frommer's). Cheapest links often go to high-risk OTAs. | **Calendar / Whole-month / Everywhere prices are cached** from recent searches (the month view reportedly shows prices found in roughly the last 4 days, with gaps where no one searched) `[claimed: Skyscanner tips / search summary]`. Results pages poll live. Expect click-through differences. | Blocked to curl (captcha). Needs a real browser. |
| **momondo** | Up `[verified]` | **Best-evidenced for lowest fares** (Frommer's #1 2026 and 2025, Which? 2018). Shows bag fees. "Hacker fares" (two one-ways) `[verified: string on results page]`. Comma-separated multi-airport URLs work, e.g. `/flight-search/ZAG,LJU,VIE-TYO/2027-01-20` `[verified]`. | Slower. Same backend as KAYAK but surfaces more OTAs `[claimed: tests]`. | Results poll live from providers. Calendar/price graphs are cached `[knowledge]`. | Results load by XHR polling: no prices in the initial HTML `[verified]`. Needs a browser. |
| **KAYAK** (+ Cheapflights, Swoodoo) | Up `[verified]` | Multi-airport URLs (`/flights/ZAG,LJU,VIE,BUD-TYO/2027-01-20` accepted `[verified]`), flexible ±3 days, Hacker Fares, price forecast, **AI Mode** (conversational, built on ChatGPT; launched late 2025 `[claimed: KAYAK PR]`). kayak.hr exists (bot-blocked) `[verified]`. | Near-duplicate of momondo. Fewer obscure OTAs. | Same as momondo. | Browser required. |
| **Kiwi.com** (OTA, not pure metasearch) | Up `[verified]` | **Virtual interlining / self-transfer** across 500+ carriers incl. Ryanair/Wizz → long-haul. Radius / multi-origin, "Anywhere", **Nomad** multi-city optimiser, date ranges `[knowledge]`. **Public MCP** at `https://mcp.kiwi.com` (no auth; `search-flight`; ±10-day flex or explicit ranges; multi-origin via comma list; returns EUR prices, segments, bags, booking link) `[verified: live calls 2026-10-04]`. | Curated results (15 per MCP call). Headline price excludes bags. Self-transfer risk: airport changes (CRL→BRU), overnight layovers. See §5 for terms. | Prices can change before ticketing (T&C 6.3.2). | **Best agent access of any engine.** |
| **Skiplagged** | Website: Cloudflare 403 `[verified]`. **MCP up** `[verified]` | **Hidden-city** fares. VI combos. Very good 2-month calendar (Frommer's). MCP tools: `sk_flights_search` (toggles `includeHiddenCity`, `includeVirtualInterlining`, `includeStandard`; `departureAirports`, max layover etc.), `sk_flex_departure_calendar`, `sk_flex_return_calendar`, `sk_destinations_anywhere` `[verified: tools/list]`. | Hidden-city breaks airline contracts of carriage: no checked bags, never on a round trip, and you risk a frequent-flyer account ban. AA v. Skiplagged (Aug 2024): no breach of contract found, but copyright infringement was `[claimed: Wikipedia]`. Rounds prices down and omits bag fees (Frommer's). | Live-ish; prices in USD. | `https://mcp.skiplagged.com/mcp` (no auth, streamable HTTP). |
| **Aviasales** | Up `[verified]` | Huge list of small OTAs (CIS, Asia). Cheap-price calendar. Travelpayouts data API (cached prices) `[knowledge]`. | Links to many little-known OTAs; vet each one. Russian-founded (HQ Phuket). | Calendar is cached from users' searches `[knowledge]`. | Unknown (not tested). |
| **Wego** | Up (JS app) `[verified]` | Middle-East and Asia OTA coverage, Gulf carriers `[knowledge]`. | Less European OTA coverage. | Live results. | JS required. |
| **Jetcost** | Up (Cloudflare 403 to curl) | Most often cheapest in Which? Oct 2025… | …because it links to unknown, poorly reviewed sites (Which? 49%). | — | Blocked. |
| **Dohop** | **Consumer search gone.** The homepage is now B2B only (RetailConnect, ConnectSure, BagConnect) `[verified: homepage text]` | Powers airline / airport self-connect products (e.g., Worldwide by easyJet, Scoot) `[claimed: Wikipedia]`. | Drop it from the search list. | — | — |
| **Hopper** | Up `[verified]` | Price prediction, "price freeze". | US-centric. **FTC: US$35M settlement (2 Jul 2026)** over hidden pre-selected fees ("VIP Support", "Tip") and misleading Price Freeze `[claimed: ppc.land/FTC]`. Business is shifting to B2B (HTS: Lloyds, Virgin Australia, Frontier) `[claimed: Wikipedia]`. | Prediction ≠ price. | Low priority. |
| **Airwander** (stopovers) | Uncertain: `www.` has no DNS; apex behind Cloudflare 403 `[verified]` | Free multi-day stopovers in any city. Reportedly now a paid "Premium Club" `[claimed: search snippet, 2026]`. | Can't verify it works. | — | Treat as optional. |
| **Azair** (azair.eu) | Up `[verified]` | Combines **62 low-cost/hybrid carriers** (Ryanair, Wizz, easyJet, Air Serbia, Pegasus, flydubai, AirAsia/AirAsia X, Vueling…), 298 airports in 51 countries `[verified: homepage]`. Many-airport origins, date ranges. Ideal for **positioning legs** from ZAG/LJU/GRZ/VIE/BUD/TSF/VCE/BGY to a long-haul gateway. | No legacy long-haul (except AirAsia X / flydubai combos). | Cached DB of LCC fares; verify on the airline site `[knowledge]`. | Plain HTML site; probably scriptable (untested). |
| **Flightlist.io** | Up `[verified]` | **Date-range search** (e.g., any day in a 2-month window), **region→region** ("Europe → South East Asia"), filters for bags, max layover, include/exclude self-transfer `[verified: homepage]`. | Seems to use Kiwi data (logos from images.kiwi.com), so it's not independent of Kiwi. | Kiwi-based. | Unknown. |
| **FlightConnections** | Up (bot challenge 202) `[verified]` | **Route discovery:** which airlines fly ZAG/VIE/BUD/… → which hubs → Japan, and schedules. Use it to build the origin and gateway list. | Not a price engine. | — | Browser. |
| **Tour.ne.jp (Travelko)** | Up `[verified]` | Japanese metasearch for **Japan-origin** fares, tours and domestic flights. | Japanese only; JP point of sale. | — | — |

### Notes on "bait" prices
- **Cached views:**
  - Skyscanner month/Everywhere, KAYAK/momondo calendars, Aviasales calendars, Azair and Google Explore all show *indicative* prices.
  - Always re-run an exact-date live search before believing a number.
- **Prices that rise at checkout:**
  - FlightNetwork (Trustpilot: "$325 → $504").
  - Jetcost-linked OTAs (Which? 2025).
  - Skiplagged rounding (Frommer's).
- **Prices that depend on how you arrive:** eDreams showed different prices to metasearch visitors, direct visitors and Prime members (AGCM, Feb 2026). Expect "metasearch landing" prices that are lower than the homepage price, *or* higher than advertised.
- **Kiwi T&C 6.3.2 (effective 11 Aug 2026):** "If the price exceeds the Carrier Reservation Price … we reserve the right (a) to cancel the Booking and refund … (b) to cover the price difference … or (c) to request you to pay the price difference." `[verified: WebFetch kiwi.com/en/pages/content/legal]`

---

## 5. OTAs: fees, reputation, risk

Trustpilot figures are from WebFetch summaries taken 2026-10-04. **Caveat:** OTAs invite reviews right after booking, before anything has gone wrong, which inflates the star average. **The % of 1★ reviews is the better risk signal.**

| OTA | Trustpilot (★ / total / % 1★) | Fee & upsell behaviour | 2025–26 changes | Risk |
|---|---|---|---|---|
| **Trip.com** | 4.4 / 206k / **13%** `[claimed: TP]` | Coupons; prices vary by locale and currency. Complaints: confusing checkout, partial refunds that keep cancellation fees, unilateral schedule changes. Pay in the ticket's native currency with a no-FX-fee card; avoid dynamic currency conversion `[knowledge]`. | Strong for **Chinese/Asian carriers** (Air China, MU, CZ, HO, 3U, HU). Locale arbitrage (e.g., HK site) has been reported since 2018 `[claimed: godsavethepoints 2018; AFF forum 2018 — dated]`. | **Low–Medium.** Best of the OTAs for this route. |
| **Kiwi.com** | 4.0 / 203k / **24%** | Service fee built into the price. **Kiwi Guarantee is optional** (~€5–20 when introduced in 2024 `[claimed: cc.cz, 14 Aug 2024]`); covers disruption credit, auto check-in, 24/7 AI chat. Refund handling: **€30 pp per flight** deducted (Saver/Standard); **Flexi keeps 20%** `[verified: T&C]`. Bags priced separately. | 2024 pivot to airline partnerships. Redirects to the airline when it can't beat its price `[claimed: cc.cz]`. **250 layoffs (18%), 29 Jan 2026** `[claimed: Skift]`. All text support goes through AI `[claimed: lupa.cz]`. MCP server launched in 2025. | **Medium.** Fine for discovery and short self-transfer legs. Never book tight self-transfers. |
| **eDreams / Opodo / GO Voyages** | eDreams 4.3 / 425k / **21%** | **Prime subscription:** the Prime price is shown by default. Annual auto-renew is about €55–100 (sources disagree: €54.99/yr, £7.99/mo × 12, a complaint about a £99.99 charge, Opodo €74.99 in 2019 `[claimed: various]`). Free trial converts to paid. Cancelling is hard. "Best price guaranteed — pay 2× the difference" `[verified: edreams.com/prime page text]`. | **AGCM €9M fine, 4 Feb 2026**: dark patterns, inflated savings claims, "price differences depending on whether users accessed the eDreams website directly or via metasearch engines, as well as on their Prime subscription status" `[verified: en.agcm.it PS12853]`. eDreams is appealing. Berlin court injunction over savings claims; Madrid consumer sanction `[claimed: Ryanair press release — interested party]`. | **Medium–High.** Book only if Prime is declined *and* the final price is still lowest. Cancel any trial immediately. |
| **Gotogate** (Etraveli) | 2.5 / 152k / **34%** | Upsells: service packages, "flexible ticket", cancellation protection `[claimed: TP]`. Complaints: refund delays of months to years, unreachable support, price higher than quoted. Which? earlier criticised it for refusing refunds and charging admin fees `[claimed]`. | Owner unchanged (CVC + KKR). | **High.** |
| **Mytrip** (Etraveli) | 2.9 / 79k / **50%** | Hidden add-ons; "deliberately built to make it difficult to see the included free option"; double charges `[claimed: TP]`. | Seat24.se now redirects here. | **High.** |
| **Flightnetwork** (Etraveli) | 2.9 / 29k / **32%** | "$325 quoted, $504 charged". Pushy add-ons. Customers unaware they booked via a third party. | Frommer's 2026 #5 on price. | **High.** |
| **Booking.com flights** (fulfilled by Etraveli) | Booking.com overall 1.4★ (mostly hotels) `[claimed: TP comparison line]` | €97 change package; misleading seat maps (Consumentenbond). Booking.com and Gotogate blame each other `[claimed: TP reviews]`. | Etraveli partnership to 2033. Frommer's 2026 #8. | **High.** |
| **lastminute.com** | 4.0 / 229k / **22%** | Hidden fees; slow refunds. | — | **Medium.** |
| **BudgetAir / Vayama** (Travix, Trip.com Group) | 3.5 / 30k / **34%** | Premium packages with "€0 cancellation fee" still charged fees `[claimed: TP]`. | vayama.com redirects to budgetair.com `[verified]`. | **Medium–High.** |
| **eSky / Lucky2go** (Katowice) | not fetched | €7 online check-in fee (Consumentenbond). Lucky2go sells VI with "Shield Protection". | esky.hr is active in Croatia `[verified: WebFetch]`. | **Medium–High.** |
| **Travelgenio** | Closed; 35k reviews, overwhelmingly 1★ | — | **Domain now redirects to a gambling site** (`tartiniexpress.com`, slot ads) `[verified: curl]`. | **Avoid / defunct.** If a metasearch ever shows it, it's a scam vector. |
| **Hopper** | n/a | Pre-selected fees (FTC). | $35M FTC settlement. | Medium; irrelevant from the EU. |
| **Expedia / Orbitz / Priceline / Hotwire / CheapOair / JustFly / FlightsMojo** | not fetched | US-centric. CheapOair/JustFly bot-blocked. FlightsMojo is a phone-sales "AI flight search" OTA (US). | Frommer's 2026 ranks Hotwire #6, Expedia #7, Priceline #9. | Low relevance for a Zagreb point of sale. |
| **Agoda flights** | not fetched | — | Frommer's 2026 #10. | Unknown. |
| **StudentUniverse** | — | — | **Now "BYOjet for Students"**: studentuniverse.com → home.byojet.com `[verified]`. | Low relevance. |
| **Traveloka** | blocked | SE-Asia OTA; useful for intra-Asia legs. | — | Medium. |

### Airline direct: when it wins and when it loses
**Direct wins:**
- Low-cost carriers (Ryanair, Wizz) and short-haul extras: OTAs charge up to 4× for bags and seats (Consumentenbond) and are ~⅓ dearer overall (Stiftung Warentest).
- Disruption handling: the airline can rebook you itself, and EU261 refunds don't pass through a middleman.
- Airline-only web or NDC promos `[knowledge]`.

**OTAs can win:**
- Net, consolidator or "private" fares, especially on Chinese, Gulf and Asian carriers. Trip.com is strongest here.
- Separate-ticket and self-transfer constructions.
- Point-of-sale or currency differences.
- OTA coupons, or OTAs subsidising fares with ancillary revenue `[knowledge]`.

**Rule of thumb:** if the airline-direct price is within ~€20–40 of the cheapest OTA *final* price, book direct.

### Asian / Japanese OTAs
| Site | Status | Use |
|---|---|---|
| Trip.com / Ctrip | Up | Main Asia-strength OTA. Also try other locales and currencies. |
| Qunar (qunar.com) | Up `[verified]` | Chinese metasearch; mainly China-origin or domestic, Chinese UI. |
| Fliggy (fliggy.com) | Up `[verified]` | Alibaba OTA; needs a Chinese account or payment. Low practicality. |
| skyticket.jp | Up `[verified]`; has an English switch | Japan-origin international, Japanese domestic, LCCs. Useful for the **JP→EU one-way return** or domestic legs. |
| HIS (his-j.com) | Akamai 403 `[verified]` | Japanese agency fares (Japan origin). |
| Surprice (surprice.jp) | **DNS SERVFAIL** `[verified via dns.google]` | Appears defunct. |
| Tour.ne.jp (Travelko) | Up `[verified]` | Japanese metasearch for Japan-origin fares. |
| Zuji (zuji.com.hk) | Up `[verified]` | Hong Kong OTA. |

These matter mainly when splitting the trip (an Europe→Japan one-way plus a Japan→Europe one-way bought in Japan), for Japanese domestic legs, or for intra-Asia positioning.

---

## 6. Best tool for each job

| Job | First choice | Also use | Why |
|---|---|---|---|
| **(a) Flexible dates / whole month** | Google Flights date grid + price graph; ITA Matrix month calendar (LOS ranges) | Skyscanner Whole/Cheapest month (cached); Kiwi MCP (`departureDateTo` range up to wide windows); Skiplagged MCP flex calendars; Flightlist.io date ranges | GF and Matrix are fare-engine accurate. The others are cached or curated, so verify. |
| **(b) Many origin airports at once** | Kiwi MCP (`flyFrom:"ZAG,LJU,VIE,BUD"` `[verified]`) and Google Flights (up to 7 origins `[claimed]`) | KAYAK/momondo comma URLs `[verified]`; Skyscanner "add nearby" / country origin; ITA Matrix comma lists; Azair radius search; Skiplagged `departureAirports` | ZAG catchment: ZAG, LJU, GRZ, VIE, BUD, TSF/VCE, TRS, RJK, PUY, ZAD, SPU, BEG, MUC, BGY. |
| **(c) Self-transfer / virtual interlining** | Kiwi.com (+MCP) | Google Flights **Cheapest** tab; Skiplagged (VI toggle); Skyscanner (shows Kiwi combos); Azair (DIY LCC legs); Lucky2go/eSky; Etraveli/TripStack-powered combos on Gotogate/Mytrip | Kiwi has the deepest LCC↔long-haul combos. DIY on airline sites is usually cheaper and lets you choose a safe buffer. |
| **(d) Open-jaw & multi-city** | ITA Matrix (multi-city, routing control) + Google Flights multi-city | KAYAK/momondo multi-city; Kiwi Nomad; Skyscanner multi-city | Matrix shows whether an open-jaw prices as one fare (cheap) or as two one-ways (expensive). |
| **(e) Cheapest seller for a known itinerary** | **momondo** (best in tests), then **Skyscanner** (most sellers + ratings) | KAYAK; Jack's Flight Club "Flight Fare Compare" extension (repeats a Google Flights search on momondo/KAYAK/Skyscanner `[claimed: jacksflightclub.com]`); ITA Matrix Powertools deep links; Trip.com in 2–3 locales; airline direct; Aviasales/Jetcost as a last sweep with vetting | Always compare the **final checkout price** with bags and card fees. |

---

## 7. New entrants (2024–2026): AI and agent tools

| Entrant | What / when | Assessment |
|---|---|---|
| Google Flights "Cheapest" tab | 16 Oct 2024; self-transfer and separate-ticket itineraries `[verified: 9to5google]` | **Must-use.** It's the only way Google surfaces creative combos. |
| Google "Flight Deals" (Gemini-based) | Beta 14 Aug 2025 (US/CA/IN), then 200+ countries and 60+ languages from 17 Nov 2025 `[claimed: AltexSoft, BGR]` | Natural-language deal discovery ranked by % saving. Good for "where/when is cheap". It pulls the same Google Flights inventory. |
| Google AI Mode travel / Canvas | Nov 2025 `[claimed: BGR]` | Planning UI, not a new price source. |
| KAYAK AI Mode | late 2025 `[claimed: KAYAK PR]` | Same KAYAK inventory. |
| Skyscanner "Explore with AI" + ChatGPT app | Feb 2026 (ChatGPT app), ~Jul 2026 (Explore with AI beta) `[claimed: TTG Asia, Techleap]` | Same Skyscanner inventory. |
| **Kiwi.com MCP** | Summer 2025 `[claimed: Alpic case study]`; live `[verified]` | **High value for the agent.** |
| **Skiplagged MCP** | `@skiplagged/mcp` v0.0.4 live `[verified]` | **High value for the agent.** |
| Navifare → **Zerolook** | Consumer "find the cheapest OTA for this itinerary" checker founded 2025, then **pivoted to a B2B ML price-prediction API**. navifare.com → zerolook.ai `[verified: curl]` | Gone for consumers. Zerolook's own pitch is to *predict* prices for AI agents instead of computing them live. **Expect more AI-agent prices that are model estimates, not bookable quotes.** |
| General LLM chatbots | — | They hallucinate prices (Frommer's 2026). Never trust them without a live fetch. |
| Amadeus Self-Service API | **Gone** (test.api.amadeus.com unreachable `[orchestrator note]`) | — |

---

## 8. Defunct / renamed / redirected (verified 2026-10-04 by curl unless noted)
- travelgenio.com → gambling site (defunct OTA).
- trip.ru → ru.gotogate.com (`closedBrand=trip`).
- seat24.se → se.mytrip.com.
- vayama.com → budgetair.com.
- studentuniverse.com → BYOjet for Students.
- mrjet.se → "mrjet-ending" page on hotels.com.
- navifare.com → zerolook.ai.
- fly.com and surprice.jp: DNS SERVFAIL (dns.google).
- www.airwander.com: no DNS record; airwander.com is behind Cloudflare 403.
- Dohop: the consumer flight search is gone; the site is B2B only.
- myholidays.com → regencytravelandtours.com.

---

## 9. Recommended search order for the cheapest-fare hunt (Zagreb → Japan)

1. **Google Flights** (Explore → date grid → price graph; multi-origin ZAG catchment; check **both** Best and Cheapest tabs). This gives the airline-direct baseline per origin and date. Scriptable via HTML.
2. **Kiwi MCP**: multi-origin (catchment + major EU gateways such as BRU, FCO, MXP, ARN, IST, FRA, AMS, CDG, LHR), wide date ranges. It finds the self-transfer floor. Then rebuild the best combo **DIY** (LCC leg on the airline site + long-haul on the airline or Trip.com) with a safe buffer.
3. **Skiplagged MCP**: a second independent inventory (it found the OU + Juneyao single ticket that GF's default list didn't show). Use hidden-city only for one-way, cabin-bag-only cases, and only knowingly.
4. **ITA Matrix**: for the 2–3 best itineraries. Check fare basis/rules, try alternative sales cities and currencies, test open-jaw (e.g., in NRT, out KIX).
5. **momondo → Skyscanner** (→ KAYAK): find the cheapest *seller* of the chosen itinerary. Note each OTA's rating.
6. **Trip.com** (2–3 locales/currencies) and the **carrier's own site** (Air China, China Eastern, China Southern, Juneyao, Sichuan, Turkish, Etihad, Qatar, Emirates, LOT, Finnair, LH Group, AF-KLM).
7. **Azair**: cheapest positioning legs ZAG-region → gateway, plus a return-leg check.
8. Optional last sweep: **Aviasales / Jetcost / Wego**, for a tiny-OTA price to *negotiate against*. Only book there if the seller passes vetting.
9. **Checkout comparison:** take the top 2–3 sellers to the final payment screen, without paying. Include bags, seat fees, service fee, card/FX fee, Prime and other default-on add-ons. Prefer airline direct within ~€20–40.

## 10. Red flags (booking-time checklist)
- The seller is Gotogate, Mytrip, Flightnetwork, Booking.com flights, BudgetAir or an unknown Jetcost/Aviasales-linked OTA. Book there only if the saving is large *and* you accept the risk of refunds or changes being a nightmare.
- eDreams/Opodo/GO Voyages showing a "Prime price" (subscription auto-enrolment), or a different price than the metasearch showed.
- Pre-ticked "flexible ticket", "support package", "VIP", "Tip", "price freeze" or "platinum" add-ons. Online check-in sold as a service.
- Kiwi self-transfer with an **airport change** (e.g., CRL→BRU, STN→LHR, BGY→MXP), overnight connections, or <3 h between separate tickets on a long-haul connection. Check transit-visa and baggage recheck rules for China and other transit countries.
- Hidden-city with a checked bag or on a round trip.
- Any price quoted by an LLM or AI "deal" tool that hasn't been re-fetched live.
- Payment-method surcharges, or dynamic currency conversion at checkout.

## 11. Open questions
- Is Google Flights' 7-origin limit still current, and does the **Cheapest** tab show the Chinese-carrier and self-transfer combos Kiwi finds? (Needs a `tfs=` URL or browser test.)
- Which OTAs appear on Google Flights' booking-options page for ZAG→TYO, e.g. Trip.com, Kiwi, Gotogate? (Needs a booking-token fetch.)
- Exact 2026 Kiwi Guarantee and eDreams Prime prices for a Croatian point of sale: check at checkout.
- Does Trip.com price the same itinerary differently by locale/currency in 2026? Only 2018 anecdotes exist; needs a live test in a browser, since Trip.com challenges curl.
- Is Airwander operational, and is it worth it for a free stopover (e.g., Istanbul, Doha, Beijing)?
- No Reddit/FlyerTalk first-hand reports could be read directly (blocked). Consider asking the user to paste threads if needed.

---

## Sources (fetched or searched 2026-10-04)
- Which? flight comparison sites (Oct 2025): https://www.which.co.uk/reviews/travel-agents/article/travel-agents/best-flight-comparison-sites-a60qa3h83bDN
- Which? 2018 summary: https://greenmotion.com/news/new-research-from-which-reveals-cheapest-flight-comparison-sites
- Frommer's 2026 (blocked; via summaries): https://www.frommers.com/tips/airfare/the-10-best-and-cheapest-airfare-search-sites-for-2026/ · https://bigi1079.iheart.com/content/2025-11-25-want-cheap-airfare-these-sites-beat-the-rest/ · https://aijourn.com/frommers-best-airfare-booking-sites-for-2026-announced/
- Frommer's 2025 mirror: https://reidsguides.com/rb/the-10-best-and-cheapest-airfare-search-sites-for-2025/
- Stiftung Warentest 2019: https://www.test.de/Preisvergleich-auf-Flugportalen-Fluege-im-Schnitt-ein-Drittel-teurer-als-bei-der-Airline-5482305-0/
- Consumentenbond 2024: https://www.consumentenbond.nl/nieuws/2024/waarschuwing-consumentenbond-vliegticketwebsites-onnodig-duur
- Google Flights Cheapest tab: https://9to5google.com/2024/10/16/google-flights-cheapest/ · Google help: https://support.google.com/travel/answer/2475306
- Google Flight Deals: https://www.altexsoft.com/travel-industry-news/google-launches-ai-powered-flight-deals-to-help-travelers-find-cheaper-trips · https://www.bgr.com/2028290/google-flight-deals-ai-mode-canvas-travel/
- Skyscanner AI: https://www.ttgasia.com/2026/07/06/skyscanner-adds-ai-travel-planning-and-flight-tracking-features/
- Kiwi: https://cc.cz/kiwi-meni-byznys-model-levnejsi-letenky-vas-necha-koupit-u-aerolinky-nabidne-ale-sluzby-navic/ · https://skift.com/2026/01/29/online-travel-agency-kiwi-lays-off-staff-in-latest-round-of-cuts/ · https://en.wikipedia.org/wiki/Kiwi.com · https://www.kiwi.com/en/pages/content/legal · https://www.kiwi.com/en/pages/guarantee · https://alpic.ai/case-studies/kiwi
- Etraveli: https://en.wikipedia.org/wiki/Etraveli_Group · https://www.debrauw.com/matters/kkr-acquires-minority-stake-in-etraveli-group
- eDreams AGCM: https://en.agcm.it/en/media/press-releases/2026/2/PS12853 · https://www.travelextra.ie/?p=113738
- Hopper FTC: https://ppc.land/ftc-fines-hopper-35-million-dollars-over-hidden-booking-fees/ · https://en.wikipedia.org/wiki/Hopper_(company)
- Skiplagged: https://en.wikipedia.org/wiki/Skiplagged · MCP https://mcp.skiplagged.com/mcp
- Aviasales: https://en.wikipedia.org/wiki/Aviasales · Dohop: https://en.wikipedia.org/wiki/Dohop
- Zerolook/Navifare: https://www.zerolook.ai/ · https://dealroom.co/news/144321-ex-google-flights-kayak-execs-raise-1-9m-to-cut-ai-driven-flight-search/
- Jack's Flight Club Fare Compare: https://jacksflightclub.com/fare-compare-extension · ITA Matrix Powertools: https://microsoftedge.microsoft.com/addons/detail/emlhgimmofcjkaepkcdnmdnhfdgpjpen
- Trustpilot (via WebFetch): /review/www.kiwi.com, /review/www.trip.com, /review/www.edreams.com, /review/mytrip.com, /review/www.gotogate.com, /review/www.flightnetwork.com, /review/www.budgetair.com, /review/www.lastminute.com, /review/www.travelgenio.com
- Dated Trip.com anecdotes: https://www.godsavethepoints.com/magic-website-savings-british-airways-flights (2018) · https://www.australianfrequentflyer.com.au/community/goto/post?id=1796287 (2018)

### Spot-check raw outputs
Raw outputs are in the scratchpad and were not committed. To reproduce, use the same calls:
- Kiwi: `POST https://mcp.kiwi.com/` with JSON-RPC `tools/call` → `search-flight` and arguments `{"flyFrom":"ZAG","flyTo":"TYO","departureDate":"20/01/2027","departureDateFlexDays":0,"currency":"EUR"}`, headers `Content-Type: application/json` and `Accept: application/json, text/event-stream`. The reply is SSE: parse `data:` lines; the result text is JSON.
- Skiplagged: `POST https://mcp.skiplagged.com/mcp` → `sk_flights_search` with `{"origin":"ZAG","destination":"TYO","departureDate":"2027-01-20","sort":"price","includeVirtualInterlining":true,"includeHiddenCity":true}`. Returns a markdown table in USD.
- Google Flights: `GET https://www.google.com/travel/flights?q=Flights%20to%20TYO%20from%20ZAG%20on%202027-01-20%20one%20way&curr=EUR&hl=en&gl=HR` with a browser UA. Regex `aria-label="From ([0-9,]+) euros[^"]*"`.
