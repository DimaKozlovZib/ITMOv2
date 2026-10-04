import os
from flask import Flask, render_template, request, redirect, url_for, flash


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
    # Render a simple list of reports
    return render_template("reports.html", reports=REPORTS)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
