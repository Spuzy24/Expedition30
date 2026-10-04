# 02 — Ways to lower the fare, with evidence and a risk rating (Zagreb → Japan)

**Researched:** 2026-10-04 · **Traveller:** probably based in Zagreb (to be confirmed), EU (Croatian) citizen, pays in EUR · **Goal:** the cheapest real, bookable ticket to Japan.

**How to read this file**
- `[verified: how]` means checked during this session. The check is either a live test or a fetch of the primary or official page, and the method is stated.
- `[claimed: source]` means a third party reports it and it was not checked independently. Treat it as a lead.
- `[background]` means general industry knowledge that was not checked this session. Confirm it before relying on it.
- **Risk scale:** **Safe** → **Low risk** → **Moderate** → **Risky** → **Violates airline ToS**. A technique can carry two labels, e.g. "Violates airline ToS (low practical risk)".
- Prices are for **1 adult, economy, in EUR**, unless the text says otherwise.

---

## 0. TL;DR: ranked by the saving we expect on this trip

| # | Technique | Evidence of real savings | Risk |
|---|---|---|---|
| 1 | **Start the ticket from another airport, mainly Vienna, and get there by ground transport** | Our live Google Flights test: VIE–TYO return **€688–787**, ZAG–TYO **€1,018**, same dates. That is **€230–330 less** before the cost of getting to Vienna. See §0.1 | Low risk |
| 2 | **Track prices and book quickly when a sale dips** | Google Flights price history for our ZAG–TYO test dates: **€776** on 20–21 Sep 2026, then €866 for 6 days, then back to about €1,017. See §0.1 | Safe |
| 3 | **Check Chinese and Korean carriers directly, and carrier sales** (Air China, Hainan, Korean, Asiana, Qatar Black Friday) | Air China MXP–TYO €551, a fare that did **not** appear on Google Flights or ITA Matrix. Hainan BRU €635 with a bag. Asiana IST €618. Korean Air VIE €688. Qatar Black Friday 2025 included **Croatia→Osaka**. See §3.5, §5, §6.6 | Safe or Low risk |
| 4 | **Use one return or open-jaw ticket, not two one-ways** | Live test: ZAG one-ways €621 + €702 = **€1,323**; the return is **€1,018**. From VIE the return (€688) costs **less than a single one-way** (€704). | Safe |
| 5 | **Be flexible on dates and use the calendar and date-grid tools** (ITA Matrix, Google Flights) | Google's own data: flying Monday to Wednesday is about 13% cheaper than weekends. Our test showed a typical range of €940–1,300 for a single date pair. | Safe |
| 6 | **Compare on total cost (bags, seats, OTA fees)** | KLM ex-Spain fare €608 becomes €723 with a bag. ANA has included only 1×23 kg on Europe routes since Nov 2024. Korean, Turkish and the Chinese carriers usually include a bag. | Safe |
| 7 | **Student discount, if eligible** (Turkish 12–34, Qatar Student Club 18–30) | Turkish: 10–15% off plus 40 kg baggage. Qatar: 10% / 15% / 20% / 20% on 4 tickets. | Safe |
| 8 | **Turkish Airlines' free refund within 24 h on its own website**, as a short hold | Official TK rule: full refund within 24 h if departure is at least 7 days away. | Safe |
| 9 | **Pay in EUR or on a card with no FX fee, and decline DCC** | Saves 1.5–3% compared with a typical bank FX fee. | Safe |

Myths, risky moves and open questions are in §10–§12.

---

## 0.1 Our own tests: live Google Flights data pulled 2026-10-04

**Method `[verified: live]`.** We built Google Flights `tfs=` protobuf query URLs with the Python library `fast-flights` 3.1.0, fetched them with `curl` through the session proxy (sending a consent cookie), and parsed the embedded `ds:1` JSON. The parse gives Google's "lowest price" field (`payload[7][0][0]`), the price-insight block (`payload[5]`: typical low and high, plus 60-day price history) and the top itineraries (`payload[2]` and `payload[3]`). All queries used **1 adult, economy, return Wed 10 Feb 2027 → Wed 24 Feb 2027, EUR**, unless stated otherwise. The code is in Appendix A.

**Limitations.** This is a single date pair and a single moment. Google Flights does not index some airline-only web fares (see §3.5). We parse only the first 10–17 itineraries. Requests with a multi-city open-jaw, and any request involving ZAG–KIX, came back from Google as errors through this method, so open-jaw is supported by secondary sources only (§3.1).

### 0.1.1 Same dates, different starting airports (return to Tokyo, TYO = any of NRT and HND)

| Origin | GF "lowest" € | Best listed itinerary € (carrier, routing) | GF "typical" range € |
|---|---|---|---|
| **VIE Vienna** | **688** | 688 Korean Air VIE–ICN / **GMP**–HND (change of airport in Seoul!); 787 KE via ICN only; 890 TK | 860–1,150 |
| IST Istanbul | 788 | 789 Etihad via AUH; 855 Korean Air | 670–950 |
| MXP Milan | 867 | 867 Etihad; 880 Finnair; 887 Qatar | 720–990 |
| MUC Munich | 874 | 875 Qatar; 876 Etihad | 820–1,200 |
| VCE Venice | 770 (itinerary not captured) | 906 Turkish; 950 ITA | 810–1,200 |
| BUD Budapest | 908 | 961 Turkish; 962 Qatar | 910–1,200 |
| BEG Belgrade | 992 | 992 flydubai/Emirates; 1,033 KLM | 910–1,250 |
| LJU Ljubljana | 998 | 1,024 LOT/Etihad; 1,052 Lufthansa; 1,058 Turkish | 1,000–1,500 |
| GRZ Graz | 989 | 1,048 Lufthansa | 1,300–1,750 |
| **ZAG Zagreb** | **1,018** | 1,018 Croatia/KLM via AMS; 1,036 Croatia/LH via MUC; 1,037 Croatia/LOT; 1,109 Turkish | 940–1,300 |

Takeaways:
- On these dates, **Vienna is €230–330 cheaper than Zagreb** for the identical trip. Istanbul, Milan and Munich are also clearly cheaper. These are "ex-" fares (§3.4).
- **Watch for a change of airport mid-journey.** The cheapest VIE fare has a self-transfer between Seoul's ICN and GMP airports on the same ticket. That means passing through Korean immigration, so check K-ETA status, and allowing time to cross the city. In ITA Matrix the `-change` extension code excludes such itineraries (§1).
- Return to Osaka (KIX) from VIE was **€693** on Korean Air, essentially the same as to Tokyo (€688).

### 0.1.2 How the ticket is built (ZAG and VIE)

| Query | € |
|---|---|
| ZAG→TYO one-way | 621 (LH/Condor/Etihad via FRA+AUH) |
| TYO→ZAG one-way | 702 (LOT via WAW) |
| **Sum of two one-ways** | **1,323** |
| ZAG⇄TYO return | **1,018** |
| VIE→TYO one-way | 704 (Qatar) |
| VIE⇄TYO return | **688** (a full return costs less than one one-way) |

### 0.1.3 Point of sale and currency on Google Flights (ZAG⇄TYO, same dates)

| `gl` / currency | Price shown | ≈ EUR (ECB rate of 2026-10-02) |
|---|---|---|
| HR, TR, IN, US, HU / EUR | 1,018 | 1,018 |
| TR / TRY | 56,302 | 1,020.6 |
| HU / HUF | 375,257 | 1,016.5 |
| JP / JPY | 180,919 | 1,022.2 |
| IN / INR | 110,393 | 1,021.0 |
| US / USD | 1,147 | 1,021.8 |
| PL / PLN | 4,465 | 1,020.0 |

**Result:** changing the country or currency on Google Flights **does not change the underlying fare**. Google converts the same EUR fare, and every result fell within 0.5%. Caveat: the `gl` parameter does not fully imitate a foreign IP or a foreign airline-site point of sale. Airline sites such as turkishairlines.com blocked automated testing, so a real airline-site POS test still has to be done by hand (§2).

### 0.1.4 Price history (Google Flights 60-day series for ZAG⇄TYO, 10–24 Feb 2027)
- Aug to mid-Sep 2026: about **€984–999**.
- **20–21 Sep 2026: €776.**
- 22–27 Sep: €866.
- From 29 Sep: €1,017–1,018. Google calls this "typical" (range €940–1,300).

A dip of about €240 lasted **2 days**. The saving came from timing a sale, not from booking a set number of weeks ahead.

### 0.1.5 Hidden city via Tokyo (one-ways ZAG/VIE → MNL, SYD, HNL)
None of the top 10–17 itineraries for these beyond-Tokyo destinations connected in NRT or HND. They route via the Gulf, China or Korea. **We found no evidence of a "Europe → beyond Japan via Tokyo, cheaper than Tokyo" pattern** for these dates (§4.3).

---

## 1. ITA Matrix: advanced use

**What it is.** Google's fare-search engine with full fare construction. It **does not sell tickets**. It is live: matrix.itasoftware.com returned HTTP 200 on 2026-10-04 `[verified: curl]`.

### 1.1 Status, 2025–2026
- The current UI is the "new" Matrix. The old interface was expected to be **discontinued by the end of 2024** `[claimed: travel-dealz.com/?p=38545, Jul 2024]`.
- ITA Matrix PowerTools browser extension **v0.56.1, updated 10 Jan 2025**, about 10k users. Version 0.56.0 **removed "Matrix 3" support** `[verified: Chrome Web Store listing]`. https://chromewebstore.google.com/detail/ita-matrix-powertools/menecfddnlmanmpadcalononkolnplpp
- UpgradedPoints guide updated 10 Jun 2026 describes the "fifth iteration" with Geo Search `[claimed: https://upgradedpoints.com/travel/ita-matrix/]`.
- Matrix has **no official API**. Its front end calls internal Google endpoints. Scraping them is unofficial and may break or violate Google's terms, so don't build the toolkit on it.

### 1.2 Routing codes: the official syntax
Source: Google's help page `[verified: fetched https://support.google.com/faqs/answer/2736497]`. Open **Advanced controls**. The codes apply to **one origin–destination pair at a time**, so a return needs them on both legs.

| Goal | Code |
|---|---|
| Flight marketed by a carrier (direct, one flight number) | `TK` or `C:TK` |
| Any number of flights on a carrier | `TK+` |
| Operated by (metal) | `O:TK` |
| Exclude a carrier | `~SU` (one flight) / `~SU+` (any number) |
| At least one flight on carrier X, others allowed | `F* TK F*` |
| Nonstop | `N`; nonstop on a carrier: `N:LO` |
| One connection at a given airport | `IST` or `X:IST`; any of several: `IST,DOH,AUH` |
| Connect at IST with other connections allowed | `F? IST F?` |
| Exactly two connections / at most two / at least two | `X X` / `X? X?` / `X X+` |
| Exclude a connection airport | `~SVO` |
| Exclude connections in a whole country | `~l:nUS+` (Google's example. A Schengen exclusion is not documented) |
| Specific flight, or a flight-number range | `LO79`, `UA1000-2000+` |
| Quantifiers | `+` one or more, `*` zero or more, `?` zero or one; `,` = OR (no spaces); space = next segment |

### 1.3 Extension codes (after `/`, separated by `;`)

| Goal | Code | Source |
|---|---|---|
| Alliance | `alliance star-alliance` / `alliance oneworld` / `alliance skyteam` | Google help `[verified]` |
| Minimum / maximum connection time (minutes) | `minconnect 90; maxconnect 360` | Google help `[verified]` |
| Add a buffer to the airline's own minimum connection time | `padconnect 30` | Google help `[verified]` |
| Maximum total duration (minutes) | `maxdur 1500` | Google help `[verified]` |
| No overnight connections / no red-eyes / no propeller aircraft | `-overnight;-redeye` / `-prop` | Google help `[verified]` |
| **No change of airport during a connection** (e.g. ICN→GMP, LHR→LGW) | `-change` | travelcodex.com/2012/01/advanced-routing-language-in-ita/ `[claimed, old but standard]` |
| No trains, no helicopters | `-train`, `-helicopter` | travelcodex `[claimed]` |
| Booking class | `f bc=w` or `f bc=w\|v` | travelcodex / princeoftravel.com (May 2024) `[claimed]` |
| Exclude carriers | `-airlines SU MU` | princeoftravel `[claimed]` |
| No codeshares; maximum stops; aircraft type | `-codeshare`, `maxstops 1`, `aircraft t:787` | princeoftravel / upgradedpoints `[claimed]` |

A fare-basis-level filter using the `f` command exists in community guides, but its exact syntax was **not verified** this session. Test it in Matrix with the "?" help link next to the field.

**Starter set for ZAG→Japan:**
- Outbound routing: `X? X?` (at most 2 connections).
- Extension: `-change; padconnect 30; maxdur 1800; -overnight`. Remove `-overnight` to see cheaper itineraries with long layovers.
- To compare hubs: run separately with `IST`, `DOH`, `AUH`, `DXB`, `WAW`, `HEL`, `PEK,PKX`, `PVG`, `ICN`.

### 1.4 Sales city, currency and calendar
- **Sales city and Currency** fields are under advanced options. Matrix then prices the fares that can be sold in that city's country `[claimed: princeoftravel, upgradedpoints]`.
  - What actually limits this is the **fare rule's sales restriction**, e.g. "tickets must be issued in HR". Open the itinerary → *Fare rules* → look for SALES RESTRICTIONS.
  - For tickets that start in the EU, an EU-based buyer cannot legally be priced differently because of their residence (§2.2).
- **Calendar of lowest fares** shows about a month of departure dates with a length-of-stay range (e.g. 10–16 nights) `[claimed: upgradedpoints/princeoftravel; UI not testable headless]`.
- **What Matrix misses:**
  - Low-cost carriers.
  - Many **airline-only web fares**. Travel-Dealz found Air China's €551 MXP–TYO fare was **not on Google Flights or ITA Matrix**, only on airchina.com `[claimed: https://travel-dealz.com/ticker/121404/]`.
  - Some NDC-only fares.
- Use Matrix as a **map of fare construction**, not as the final price.

### 1.5 Turning a Matrix result into a booking
1. Write down the flight numbers, booking classes and fare basis from the "Fare construction" panel. Then rebuild the same itinerary as a **multi-city** search on the operating or marketing airline's site, matching the booking class (e.g. TK "V").
2. Use **ITA Matrix PowerTools** (Chrome, Edge, Firefox, Tampermonkey). It builds deep links to airlines: AA, AC, AF, AS, AZ, BA, CZ, DL, IB, KL, LA, LH, LX, OA, PS, QF, TK. It also links to OTAs (Expedia, Priceline, Seat24, Gotogate, Budjet, Travelstart, Supersaver) and to metasearch (Kayak, Skyscanner, Momondo) `[claimed: openuserjs listing via search snippet]`.
   - Reported reliability: AA links usually work. **LH links often fail on codeshares**, and BA/IB links error or reprice `[claimed: travel-dealz Jul 2024]`.
3. **BookWithMatrix** (bookwithmatrix.com, live 2026-10-04 `[verified: HTTP 200]`): paste the itinerary JSON from Matrix's "Copy itinerary as JSON". It outputs links to **Justfly, FlightNetwork, Priceline, AA, Delta, Alaska**. That is US-centric and of little use for an EU itinerary `[verified: fetched site]`.
4. Fallback: search the exact flights on Google Flights or Skyscanner (multi-city with flight-time filters). Booking options there often include OTAs that can ticket mixed-carrier fares.

**Applies to ZAG→Japan:** high, as a research tool. **Risk: Safe.**

---

## 2. Point of sale (POS) and currency arbitrage

### 2.1 How it works and when it actually works
- Airlines file fares **by point of origin**. Fare rules can add sales restrictions such as "must be ticketed in country X".
- Selling the same origin fare in another currency normally uses IATA or bank conversion rates. An old IATA/oneworld rule read: "the fare will be that published for the country of origin converted to the currency of the country of sale at the bank selling rate… must not be lower than from the country of sale" (exception: travel originating and sold within Europe) `[claimed: Australian Frequent Flyer / FlyerTalk quoting the oneworld fare rule, removed after 2019]`.
- **Real POS gaps come from:**
  - (a) market-specific web promotions;
  - (b) different OTA markups or discounts per market;
  - (c) **stale exchange rates when a currency moves fast.** Example: paying TK in TRY during the 2018 lira crash saved about €200 on PRG–ICN (€1,560 → about €1,350) `[claimed: vielfliegertreff.de thread, Aug 2018]`;
  - (d) occasional OTA glitches. Example: Expedia **Japan** mispriced Turkish Airlines Europe→Japan at about **€238–240** return in 2016 `[claimed: secretflying.com post, 2016]`.

### 2.2 EU-internal POS is legally protected (Safe)
- Regulation (EC) 1008/2008, **Art. 23(1)**: fares for flights from an EU airport "shall be granted without any discrimination based on the nationality or the place of residence of the customer or on the place of establishment of the air carrier's agent or other ticket seller within the Community" `[verified: text quoted via legislation.gov.uk/eumonitor search extracts; EUR-Lex fetch was challenge-blocked]`.
- So a Zagreb resident may buy on lufthansa.com/de, austrian.com/at, klm.nl and so on, and the airline may not refuse or reprice because of residence. **Risk: Safe.**

### 2.3 Non-EU POS (TRY, INR, KRW, JPY, RSD…)
- **Steps:** on the airline site, switch the country or market (e.g. turkishairlines.com/tr-tr or /en-tr, qatarairways.com/en-in). Price the identical itinerary and compare the total in EUR at the card's actual exchange rate.
- **Evidence for 2024–2026: weak.**
  - Our Google Flights test showed **no difference** across TRY, HUF, JPY, INR, USD and PLN (§0.1.3).
  - Qatar's India-site deals are tied to Indian bank cards and Indian installments `[claimed: traveltrendstoday.in, icicibank.com]`, so they are not usable by an EU cardholder.
  - Turkish-site TRY savings in reports are mostly on **domestic Turkish** routes `[claimed: turkeytravelplanner.com]`.
  - No documented 2025–2026 example of a cheaper Europe→Japan fare on a non-EU POS was found.
- **Risks:**
  - The fare rule may require issuance in that country.
  - Card billing-country checks or 3-D Secure failures.
  - The airline may ask to see the payment card or a cardholder authorisation at check-in.
  - Customer service in another market.
- **Risk: Low risk to Moderate.** It is not illegal. The worst case is cancellation and refund or a fare-difference demand. Worth **one manual check on TK and QR** once a candidate itinerary exists.

### 2.4 VPN
Independent tests found nothing:
- Experte.com (Skyscanner; DE, US, PT and JP locations; including LAX–TYO at €394 everywhere): **no difference** `[claimed: https://experte.com/vpn/cheaper-flights]`.
- Tom's Guide (6-hour test) found little. Its best case was SFO–Japan **$63 (7%)** cheaper via a Brazil VPN `[claimed: tomsguide.com via search snippet]`.
- France's CNIL and DGCCRF investigated IP-based pricing in 2013 and found that **no observed technique used the IP address to set prices** `[claimed: Hogan Lovells/lemondeinformatique summaries]`.

**Verdict:** a VPN only matters as a way to reach a foreign POS (§2.3), and Google Flights does not need it. **Risk: Low risk** (grey area in some ToS). **Expected benefit: about zero.**

### 2.5 Card FX: practical
- **Always pay in the merchant's currency and decline dynamic currency conversion (DCC).**
- For EUR-priced tickets (most ex-EU fares), there is no FX cost.
- For non-EUR:
  - Revolut Standard: €1,000 per month of fee-free exchange, then 1%, plus about 1% extra at weekends `[claimed: Revolut fee pages via search]`.
  - Wise: about 0.35–1.5% depending on the currency pair `[claimed]`.
- [background] EU PSD2 (Directive 2015/2366, Art. 62(4)) bans surcharges for consumer cards in the EEA. OTAs work around it with "discounts" for their preferred payment method, so compare final prices.
- **Risk: Safe.**

---

## 3. How the ticket is built

### 3.1 Open-jaw (into Tokyo, out of Osaka, or the reverse) — Safe
- **How:** use the "multi-city" search. Legacy carriers price open-jaws as two half-returns, so the price is usually close to a plain return.
- **Evidence:**
  - VIE–KIX return €693 against VIE–TYO return €688, so the two Japanese gateways price alike `[verified: §0.1.1]`.
  - KLM ex-Spain deal: same €608 "to either destination", Tokyo or Osaka `[claimed: travel-dealz.com/deal/klm-spain-japan/]`.
  - Hainan BRU deal: "Trip.com can be an easier experience, in particular with open jaw tickets" `[claimed: travel-dealz.com/deal/hainan-japan/]`.
- **Limitation:** our tool could not price a multi-city open-jaw, so the toolkit should test it manually on Google Flights or the airline site.
- **Applies:** high. It saves a Tokyo↔Osaka backtrack (about ¥14k by shinkansen [background]).

### 3.2 Return vs two one-ways — Safe
- On full-service long-haul, a return is far cheaper than two one-ways (ZAG: €1,018 vs €1,323), and sometimes cheaper than one one-way (VIE) `[verified: §0.1.2]`.
- Exception: Chinese and Gulf carriers occasionally sell cheap one-ways. **Always price both ways.**

### 3.3 Stopover programmes — Safe (they add value more than they cut price)

| Programme | Terms (2026) | Source |
|---|---|---|
| **Turkish "Stopover in Istanbul"** (free hotel) | Ticket on TK stock (235-), **return on one booking**, same departure and arrival country, layover **20 h – 7 days**, not N or R class, apply **72 h ahead**. **1 free night in economy.** | `[claimed: blog.wego.com, updated 10 Jun 2026; official TK page blocked]` |
| **Touristanbul** (free tour) | Connections of 6–24 h at IST, sign up at the desk in the airport; schedule changed 1 May 2026 | `[claimed: blog.wego.com]` |
| **Finnair stopover** | Helsinki stopover of up to 5 days at **no extra fare**, via multi-city | `[claimed: afar.com summary]` |
| **ANA "Stopover & Add-on Free Fare"** | Up to **2 free domestic flights in Japan** (taxes payable) on a Europe/UK→Tokyo economy ticket. Booking window 24 Nov 2025 – 31 Jan 2026. Watch for a repeat in winter 2026/27. | `[claimed: euronews.com 2025-11-25]` |
| **China transit** | Croatians: **30 days visa-free in China until 31 Dec 2026** (business, tourism, **transit**) | `[verified: Croatian MFA mvep.gov.hr China page]`. Note: the MFA page still lists only the old 72 h / 144 h transit schemes. [background] China moved to 240 h transit in Dec 2024; check for 2027 trips. |

### 3.4 "Ex-" fares and positioning — Low risk (ground transport) or Moderate (separate flight)
- **How:** search the trip from nearby hubs (VIE, BUD, MUC, MXP, VCE, IST, BEG, LJU, GRZ), then reach that airport by train, bus or car, ideally **the day before**.
- **Evidence:**
  - Our test: VIE €688–787, IST €788, MXP €867, MUC €874 against ZAG €1,018 `[verified: §0.1.1]`.
  - Recent deals: Air China MXP €551 (Dec 2026), KLM ex-Spain €608, Hainan BRU €635 (bag included), **Asiana IST €618** (23 kg), SAS from 13 EU countries €471–565 (Nov 2025 – Mar 2026) `[claimed: travel-dealz.com Japan feed, fetched 2026-10-04]`.
- **Risk if positioning by plane on a separate ticket:**
  - A delay that makes you miss the long-haul is your problem.
  - The two tickets have separate baggage.
  - Keep at least 4–5 h of buffer, or travel the day before.
- **Variant (Violates airline ToS):** a ticket that starts or ends at the far airport but where you skip a leg, e.g. VIE–X–TYO–X–VIE flown from X. See §4.

### 3.5 Look past the usual metasearch results (Chinese and Korean carriers) — Safe
- **Why:** Air China, China Eastern, Hainan and others sell web-only fares that Google Flights and Matrix may not show (the €551 MXP case above).
- **Steps:**
  - Check airchina.com, ceair.com, hainanairlines.com, koreanair.com and flyasiana.com directly, using their "flexible dates" calendars.
  - Trip.com sometimes beats the airline site for these carriers [claimed: travel-dealz Hainan deal].
- **For Croatians:** visa-free China until the end of 2026 makes connecting in PEK, PVG or PKX straightforward.

### 3.6 Self-transfer and virtual interlining (Kiwi, Google Flights "Cheapest" tab) — Moderate
- **What is offered:**
  - Since Oct 2024, Google Flights has a **"Cheapest" tab** that shows "longer layovers, self-transfers or purchasing different legs of the trip through multiple airlines or booking sites" `[verified: blog.google 2024-10-16]`.
  - Kiwi.com's **Guarantee is an optional paid add-on** in 2026, not included by default `[claimed: kiwi.com/stories, May 2026]`. Without it, "the carrier is not responsible for segments booked with other carriers" `[verified: kiwi.com help article]`.
- **How to protect yourself:**
  - Allow at least 3–4 h at the self-transfer point (landside: collect bags, check in again, pass security).
  - Have hand baggage only, or bags you can re-check yourself.
  - Check visas for **landside** entry at the transfer point. For Croatians, Turkey, the UAE, Qatar and China (to end-2026) are easy. The UK requires an ETA and Korea may require K-ETA ([background], verify).
  - Watch Schengen exit and re-entry rules on the way back.
  - Prefer the self-transfer on the outbound with a buffer day; consider travel insurance that covers missed connections.
- **Evidence of savings:** Google's cheapest OW ZAG–TYO, €621, was a three-carrier itinerary (LH/Condor/Etihad). The "hide separate tickets" flag returned the same result, so it may be one ticket; inconclusive.

### 3.7 Nested and back-to-back tickets — Low risk if every segment is flown
These only matter if more than one Japan trip is planned. Example: a ZAG–TYO–ZAG return plus an ex-Japan return (TYO–ZAG–TYO) for a later trip. They use the weak yen (¥177/€, ECB 2026-10-02) for the ex-Japan ticket. Each ticket's minimum and maximum stay must fit, e.g. KLM: minimum 3 days or a Sunday, maximum 3 months `[claimed: travel-dealz KLM deal]`. Not relevant to a single trip.

### 3.8 Fifth-freedom flights — not applicable
Fifth-freedom routes into Japan today are Asia-internal, e.g. AirAsia BKK–KHH–NRT, BKK–TPE–OKA and CNX–TPE–CTS (from Jun 2025) `[claimed: aavplc.com newsroom]`. The only use is as a cheap final leg after a cheap Europe→Bangkok or Taipei fare, which is a self-transfer (Moderate).

### 3.9 Fuel or YQ dumping — dead for practical purposes; Violates airline ToS
- The best-known trick was killed within hours in March 2010 [claimed: viewfromthewing / liveandletsfly].
- Scott Mackenzie (Travel Codex) in 2017: "not what it once was… the opportunity cost… is rarely worth the financial savings" `[claimed: travelcodex.com/?p=14443]`.
- No 2025–2026 working examples were found. **Ignore.**

---

## 4. Hidden city / skiplagging and throwaway tickets

### 4.1 How it works
- **Hidden city:** book A→B→C because it is cheaper than A→B, and get off at B.
- **Throwaway:** book a return because it is cheaper than a one-way, and skip the return.
- Both break the coupon-sequence clause in the conditions of carriage (IATA RP1724 Art. 3.3) `[claimed: BEUC docs]`.

### 4.2 Risks and legal position (2026)
- **Hidden city is a one-way-only technique.**
  - Skipping any segment cancels all later segments.
  - Checked bags go to C.
  - Irregular operations can reroute you away from B.
  - You must meet visa requirements for C.
  - Airlines can confiscate miles or close accounts `[claimed: Jack's Flight Club article, updated 9 Oct 2025]`.
- **Lufthansa vs passenger** (OSL–FRA–SEA, skipped FRA–OSL, LH claimed €2,112): **dismissed** by the Berlin-Mitte court in Dec 2018. The appeal did not succeed; reports say it was withdrawn `[claimed: CNN 2019, godsavethepoints]`.
- **American Airlines vs Skiplagged:** a **$9.4M** judgment for AA (jury Oct 2024, finalised May 2025). It was against the **website**, on copyright grounds, not against passengers `[claimed: Dallas Morning News, Law360 via search]`.
- **EU 261 reform** (political agreement 15 Jun 2026; EP vote 7 Jul 2026; Council 13 Jul 2026): **"No-show policies for return flights are banned… passengers who do not take the outbound journey cannot be denied boarding on the return flight"**, and no fee may be charged. It **applies about 12 months after publication, so roughly H2 2027**. It **does not legalise skipping onward segments on a one-way** `[verified: EC news release transport.ec.europa.eu 2026-06-15; status: skyrefund.com updated 2026-09-30]`.
- National courts in DE (BGH 2010), AT (OGH 2013) and ES have already held unconditional no-show clauses unfair `[claimed: BEUC]`.

### 4.3 Is there a Japan-relevant pattern?
- In our scan, ZAG or VIE one-ways to MNL, SYD and HNL showed **no Tokyo-connecting itineraries among the cheapest results** (§0.1.5). Japan is mostly an end point from Europe.
- A theoretical pattern is "Europe→(Asia beyond) on JAL or ANA via Tokyo". JAL and ANA do sometimes discount through-fares via Tokyo `[claimed: Australian Frequent Flyer thread]`, but no current example beats the Tokyo fare.
- **Rating: Violates airline ToS / Risky.** Use it only with the user's explicit consent, on a one-way, with hand baggage only.

---

## 5. Mistake fares and deal alerts

### 5.1 How often, how fast, and are they honoured?
- Going counted **16 mistake fares in 2025**, a record and double 2024, all US-origin examples. It says about **10% are cancelled, often within 72 h**, and advises waiting **about 2 weeks** before booking non-refundable extras (guide updated 3 Jun 2026) `[claimed: going.com/guides/mistake-fares]`.
- A contrasting view: an UpgradedPoints editor says "at least half… have been canceled". Air France cancelled 1,500-mile business awards except for elite members `[claimed: upgradedpoints.com]`.
- **EU law view** (European Consumer Centre Austria): if the error is *obvious*, the seller may contest the contract **up to 3 years** later (Austrian law). The consumer is stronger if the price was online for days or weeks and was not obviously wrong `[verified: fetched europakonsument.at/en/page/error-fares]`.
- A German court threatened a deal site with fines and jail for spreading a Lufthansa error fare `[claimed: viewfromthewing]`.
- **Practical rule:** book within minutes, with a card that allows a chargeback if needed. Don't call the airline, and don't book non-refundable hotels for about 2 weeks. **Risk: Low risk** (the worst case is a refund).

### 5.2 Which deal sources are alive and can be monitored (checked 2026-10-04)

| Source | Status | Feed for automation |
|---|---|---|
| **Travel-Dealz** (DE/EU, English) | Active (posts 2 Oct 2026) | **`https://travel-dealz.com/destination/japan/feed/`** returns RSS 200 and is Japan-specific; also `https://travel-dealz.com/feed/` `[verified: curl]` |
| **Fly4free.com / .pl** | Active (posts 4 Oct 2026) | `https://www.fly4free.com/feed/` and `https://www.fly4free.pl/feed/` return RSS 200; `/flights/flight-deals/asia/feed/` works (last item Aug 2026); tag and search feeds return 403 `[verified: curl]` |
| **HolidayPirates / Urlaubspiraten / TravelPirates** | Active | `holidaypirates.com/feed`, `urlaubspiraten.de/feed`, `travelpirates.com/feed` return 200 `[verified: curl]` |
| **The Flight Deal** (US) | Active | `theflightdeal.com/feed/` returns 200 `[verified]`; US origins, low relevance |
| **Thrifty Traveler** (US) | Active | `thriftytraveler.com/feed/` returns 200 `[verified]`; US-centric |
| **Secret Flying** | Site up but behind a Cloudflare challenge | `/feed/` returns **403** to curl and WebFetch `[verified]`. It needs a browser or e-mail alerts. |
| **Jack's Flight Club** | Up (HTTP 200) | No RSS; e-mail or app. Premium about £39/yr in Europe `[claimed]`; Zagreb as a departure airport not confirmed. |
| **Going** | Up (HTTP 200) | US-focused, e-mail only |
| **Pelikan.cz / Letuška.cz** (CZ OTAs) | Up (HTTP 200) | No RSS found (`/rss` returns HTML) |
| Telegram channels (@secretflying, @fly4free, @traveldealz…) | No public message preview at `t.me/s/…` | Not verified |
| Reddit r/JapanTravel, r/travelhacks, r/Shoestring | Background | Useful for sanity checks, not for alerts |
| FlyerTalk Mileage Run forum | 403 to WebFetch | Manual reading only |

**Automation idea for the toolkit:** poll the three Japan-relevant RSS feeds (travel-dealz Japan, fly4free.com, fly4free.pl) a few times a day and keyword-match: `Japan|Tokyo|Osaka|Haneda|Narita|Kansai|Japonsk|Tokio` together with `Zagreb|Croatia|Vienna|Wien|Budapest|Ljubljana|Venice|Milan|Munich|Graz|Belgrade|Trieste`.

---

## 6. Timing: evidence, not folklore

### 6.1 How far ahead to book
- **Google Flights data** (Sep 2024, 4–5 years of history):
  - US→Europe was cheapest about **94 days** out.
  - For international trips in general, prices "don't meaningfully drop" before departure and **start rising within about 50 days**.
  - [claimed: thriftytraveler.com Google Flights data article; blog.google 2024 post (fetched) says "booking early for international trips"]
- **Expedia/ARC "Air Hacks 2026"** (US and Canada ticketing data): Friday is the cheapest day to book (−3%) and to fly (−8%). It claims international trips are cheaper booked 31–45 days out than 6 months out `[claimed: expedia newsroom via search; pages returned 429 to us]`. This conflicts with Google's data. Treat it as US-market data.
- **Which?/Skyscanner (UK, 2023):** about 6 months ahead on average, varying widely by route `[claimed: which.co.uk, Feb 2023]`.
- **Our data point:** ZAG–TYO for Feb 2027 sat around €985–1,018 at 4–6 months out. The only real drop was a **2-day sale** (€776) (§0.1.4).
- **Conclusion for Europe→Japan:** start watching **3–8 months** ahead, set alerts, and **book when a sale or deal appears**. Don't wait for the final 6 weeks.

### 6.2 Day of the week
- **Day you book:** about a 1.3% difference, which is noise `[claimed: Google via thriftytraveler]`. Expedia says Friday saves 3%. **Myth-level effect.**
- **Day you fly:** Monday to Wednesday about **13% cheaper** than Friday to Sunday on average, with a smaller gap on international routes (Google) `[claimed]`. **This is real; use the date grid.**

### 6.3 Cookies and incognito
- CNIL/DGCCRF (France, 2013) found no IP-based price adjustment. They did find cookie-driven OTA fee changes [claimed].
- A 2025 test reported incognito cheaper in 7% of searches, dearer in 5% and identical in 88% `[claimed: search summary citing a 2025 study]`.
- Delta's use of AI pricing (Fetcherr, about 3% of its domestic network in 2025) drew US Senate questions. Delta stated that **no fare targets individuals** `[claimed: AJC, NBC, Jul 2025]`.
- **Verdict: myth.** Prices move because inventory and demand move.

### 6.4 Price tracking and guarantees
- **Google Flights:** tracking for specific dates, plus "Any dates" tracking that e-mails when prices are low **in the next 3–6 months** `[verified: blog.google 2024-09-05]`.
- **Google Flights price guarantee:** US departures only, "Book on Google" fares, refunds up to $500 a year `[claimed: aerointernational.de, liveandletsfly]`. **Not available for ZAG.**
- **Google "Flight Deals" (AI):** beta Aug 2025 in the **US, Canada and India** only `[verified: blog.google 2025-08-14]`.
- **Skyscanner and Kayak alerts:** standard. **Hopper** price predictions and "price freeze" are vendor claims, so verify EU availability.

### 6.5 Holds and free cancellation
- **EU:** there is **no statutory cooling-off period** for flights. Passenger transport is outside the Consumer Rights Directive (Art. 3(3)(k)) `[claimed: EC answer via ieu-monitoring]`. The US DOT 24-hour rule applies only to US flights.
- **Turkish Airlines:** a **full refund within 24 h of purchase** for tickets bought on turkishairlines.com or the app, if departure is **at least 7 days** away. Excluded: changed tickets, tickets issued with "Hold the price", and ancillaries `[verified: turkishairlines.com official pages as indexed in search; direct fetch blocked by bot protection]`. **This works as a free 24 h hold.**
- **Paid holds:**
  - Emirates "Hold My Fare": 48 h, fee refunded if you buy `[claimed: aviationweek]`.
  - Qatar "Hold my booking": up to 72 h, may cost a fee `[claimed: qatarairways.com page in search]`.
  - TK "Hold the price": paid `[claimed]`.
- Lufthansa "24 h free cancellation" pages in search results were **phone-number SEO spam** (e.g. on goodreads, saylor.org, a .pdf on autoritedelaconcurrence.fr). **Ignore them.**

### 6.6 Sale calendar
- **Qatar Black Friday (ex-Europe) 2025:** booking 21 Nov – 2 Dec 2025, up to 20% off base fares, 17 European countries. **Croatia→Osaka** was included `[claimed: loyaltylobby.com 2025-11-22]`. Expect something similar around late November 2026.
- **Qatar (US) Black Friday 2025:** up to 30% off `[claimed]`. **LOT** has a Black Friday page (lot.com, blocked to us).
- **Turkish:** reportedly no Black Friday sale in years `[claimed: travelingformiles]`, but frequent market promotions.
- **"Travel Tuesday"** (2 Dec 2025) deals are mostly from the US.
- Chinese carriers' promotions appear on travel-dealz all year (e.g. Air China MXP, July 2026, for December travel).

---

## 7. Miles and points (brief)

| Option | Fact | Verdict for this trip |
|---|---|---|
| Finnair Plus (Avios) HEL–Tokyo economy | **30,000 Avios + about £244 taxes one-way** on finnair.com (about £411 on ba.com) `[claimed: headforpoints.com 2025-09-12]` | A return of about 60k Avios plus about €560 in cash is **not cheaper** than a €690–1,000 cash fare. |
| Flying Blue Promo Rewards | Up to about 25% off selected routes each month; mostly transatlantic; Japan is rarely included `[claimed: frequentmiler/insideflyer]` | Only useful if Japan appears and miles are already held. |
| Turkish Miles&Smiles | Devaluation in Dec 2025; partner business class about 85–90k one-way `[claimed: search summary]` | Not useful in economy without a balance. |
| Revolut RevPoints (available in **Croatia**) | Transfer 1:1 to 30+ programmes, incl. Avios, Flying Blue, Qatar, Etihad, Turkish `[claimed: Revolut/insideflyer]` | Accrues slowly; a small top-up at most. |
| Buying miles | Rarely below about 1.5–2 € cents per mile [background] | **Not worth it** for economy here. |

**Bottom line:** someone in the EU without points cannot realistically beat a €550–800 economy cash fare with miles on this route. **Risk: Safe.**

---

## 8. Discounts and payment

| Lever | Facts | Risk |
|---|---|---|
| **Turkish Airlines student fare** | Ages **12–34** on international flights. **10%** off flights from or to Türkiye, **15%** between two points outside Türkiye. **40 kg** baggage (2×23 kg on piece-concept routes). Requires Miles&Smiles membership, choosing "Student" as passenger type, and proof (university ID, ISIC, etc.), renewed yearly `[verified: turkishairlines.com student pages as indexed; direct fetch blocked]` | Safe if eligible |
| **Qatar Student Club** | Ages **18–30**. Four discounted tickets at 10%, 15%, 20%, 20%. Extra 10 kg or 1 piece. Two free date changes. QR-operated flights only `[claimed: travel-dealz, wego, qatarairways.com pages]` | Safe if eligible |
| StudentUniverse | **Booking portal closed 2 Jun 2025** (BYOjet) `[claimed: search summary]` | — |
| Trip.com new-user codes | Small, e.g. **USD 3–15** off a flight; referral codes advertise "up to 20%", with flights lower `[claimed: trip.com promo pages]` | Low risk (OTA service) |
| Cashback portals | ShopBack/Capital One cashback on Trip.com is for SG/US markets. No Croatia-resident portal with flight cashback found | — |
| **eDreams Prime** | From about **€54.99/yr** (30-day free trial, renews automatically). Ryanair alleges inflated "discounts" `[claimed: search summary]`. Only worth it if the Prime price beats every other channel by more than the fee, and cancel the trial straight away. | Low risk (subscription trap) |
| Price freeze (Hopper, airline paid holds) | The fee is lost if you don't buy; useful only around expected sale dips | Low risk |
| Payment | Pay in EUR or on a zero-FX card, decline DCC. Revolut weekend markup +1% `[claimed]` | Safe |

---

## 9. Comparing on total cost

**Compare like with like.** Use the total for 1–2 checked bags, a seat (usually skip it), OTA service and "payment" fees, and the cost and time of any positioning.

| Carrier or fare (Europe↔Japan, economy) | Checked bag in cheapest fare? | Source |
|---|---|---|
| Korean Air | 1×23 kg (the VIE €688 result did not change with a 1-bag filter) | `[verified: our GF test]` |
| Turkish Airlines | Bag included; recent deal "with 30 kg luggage" (KUL, Oct 2026) | `[claimed: travel-dealz feed]` |
| Hainan / Asiana deals | 23 kg included | `[claimed: travel-dealz]` |
| Air France / KLM Economy Light | **No bag**: €608 → €723 with a bag (+€115 return) | `[claimed: travel-dealz KLM deal]` |
| **ANA** | **1×23 kg since 1 Nov 2024** on Europe routes; 2 bags need a dearer fare (+€120) | `[claimed: travel-dealz ?p=69022]` |
| **JAL** | **2×23 kg** kept | `[claimed: same article]` |
| SAS Go Light | No bag; about €45 per direction on SAS | `[claimed: travel-dealz SAS deal]` |
| Lufthansa Group / Finnair / LOT light fares | Often no bag on long-haul light fares; check at booking | [background] |

**OTA vs direct booking:**
- OTAs can be up to about **€180 cheaper** (SAS case) but charge more for bags and service `[claimed: travel-dealz]`.
- Lufthansa Group adds a **GDS distribution cost charge** of €18–23 per ticket (Amadeus €19 from 5 May 2026) on traditional-GDS bookings. Booking on LH's own sites or via NDC is exempt `[claimed: touristik-aktuell, travelmarketreport via search]`.
- AF-KLM charge a reduced GDS surcharge (€3–4 per segment, 2025–2026) `[claimed]`.
- For LH, OS, LX and AF/KL, the airline's own site is often cheapest or equal.

---

## 10. Myths and stale advice to ignore

1. **A VPN or a "foreign country" setting on Google Flights lowers the price.** Our test: identical within 0.5% across 7 markets (§0.1.3). Independent VPN tests found nothing (§2.4).
2. **Clear cookies or use incognito.** No evidence (§6.3).
3. **Book on Tuesday, or exactly N weeks ahead.** The booking-day effect is about 1–3%. Advance-window studies conflict and are US-market. Catching a sale matters far more (§6.1–6.2).
4. **Fuel dumping, "3X" segments.** Effectively dead since about 2010–2017 (§3.9).
5. **Hidden city via Tokyo.** No pattern found for Zagreb or Vienna (§4.3).
6. **"Kiwi protects every self-transfer."** The Guarantee is a paid add-on in 2026 (§3.6).
7. **StudentUniverse for student fares.** Closed in Jun 2025.
8. **"24-hour free cancellation" on every airline.** It is US-only law. In Europe only specific airlines offer it, e.g. Turkish on its own site. Many web pages claiming otherwise are SEO spam.
9. **Google Flights price guarantee.** US departures only.
10. **Miles are always cheaper.** Not for economy Europe→Japan without existing points (§7).

---

## 11. Risky techniques: use only with the user's explicit consent

| Technique | Why it is risky | Rating |
|---|---|---|
| Hidden-city or throwaway segments | Breaks the coupon-sequence clause. Later segments are cancelled, bags go to the ticketed destination, miles can be confiscated. The 2026 EU ban covers **return** no-shows only, and only from about H2 2027. | Violates airline ToS / Risky |
| Self-transfer on separate tickets (incl. Google "Cheapest" tab, Kiwi) | No protection if you misconnect. You re-check bags and need visa or landside entry (UK ETA, K-ETA). | Moderate |
| Change of airport within one ticket (e.g. **ICN→GMP** on the €688 Korean Air fare) | Needs Korean entry (check K-ETA for Croatians at travel time) and about 1 h of ground transfer. Use Matrix `-change` to avoid it. | Moderate |
| Positioning by plane on a separate ticket | You absorb a missed connection. Prefer ground transport the day before. | Moderate |
| Non-EU POS with card or billing mismatch | Possible cancellation, fare-difference demand, or card check at the airport | Low risk – Moderate |
| Mistake fares | Possible cancellation; hold off on non-refundable extras for about 2 weeks | Low risk |

---

## 12. Open questions for the user or orchestrator

1. **Home airport and willingness to travel.** Would you take a bus or train to **Vienna** (the strongest saving in our test), or to Budapest, Munich, Venice or Milan? Should we include Istanbul as a start?
2. **Dates and flexibility.** Travel window, trip length, and how many days either side we can shift.
3. **Eligibility for discounts.** Age and **student status**: Turkish student fare (12–34), Qatar Student Club (18–30).
4. **Baggage.** Hand luggage only, or 1–2 checked bags? This changes the ranking (§9).
5. **Japan airports.** Is open-jaw Tokyo in / Osaka out acceptable?
6. **Risk appetite.** Are self-transfers, separate positioning flights, or ToS-violating tricks acceptable?
7. **Payment cards.** Which cards are available (Revolut, Wise, Croatian bank card with an FX fee)?
8. **Existing points or status** (Miles&Smiles, Flying Blue, Avios, RevPoints).
9. **Still to verify by hand:**
   - Turkish and Qatar fares on the TR and IN POS for the final itinerary (airline sites block bots).
   - Multi-city open-jaw prices (our tool could not query them).
   - Whether Chinese carriers' own sites undercut Google Flights for the chosen dates.

---

## Appendix A: reproducing the live Google Flights tests

```python
# pip install fast-flights==3.1.0 typing_extensions selectolax
import json, subprocess
from selectolax.lexbor import LexborHTMLParser
from fast_flights import create_query, FlightQuery
q = create_query(flights=[FlightQuery(date="2027-02-10", from_airport="ZAG", to_airport="TYO"),
                          FlightQuery(date="2027-02-24", from_airport="TYO", to_airport="ZAG")],
                 trip="round-trip", currency="EUR", language="en")
url = q.url() + "&gl=HR"
html = subprocess.run(["curl","-sSL","--compressed","-A","Mozilla/5.0 ... Chrome/126.0 Safari/537.36",
        "-H","Cookie: CONSENT=YES+cb; SOCS=CAESHAgBEhJnd3NfMjAyNDAxMDEtMF9SQzIaAmVuIAEaBgiAo_CmBg", url],
        capture_output=True, text=True).stdout
p = json.loads(LexborHTMLParser(html).css_first(r"script.ds\:1").text().split("data:",1)[1].rsplit(",",1)[0])
lowest = p[7][0][0][1]                      # Google's lowest price for the query
typical = (p[5][4][1], p[5][5][1])          # "typical" low/high
history = p[5][10][0]                       # [[epoch_ms, price], ...] last ~60 days
itins = [(k[1][0][1], k[0][0], [(s[3], s[6]) for s in k[0][2]]) for i in (2,3) for k in (p[i][0] or [])]
```

Notes:
- Space requests 5–8 s apart. Google sometimes returns `errorHasStatus: true`; we saw this for ZAG–KIX and for multi-city open-jaw queries.
- `connecting_airports` filtering did not work reliably.
- The library's own `get_flights()` parses only `payload[3]` (the "other flights" list). Read `payload[2]` as well.

## Appendix B: main sources (all accessed 2026-10-04)

**ITA Matrix**
- https://support.google.com/faqs/answer/2736497
- https://princeoftravel.com/guides/how-to-use-ita-matrix-like-a-pro/
- https://www.travelcodex.com/2012/01/advanced-routing-language-in-ita/
- https://upgradedpoints.com/travel/ita-matrix/
- https://travel-dealz.com/?p=38545
- https://bookwithmatrix.com/
- https://chromewebstore.google.com/detail/ita-matrix-powertools/menecfddnlmanmpadcalononkolnplpp

**Google Flights**
- https://blog.google/products-and-platforms/products/search/google-flights-cheapest-tab/
- https://blog.google/products/search/how-to-save-money-google-travel-2024/
- https://blog.google/products-and-platforms/products/search/google-flights-ai-flight-deals/
- https://thriftytraveler.com/news/travel/google-flights-data-analysis/

**POS, VPN, legal**
- https://experte.com/vpn/cheaper-flights
- https://www.tomsguide.com/computing/vpns/can-a-vpn-get-cheaper-flights
- https://vielfliegertreff.de/forum/threads/ota-mit-tuerkische-lira.123238/
- https://revman.substack.com/p/airfare-arbitrage
- https://www.legislation.gov.uk/eur/2008/1008/chapter/IV
- https://transport.ec.europa.eu/news-events/news/commission-welcomes-landmark-agreement-revised-air-passenger-rights-2026-06-15_en
- https://skyrefund.com/en/blog/eu261-reform-2026
- https://ploum.nl/en/news/No-show-clauses-under-fire-passenger-rights-versus-contractual-freedom
- https://www.godsavethepoints.com/skiplagging-hidden-city-legal-battle/
- https://members.jacksflightclub.com/articles/what-is-hidden-city-airfare-ticketing
- https://europakonsument.at/en/page/error-fares
- https://upgradedpoints.com/news/airline-no-longer-honoring-mistake-fares/
- https://www.going.com/guides/mistake-fares

**Deals and carriers**
- https://travel-dealz.com/destination/japan/
- https://travel-dealz.com/ticker/121404/
- https://travel-dealz.com/deal/hainan-japan/
- https://travel-dealz.com/deal/klm-spain-japan/
- https://travel-dealz.com/?p=67288
- https://travel-dealz.com/?p=69022
- https://loyaltylobby.com/2025/11/22/qatar-airways-ex-europe-black-friday-sale-for-2025-book-by-december-2/
- https://blog.wego.com/turkish-airlines-stopover-program/
- https://euronews.com/travel/2025/11/25/this-japanese-airline-is-offering-free-domestic-flights-for-uk-and-european-travellers
- https://mvep.gov.hr/consular-informations/visas/visas-22879/22879?country=66
- https://travel-dealz.com/?p=100410

**Kiwi**
- https://www.kiwi.com/en/pages/guarantee
- https://www.kiwi.com/stories/kiwi-com-fees-in-2026-what-todays-deal-hunting-travelers-need-to-know/

**Turkish Airlines** (official pages, indexed via search; direct fetch blocked)
- https://www.turkishairlines.com/en-int/ticket-refund-at-no-charge-in-the-first-24-hours/
- https://www.turkishairlines.com/en-int/student-flight-discount/

**Timing**
- https://www.which.co.uk/news/article/the-cheapest-day-to-book-and-to-fly-afeG35z2iUzT
- Expedia Air Hacks 2026: https://www.expedia.co.uk/newsroom/expedia-2026-air-hacks-2/ (429 to us; figures taken from search summaries)

**Exchange rates**
- ECB reference rates 2026-10-02: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml
