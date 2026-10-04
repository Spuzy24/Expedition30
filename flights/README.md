# flights/: Japan cheapest-ticket toolkit

Start with the repo-root `CLAUDE.md` and the `/flight-hunt` skill (`.claude/skills/flight-hunt/SKILL.md`).

```
flights/
├── profile.md        traveler profile & trip brief (fill TBDs with the user)
├── playbook.md       the full search method
├── sources.md        every source: automated vs manual, blind spots, seller trust tiers
├── tools.md          script reference (commands, options, gotchas, troubleshooting)
├── tricks.md         money-saving techniques with evidence + risk ratings; myths; ITA codes
├── japan.md          Japan market cheat sheet (benchmarks, carriers, airports, seasons, entry)
├── origins.md        departure airports from home, ground costs, positioning routes
├── benchmarks.md     same-query cross-source test results
├── research/         dated deep-research snapshots (2026-10-04), fully sourced
├── scripts/          all tools (setup.sh, requirements*.txt)
└── searches/
    ├── ground.json   per-person round-trip ground cost to each departure airport
    ├── quotes.jsonl  price log (scripts/quotes.py)
    ├── _template/    copy for a new trip
    └── <trip-id>/    notes.md, report.md, caches for each hunt
```
