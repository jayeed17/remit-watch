"""discover.py - check which USD->X corridors have real coverage before adding them.

Run manually:
    python scripts/discover.py

For each candidate destination currency, checks:
  1. does a mid-market rate exist (frankfurter.app, falling back to er-api.com)
  2. does Wise's comparison endpoint return at least 2 providers at $500

Prints a table sorted by provider count, then writes the corridors that passed
both checks to scripts/corridors_available.json, also sorted by provider count.

This is a one-off research tool, not wired into the hourly workflow. Nothing
here touches docs/data or CORRIDORS in collect.py - it only reports what's
available so a human can pick what to add.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from remit import compare, mid_market  # noqa: E402

# (currency, country). A couple of these are officially dollarized economies
# (El Salvador, Ecuador use USD) - included anyway so the table shows *why*
# they fail rather than silently omitting them.
CANDIDATES = [
    ("INR", "India"),
    ("MXN", "Mexico"),
    ("PHP", "Philippines"),
    ("PKR", "Pakistan"),
    ("BDT", "Bangladesh"),
    ("NGN", "Nigeria"),
    ("EGP", "Egypt"),
    ("GTQ", "Guatemala"),
    ("VND", "Vietnam"),
    ("NPR", "Nepal"),
    ("DOP", "Dominican Republic"),
    ("HNL", "Honduras"),
    ("SVC", "El Salvador"),      # dollarized (USD) - expect no separate mid-market rate
    ("COP", "Colombia"),
    ("GHS", "Ghana"),
    ("KES", "Kenya"),
    ("MAD", "Morocco"),
    ("LKR", "Sri Lanka"),
    ("JMD", "Jamaica"),
    ("HTG", "Haiti"),
    ("PEN", "Peru"),
    ("USD", "Ecuador"),          # dollarized (USD) - same corridor as source, expect a fail
    ("BRL", "Brazil"),
    ("IDR", "Indonesia"),
    ("THB", "Thailand"),
    # a few more large remittance corridors worth checking:
    ("CNY", "China"),
    ("NIO", "Nicaragua"),
    ("UAH", "Ukraine"),
    ("PLN", "Poland"),
    ("ETB", "Ethiopia"),
]

SLEEP_AFTER_FX = 1.0
SLEEP_AFTER_WISE = 1.5

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(__file__).resolve().parent / "corridors_available.json"


def check(dst: str, country: str) -> dict:
    row = {"dst": dst, "country": country, "mid_market": None, "providers": 0, "passed": False, "note": ""}

    try:
        row["mid_market"] = mid_market("USD", dst)
    except Exception as e:  # noqa: BLE001
        row["note"] = f"no mid-market rate: {e}"
        return row
    time.sleep(SLEEP_AFTER_FX)

    try:
        quotes = compare("USD", dst, 500, row["mid_market"])
        row["providers"] = len(quotes)
        if row["providers"] < 2:
            row["note"] = "fewer than 2 providers at $500"
        else:
            row["passed"] = True
    except Exception as e:  # noqa: BLE001
        row["note"] = f"Wise comparison failed: {e}"
    time.sleep(SLEEP_AFTER_WISE)

    return row


def main() -> int:
    results = []
    for dst, country in CANDIDATES:
        print(f"checking {country} ({dst})...", file=sys.stderr)
        results.append(check(dst, country))

    results.sort(key=lambda r: r["providers"], reverse=True)

    name_w = max(len(r["country"]) for r in results) + 1
    print(f"\n{'country':<{name_w}}{'currency':<9}{'providers':>10}{'mid-market':>13}   note")
    print("-" * (name_w + 9 + 10 + 13 + 3 + 40))
    for r in results:
        mid = f"{r['mid_market']:.4g}" if r["mid_market"] is not None else "-"
        status = "ok" if r["passed"] else r["note"]
        print(f"{r['country']:<{name_w}}{r['dst']:<9}{r['providers']:>10}{mid:>13}   {status}")

    passed = [r for r in results if r["passed"]]
    passed_sorted = sorted(passed, key=lambda r: r["providers"], reverse=True)
    OUT.write_text(json.dumps(
        [{"dst": r["dst"], "country": r["country"], "providers": r["providers"], "mid_market": r["mid_market"]}
         for r in passed_sorted],
        indent=2,
    ))

    print(f"\n{len(passed)} of {len(results)} candidates passed both checks.")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
