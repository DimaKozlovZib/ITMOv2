import os
import io
import csv
import json
import threading
from datetime import datetime, timezone
from urllib.parse import urlencode, parse_qsl

from flask import Flask, render_template, request, redirect, url_for, Response


app = Flask(__name__)
# Simple secret key; in production, set via env var
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")


@app.context_processor
def inject_ui_dicts():
    """Expose label/text dicts to templates (display only, no logic in templates)."""
    return {
        "ERROR_TEXTS": ERROR_TEXTS,
        "STATUS_LABELS": STATUS_LABELS,
        "VIBE_LABELS": VIBE_LABELS,
    }


# Contract constants (practices/practice_05/contract.md, «Единые определения»)
STATUSES = ("new", "confirmed", "rejected")
VIBES = ("low", "medium", "high")
DEFAULT_VIBE = "medium"
EXPORT_FORMATS = ("csv", "json")

# Whitelist for return_query on status change (contract, «Маршруты»)
RETURN_QUERY_WHITELIST = ("status", "vibe_level", "group", "q")

# UI texts mapped by code (contract, «Тексты для UI»). Used only for display.
ERROR_TEXTS = {
    "NAME_REQUIRED": "Укажите имя студента.",
    "DETAILS_REQUIRED": "Опишите ситуацию.",
    "NAME_LENGTH": "Имя студента: от 2 до 60 символов.",
    "GROUP_LENGTH": "Группа: не больше 20 символов.",
    "DETAILS_LENGTH": "Описание: от 10 до 1000 символов.",
    "VIBE_INVALID": "Выберите уровень из списка.",
    "DUPLICATE": "Такой донос уже отправлен. Измените данные и отправьте снова.",
    "INTERNAL_ERROR": "Не удалось отправить донос. Попробуйте ещё раз.",
}

# Status and vibe labels for display (contract: codes in logic, labels in UI)
STATUS_LABELS = {
    "new": "На рассмотрении",
    "confirmed": "Подтверждён",
    "rejected": "Отклонён",
}
VIBE_LABELS = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
}

# In-memory storage for reports; resets on server restart
REPORTS = []
_NEXT_ID = 1
# Guards creation and status change: duplicate check + insert must be atomic
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Model and helpers
# ---------------------------------------------------------------------------

def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_key(name: str, details: str) -> tuple:
    """Duplicate key: trim, collapse whitespace runs to one space, casefold."""
    def norm(s: str) -> str:
        return " ".join(s.split()).casefold()
    return (norm(name), norm(details))


def format_record(r: dict) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "group": r["group"],
        "details": r["details"],
        "vibe_level": r["vibe_level"],
        "status": r["status"],
        "created_at": r["created_at"],
    }


def wants_json() -> bool:
    """Representation choice by Accept header (contract, «Представления»)."""
    return "application/json" in request.headers.get("Accept", "")


def api_error(code: str, status: int, fields=None):
    body = {"error": {"code": code}}
    if fields is not None:
        body["error"]["fields"] = fields
    return Response(json.dumps(body, ensure_ascii=False), status=status,
                    mimetype="application/json; charset=utf-8")


def plain_error(message: str, status: int, title: str | None = None):
    """Browser error page: not_found.html for 404, error.html otherwise (contract screens 4-5)."""
    if status == 404:
        return render_template(
            "not_found.html",
            title=title or "Страница не найдена.",
            message=message,
        ), 404
    return render_template("error.html", title=title or message, message=message if title else None), status


# ---------------------------------------------------------------------------
# Validation (contract, «Поля форм и ограничения» и «Ошибки»)
# ---------------------------------------------------------------------------

def validate_report(form) -> tuple[dict, list[dict]]:
    """Return (cleaned_values, field_errors). Trims edges before checks."""
    name = (form.get("name") or "").strip()
    group = (form.get("group") or "").strip()
    details = (form.get("details") or "").strip()
    vibe = (form.get("vibe_level") or "").strip().lower() or DEFAULT_VIBE

    errors: list[dict] = []
    if not name:
        errors.append({"field": "name", "code": "NAME_REQUIRED"})
    elif not (2 <= len(name) <= 60):
        errors.append({"field": "name", "code": "NAME_LENGTH"})

    if len(group) > 20:
        errors.append({"field": "group", "code": "GROUP_LENGTH"})

    if not details:
        errors.append({"field": "details", "code": "DETAILS_REQUIRED"})
    elif not (10 <= len(details) <= 1000):
        errors.append({"field": "details", "code": "DETAILS_LENGTH"})

    if vibe not in VIBES:
        errors.append({"field": "vibe_level", "code": "VIBE_INVALID"})

    return {"name": name, "group": group, "details": details, "vibe_level": vibe}, errors


def create_report(values: dict):
    """Return (record, None) or (None, 'DUPLICATE'). Atomic under _LOCK."""
    global _NEXT_ID
    key = _normalize_key(values["name"], values["details"])
    with _LOCK:
        for r in REPORTS:
            if _normalize_key(r["name"], r["details"]) == key:
                return None, "DUPLICATE"
        record = {
            "id": _NEXT_ID,
            "name": values["name"],
            "group": values["group"],
            "details": values["details"],
            "vibe_level": values["vibe_level"],
            "status": "new",
            "created_at": _now_utc(),
        }
        _NEXT_ID += 1
        REPORTS.append(record)
    return record, None


def find_report(report_id: int):
    for r in REPORTS:
        if r["id"] == report_id:
            return r
    return None


# ---------------------------------------------------------------------------
# Filters and counters (contract, «Фильтры списка и счётчики»)
# ---------------------------------------------------------------------------

def parse_filters(args):
    """Return (filters, error_code). Missing/empty/'all'/'any' means no filter."""
    status = (args.get("status") or "").strip().lower()
    vibe = (args.get("vibe_level") or "").strip().lower()
    group = (args.get("group") or "").strip()
    q = (args.get("q") or "").strip()

    if status in ("", "all"):
        status = None
    elif status not in STATUSES:
        return None, "INVALID_STATUS"

    if vibe in ("", "any"):
        vibe = None
    elif vibe not in VIBES:
        return None, "VIBE_INVALID"

    return {"status": status, "vibe_level": vibe, "group": group, "q": q}, None


def apply_filters(records, f):
    out = []
    for r in records:
        if f["status"] and r["status"] != f["status"]:
            continue
        if f["vibe_level"] and r["vibe_level"] != f["vibe_level"]:
            continue
        if f["group"] and f["group"].lower() not in r["group"].lower():
            continue
        if f["q"]:
            needle = f["q"].lower()
            if needle not in r["name"].lower() and needle not in r["details"].lower():
                continue
        out.append(r)
    return out


def counts(all_records, shown_records) -> dict:
    by_status = {s: 0 for s in STATUSES}
    for r in all_records:
        by_status[r["status"]] += 1
    return {"total": len(all_records), "shown": len(shown_records), "by_status": by_status}


# ---------------------------------------------------------------------------
# Status change (contract, «Смена статуса и кнопки в UI»)
# ---------------------------------------------------------------------------

def change_status(report_id: int, target: str):
    """Return error code or None. Order: status value first, then existence."""
    if target not in STATUSES or target == "new":
        return "INVALID_STATUS"
    with _LOCK:
        r = find_report(report_id)
        if r is None:
            return "NOT_FOUND"
        # new -> confirmed|rejected; confirmed <-> rejected; same status = no-op success
        r["status"] = target
    return None


def safe_return_query(raw: str) -> dict:
    """Keep only whitelisted filter params from return_query (contract)."""
    params = dict(parse_qsl(raw or "", keep_blank_values=True))
    return {k: params[k] for k in RETURN_QUERY_WHITELIST if k in params}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return render_template("index.html")


@app.post("/report")
def submit_report():
    values, errors = validate_report(request.form)
    if errors:
        if wants_json():
            return api_error("VALIDATION_FAILED", 422, fields=errors)
        return render_template(
            "index.html",
            field_errors={e["field"]: e["code"] for e in errors},
            values=request.form,
            form_error=None,
        ), 422

    try:
        record, code = create_report(values)
    except Exception:  # unexpected failure: storage unchanged (contract: INTERNAL_ERROR, 500)
        app.logger.exception("create_report failed")
        if wants_json():
            return api_error("INTERNAL_ERROR", 500)
        return render_template(
            "index.html", field_errors={}, values=request.form, form_error="INTERNAL_ERROR"
        ), 500
    if code == "DUPLICATE":
        if wants_json():
            return api_error("DUPLICATE", 409)
        return render_template(
            "index.html", field_errors={}, values=request.form, form_error="DUPLICATE"
        ), 409

    # Contract: success is 302 -> /thanks?id={id} (no separate JSON success shape defined)
    return redirect(url_for("thanks", id=record["id"]), code=302)


@app.get("/thanks")
def thanks():
    raw = request.args.get("id")
    if raw is None:
        if wants_json():
            return Response(json.dumps({"id": None}), mimetype="application/json; charset=utf-8")
        return render_template("thanks.html", report_id=None)

    if not raw.isdigit() or int(raw) <= 0 or find_report(int(raw)) is None:
        if wants_json():
            return api_error("NOT_FOUND", 404)
        return plain_error("Запрошенный донос не найден.", 404, title="Донос не найден")

    report_id = int(raw)
    if wants_json():
        return Response(json.dumps({"id": report_id}), mimetype="application/json; charset=utf-8")
    return render_template("thanks.html", report_id=report_id)


@app.get("/reports")
def reports():
    filters, code = parse_filters(request.args)
    if code:
        if wants_json():
            return api_error(code, 400)
        return plain_error("Некорректный запрос.", 400, title="Некорректный запрос.")

    shown = apply_filters(REPORTS, filters)
    data = {
        "reports": [format_record(r) for r in shown],
        **counts(REPORTS, shown),
    }
    if wants_json():
        return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json; charset=utf-8")

    # HTML: keep the existing template context (reports, filters) and add counters
    return render_template(
        "reports.html",
        reports=shown,
        filters={
            "vibe_level": filters["vibe_level"] or "any",
            "group": filters["group"],
            "q": filters["q"],
            "status": filters["status"] or "all",
            "applied": bool(filters["status"] or filters["vibe_level"] or filters["group"] or filters["q"]),
        },
        total=data["total"],
        shown_count=data["shown"],
        by_status=data["by_status"],
        changed_id=request.args.get("changed_id"),
        changed_to=request.args.get("changed_to"),
    )


@app.get("/reports/<int:report_id>")
def report_one(report_id: int):
    r = find_report(report_id)
    if r is None:
        if wants_json():
            return api_error("NOT_FOUND", 404)
        return plain_error("Запрошенный донос не найден.", 404, title="Донос не найден")
    if wants_json():
        return Response(json.dumps(format_record(r), ensure_ascii=False),
                        mimetype="application/json; charset=utf-8")
    return Response(json.dumps(format_record(r), ensure_ascii=False),
                    mimetype="application/json; charset=utf-8")


@app.post("/reports/<int:report_id>/status")
def set_status(report_id: int):
    target = (request.form.get("status") or "").strip().lower()
    try:
        code = change_status(report_id, target)
    except Exception:  # unexpected failure: status unchanged (contract: INTERNAL_ERROR, 500)
        app.logger.exception("change_status failed")
        if wants_json():
            return api_error("INTERNAL_ERROR", 500)
        return plain_error("Не удалось изменить статус. Попробуйте ещё раз.", 500,
                           title="Не удалось изменить статус.")

    if code:
        if wants_json():
            return api_error(code, {"INVALID_STATUS": 400, "NOT_FOUND": 404}.get(code, 500))
        if code == "NOT_FOUND":
            return plain_error("Запрошенный донос не найден.", 404, title="Донос не найден")
        return plain_error("Некорректный запрос.", 400, title="Некорректный запрос.")

    # Contract: browser success is 303 -> /reports?changed_id&changed_to (+ whitelisted return_query).
    # API success body is not defined by the contract; return the updated record (200) as a stopgap.
    if wants_json():
        return Response(json.dumps(format_record(find_report(report_id)), ensure_ascii=False),
                        mimetype="application/json; charset=utf-8")
    extra = safe_return_query(request.form.get("return_query", ""))
    query = {"changed_id": report_id, "changed_to": target, **extra}
    return redirect("/reports?" + urlencode(query), code=303)


@app.get("/reports/export")
def reports_export():
    fmt = (request.args.get("format") or "csv").strip().lower()
    if fmt not in EXPORT_FORMATS:
        return api_error("INVALID_FORMAT", 400)

    filters, code = parse_filters(request.args)
    if code:
        return api_error(code, 400)

    records = apply_filters(REPORTS, filters)

    if fmt == "json":
        body = json.dumps([format_record(r) for r in records], ensure_ascii=False)
        return Response(
            body,
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=reports.json"},
        )

    # CSV: RFC 4180 via csv module; formula-injection guard; UTF-8 with BOM
    def guard(v):
        s = "" if v is None else str(v)
        return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s

    buf = io.StringIO(newline="")
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "group", "vibe_level", "status", "created_at", "details"])
    for r in records:
        writer.writerow([
            r["id"],
            guard(r["name"]),
            guard(r["group"]),
            r["vibe_level"],
            r["status"],
            r["created_at"],
            guard(r["details"]),
        ])
    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=reports.csv"},
    )


@app.errorhandler(404)
def not_found_any(_err):
    # Unknown path: plain 404 for API, page for browser (contract, «Маршруты»)
    if wants_json():
        return Response("", status=404)
    return plain_error("Страница не найдена.", 404, title="Страница не найдена.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="127.0.0.1", port=port, debug=True)
