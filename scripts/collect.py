"""Collect quotes for every corridor and write JSON the static site reads.

Run hourly by .github/workflows/collect.yml. Writes:
  docs/data/latest.json              - current snapshot, all corridors
  docs/data/history/USD-BDT.json     - rolling 30 days of cost-to-send
"""
from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import asdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from remit import compare, mid_market  # noqa: E402

# Add corridors here. Brackets exist because fees are tiered - the site picks
# the nearest bracket and recomputes exactly from that bracket's rate + fee.
CORRIDORS = [
    ("USD", "BDT", "Bangladesh"),
    ("USD", "INR", "India"),
    ("USD", "PKR", "Pakistan"),
    ("USD", "MXN", "Mexico"),
    ("USD", "PHP", "Philippines"),
    ("USD", "DOP", "Dominican Republic"),
]
BRACKETS = [200, 500, 1000]
MAX_POINTS = 720  # ~30 days hourly

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"


def write_json(path: pathlib.Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), sort_keys=False))


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def main() -> int:
    ts = datetime.now(timezone.utc).isoformat(timespec="minutes")
    snapshot = {"generated": ts, "brackets": BRACKETS, "corridors": []}
    failures = []

    for src, dst, country in CORRIDORS:
        try:
            mid = mid_market(src, dst)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{src}-{dst} mid-market: {e}")
            continue

        entry = {"src": src, "dst": dst, "country": country, "mid": mid, "quotes": {}}
        for amount in BRACKETS:
            try:
                quotes = compare(src, dst, amount, mid)
            except Exception as e:  # noqa: BLE001
                failures.append(f"{src}-{dst}@{amount}: {e}")
                continue
            entry["quotes"][str(amount)] = [asdict(q) for q in quotes]

        if not entry["quotes"]:
            continue
        snapshot["corridors"].append(entry)

        # History tracks the mid bracket only - one number per provider per hour.
        mid_bracket = str(BRACKETS[len(BRACKETS) // 2])
        rows = entry["quotes"].get(mid_bracket) or next(iter(entry["quotes"].values()))
        path = DATA / "history" / f"{src}-{dst}.json"
        hist = load_json(path, [])
        hist.append(
            {
                "ts": ts,
                "mid": round(mid, 6),
                "providers": {r["provider"]: r["lost_pct"] for r in rows},
            }
        )
        write_json(path, hist[-MAX_POINTS:])
        print(f"{src}->{dst}: {len(rows)} providers, cheapest {rows[0]['provider']} "
              f"at {rows[0]['lost_pct']}%")

    if not snapshot["corridors"]:
        print("no corridors collected:", *failures, sep="\n  ", file=sys.stderr)
        return 1

    snapshot["failures"] = failures
    write_json(DATA / "latest.json", snapshot)
    for f in failures:
        print("warn:", f, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
