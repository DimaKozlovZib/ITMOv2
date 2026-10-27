---
name: http-smoke
description: Use when performing quick HTTP smoke checks against a local Flask app. Focus on verifying status codes, redirects, and headers for endpoints like /, /reports, /reports/export, without adding full test frameworks.
---

# HTTP Smoke Checks

Use to validate that endpoints respond as expected after adding small features.

Checklist
- GET / returns 200 and HTML contains the form
- POST /report with minimal data returns 302 -> /thanks
- GET /thanks returns 200
- GET /reports lists submitted data
- GET /reports/export?format=csv returns 200, `Content-Type` text/csv, `Content-Disposition` attachment
- GET /reports/export?format=json returns 200, `Content-Type` application/json
- Unknown format returns 400

Example using Python `requests`

```python
import requests

base = "http://127.0.0.1:5000"
r = requests.get(f"{base}/reports/export", params={"format": "csv"})
assert r.status_code == 200
assert r.headers["Content-Type"].startswith("text/csv")

r = requests.get(f"{base}/reports/export", params={"format": "json"})
assert r.status_code == 200
assert r.headers["Content-Type"].startswith("application/json")

r = requests.get(f"{base}/reports/export", params={"format": "pdf"})
assert r.status_code == 400
```
