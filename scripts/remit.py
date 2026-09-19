"""remit.py - true all-in cost of a remittance, ranked.

    python remit.py USD INR 500
    python remit.py USD BDT 300 --save corridors.db

No API key needed. Wise's comparison endpoint is public.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

WISE = "https://api.wise.com/v4/comparisons/"
FX_SOURCES = [
    ("https://api.frankfurter.app/latest", lambda d, dst: d["rates"][dst]),
    ("https://open.er-api.com/v6/latest", lambda d, dst: d["rates"][dst]),
]


@dataclass
class Quote:
    provider: str
    kind: str
    rate: float
    fee: float
    received: float
    lost: float          # absolute $ worse than mid-market
    lost_pct: float      # fee + spread, the only number that matters
    collected: str | None


def _get(url: str, params: dict) -> dict | list:
    req = urllib.request.Request(
        f"{url}?{urllib.parse.urlencode(params)}",
        headers={"User-Agent": "remit-compare/0.1"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def mid_market(src: str, dst: str) -> float:
    """ECB first; falls back for corridors ECB doesn't cover (BDT, PKR...)."""
    errors = []
    for url, pick in FX_SOURCES:
        try:
            if "frankfurter" in url:
                return float(pick(_get(url, {"from": src, "to": dst}), dst))
            return float(pick(_get(f"{url}/{src}", {}), dst))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")
    raise RuntimeError("no mid-market rate: " + "; ".join(errors))


def compare(src: str, dst: str, amount: float, mid: float | None = None) -> list[Quote]:
    mid = mid or mid_market(src, dst)
    data = _get(WISE, {"sourceCurrency": src, "targetCurrency": dst, "sendAmount": amount})
    providers = data if isinstance(data, list) else data.get("providers", [])
    ideal = amount * mid

    best: dict[str, Quote] = {}
    for p in providers:
        name = p.get("name") or p.get("alias", "?")
        for q in p.get("quotes", []):
            rate = q.get("rate")
            if not rate:
                continue
            fee = float(q.get("fee") or 0)
            received = float(q.get("receivedAmount") or (amount - fee) * float(rate))
            lost = ideal - received
            quote = Quote(
                provider=name,
                kind=p.get("type", "?"),
                rate=float(rate),
                fee=fee,
                received=round(received, 2),
                lost=round(lost, 2),
                lost_pct=round(100 * lost / ideal, 2),
                collected=q.get("dateCollected"),
            )
            if name not in best or quote.lost < best[name].lost:
                best[name] = quote
    return sorted(best.values(), key=lambda q: q.lost)


def save(db: str, src: str, dst: str, amount: float, quotes: list[Quote]) -> None:
    """History is the moat - nobody publishes what a corridor cost last month."""
    con = sqlite3.connect(db)
    con.execute(
        """CREATE TABLE IF NOT EXISTS quotes (
            ts TEXT, src TEXT, dst TEXT, amount REAL, provider TEXT, kind TEXT,
            rate REAL, fee REAL, received REAL, lost REAL, lost_pct REAL,
            PRIMARY KEY (ts, src, dst, amount, provider))"""
    )
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.executemany(
        "INSERT OR REPLACE INTO quotes VALUES (:ts,:src,:dst,:amount,:provider,:kind,"
        ":rate,:fee,:received,:lost,:lost_pct)",
        [{"ts": ts, "src": src, "dst": dst, "amount": amount, **asdict(q)} for q in quotes],
    )
    con.commit()
    con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("amount", type=float)
    ap.add_argument("--save", metavar="DB")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    mid = mid_market(a.src.upper(), a.dst.upper())
    quotes = compare(a.src.upper(), a.dst.upper(), a.amount, mid)

    if a.save:
        save(a.save, a.src.upper(), a.dst.upper(), a.amount, quotes)
    if a.json:
        print(json.dumps([asdict(q) for q in quotes], indent=2))
        return

    print(f"\n{a.amount:,.0f} {a.src.upper()} -> {a.dst.upper()}  mid-market {mid:,.4f}\n")
    print(f"{'provider':<28}{'rate':>12}{'fee':>9}{'they get':>14}{'you lose':>11}{'':>8}")
    print("-" * 82)
    for q in quotes:
        print(
            f"{q.provider[:27]:<28}{q.rate:>12,.4f}{q.fee:>9,.2f}"
            f"{q.received:>14,.2f}{q.lost:>11,.2f}{q.lost_pct:>7.2f}%"
        )
    if len(quotes) > 1:
        gap = quotes[-1].lost - quotes[0].lost
        print(f"\ncheapest vs worst: {gap:,.2f} {a.src.upper()} on this one transfer")


if __name__ == "__main__":
    main()
