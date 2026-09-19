# remit-watch

The real cost of sending money home — the transfer fee **plus** the exchange-rate
markup, compared across providers and tracked hourly.

Most comparison sites show you the advertised rate. The advertised rate is where the
money is actually taken. This measures every provider against the mid-market rate and
reports one number: the percentage of your money that never arrives.

## Run it locally

```bash
git clone https://github.com/USER/remit-watch && cd remit-watch
python scripts/remit.py USD BDT 500        # one corridor, printed
python scripts/collect.py                   # all corridors, writes docs/data/
python -m http.server -d docs 8000          # open http://localhost:8000
```

No dependencies, no API keys. Python 3.10+.

## Publish it

1. Push to GitHub.
2. **Settings → Pages →** Source `Deploy from a branch`, branch `main`, folder `/docs`.
3. **Settings → Actions → General →** Workflow permissions: `Read and write`.
4. **Actions → collect → Run workflow** once to seed `docs/data`.

Live at `https://USER.github.io/remit-watch`. The hourly job commits each new snapshot,
so the chart fills itself in.

## How it works

```
collect.yml (hourly cron)
   └─ collect.py
        ├─ remit.py → api.wise.com/v4/comparisons   (multi-provider quotes)
        └─ remit.py → frankfurter.app / er-api.com  (mid-market rate)
             └─ writes docs/data/*.json → git commit → Pages redeploys
```

The repo is the database. Every snapshot is a commit, so the price history is
version-controlled and anyone can audit where a number came from.

## Scope, honestly

- Quotes come from Wise's public comparison endpoint, which estimates competitor pricing
  from hourly scrapes and covers **bank transfer in, bank transfer out only**.
- Cash pickup — how a large share of money actually moves on these corridors — is not
  covered yet. Scraping Remitly / Ria / Western Union directly is the next step.
- First-transfer promo rates are not yet distinguished from standing rates.
- Sampled at $200 / $500 / $1000. Other amounts are recomputed from the nearest sample,
  so they are close but not exact where fee tiers change.
- Nothing here is financial advice. It is a measurement, and the method is in the code.

## License

MIT
