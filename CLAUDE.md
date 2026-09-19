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
| `docs/data/latest.json` | Current snapshot, all corridors, each with its own `tier`, `generated`, and `rate_uncertain`/`rate_disagreement_pct` (known gap #5). |
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
5. **Reference-rate accuracy for thin currencies is a real, measured problem, not a
   hypothetical one.** 12 of 16 corridors (everything except INR, MXN, PHP, CNY) fall
   back to `er-api.com` because ECB/`frankfurter.app` doesn't publish them at all, and
   `er-api`'s free tier updates once per 24h. `mid_market()` now averages `er-api` with
   a second free daily mirror when frankfurter fails, and `collect.py` cross-checks the
   result against Wise's own self-declared mid-market quote (free — same API call,
   never used as the reference itself, since Wise is a ranked competitor). Measured
   disagreement against Wise: COP 1.79% → 0.90% after widening (looks like simple
   staleness — two independent sources now agree, fixed). NGN stayed at ~3.0%
   (averaging the two daily sources doesn't move it, because *both* agree with each
   other and disagree with Wise — this looks like a genuine dispute about which real
   NGN rate to use, not staleness, and isn't fixable with free sources). Everything
   else measured under 0.35%. Corridors over 1% disagreement are marked
   `"rate_uncertain": true` with `"rate_disagreement_pct"` in `latest.json`, and the
   frontend discloses this plainly rather than showing a confidently precise number.
   If you add a corridor via `discover.py`, check its disagreement before trusting it.

   **Diagnostic for a newly-flagged corridor**: compare `er-api` and the third source
   (`_currency_api`) to *each other*, not just each to Wise. If the two free sources
   agree with each other but both disagree with Wise (NGN: 0.15% apart from each
   other, ~3% apart from Wise) - widening sources won't help, because averaging two
   agreeing sources isn't a second opinion, it's the same opinion twice. That pattern
   is consistent with a real dual-rate market (official vs. parallel/market rate -
   Nigeria has a documented history of this; Egypt's 2022-2023 currency float is a
   plausible future candidate, though it currently measures under 0.1% and isn't
   flagged - don't treat this as a current problem, just a reason to keep watching
   it). If instead the two free sources disagree with *each other* too (COP: 1.73%
   apart), that looks like ordinary staleness/noise, and widening genuinely helps -
   confirmed: COP's Wise-disagreement dropped from 1.79% to 0.90% after averaging.

   Don't rewrite "our data sources disagree" into "dual-rate market" copy yet - that
   needs days of `rate_disagreement_pct` history (now recorded per-reading in
   `docs/data/history/*.json`, not just the current snapshot) showing the gap is
   *persistent* rather than a one-off fluctuation. If NGN's history shows a stable
   ~3% gap over time rather than noise, the frontend wording should change to name
   the likely cause instead of implying an unresolved data error.

## Do not

- Present this as financial advice, or add a "recommended provider" CTA. It reports a
  measurement; the user decides.
- Add affiliate or referral links. Referral money on the exact providers being ranked
  destroys the only thing this project has.
- Drop or smooth historical data points to make a chart look cleaner.
- Quietly widen scope claims in the README. If cash pickup is not covered, the README
  says so.
