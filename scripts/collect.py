"""Collect quotes for every corridor and write JSON the static site reads.

Two tiers, run on different schedules (see .github/workflows/collect.yml and
collect-extended.yml):
  core     - the original 7 corridors, all 3 amount brackets, hourly.
  extended - newer, lower-volume corridors, 2 brackets, every 3 hours.

Each run only touches the corridors in the tier it was asked for - the other
tier's most recent entries in latest.json are preserved untouched. Every
corridor entry carries its own "generated" and "tier" fields, since core and
extended corridors are collected on different schedules and can be different
ages at any given moment; the site shows that, not just one global timestamp.

Writes:
  docs/data/latest.json              - current snapshot, all corridors
  docs/data/history/USD-BDT.json     - rolling 30 days of cost-to-send
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import asdict
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from remit import compare, mid_market, wise_mid_market  # noqa: E402

# Above this, disclose the reference rate as uncertain rather than show a
# confidently-precise number. Calibrated against real measurements: most
# corridors disagree with Wise's self-declared mid by well under 0.5%; COP
# and NGN were the only ones over 1% (see CLAUDE.md known gaps).
RATE_DISAGREEMENT_THRESHOLD = 1.0

CORE = [
    ("USD", "BDT", "Bangladesh"),
    ("USD", "INR", "India"),
    ("USD", "PKR", "Pakistan"),
    ("USD", "MXN", "Mexico"),
    ("USD", "PHP", "Philippines"),
    ("USD", "DOP", "Dominican Republic"),
    ("USD", "NPR", "Nepal"),
]

# Picked from scripts/discover.py's results. El Salvador was requested but
# dropped: it's officially dollarized (USD), so there's no separate currency
# to mark up, and Wise's USD->USD comparison returns exactly one quote
# (itself) - nothing to compare, so nothing worth shipping.
EXTENDED = [
    ("USD", "VND", "Vietnam"),
    ("USD", "GTQ", "Guatemala"),
    ("USD", "COP", "Colombia"),
    ("USD", "NGN", "Nigeria"),
    ("USD", "HNL", "Honduras"),
    ("USD", "EGP", "Egypt"),
    ("USD", "CNY", "China"),
    ("USD", "PEN", "Peru"),
    ("USD", "JMD", "Jamaica"),
]

# Brackets exist because fees are tiered - the site picks the nearest bracket
# and recomputes exactly from that bracket's rate + fee.
TIERS = {
    "core": {"corridors": CORE, "brackets": [200, 500, 1000]},
    "extended": {"corridors": EXTENDED, "brackets": [200, 500]},
}
MAX_POINTS = 720  # ~30 days hourly for core; extended fills in more slowly

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


def collect_tier(tier_name: str, ts: str, existing_by_dst: dict, failures: list) -> None:
    cfg = TIERS[tier_name]
    for src, dst, country in cfg["corridors"]:
        try:
            mid = mid_market(src, dst)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{src}-{dst} mid-market: {e}")
            continue

        # Free cross-check: compare our reference rate against Wise's own
        # self-declared mid-market quote (already fetched below, but this
        # needs its own call since compare() only returns provider quotes,
        # not Wise's mid). Never used as the reference itself - see
        # wise_mid_market()'s docstring for why.
        try:
            wise_mid = wise_mid_market(src, dst)
        except Exception:  # noqa: BLE001
            wise_mid = None
        disagreement = 100 * abs(wise_mid - mid) / wise_mid if wise_mid else None

        entry = {
            "src": src, "dst": dst, "country": country, "mid": mid,
            "tier": tier_name, "generated": ts,
            "rate_uncertain": bool(disagreement and disagreement > RATE_DISAGREEMENT_THRESHOLD),
            "rate_disagreement_pct": round(disagreement, 2) if disagreement is not None else None,
            "quotes": {},
        }
        for amount in cfg["brackets"]:
            try:
                quotes = compare(src, dst, amount, mid)
            except Exception as e:  # noqa: BLE001
                failures.append(f"{src}-{dst}@{amount}: {e}")
                continue
            entry["quotes"][str(amount)] = [asdict(q) for q in quotes]

        if not entry["quotes"]:
            continue
        existing_by_dst[dst] = entry

        # History tracks $500 - every tier collects it - one number per
        # provider per collection.
        rows = entry["quotes"].get("500") or next(iter(entry["quotes"].values()))
        path = DATA / "history" / f"{src}-{dst}.json"
        hist = load_json(path, [])
        hist.append(
            {
                "ts": ts,
                "mid": round(mid, 6),
                "rate_disagreement_pct": entry["rate_disagreement_pct"],
                "providers": {r["provider"]: r["lost_pct"] for r in rows},
            }
        )
        write_json(path, hist[-MAX_POINTS:])
        flag = f" [RATE UNCERTAIN: {disagreement:.2f}% disagreement]" if entry["rate_uncertain"] else ""
        print(f"{src}->{dst}: {len(rows)} providers, cheapest {rows[0]['provider']} "
              f"at {rows[0]['lost_pct']}%{flag}")


def main(tier: str) -> int:
    ts = datetime.now(timezone.utc).isoformat(timespec="minutes")
    tier_names = list(TIERS) if tier == "all" else [tier]

    # Load whatever's already there and only overwrite the corridors in the
    # tier(s) we were asked to run - the other tier's entries pass through
    # untouched, each keeping its own "generated" timestamp.
    existing = load_json(DATA / "latest.json", {})
    existing_by_dst = {c["dst"]: c for c in existing.get("corridors", [])}
    failures = []

    for name in tier_names:
        collect_tier(name, ts, existing_by_dst, failures)

    corridors = list(existing_by_dst.values())
    if not corridors:
        print("no corridors collected:", *failures, sep="\n  ", file=sys.stderr)
        return 1

    all_brackets = sorted({int(b) for c in corridors for b in c["quotes"]})
    snapshot = {"generated": ts, "brackets": all_brackets, "corridors": corridors, "failures": failures}
    write_json(DATA / "latest.json", snapshot)
    for f in failures:
        print("warn:", f, file=sys.stderr)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["core", "extended", "all"], default="all",
                     help="which corridors to collect (default: all, for manual runs)")
    args = ap.parse_args()
    raise SystemExit(main(args.tier))
