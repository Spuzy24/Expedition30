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
| ITA Matrix default (`matrix.py search`) | €1,083 | — | OZ BUD–ICN–NRT | Default answer is a **pruned subset** (4–5 carriers): no MU/CA/QR shown |
| **ITA Matrix forced `--route "MU+" --route-ret "MU+"`** | **€715** (seats confirmed) / €686 (`--no-avail`) | (MU fare incl. bags) | MU602/MU523 BUD–PVG–NRT RT | **Matrix DOES have MU.** Force carriers (`--carriers MU,CA,CZ,…`) or you miss the cheapest |
| Kiwi GraphQL `search --checked-bags 1` | €1,135 | 1 | CA/MU out + TR back combos | Bag-pricing path gives odd results. Cross-check with the MCP |

**Conclusions (B1):**
0. Control checks: `gflights.py search --from BUD --to TYO … --via PVG,PEK,CAN` (RT) and `--via PVG` (OW) returned **0 itineraries**, while `--via IST` returned TK normally. So **Google Flights does not carry these MU/CA/CZ fares at all**; it's a real gap, not a script limit. ITA Matrix does have them, but only shows them when forced with routing codes (default answers are pruned).
1. The floor (~€686–741 with bags) came from **Chinese carriers ex-BUD**, visible on momondo, Aviasales, Booking, Kiwi and carrier-forced Matrix, but **invisible on Google Flights** and in Matrix's default answer. Never rely on Google alone; always run Matrix with `--carriers`.
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

## B2 (2026-10-04): open-jaw premium (in TYO, out OSA) vs plain return, out 12 May / back 26 May 2027
| Source | Plain RT | Open-jaw | Premium |
|---|---|---|---|
| ITA Matrix VIE (`--slice VIE:TYO:… --slice OSA:VIE:…`) | €1,151 (NH/OS nonstop) | €1,475 (NH out, LH via MUC back) | **+€324 (+28%)** |
| momondo BUD (MU out / CZ back) | €688 (NRT/HND both ways) | €686 (out PVG–KIX, back KIX–CAN) | ≈ 0 |
| Kiwi MCP ZAG, Air China only (Jan/Feb) | €1,881 (HND/HND) | €1,879 (HND in / KIX out) | ≈ 0 |

**Conclusion:** the "open-jaw ≈ return" rule from blogs holds for Chinese carriers (and Kiwi/momondo
mix TYO/OSA automatically when the destination list is `TYO,OSA`), but NOT always for European/Star
Alliance fares. **Always price it explicitly**, never assume.
