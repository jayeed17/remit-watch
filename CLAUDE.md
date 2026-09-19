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
collect.yml (hourly cron, GitHub Actions)
  └─ scripts/collect.py
       ├─ scripts/remit.py → api.wise.com/v4/comparisons   (provider quotes)
       └─ scripts/remit.py → frankfurter.app, er-api.com   (mid-market rate)
            └─ writes docs/data/*.json → git commit → Pages redeploys
```

The git history **is** the time series. Every snapshot is a commit. Don't rewrite
history in `docs/data`, don't squash the bot's commits, don't add anything there to
`.gitignore`.

| Path | Role |
|---|---|
| `scripts/remit.py` | Fetch + normalize + rank. Also a standalone CLI. |
| `scripts/collect.py` | Loop corridors, write JSON, trim history to 720 points. |
| `docs/index.html` | The entire frontend. Single file, no build step. |
| `docs/data/latest.json` | Current snapshot, all corridors, all brackets. |
| `docs/data/history/SRC-DST.json` | Rolling 30 days, `lost_pct` per provider per hour. |
| `.github/workflows/collect.yml` | The cron. Needs repo write permission. |

## Constraints

- **Python: standard library only.** No requests, no pandas. The workflow installs
  nothing, and adding a dependency means adding an install step and a lockfile.
- **Frontend: no framework, no bundler, no npm.** Vanilla JS in `docs/index.html`.
  Google Fonts is the only external request. Keep it that way — the page must work on
  a slow phone.
- **No secrets.** Both APIs are keyless. If a provider ever needs a key, it goes in
  Actions secrets and never in `docs/`, because `docs/` is publicly served.
- **The JSON shape is a contract** between `collect.py` and `index.html`. Changing a
  field name means changing both, plus historical files already committed stay in the
  old shape — write a migration or read defensively.

## Commands

```bash
python scripts/remit.py USD BDT 500      # one corridor, printed table
python scripts/remit.py USD INR 500 --json
python scripts/collect.py                # all corridors → docs/data/
python -m http.server -d docs 8000       # serve the site locally
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
4. Fee tiers are sampled at $200 / $500 / $1000 and interpolated in between.

## Do not

- Present this as financial advice, or add a "recommended provider" CTA. It reports a
  measurement; the user decides.
- Add affiliate or referral links. Referral money on the exact providers being ranked
  destroys the only thing this project has.
- Drop or smooth historical data points to make a chart look cleaner.
- Quietly widen scope claims in the README. If cash pickup is not covered, the README
  says so.
