# Benchmarks: same query across all sources (evidence for the playbook's source order)

> Re-run a benchmark like this occasionally (inventories and site behaviour change). Append new
> runs with the date. Prices are 1 adult, economy, EUR, fetched live on the run date.

## B1 (2026-10-04): RT {ZAG,VIE,BUD} → {TYO,OSA}, out 12 May 2027, back 26 May 2027 (exact dates)

| Source (tool) | Cheapest | Bags | Itinerary / seller | Note |
|---|---|---|---|---|
| **momondo.de** (`kayak.py`) | **€686** | **2×23 kg** | MU BUD–PVG–KIX / **CZ** KIX–CAN–BUD, one ticket, seller **Opodo** | Mixed-carrier combo no other engine showed. Opodo = caution seller (check Prime/checkout price) |
| Aviasales (`aviasales.py`) | €706 / €718 | 0 (Kiwi) / 2 (Gotogate) | MU BUD–PVG–NRT RT | "cheapest_with_baggage" €718 |
| Booking.com Flights (`booking_flights.py`) | €741 | 2 | MU BUD–PVG–NRT RT | Etraveli inventory (high-risk seller tier) |
| Kiwi MCP (`mcp_flights.py kiwi`) | €748 | **reported 0 checked** (wrong: MU fare includes bags) | MU BUD–PVG–NRT RT | With `--bags 1` it jumped to €1,083 MU / €925 CA VIE–PEK–HND. **Kiwi's bag data for Chinese carriers is unreliable** |
| Skiplagged MCP | $855 (≈€762) | ? | MU/FM BUD–PVG–NRT RT | USD |
| Google Flights (`gflights.py search`) | €811 | (QR incl.) | QR BUD–DOH–HND | **No China Eastern/Air China in its list at all** |
| ITA Matrix (`matrix.py search`) | €1,083 | — | OZ BUD–ICN–NRT | **No MU, no CA, no QR.** Matrix lacks Chinese-carrier fares on this route |
| Kiwi GraphQL `search --checked-bags 1` | €1,135 | 1 | CA/MU out + TR back combos | Bag-pricing path gives odd results. Cross-check with the MCP |

**Conclusions (B1):**
0. Control check: `gflights.py search --from BUD --to TYO --date 2027-05-12 --return 2027-05-26 --via PVG,PEK,CAN` returned **0 itineraries**. Google Flights does not have these MU/CA/CZ fares at all; this isn't a script limit.
1. The floor (~€686–741 with bags) came from **Chinese carriers ex-BUD**, visible on momondo, Aviasales, Booking and Kiwi, but **invisible on Google Flights and ITA Matrix**. Never rely on Google/Matrix alone for Europe→Japan.
2. **momondo/Kayak found a cheaper mixed-carrier ticket** (MU out + CZ back) than any single-carrier RT. Always include `kayak.py`.
3. Bags: OTAs (Booking, Gotogate, Opodo) list 2 bags on MU; Kiwi said 0. **Verify bag allowance on the carrier's fare/OTA checkout**, not on Kiwi.
4. ZAG and VIE single tickets were never in the top results. BUD is the region's cheap origin for this trip (+€60–80 ground, see `origins.md`).

## B0 (2026-10-04): one-way probes, Jan–Mar 2027 (various agents)
| Query | Source | Cheapest | Construction |
|---|---|---|---|
| ZAG→TYO OW 20 Jan | Google Flights default list | €571 | LH/Condor/Etihad |
| ZAG→TYO OW 20 Jan | Kiwi MCP | €418 | JU ZAG–BEG–ARN + MU ARN–PVG–HND (self-transfer) |
| ZAG→TYO OW 20 Jan ±3 | Kiwi MCP | €373 | FR ZAG–CRL + bus + CA BRU–PEK–HND, no bags |
| ZAG→TYO OW 20 Jan | Skiplagged | $566 | OU ZAG–BRU + HO BRU–PVG–NRT (single ticket) |
| {ZAG,LJU,GRZ,VIE,BUD}→{TYO,OSA} OW 20 Jan ±3 | Kiwi MCP | €443 | MU BUD–PVG–NRT |
| ZAG nearby→TYO,OSA OW 10 Mar ±3 | Kayak.de | €356 | FR ZAG–CRL + HO BRU–PVG–KIX (Kiwi self-transfer) |
| home→hub + hub→Japan OW 5–12 Mar | `positioning.py` | €353–364 | FR/W6 → CRL + HO BRU–PVG–NRT €327 |
| Europe origins → TYO,OSA OW 5–12 Mar | `kiwi_graphql.py origin-scan` | BRU €327, IST €373, ZAG €385 (ST), MXP €388, VIE €403 | cheapest hub = **BRU** |
| same, 10–16 May | `origin-scan` | **IST €349** (IST–PKX–HND single ticket), VIE €362 (Scoot), BUD €443 (MU) | cheapest hub = **IST** (changes with dates!) |
| VIE/BUD/ZAG→TYO,OSA OW 12 May ±3 | momondo.de | €340 | Scoot VIE–SIN–KIX (no bags) |
| ZAG→TYO RT 10–24 Feb | Google Flights | €1,018 (VIE €688 KE, IST €788, MXP €867, MUC €874, BUD €908) | origin effect €230–330 |
| ZAG→TYO RT 10–24 Feb, 7 points of sale | Google Flights `gl`/`curr` | all within 0.5% | POS switching is a myth on GF |
| Air China ZAG→HND OW 20 Jan | Kiwi `--only-airlines CA` | €625 (incl. bag) | Hidden in Kiwi's unfiltered results |
| Air China ZAG↔TYO RT Jan/Feb | Kiwi `--only-airlines CA` | €1,524–1,879 | implausible: Kiwi stitching; check other sources |
