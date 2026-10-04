# Orchestrator notes (my own findings while sub-agents research)

## 2026-10-04: environment probes
- Reachable via curl: google.com/travel/flights, matrix.itasoftware.com, kiwi.com, kayak.com,
  momondo.com, trip.com, aviasales.com, azair.eu, secretflying.com (HTML), wego.com,
  edreams.com, flightconnections.com, serpapi.com, api.duffel.com, reddit.com.
- Blocked: skiplagged.com (403 Cloudflare bot block, site-side), fly4free.com homepage (403,
  but its RSS feeds return 200), test.api.amadeus.com (CONNECT 502: Amadeus Self-Service is gone).
- FX: api.frankfurter.dev (ECB) OK; open.er-api.com OK (more currencies). → scripts/fx.py

## Deal feeds (tested 2026-10-04) → scripts/deals.py
OK: fly4free.com (europe/asia/all), fly4free.pl (+ tag/japonia), urlaubspiraten.de/.at,
travel-dealz.de/.com (+ ?s=japan&feed=rss2), piratinviaggio.it, travelpirates.com,
theflightdeal.com, loyaltylobby.com.
Blocked for bots: secretflying.com/feed (403), jacksflightclub (no feed), flynous (403),
reddit RSS (429 after 1st call), pelikan.cz (no RSS), letuska.cz (unreachable).

## Price benchmarks from fly4free.pl Japan tag (round trip, economy, 2026)
| Deal | PLN | ≈EUR | Construction |
|---|---|---|---|
| Tokyo from 2002 PLN (Nov–Dec 2026) | 2002 | ~457 | Ryanair GDN→ARN + **Air China ARN–PEK–HND** (23 kg incl. on CA), booked via Skyscanner |
| Osaka 2098 PLN (Nov–Dec 2026) | 2098 | ~479 | Ryanair GDN→ARN + Air China ARN–PEK–KIX |
| Osaka 2090 PLN | 2090 | ~477 | (mid-2026) |
| Etihad to Asia from 1983 PLN | 1983 | ~453 | Etihad sale |
| Etihad Tokyo 2712 / 2781 PLN | ~2750 | ~630 | Etihad from WAW |
| Qatar Japan 2552–2838 PLN | ~2700 | ~585–650 | Qatar sale |
| Tokyo from 5 Polish cities 2934 PLN | 2934 | ~670 | LOT/other (to check) |

**Pattern:** the absolute floor (~€450–480 RT incl. checked bag on long-haul) comes from
Chinese carriers (Air China via PEK) **from a European city that isn't home**, reached by a
cheap low-cost positioning flight on a separate ticket. ⇒ the playbook must include a
**Europe-wide long-haul origin sweep** (which European airport has the cheapest Japan fare on
the dates?) + **positioning cost** from home (Azair/Ryanair/Wizz), not just nearby airports.
Air China gives free transit hotels on long PEK connections.

## 2026-10-04: Kiwi & Skiplagged public MCP servers (verified by me)
- `https://mcp.kiwi.com` (tool `search-flight`) and `https://mcp.skiplagged.com/mcp`
  (`sk_flights_search`, `sk_flex_departure_calendar`, `sk_flex_return_calendar`,
  `sk_destinations_anywhere`) answer plain JSON-RPC POSTs, no auth. → scripts/mcp_flights.py
- Kiwi: multi-origin & multi-destination in ONE call ("ZAG,LJU,GRZ,VIE,BUD" → "TYO,OSA"),
  ±10 day flex, nights-in-destination, bag requirements, self-transfer toggle, sort=price.
  Hard cap ≈15 itineraries per call → split sweeps (per origin / per destination / per date
  window) so cheap options aren't crowded out. 3–10 s per call.
- Skiplagged: up to 100 results/page (300 available), flags hidden-city & virtual-interline,
  shows airport changes (e.g. Ryanair into STN, Air India out of LHR). Prices in USD.

## Sample results (search date 2026-10-04, 1 adult economy, Jan/Feb 2027)
| Query | Cheapest | Notes |
|---|---|---|
| Kiwi ZAG→TYO RT 20 Jan–3 Feb exact | €1114 (NH via FRA) | Air China ZAG flights not shown; ZAG direct-origin is expensive |
| Kiwi {ZAG,LJU,GRZ,VIE,BUD}→{TYO,OSA} OW 20 Jan ±3 | **€443 MU BUD–PVG–NRT** (cabin bag, no hold bag) | €449 BUD–PVG–HND incl. 1 checked bag |
| Kiwi same, RT ±3/±3 | **€734 KE BUD–ICN–HND** (1 checked bag) | VIE–ICN KE €739; CA via PEK €805–864 |
| Kiwi {TYO,OSA}→{region} OW 3 Feb ±3 | €414 Scoot KIX–SIN–VIE (no hold bag) | CA HND–PEK–VIE/BUD €570 with bag |
| Kiwi MU only BUD↔TYO RT | €891 | = 2× one-way: MU prices RT ≈ sum of OWs |
| Skiplagged ZAG→TYO OW 20 Jan | $566 OU+HO ZAG–BRU–PVG–NRT | also CA via BRU–PEK $582; Ryanair+Air India STN~LHR (airport change!) $595 |

**Lessons:** (1) Budapest beats Zagreb by hundreds of EUR. (2) RT vs 2×OW: it depends on the
carrier (KE RT is far below 2×OW; MU RT = 2×OW) → always price both, plus open-jaw / mixed
carriers. (3) Engines disagree, so use several (Kiwi didn't show Air China's new ZAG route
on that date; Skiplagged found OU+HO via BRU).
