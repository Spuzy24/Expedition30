# CLAUDE.md: Japan flight hunt (branch `claude/nice-albattani-0rz6ea`)

## What this branch is for
Find the user (probably Sebastijan, per the earlier trip in this repo) the **absolute cheapest real, bookable flight ticket to Japan**: from
every airport reachable from home, to the Japanese airports the user names, across every useful
search engine, OTA, airline and trick, ranked by **true total cost** (fare + bags + ground/positioning
+ fees). Built and tested 2026-10-04.

> The PWA files at the repo root (`index.html`, `app.js`, `data.js`, `styles.css`, `service-worker.js`,
> `manifest.webmanifest`, `icons/`, `tickets/`, `progress.md`, `README.md`) belong to the earlier
> "Expedition 33" trip planner. **Don't touch them** unless the user asks.

## Start here
- Doing a hunt? Run the skill **`/flight-hunt`** (`.claude/skills/flight-hunt/SKILL.md`): the operational checklist.
- Fresh container? `bash flights/scripts/setup.sh` first (deps, Playwright pin, Chromium proxy CA, smoke tests).
- Then read, as needed:

| File | What |
|---|---|
| `flights/profile.md` | Traveler profile & trip brief (**many TBDs: ask the user**) |
| `flights/playbook.md` | Full method: recon → sweeps A/B/C → seller → validate → report → monitor |
| `flights/sources.md` | Every source: auto vs manual, strengths, blind spots, seller trust tiers |
| `flights/tools.md` | All scripts: commands, options, gotchas, "when things break" |
| `flights/tricks.md` | What saves money (evidence), myths, risky tricks (consent needed), ITA Matrix codes |
| `flights/japan.md` | Japan market: price benchmarks, carriers/routes 2026–27, airports, seasonality, entry/transit |
| `flights/origins.md` | Departure airports from Zagreb, ground costs, break-even rules, positioning routes |
| `flights/benchmarks.md` | Same-query cross-source tests: why the source order is what it is |
| `flights/research/*.md` | Dated deep-research snapshots (sourced, tagged verified/claimed) |
| `flights/searches/` | `quotes.jsonl` (price log), `ground.json` (ground costs), one folder per trip |

## Facts that change how to search (verified 2026-10-04)
1. **Google Flights doesn't carry the Chinese carriers** (China Eastern, Air China, China Southern) on Europe→Japan, and those are usually the cheapest. **ITA Matrix has them but prunes its default answer**, so force carriers (`matrix.py --carriers MU,CA,CZ,…` or `--route "MU+"`). Benchmark B1: momondo €686 / Matrix-forced-MU €715 vs Google €811 vs Matrix-default €1,083.
2. **momondo/Kayak (`kayak.py`), Kiwi (MCP + GraphQL), Aviasales, Booking.com and Skiplagged** each see different inventory. Use them all. momondo found a mixed MU+CZ combination nobody else showed (one ticket or two combined one-ways: not verified, so check at checkout).
3. **Origin beats tricks:** in the Google test (RT 10–24 Feb 2027) VIE was €230–330 below ZAG for the same dates, and one-way hub fares from BRU/IST undercut ZAG single tickets in the Kiwi origin-scans. The cheapest European hub changes with dates (Kiwi one-way origin-scan: BRU in Mar 2027, IST in May 2027; Google's RT sweep for Feb–Mar ranked ATH first). Price ground or positioning legs and compare totals.
4. **Engines hide carriers:** Kiwi showed Air China's new ZAG→OTP→PEK flight (since Sep 2026) only with `--only-airlines CA`. China Eastern (the cheapest carrier in B1/B3) is missing from Google Flights and from Matrix's default answer; in B3 it was also missing from both Kiwi answers and appeared only via Matrix `--route MU+` (momondo/Aviasales/Booking were not run in B3; in B1 they showed it). **Per-carrier passes are mandatory** and do not replace the OTA/meta sweep.
5. **Kiwi's bag data is wrong for Chinese carriers** (says 0 checked when the fare includes 2×23 kg). Verify bags via the OTA/airline.
6. **Switching Google Flights country/currency changes nothing** (7 markets within 0.5%). VPN/incognito are myths.
7. Return vs 2× one-way vs open-jaw: no fixed winner (one measured open-jaw was +28% on a Star Alliance fare; no clean Chinese-carrier measurement yet). Price all of them, and include Japan-side costs (Shinkansen backtrack vs open-jaw) in the comparison.
8. **Blocked to bots, so manual for the user:** Skyscanner, Trip.com, airline sites (Air China, Turkish, Qatar, LOT…), Secret Flying. Give exact URLs. Never bypass captchas.

## User context
- Home base **Zagreb, Croatia: ASSUMED** (the previous trip in this repo flew ZAG→BSL). Not yet confirmed.
- Japan airports, dates, travelers, bags, risk appetite: **not yet given**, see `flights/profile.md`.
  The earlier trip was for 2 travelers (Sebastijan & Mia), so ask whether this one is too (car/ground economics change at 2+).
- Croatian/EU passport assumed: Japan visa-free 90 d; Korea needs K-ETA to enter (not for airside transit). China: one-ticket airside transit needs no visa; 240-h visa-free transit covers landside self-transfers/stopovers en route to Japan; the 30-day visa-free entry runs to 31 Dec 2026 (renewal expected to be decided ~Nov 2026: re-check for 2027 travel).

## Rules
- **Never** book, pay, log in, create accounts, or enter personal/payment data. The user buys.
- **Never** state a price that wasn't fetched live in this session. Re-verify before reporting.
- Risky/ToS tricks (hidden-city, throwaway) only with the user's explicit opt-in. Self-transfer and positioning flights need the user's OK plus buffers.
- Respect sites: keep the scripts' pacing, run one search per site at a time, never rotate IPs/user agents or use proxies to get around a block, and on 429 / captcha / "verify you are human" / press-and-hold stop that source for the session (a JS challenge that a normal browser passes silently is the limit; anything interactive is manual-only). Several tools use sites' unofficial internal endpoints at low volume: say so once at intake, and if the user objects, use only the manual URLs plus the public MCP servers.
- Log every meaningful quote: `python3 flights/scripts/quotes.py add …`. Keep per-trip notes in `flights/searches/<trip>/notes.md`. Commit and push results (the container is ephemeral).
- When you learn something new (a route starts or ends, a tool breaks, a trick works or fails), **update the living docs** (`japan.md`, `tools.md`, `sources.md`, `tricks.md`, `benchmarks.md`) with a date.
- Living docs > research snapshots: if they disagree, trust the newer dated note and fix the other.

## Quick commands
```bash
S=flights/scripts
python3 $S/deals.py --days 60                                    # Japan sales / error fares
python3 $S/kayak.py --site www.momondo.de --from ZAG,VIE,BUD --to TYO,OSA --depart 2027-05-12 --return 2027-05-26
python3 $S/mcp_flights.py kiwi ZAG,LJU,GRZ,VIE,BUD TYO,OSA 2027-05-12 --flex 3 --ret 2027-05-26 --ret-flex 3
python3 $S/kiwi_graphql.py origin-scan --to TYO,OSA --dates 2027-05-10..2027-05-16 --origins ZAG,VIE,BUD,IST,BRU,MXP
python3 $S/positioning.py --home ZAG,VIE,BUD --hubs BRU,IST,MXP --to TYO,OSA --dates 2027-05-10..2027-05-16
python3 $S/gflights.py search --from ZAG,VIE,BUD --to TYO,OSA --date 2027-05-12 --return 2027-05-26
python3 $S/quotes.py list --trip <trip-id>
```
MCP servers `kiwi` and `skiplagged` are registered in `.mcp.json` (if they aren't loaded as tools,
`mcp_flights.py` calls the same endpoints).
