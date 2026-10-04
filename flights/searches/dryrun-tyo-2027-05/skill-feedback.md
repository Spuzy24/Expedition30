# Skill feedback: dry run `dryrun-tyo-2027-05` (2026-10-04, 18:16–19:05 UTC)

> Written by the dry-run test agent; saved by the orchestrator. Resolution status of each item is tracked in
> `flights/research/09-review-resolution.md`.

Query: ZAG, 1 adult, 1 checked bag, TYO or OSA, out 12 May 2027 ±3, about 14 nights, bus to VIE/BUD OK,
self-transfer only if it saves > €100, no hidden-city. Read SKILL.md and CLAUDE.md at commit 197d2ee.

## Friction log (in the order hit)

- **F1. Setup.** `setup.sh` took 4 s (the skill said about 1 min). Smoke tests cover only fx and the Kiwi/Skiplagged MCP servers, not gflights, matrix, kayak, aviasales, booking or flixbus. *Fix:* `setup.sh --full` with one tiny request per scraper; reword "5 s (cached) – 1 min".
- **F2. Intake blocks.** Nothing covers a request that already fixes origin/dates/pax/bags, or a run where nobody can be asked. *Fix:* start with profile defaults; list questions and assumptions at the top of notes.md and report.md; user-stated thresholds override profile defaults.
- **F3. Self-transfer thresholds contradicted each other** (€80 / €150 / €100 and 3 h vs 4–6 h). [fixed in profile.md] Also say: the user's own number wins.
- **F4. China entry for 2027 was unclear.** [fixed]
- **F5. Recon calendars mean different things.**
  - `kiwi_graphql.py calendar` is one-way (the skill doesn't pass `--return-dates`/`--nights`).
  - `gflights.py calendar --stay 12-16 --to TYO,OSA` takes about 10 requests (2 m 50 s, two 429s); the OSA cache is sparse.
  - `skcal` flexes only the return date, in USD (useless here).

  *Fix:* use one stay length on Google (`--stay N`), use the Kiwi calendar with `--nights`, and drop `skcal` from recon.
- **F6. Kiwi bag flags hide the cheapest fare. ← can miss the winner.** `kiwi_graphql.py search … --checked-bags 1` priced MU at **€1,051.89** vs **€717** without the flag, although OPODO, Gotogate and Booking all show 2×23 kg included. *Fix:* never use Kiwi bag flags; add bag cost per carrier instead. Use `gflights --bags N` for full-service carriers. kiwi_graphql should warn when `--checked-bags` is set.
- **F7. Kiwi multi-origin results are not a global price sort. ← missed the #2 option.** Air India VIE ⇄ HND €708 (1 PNR, 1 bag) was missing from the skill's MCP multi-origin line (€717 MU min), from `kiwi_graphql.py search --from ZAG@400` (€717), and from `--from VIE BUD` even with `--limit-api 250`. Only `origin-scan` and `--only-airlines AI` found it. *Fix:* make `origin-scan` (round trip) the main Kiwi sweep, and have `search` loop per origin.
- **F8. The per-carrier list misses AI (VIE €708), TR (Scoot VIE €675) and ET (ATH €588).** *Fix:* a broader list, or iterate `--exclude-airlines <top carrier>` until no new carrier appears (3 calls surfaced QR, TR and CA).
- **F9. Kiwi MCP column `bags(p/c/h)` is undocumented.** `1/1/0` means 0 checked. *Fix:* label it `pers/cabin/HOLD` with a legend.
- **F10. momondo top-N collapses to one fare.** With `--flex 3`, all 50 rows were the same MU fare on different dates; JSON holds only page 1; BAGS UNKNOWN for Kiwi/split rows; SKYPICKER is shown as `hacker=False`. *Fix:* `--dedupe` (on by default with `--flex`), `--pages 3`, and reconcile the SKYPICKER flag.
- **F11. Skiplagged.** The skill line omits `--no-hidden-city`. Prices are USD only. "One-stop" round trips are 2 one-way tickets (`#trip=A,B`). *Fix:* add the flag, convert to EUR, label "2×OW".
- **F12. Aviasales' `cheapest_with_baggage`** (716 vs 856 here) was the strongest bag evidence and gets cut off by `| tail`. *Fix:* mention it in the skill and repeat the line at the end of the output.
- **F13. Google bag pricing.** The skill's gflights line has no `--bags`. With `--bags 1`, Google priced Scoot at €675 while Aviasales/Kiwi show the bag isn't included. *Fix:* add `--bags 1` and note that Google's bag-inclusive price is unreliable for LCCs (Scoot, ZIPAIR).
- **F14. No "typical price" range.** `price_insights` was `{}` on multi-origin searches. *Fix:* document when it appears (single origin and destination) or rely on japan.md benchmarks.
- **F15. gflights hangs silently on 429:** 45/90/180 s back-off, up to 5¼ min per request, killed after 5+ min. *Fix:* `--max-wait`, fail fast by default, and "first 429 → stop Google for the session".
- **F16. Matrix `--carriers` cost:** about 40 s per carrier, so 8 carriers take over 5 min. CZ returned 0 even though OTAs sell MU/CZ. *Fix:* default to `MU,CA,QR` and add carriers seen elsewhere.
- **F17. Matrix open-jaw is broken. ← wrong-conclusion risk.** `--slice … --carriers MU` returned €4,241 because routing was applied to `slices[0]` only, so the return was priced on NH+TK. *Fix:* apply `--route-ret`/`--ext-ret` (or `--route`) to the later slices; support per-slice routing.
- **F18. Sweep B lines run one-way as written** (no `--return-dates`), so one-way hub fares are compared with round-trip home fares. *Fix:* add `--return-dates`; note per-city's limits.
- **F19. `gflights.py sweep --origins europe` is too heavy** (20–25 min, 60 calls) for a shared IP. *Fix:* make it optional.
- **F20. positioning.py was the slowest step** (8 min 19 s). It is one-way, positioning legs are fare-only with no bag, and it can't combine with a round-trip hub fare. A quick margin check showed it couldn't win: ATH €588 vs BUD €717 leaves €129, which positioning, bags and nights eat. *Fix:* `--return-dates`, `--pos-bag-eur`; skip positioning when (home RT − hub RT) < ~€150–200.
- **F21. Ground costs are wrong and under-counted. ← understates totals.**
  - `ground.json` says BUD is 5.3 h, but `flixbus_ground.py --date 2027-05-11/12` shows only 8.5–12 h transfers, with no direct bus.
  - A Budapest night is needed for a 12:30 flight.
  - `quotes.py` ignores `hotel_if`.

  *Fix:* run `flixbus_ground.py --date` per finalist, pass `--ground`/`--extras` explicitly, and warn when `hotel_if` exists. `flixbus_ground.py` returns city stops, not airports, and doesn't cover trains (the ZAG–BUD train exists).
- **F22. quotes.py misranks.** (a) Unknown bags count as €0, so a €627 split ranked #1. (b) There is no supersede, so the same itinerary shows at €744 and €804. (c) The extras column is hidden. *Fix:* flag `bags?`, add `list --latest` / supersede, show `extras€`.
- **F23. Manual URLs are hard to find** and are missing for ceair.com, airindia.com and flyscoot.com. *Fix:* link them from skill §7.
- **F24. The subagent harness blocked writing `report.md`.** *Fix:* "if file writes are blocked, return the report text to the caller".
- **F25. Docs and trip files changed during the run.** *Fix:* re-read SKILL.md before reporting in long sessions; don't commit another session's in-progress trip folder.
- **F26. monitor.py works** (17–19 s per check). But a Kiwi check with `--checked-bags 1` never saw MU, and the monitor takes the cheapest row regardless of bags or self-transfer. *Fix:* watch checks should use no Kiwi bag flags, `--no-self-transfer`, and one origin per check.
- **F27. No label for leads** (Matrix fare levels without availability). *Fix:* `--lead` / `--risk lead`, excluded from "best".

**Risks of missing the cheapest fare:** F6, F7, F8, F10, F17, F18. **Totals understated:** F21, F22.

## Best sources for this query
1. **momondo (`kayak.py`):** cheapest single ticket (OPODO €684 MU/CZ, bags shown, seller), plus the split fare.
2. **Kiwi GraphQL `origin-scan`:** the only sweep that found Air India VIE €708.
3. **Aviasales:** the `cheapest_with_baggage` signal.
4. **Matrix forced MU:** the airline-direct fare level (€715).
5. **Google Flights:** Scoot and the QR baseline; no Chinese carriers.

Low value here: deals.py, skcal, per-city, positioning.py (8 min, no winner), Matrix open-jaw (then broken).

## Time per step
| Step | Time |
|---|---|
| Setup | 4 s |
| Intake | 2 min |
| Recon | 4 min |
| Sweep A | 10 min |
| Sweep B | 12 min |
| Sweep C + seller + validation | 16 min (5 lost to a stuck Google call) |
| Monitor | 2 min |
| Write-up | 10 min |
