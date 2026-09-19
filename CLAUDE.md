# CLAUDE.md

Context for Claude Code working in this repo.

## What this is

A static site that measures the true cost of a remittance — transfer fee **plus**
exchange-rate markup — across providers, and tracks it hourly. Audience is people
sending money home, not traders. Every number on the page must be traceable to a
collected quote.

The one metric that matters is `lost_pct`: the share of the sender's money that does
not arrive, measured against the mid-market rate. Never rank or headline by advertised
rate or by fee alone — that is exactly the distortion this project exists to correct.

## Architecture

There is no server and no database. Do not add either.

```
collect.yml (hourly cron, GitHub Actions)            --tier core
collect-extended.yml (every-3-hours cron)              --tier extended
  └─ scripts/collect.py
       ├─ scripts/remit.py → api.wise.com/v4/comparisons   (provider quotes)
       └─ scripts/remit.py → frankfurter.app, er-api.com   (mid-market rate)
            └─ merges into docs/data/*.json → git commit → Pages redeploys
```

Corridors are split into two tiers (both defined in `scripts/collect.py`):
`CORE` (the original corridors, all 3 amount brackets, collected hourly) and
`EXTENDED` (lower-volume corridors, 2 brackets, collected every 3 hours, to
keep the request count down). Each run only overwrites the corridors in the
tier it was asked for — the other tier's entries in `latest.json` pass through
untouched, each carrying its own `generated` timestamp, since core and
extended corridors are collected on different schedules and can be different
ages at any moment. The frontend shows that per-corridor freshness rather than
one global timestamp. `scripts/discover.py` is a separate, manually-run
research tool (not wired into either workflow) for checking whether a
candidate corridor has real coverage before it's added to `CORE`/`EXTENDED`.

The git history **is** the time series. Every snapshot is a commit. Don't rewrite
history in `docs/data`, don't squash the bot's commits, don't add anything there to
`.gitignore`.

| Path | Role |
|---|---|
| `scripts/remit.py` | Fetch + normalize + rank. Also a standalone CLI. |
| `scripts/collect.py` | Loop corridors for a tier, merge into JSON, trim history to 720 points. |
| `scripts/discover.py` | Manual research tool — checks candidate corridors before adding them. |
| `docs/index.html` | Single-corridor tool: pick a country, pick an amount, see who's cheapest. |
| `docs/compare.html` | Full sortable comparison across every tracked corridor. |
| `docs/style.css` | Shared stylesheet for both pages. |
| `docs/app.js` | Shared JS: formatters, flag SVGs, data loading. No build step — plain `<script src>`. |
| `docs/data/latest.json` | Current snapshot, all corridors, each with its own `tier` + `generated`. |
| `docs/data/history/SRC-DST.json` | Rolling 30 days, `lost_pct` per provider per hour. |
| `.github/workflows/collect.yml` | Hourly cron, `--tier core`. Needs repo write permission. |
| `.github/workflows/collect-extended.yml` | Every-3-hours cron, `--tier extended`. |

## Constraints

- **Python: standard library only.** No requests, no pandas. The workflow installs
  nothing, and adding a dependency means adding an install step and a lockfile.
- **Frontend: no framework, no bundler, no npm.** Vanilla JS across `docs/index.html`,
  `docs/compare.html`, and the shared `docs/style.css` / `docs/app.js` — plain
  `<link>`/`<script src>`, no module loader. Google Fonts is the only external
  request. Keep it that way — the pages must work on a slow phone. Paths between
  the two HTML files and the shared assets must stay relative — Pages serves this
  from `/remit-watch/`, not the domain root.
- **No secrets.** Both APIs are keyless. If a provider ever needs a key, it goes in
  Actions secrets and never in `docs/`, because `docs/` is publicly served.
- **The JSON shape is a contract** between `collect.py` and `index.html`. Changing a
  field name means changing both, plus historical files already committed stay in the
  old shape — write a migration or read defensively.

## Commands

```bash
python scripts/remit.py USD BDT 500      # one corridor, printed table
python scripts/remit.py USD INR 500 --json
python scripts/collect.py                # both tiers → docs/data/ (manual default)
python scripts/collect.py --tier core    # what collect.yml runs, hourly
python scripts/collect.py --tier extended  # what collect-extended.yml runs, every 3h
python scripts/discover.py               # check candidate corridors before adding them
python -m http.server -d docs 8000       # serve both pages locally
```

No test suite yet. If you add one, `unittest` from the stdlib, fixtures in
`tests/fixtures/*.json` — do not hit the network in tests.

## Conventions

- Upstream field names (`receivedAmount`, `dateCollected`) are read defensively with
  fallbacks. Wise has changed them before. Keep new parsing equally defensive.
- A corridor that fails collection is appended to `failures` and skipped. One dead
  corridor must never take down the snapshot for the rest.
- Money is formatted in the destination currency on the page, USD for what was lost.
- Copy is plain and sentence case. No ALL-CAPS labels, no hype. Errors say what broke
  and what to do about it.

## Known gaps — fix these before adding features

1. **Cash pickup is not covered.** Wise's endpoint estimates bank-transfer in and out
   only. Cash pickup is how much of this money actually moves on USD→BDT, PKR, MXN,
   PHP. Scraping Remitly / Ria / Western Union directly is the highest-value work here.
2. **Promo rates are not flagged.** First-transfer teaser rates are the growth engine
   for these apps and they distort the ranking. Detecting and labelling them matters
   more than any UI work.
3. **Single-source risk.** Every competitor quote currently comes from Wise, a
   competitor. This is disclosed in the README and must stay disclosed until there is
   a second independent source.
4. Fee tiers are sampled at $200 / $500 / $1000 for `CORE` corridors, $200 / $500
   only for `EXTENDED` — and interpolated in between. The site falls back to the
   nearest available bracket for an extended-tier corridor at $1000; it's an
   approximation, not a missing feature.

## Do not

- Present this as financial advice, or add a "recommended provider" CTA. It reports a
  measurement; the user decides.
- Add affiliate or referral links. Referral money on the exact providers being ranked
  destroys the only thing this project has.
- Drop or smooth historical data points to make a chart look cleaner.
- Quietly widen scope claims in the README. If cash pickup is not covered, the README
  says so.
