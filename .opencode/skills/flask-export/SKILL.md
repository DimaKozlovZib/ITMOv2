---
name: flask-export
description: Use ONLY when adding CSV/JSON export endpoints to a Flask app (e.g., GET /reports/export?format=csv|json). Covers route design, proper Content-Type and Content-Disposition headers, CSV generation with newline handling and optional UTF-8 BOM for Excel, and JSON serialization.
---

# Flask CSV/JSON Export

Use when implementing downloadable exports from in-memory data (e.g., `REPORTS`). Keep the existing routes intact; add a dedicated export endpoint.

Key points
- Route: `GET /reports/export?format=csv|json`
- CSV headers: `text/csv; charset=utf-8`
- JSON headers: `application/json; charset=utf-8`
- Always set `Content-Disposition: attachment; filename=...`
- For CSV on Windows/Excel, consider a UTF-8 BOM prefix to ensure Cyrillic displays correctly
- For the Python CSV writer, use `newline=""` on the underlying text buffer to avoid blank lines

Minimal example

```python
import io, csv, json
from flask import Response, request

@app.get("/reports/export")
def export_reports():
    fmt = (request.args.get("format") or "csv").lower()

    if fmt == "json":
        body = json.dumps(REPORTS, ensure_ascii=False)
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reports.json"},
        )

    if fmt == "csv":
        buf = io.StringIO(newline="")  # avoids extra blank lines
        w = csv.writer(buf)
        w.writerow(["name", "group", "vibe_level", "details"])
        for r in REPORTS:
            w.writerow([
                r.get("name", ""),
                r.get("group", ""),
                r.get("vibe_level", ""),
                r.get("details", ""),
            ])
        payload = buf.getvalue()
        # Optional BOM for Excel compatibility
        bom = "\ufeff"
        return Response(
            bom + payload,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reports.csv"},
        )

    return Response("Unknown format", status=400)
```

Validation checklist
- 200 OK for csv/json; 400 for unknown format
- Correct `Content-Type` and `Content-Disposition`
- CSV first row is header; rows count matches `len(REPORTS)`
- JSON parses and matches dictionaries' keys
