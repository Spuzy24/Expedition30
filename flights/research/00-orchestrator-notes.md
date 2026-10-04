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
