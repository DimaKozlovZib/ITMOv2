"""Compute median speed metrics for A/B runs.

Reads results/A_s42_r*.json and B_s42_r*.json, computes medians for
wall_seconds and decode_tokens_per_second, writes results/speed_summary.json,
and prints a short human-readable summary.
"""
from __future__ import annotations

import json
import statistics as S
from glob import glob
from pathlib import Path


def collect(paths: list[str]):
    walls = []
    dps = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        walls.append(d.get("wall_seconds"))
        dps.append(d.get("decode_tokens_per_second"))
    return {
        "count": len(paths),
        "median_wall": float(S.median(walls)) if walls else None,
        "median_decode_tps": float(S.median(dps)) if dps else None,
        "files": paths,
    }


def main() -> None:
    base = Path(__file__).resolve().parent / "results"
    a_paths = sorted(glob(str(base / "A_s42_r*.json")))
    b_paths = sorted(glob(str(base / "B_s42_r*.json")))
    summary = {"A": collect(a_paths), "B": collect(b_paths)}
    out_path = base / "speed_summary.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Saved:", out_path)
    for k in ("A", "B"):
        m = summary[k]
        print(
            f"{k}: n={m['count']} median wall={m['median_wall']:.3f}s, "
            f"median decode={m['median_decode_tps']:.3f} tok/s"
        )


if __name__ == "__main__":
    main()
