"""
Quick smoke checks for Practice 4 (Flask app) including export feature.

Runs against Flask test_client so it doesn't require the dev server.
Exits with non-zero status on failure to be usable in git hooks/CI.
"""
from __future__ import annotations

import os
import sys
from typing import Any

# Ensure project root is on sys.path when running as `python scripts/...`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> int:
    try:
        # Import the app under test
        from practices.practice_04.project.server import app, REPORTS  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"ERROR: failed to import app: {e}")
        return 1

    client = app.test_client()

    # Start from a clean in-memory state
    try:
        REPORTS.clear()
    except Exception:
        pass

    def check(cond: bool, msg: str) -> None:
        if not cond:
            print(f"CHECK FAILED: {msg}")
            raise SystemExit(1)

    # GET /
    r = client.get("/")
    check(r.status_code == 200, f"GET / returned {r.status_code}")

    # POST /report (minimal valid payload)
    r = client.post(
        "/report",
        data={"name": "Test", "details": "Hello", "vibe_level": "medium", "group": ""},
        follow_redirects=False,
    )
    check(r.status_code in (302, 303), f"POST /report expected redirect, got {r.status_code}")
    loc = r.headers.get("Location", "")
    check(loc.endswith("/thanks"), f"POST /report Location header not /thanks: {loc!r}")

    # GET /thanks
    r = client.get("/thanks")
    check(r.status_code == 200, f"GET /thanks returned {r.status_code}")

    # GET /reports should include submitted item
    r = client.get("/reports")
    check(r.status_code == 200, f"GET /reports returned {r.status_code}")
    check(b"Test" in r.data, "Submitted report not listed on /reports")

    # Export CSV
    rcsv = client.get("/reports/export?format=csv")
    ct = rcsv.headers.get("Content-Type", "")
    cd = rcsv.headers.get("Content-Disposition", "")
    check(rcsv.status_code == 200, f"CSV export returned {rcsv.status_code}")
    check(ct.startswith("text/csv"), f"CSV Content-Type wrong: {ct!r}")
    check("attachment" in cd and "reports.csv" in cd, f"CSV Content-Disposition wrong: {cd!r}")
    # Remove BOM if present and verify header row exists
    csv_text = rcsv.data.decode("utf-8-sig")
    lines = csv_text.splitlines()
    check(len(lines) >= 2, "CSV should contain at least header and one row")
    check(lines[0] == "name,group,vibe_level,details", f"CSV header wrong: {lines[0]!r}")

    # Export JSON
    rjson = client.get("/reports/export?format=json")
    ctj = rjson.headers.get("Content-Type", "")
    cdj = rjson.headers.get("Content-Disposition", "")
    check(rjson.status_code == 200, f"JSON export returned {rjson.status_code}")
    check(ctj.startswith("application/json"), f"JSON Content-Type wrong: {ctj!r}")
    check("attachment" in cdj and "reports.json" in cdj, f"JSON Content-Disposition wrong: {cdj!r}")
    data: Any = rjson.get_json(silent=True)
    check(isinstance(data, list) and len(data) >= 1, "JSON payload should be a non-empty list")

    # Unknown format -> 400
    rbad = client.get("/reports/export?format=pdf")
    check(rbad.status_code == 400, f"Unknown format should return 400, got {rbad.status_code}")

    print("OK: practice_04 export smoke checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
