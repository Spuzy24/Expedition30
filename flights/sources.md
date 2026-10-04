# Sources catalog: where to look, how, and how much to trust it

> Living summary of `research/01-search-engines.md`, `05-tools-google-matrix.md`,
> `06-tools-ota-meta.md`. Status = tested from the cloud container on 2026-10-04.
> **Auto** = a script/MCP queries it. **Manual** = blocked to bots, so ask the user to check in
> their own browser (give them exact URLs). Never try to defeat captchas.

## 1. Discovery engines (find the fare / itinerary)

| Source | Status | How we query it | Unique strength | Watch out |
|---|---|---|---|---|
| **Google Flights** | Auto | `scripts/gflights.py` (see tools.md) | Airline-direct baseline; date grid, price history ("typical" range + 60-day history), Explore; "Cheapest" tab incl. self-transfer | Default list misses many Chinese-carrier & self-transfer combos; some airline web fares (Air China promos) absent; POS/currency switching changes nothing |
| **ITA Matrix** | Auto (partial) / Manual | `scripts/matrix.py` (see tools.md) | Routing & extension codes, fare rules/basis, month calendar with length-of-stay, sales city | No LCCs, no self-transfer, misses some web-only fares; can't book on it |
| **Kiwi.com: MCP** | Auto | `scripts/mcp_flights.py kiwi` (or native MCP tool `kiwi` via .mcp.json) | Multi-origin/destination, ±10 d flex, ranges, nights, bag filter, carrier filters | ~15 results/call; hides carriers unless filtered; RT pricing of some carriers (CA) is implausible |
| **Kiwi.com: web GraphQL** | Auto | `scripts/kiwi_graphql.py` | Radius (`ZAG@300`), `Country:`/`Continent:` origins, **per-city** cheapest, **origin-scan**, price calendar, bags priced in | Many results are self-transfer (flag shown); `Continent:europe` plain search is thin, so use per-city/origin-scan |
| **Skiplagged: MCP** | Auto | `scripts/mcp_flights.py sk / skcal / sksweep` | Independent inventory (found OU+Juneyao single tickets); hidden-city flag; 100 results/page; calendars | USD prices; rounds down; hidden-city = ToS risk |
| **Kayak / momondo** | Auto | `scripts/kayak.py` (use momondo.de / kayak.de for EUR) | Live meta-search over all OTAs + airlines + Kiwi combos; multi-origin, nearby, ±3 days; shows bag inclusion and provider | Results sorted by price may be self-transfer (KIWIVI*) |
| **Aviasales** | Auto (browser) | `scripts/aviasales.py` | OTA-built self-transfer packages (Mytrip FR+MU, Lucky2Go), tiny OTAs | ~45 s/search; vet unknown sellers |
| **Booking.com Flights** | Auto (browser) | `scripts/booking_flights.py` | = Etraveli inventory (Gotogate/Mytrip/Flightnetwork), full price breakdown, bags | Seller risk HIGH (Etraveli) |
| **Ryanair / Wizz** | Auto | `scripts/ryanair_wizz.py` | Positioning fares: cheapest to every destination, daily calendars, RT | Fare only, no bags; Wizz has no ZAG/VIE; Ryanair none from LJU/GRZ |
| **Positioning combiner** | Auto | `scripts/positioning.py` | Home → hub (FR/W6, incl. sibling airports like CRL↔BRU) + cheapest Kiwi long-haul hub→Japan, buffer-aware, both directions | Ground transfer between sibling airports not costed; separate tickets |
| **AZair** | Auto (stale) | `scripts/azair.py` | LCC route ideas incl. 1-change LCC combos | Prices months old; no results beyond ~Jan 2027. Discovery only |
| **FlightConnections** | Auto (browser) | `scripts/flightconnections.py` | Who flies where (nonstop networks, flights/month) | No prices |
| **Deal feeds** | Auto | `scripts/deals.py` (22 RSS feeds) | Flash sales, error fares, regional benchmarks (fly4free.pl Japan tag, travel-dealz Japan, utazomajom.hu) | Expired deals; Secret Flying feed blocked |
| **Skyscanner** | **Manual** | user's browser: `skyscanner.net/transport/flights/zag/tyoa/YYMMDD/YYMMDD/`, whole month `?oym=2703&iym=2703`, Everywhere `/transport/flights-from/zag/` | Broadest tiny-OTA list + seller ratings; whole-month/Everywhere | PerimeterX captcha to bots; month/Everywhere prices cached |
| **Trip.com** | **Manual** (also visible inside Kayak as provider CTRIPAIR) | user's browser: `trip.com/flights/showfarefirst?dcity=vie&acity=tyo&ddate=2027-03-10&triptype=ow&class=y&quantity=1&locale=en-XX&curr=EUR` (try other locales) | Often cheapest seller for Chinese carriers (CA, MU, CZ, HO, HU), open-jaw | Verification wall to bots |
| **Secret Flying** | **Manual** | secretflying.com origin pages (Zagreb, Ljubljana, Vienna, Budapest, Belgrade) | Error fares from our region | Cloudflare blocks scripts |
| Airline sites (Air China, China Eastern, Juneyao, Hainan, Korean, Turkish, Qatar, LOT, Finnair, Etihad…) | **Manual** (bot walls) | user's browser, exact flights/dates from our shortlist | Web-only promos (Air China €551 MXP case), direct-booking protection, Air China Fri–Sun discount | Air China airchina.com blocks cloud IPs; airchina.at loads but its search can't be automated |

## 2. Seller trust (who you actually pay)

| Tier | Sellers | Rule |
|---|---|---|
| **Prefer** | The airline itself | Book direct if within ~€20–40 of the cheapest OTA *final* price |
| OK | Trip.com (4.4★, 13% 1★), Kiwi.com (4.0★, 24% 1★; Guarantee is a paid add-on), lastminute | Use when the saving is real; screenshot everything |
| Caution | eDreams/Opodo/GO Voyages (Prime subscription trap; AGCM €9M fine Feb 2026: prices differ by arrival channel), eSky/Lucky2Go, BudgetAir | Decline Prime/trials; compare the final price |
| High risk | Etraveli brands: Gotogate (2.5★, 34% 1★), Mytrip (2.9★, 50% 1★), Flightnetwork, Booking.com flights; unknown Jetcost/Aviasales-linked OTAs | Only for big savings on a simple ticket, with the user's OK |
| Dead / scam | Travelgenio (domain now a gambling site), fly.com, surprice.jp, StudentUniverse, Dohop consumer search, MrJet, Navifare | Never |

Checkout red flags: pre-ticked "flexible ticket" / "support package" / "VIP" / "price freeze",
online check-in sold as a service, payment-method "discounts", dynamic currency conversion,
price higher than the metasearch showed.

## 3. What the tests taught us about coverage (2026-10-04)
- **No engine finds everything.** Same trip, different winners:
  - Google Flights default list: €571 ZAG→TYO OW.
  - Kiwi: €418 self-transfer / €373 ±3 days.
  - Skiplagged: $566 single ticket.
  - Kayak `--nearby --flex 3`: €356 FR+HO via CRL.
- **Carrier blind spots:** Kiwi showed Air China ZAG only with `--only-airlines CA`. Air China promos are often missing from GF/ITA.
- **Independent tests:** momondo ranked #1 for lowest fares in Frommer's 2025 and 2026; Skyscanner top-rated by Which? (Oct 2025); Google Flights mid-pack on price but best for discovery.
- **Cached vs live:** Skyscanner month/Everywhere, Kayak/momondo calendars, Aviasales ribbon, AZair and Google Explore are indicative only. Always re-run an exact-date live search.
