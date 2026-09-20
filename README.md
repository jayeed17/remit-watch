# remit-watch

**[jayeed17.github.io/remit-watch](https://jayeed17.github.io/remit-watch/)**

The real cost of sending money home: the transfer fee **plus** the exchange-rate
markup, compared across providers and tracked hourly.

Most comparison sites show you the advertised rate. The advertised rate is where the
money is actually taken. This measures every provider against the mid-market rate and
reports one number: the percentage of your money that never arrives.

16 corridors. No server, no database, no tracking, no affiliate links.

## What's here

| Page | For |
|---|---|
| [index](https://jayeed17.github.io/remit-watch/) | Pick a country and an amount, see who gets the most money there |
| [compare](https://jayeed17.github.io/remit-watch/compare.html) | Every corridor ranked by what it costs to send right now |

## Run it locally

```bash
git clone https://github.com/jayeed17/remit-watch && cd remit-watch
python scripts/remit.py USD BDT 500        # one corridor, printed
python scripts/collect.py --tier all       # every corridor, writes docs/data/
python -m http.server -d docs 8000         # open http://localhost:8000
```

No dependencies, no API keys, no build step. Python 3.10+.

## How it works

```
collect.yml         (hourly)      → collect.py --tier core
collect-extended.yml (every 3h)   → collect.py --tier extended
     └─ remit.py → api.wise.com/v4/comparisons       provider quotes
     └─ remit.py → frankfurter.app, er-api.com, …    mid-market reference
          └─ writes docs/data/*.json → git commit → Pages redeploys
```

The repo is the database. Every snapshot is a commit, so the price history is
version-controlled and anyone can audit where a number came from.

Corridors are split into two tiers. Core runs hourly at three amounts. Extended runs
every three hours at two. Each corridor carries its own timestamp, and both pages show
how old the numbers are.

| Path | Role |
|---|---|
| `scripts/remit.py` | Fetch, normalize, rank. Also a standalone CLI. |
| `scripts/collect.py` | Loop corridors by tier, write JSON, trim history. |
| `scripts/discover.py` | Manual: test which corridors have usable data before adding them. |
| `scripts/corridors_available.json` | discover.py's output: candidate corridors that passed both checks. |
| `scripts/incentives.json` | Hand-maintained receiving-country incentive schemes. |
| `docs/` | The site. Two pages, shared CSS and JS, no framework. |
| `docs/data/` | Generated snapshots and rolling 30-day history. |

## Things the site tells you that others don't

**When we're not sure.** If our reference rate sources disagree about a currency by
more than 1%, that corridor is flagged and the disagreement is shown. Nigeria currently
sits around 3%, and its two independent sources agree with each other. This points at
a real gap between the published rate and the rate providers actually transact at,
rather than a data fault.

**Receiving-country incentives.** Bangladesh pays a 2.5% government cash incentive on
wage earners' remittances sent through formal channels. It's shown as its own line,
never folded into what arrives. It comes from a different party, often lands days
later, and doesn't cover freelance or remote-work income.

**The US remittance tax.** Since January 2026 a 1% federal excise tax applies to
transfers funded with cash, money orders or cashier's checks. Bank and card funding are
exempt. Every quote here assumes bank funding, so the tax isn't in these numbers. The
site explains how to avoid paying it.

## Scope, honestly

- Quotes come from Wise's public comparison endpoint, which estimates competitor
  pricing from periodic scrapes. That's a single source, and it's a competitor to the
  providers it reports on.
- **Bank transfer in, bank transfer out only.** Cash pickup, which is how a large share
  of money actually moves on several of these corridors, is not covered yet.
- First-transfer promotional rates are not yet distinguished from standing rates.
- Sampled at fixed amounts and recomputed in between, so figures away from those
  amounts are close, not exact.
- Incentive data is hand-verified and dated. Policy changes without notice, so check
  the verification date.
- Nothing here is financial advice. It's a measurement, and the method is in the code.

## License

MIT
