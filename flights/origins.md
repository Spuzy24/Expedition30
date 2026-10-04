# Departure airports & positioning (home = Zagreb, ASSUMED until the user confirms)

> Living summary. Deep sources: `research/04-home-region.md` (snapshot 2026-10-04).
> Round-trip ground costs used by `scripts/quotes.py` live in `searches/ground.json`.
> **Different home base?** Re-run `scripts/flixbus_ground.py --from "<City>" --date <date>` and
> `--drive --home <lon,lat>`, then rewrite ground.json and the tiers below.

## 1. Origin set to search, in priority order

| # | Airport(s) | Ground from ZAG (return, pp) | Why it's in the set | Must beat best ZAG fare by |
|---|---|---|---|---|
| 1 | **ZAG** | €16 | Home. **Air China via OTP→PEK (Mon/Wed/Fri)**, TK, QR, LO, LH group, AF/KL, IB, flydubai | — |
| 2 | **VIE** | €56 (Fri ~€75). Night bus 01:45/23:30 or FlixBus direct to airport 06:30→11:55 | Densest Asia network in reach: ANA nonstop HND, OS NRT (summer), CA, MU (XIY), HU, KE, BR, CI, EK, QR, EY, TK. Repeated sub-€500 Japan deals | ~€100 |
| 3 | **BUD** | €60–80 (+€50 hotel for a non-Friday morning flight; Fri 23:59 bus reaches the airport 04:50) | Chinese-carrier hub: CA (PEK, CKG), MU/FM (PVG, XIY, NGB), CZ (CAN), HU; KE, OZ. **Cheapest regional origin on average** | ~€100–170 |
| 4 | **BEG** | €56 (22:15 night bus; non-Schengen border) | Air Serbia/CZ to CAN & PVG, Hainan PEK, QR, flydubai | ~€105 |
| 5 | **LJU, GRZ** | €30 each | Same LH-group/TK/LO products as ZAG, sometimes cheaper | ~€45–50 |
| 6 | **MUC** | €90–130 (night bus 22:30 or EN Lisinski night train) | LH/ANA nonstop HND, LH KIX | ~€180–220 |
| 7 | **VCE (+TRS)** | €45 (FlixBus direct to VCE airport) | EK, QR, TK, MU (PVG) | ~€80 |
| 8 | **Virtual origins** via positioning flight: MXP/BGY, FCO, WAW, IST, HEL, ARN, BRU, STN/LGW/LHR | actual positioning fare ×2 + transfers + buffer night | Where a Europe-wide sweep finds a much cheaper long-haul | > €100 over options 1–7 |

**Skip for long-haul** (positioning only): TSF, BTS, SJJ, TZL, BNX, ZAD, SPU, RJK, PUY, OSI, KLU, MBX, PRG.

Break-even rule: `(ground_return − 16) + hotel + €6 × extra ground hours (both ways)`. The €6/h is
a time-and-hassle allowance; ask the user if they value their time differently.

## 2. Getting to the airport on time (from Zagreb, public transport)
| Airport | Earliest same-day arrival | Flight departs before… | then |
|---|---|---|---|
| LJU | ~10:30 | ~12:30 | hotel night (+€60) or GoOpti |
| GRZ | ~05:15 (01:45 bus) | ~07:00 | fine |
| VIE | ~07:45 (01:45 bus) or 04:35 (23:30 bus) | ~09:45 | night bus, no hotel |
| BUD | 04:50 (Fri only, 23:59 bus) | ~07:00 Fri / evening other days | hotel (+€50) |
| BEG | ~05:00 (22:15 bus) | ~07:00 | night bus |
| MUC | ~07:45 (bus) / ~06:50 (night train) | ~09:30 | night bus/train |
| VCE | 23:55 the evening before (18:00 bus), or 13:45 | ~15:30 | evening bus + airport night |

FlixBus direct-to-airport runs vary by weekday, so **re-run `flixbus_ground.py` for the real dates**.
Car: only worth it for 2+ travelers (ZAG parking ~€193/14 days; VIE off-site from ~€119/14 days).

## 3. Positioning flights (low-cost legs to long-haul gateways)
Ryanair routes (verified 2026-10-04 via `https://www.ryanair.com/api/views/locate/searchWidget/routes/en/airport/<IATA>`):
- **ZAG** → BGY, BSL, BVA, CRL, DUB, EIN, **FCO**, FMM, MLA, NAP, NRN, **STN**, **WMI**
- **VIE** → **ARN, HEL, CPH, WAW**, ATH, BCN, BGY, BVA, CRL, DUB, EIN, FCO, MXP, STN, TSF, VCE…
- **BUD** → ARN, CPH, BGY, MXP, STN, BVA, CRL, PRG, WMI…
- **ZAD** (mostly summer) → ARN, HEL, CPH, VIE, BUD, MXP, STN…

Proven feeder → Japan pairings:
- ZAG–FCO → ITA FCO–HND
- ZAG–BGY → CA/NH ex-MXP
- ZAG–WMI → LOT WAW–NRT
- ZAG–STN → Chinese/Gulf carriers ex-London
- ZAG–CRL/BVA/EIN → Hainan/CA ex-BRU, AF ex-CDG, KL ex-AMS
- VIE/BUD–ARN → CA/NH ex-ARN (the €457 GDN–ARN–PEK–HND deal pattern)
- VIE/ZAD–HEL → Finnair
- ZAG–IST/SAW → TK/NH/OZ ex-IST

Separate-ticket rules (see `tricks.md`):
- ≥ 4–6 h buffer on the day, or a **buffer night** before the long-haul.
- Bags must be re-checked.
- Watch for airport changes (BGY→MXP, CRL→BRU, STN→LHR, WMI→WAW).
- Cabin-bag sizes differ (Ryanair free item 40×30×20 cm).

Wizz Air network not verified (its API needs a build token). Use Azair/Kiwi, which include Wizz.

## 4. Regional deal feeds (scanned by `scripts/deals.py`)
Best Japan signal:
- `fly4free.pl/tag/japonia/feed/` (Polish, regular Japan posts, also VIE/BUD/PRG origins)
- `travel-dealz.com/?s=Tokyo&feed=rss2` (VIE/MXP/BUD Chinese-carrier promos)
- `utazomajom.hu/?s=Tokió&feed=rss2` (BUD-origin Japan deals)

Manual only: Secret Flying (Cloudflare blocks scripts; it has Zagreb/Ljubljana/Budapest/Vienna/Belgrade origin pages); Croatian/Serbian Facebook "jeftini letovi" groups (need a login, so ask the user).
