# 09: How the review findings were resolved (2026-10-04)

Inputs:
- `07-docs-review.md` (docs audit: 3 P0, 18 P1, 20 P2)
- `08-scripts-qa.md` (script QA: 8 P0, 7 P1, 14 P2, plus 12 patches)
- `searches/dryrun-tyo-2027-05/skill-feedback.md` (end-to-end dry run: F1–F27)

All fixes were committed on branch `claude/nice-albattani-0rz6ea` the same day. A final integration run
(9–23 Jun 2027) passed: momondo, Kiwi origin-scan and MCP, Matrix `--carriers`, Google single-origin search and quotes. It found one new
server-side issue (Skiplagged round-trip prices missing), which is now handled.

## Status by theme
| Theme | Items | Resolution |
|---|---|---|
| Party size never passed / per-person vs total unclear | 07 P0-1, 08 B14, F-run | `--adults` everywhere in SKILL. Tested pp-vs-total table in `tools.md`. Headers say `EUR/pp` or `EUR total`. `mcp_flights --log` passes `--pax/--per total`. `positioning --adults`. `quotes --per total` requires `--pax` |
| Ground €0 for unknown origins; hotel halved; `hotel_if` ignored | 07 P0-2, 08 B4/B5, F21 | `quotes.py`: conservative default shown as `?`, hotel counted once, `hotel_if` warning, one-way rows get half ground, per-trip `ground.json` + `--ground-file`. BUD ground note corrected (no direct bus in May 2027) |
| Bag fees never added / Kiwi bag data | 07 P0-3, 08 B1/B6/B15, F6, F12, F13, F22 | `quotes.py` `0?` + `--need-bag`. `positioning --pos-bag-eur`. `kiwi_graphql` FARE€/KIWI-BAG€ columns, warning, `--fsc-bags-included`. MCP HOLD legend + "unknown" logging. Aviasales `EUR+BAG` and repeated summary. Docs: never rank on Kiwi bag prices; MU Basic caveat; Google LCC bag caveat |
| Hidden-city default on | 07 P1-1, F11 | `sk` hidden-city OFF by default (`--hidden-city` opt-in with warning) |
| Airport changes invisible | 07 P1-2 | `~` marker in kayak, kiwi_graphql, aviasales, booking (and sk); JSON `airport_change` |
| Return to another airport | 07 P1-3 | Documented (tools §4b, SKILL §6). Kiwi combined RT query finds cross-airport returns. `--return-to` logging |
| Open-jaw evidence and tooling | 07 P1-4, F17 | B2 conclusion corrected. `matrix.py --slice` now forces every slice (`--carriers`), per-slice `:ROUTE`. Test went €4,241 → €819. Japan-side backtrack via `--extras` |
| Overclaims (fact 4, B3, single ticket) | 07 P1-5, P1-15 | Reworded in CLAUDE.md and benchmarks. momondo `TICKET` column added |
| One-way vs RT ranking; return-direction commands | 07 P1-6, F18 | `quotes --rt-only/--ow-only`, OW ground. SKILL §5 return-direction commands. Sweep B with `--return-dates` |
| Recon calendars biased or contradictory | 07 P1-7, F5 | Kiwi RT calendar (`--nights`); Google one stay length; Matrix calendar with `--route`; `skcal` documented as return-flex only |
| Self-transfer thresholds contradicted | 07 P1-8, F3 | `profile.md`: 4–6 h or overnight, €100 (€150 Asian hub); user's own number wins (SKILL §1) |
| China entry for 2027 | 07 P1-9, F4 | Airside / 240 h / 30-day distinguished in all docs |
| Wizz "not queryable" | 07 P1-10 | Fixed in `origins.md` |
| Home not Zagreb / destination not Japan | 07 P1-11/12 | SKILL §1 recipes. `quotes ground-init --trip`. `deals.py --keywords/--region-words` |
| Monitor semantics / stop rule | 07 P1-13, F26 | Alerts fire once per crossing. Like-for-like rules. Commit before Routine. Routine prompt has a stop rule (≤ 14 days or BOOKED) |
| Manual checks incomplete | 07 P1-14, F23 | Google "Cheapest" tab + multi-city, ceair/airindia/flyscoot, trains, Japan-origin OTAs (tools §11) |
| Unofficial endpoints disclosure | 07 P1-16 | CLAUDE.md rule + SKILL §1 disclosure + guardrails |
| Japan-side costs | 07 P1-17 | tools §10 (`--extras` ~€80 backtrack, NRT vs HND) |
| `--log` mislabels | 07 P1-18, 08 B3 | Fixed in `mcp_flights.py` (destinations, carriers, self-transfer flag, party totals) |
| Kiwi multi-origin misses fares | F7, 08 B2 | `kiwi_graphql search` loops per origin (+ combined RT query); `origin-scan` RT is the main Kiwi sweep; MCP builds OW+OW (`tkt` column) |
| Per-carrier list too narrow | F8 | Broader list (AI, ET, TR, SQ, CX, HO…) + `--exclude-airlines` loop |
| momondo top-N collapses | F10 | `kayak.py --dedupe` (default with flex/multi-origin), `--pages`, all pages in JSON, multi-origin `--nearby` |
| Google hangs on 429 | F15 | `--max-wait` (60 s), exit 4 → stop Google for the session; insights only on single-origin searches (F14) |
| Matrix cost and pruning | F16, 08 B18/B27 | Default `--carriers MU,CA,QR` then add; dedupe of forced-carrier duplicates |
| Sweep cache reuse with different flags | 08 B8 | Cache signature includes all filters |
| setup.sh false "done" | 08 B10, F1 | apt-get update, fingerprint check, pip errors surfaced, Chromium smoke test, `--full` live checks |
| positioning one-way only, slow, time zones | F20, 08 B6/B7/B26 | `--return-dates` RT mode, `--compare-home-rt` skip rule, time-zone-correct Wizz arrival, route cache |
| Leads mixed with prices | F27 | `quotes add --lead` (hidden from default list, excluded from `best`) |
| Re-prices duplicate rows; extras hidden | F22 | `--latest`, `--supersedes`, `extra€` column |
| Misc (flightconnections ISO2 filter, fx unknown currency, deals undated/utm, booking bag sum, gflights grid filters, gflights_calendar flags) | 08 B11/B12/B13/B16–B22 | Patched (`patches/07`–`12`) |
| Subagent couldn't write report.md | F24 | SKILL §7: return the text to the caller if writes are blocked |
| Docs changed during a long run | F25 | CLAUDE.md: re-read the skill before reporting; don't commit another session's trip folder |

## Not done (deliberately), with reason
- **Kayak/Google multi-city search** (open-jaw): not implemented. Matrix `--slice` plus manual Google multi-city cover it.
- **Per-check row filters inside `monitor.py`:** replaced by the like-for-like check rules.
- **Google calendar/grid/explore per-person vs total:** unverified because of the 429 budget. Labelled "assumed total".
- **`_common.py` vs `fx.py` duplicate FX sources (08 B25):** low impact. Both use ECB-based rates.
- **Skiplagged round-trip prices missing (server-side, 2026-10-04 evening):** handled (`n/a` + warning); use one-way `sk` per direction.
