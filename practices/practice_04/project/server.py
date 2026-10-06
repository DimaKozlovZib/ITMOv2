import os
import io
import csv
import json
from flask import Flask, render_template, request, redirect, url_for, flash, Response


app = Flask(__name__)
# Simple secret key for flash messages; in production, set via env var
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")


# In-memory storage for reports; resets on server restart
REPORTS = []


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/report")
def submit_report():
    name = (request.form.get("name") or "").strip()
    group = (request.form.get("group") or "").strip()
    details = (request.form.get("details") or "").strip()
    vibe_level = (request.form.get("vibe_level") or "medium").strip()

    # Minimal validation
    errors = []
    if not name:
        errors.append("Укажите имя студента")
    if not details:
        errors.append("Опишите ситуацию")

    if errors:
        for e in errors:
            flash(e, "error")
        # repopulate fields via query string or simpler: rely on browser back
        return redirect(url_for("index"))

    REPORTS.append(
        {
            "name": name,
            "group": group,
            "details": details,
            "vibe_level": vibe_level,
        }
    )

    return redirect(url_for("thanks"))


@app.get("/thanks")
def thanks():
    return render_template("thanks.html")


@app.get("/reports")
def reports():
    """Render list of reports with optional filters via query params.

    Supported params (no state persisted):
    - vibe_level: any|low|medium|high (default: any)
    - group: substring filter for group field (case-insensitive)
    - q: substring search across name and details (case-insensitive)
    """
    # Read and normalize filters from query string
    vibe_level = (request.args.get("vibe_level") or "any").lower().strip()
    group_q = (request.args.get("group") or "").strip()
    q = (request.args.get("q") or "").strip()

    # Restrict vibe_level to allowed values; treat unknown as 'any'
    allowed_vibes = {"low", "medium", "high"}
    vibe_filter = vibe_level if vibe_level in allowed_vibes else "any"

    # Apply filters in-memory; original storage remains unchanged
    filtered = []
    for r in REPORTS:
        # Start optimistic; drop out on first mismatch
        keep = True

        if vibe_filter != "any":
            if (r.get("vibe_level") or "").lower() != vibe_filter:
                keep = False

        if keep and group_q:
            if group_q.lower() not in ((r.get("group") or "").lower()):
                keep = False

        if keep and q:
            name = (r.get("name") or "").lower()
            details = (r.get("details") or "").lower()
            if q.lower() not in name and q.lower() not in details:
                keep = False

        if keep:
            filtered.append(r)

    filters_applied = (vibe_filter != "any") or bool(group_q) or bool(q)

    return render_template(
        "reports.html",
        reports=filtered,
        filters={
            "vibe_level": vibe_filter,
            "group": group_q,
            "q": q,
            "applied": filters_applied,
        },
    )


@app.get("/reports/export")
def reports_export():
    """Export reports in CSV or JSON format.

    Query param: format=csv|json (default: csv)
    """
    fmt = (request.args.get("format") or "csv").lower()

    if fmt == "json":
        body = json.dumps(REPORTS, ensure_ascii=False)
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reports.json"},
        )

    if fmt == "csv":
        # Build CSV with header; include UTF-8 BOM for better Excel support on Windows
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow(["name", "group", "vibe_level", "details"])
        for r in REPORTS:
            writer.writerow([
                (r.get("name") or ""),
                (r.get("group") or ""),
                (r.get("vibe_level") or ""),
                (r.get("details") or ""),
            ])
        payload = buf.getvalue()
        bom = "\ufeff"  # Excel-friendly BOM
        return Response(
            bom + payload,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reports.csv"},
        )

    return Response("Unknown format", status=400)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
