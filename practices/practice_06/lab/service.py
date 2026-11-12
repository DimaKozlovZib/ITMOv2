"""Deliberately vulnerable local shop. All identities and data are synthetic."""

import argparse
import json
import html
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from sandbox import Sandbox


class Shop:
    def __init__(self):
        self.sandbox = Sandbox()
        self.lock = threading.RLock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE profiles(id INTEGER PRIMARY KEY, name TEXT, email TEXT, address TEXT);
            INSERT INTO profiles VALUES
                (1, 'TEST_ALICE', 'alice@example.invalid', 'TEST_ADDRESS_A'),
                (2, 'TEST_BOB', 'bob@example.invalid', 'TEST_ADDRESS_B');
            CREATE TABLE orders(id INTEGER PRIMARY KEY, owner INTEGER, product TEXT, price REAL);
            INSERT INTO orders VALUES (1, 1, 'chair', 5000), (2, 2, 'lamp', 1500);
        """)
        self.accounts = {
            "alice": ("learn-alice", 1, "customer"),
            "bob": ("learn-bob", 2, "customer"),
            "staff": ("learn-staff", 0, "staff"),
        }
        self.sessions = {}
        self.products = {"chair": 5000, "lamp": 1500}
        self.reviews = []
        self.logs = []
        # Map user id to login name for file access logic
        self.usernames_by_id = {info[1]: name for name, info in self.accounts.items()}

    def rows(self, query):
        return [dict(row) for row in self.db.execute(query)]

    def rows_params(self, query, params):
        return [dict(row) for row in self.db.execute(query, params)]

    def get_session(self, headers):
        token = headers.get("X-Token")
        return self.sessions.get(token)

    def is_staff(self, session):
        return bool(session and session.get("role") == "staff")

    def sanitize_logs(self):
        def mask(value):
            try:
                s = str(value)
            except Exception:
                return "***"
            if len(s) <= 4:
                return "***"
            return "***" + s[-4:]

        redacted = []
        for entry in self.logs:
            # Shallow copy and redact sensitive fields
            e = {k: (entry[k].copy() if isinstance(entry[k], dict) else entry[k]) for k in entry}
            headers = e.get("headers", {})
            for key in list(headers.keys()):
                if key.lower() in ("x-token", "authorization"):
                    headers[key] = mask(headers[key])
            body = e.get("body")
            if isinstance(body, dict):
                for key in list(body.keys()):
                    if key.lower() in ("password", "token"):
                        body[key] = "***"
            redacted.append(e)
        return redacted

    def dispatch(self, method, target, body, headers):
        url = urlsplit(target)
        query = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
        self.logs.append({"method": method, "target": target, "body": body, "headers": dict(headers)})
        if method == "GET" and url.path == "/health":
            return 200, {"status": "ok"}
        if method == "GET" and url.path == "/products":
            return 200, self.products
        if method == "POST" and url.path == "/login":
            account = self.accounts.get(body.get("username"))
            if not account or body.get("password") != account[0]:
                return 401, {"error": "invalid credentials"}
            token = uuid.uuid4().hex
            self.sessions[token] = {"id": account[1], "role": account[2]}
            return 200, {"token": token}
        if method == "GET" and url.path == "/profile":
            session = self.get_session(headers)
            if not session:
                return 401, {"error": "login required"}
            if self.is_staff(session) and "id" in query:
                try:
                    pid = int(query.get("id"))
                except Exception:
                    return 400, {"error": "invalid id"}
                rows = self.rows_params("SELECT * FROM profiles WHERE id = ?", (pid,))
            else:
                rows = self.rows_params("SELECT * FROM profiles WHERE id = ?", (session["id"],))
            return 200, rows
        if method == "GET" and url.path == "/search":
            q = query.get("q", "")
            return 200, self.rows_params("SELECT * FROM profiles WHERE name LIKE ?", (f"%{q}%",))
        if method == "GET" and url.path == "/orders":
            session = self.get_session(headers)
            if not session:
                return 401, {"error": "login required"}
            if self.is_staff(session):
                return 200, self.rows("SELECT * FROM orders")
            return 200, self.rows_params("SELECT * FROM orders WHERE owner = ?", (session["id"],))
        if method == "POST" and url.path == "/orders":
            session = self.sessions.get(headers.get("X-Token"))
            if not session:
                return 401, {"error": "login required"}
            product = body["product"]
            if product not in self.products:
                return 400, {"error": "unknown product"}
            price = self.products[product]
            cursor = self.db.execute("INSERT INTO orders(owner, product, price) VALUES (?, ?, ?)",
                                     (session["id"], product, price))
            self.db.commit()
            return 201, {"id": cursor.lastrowid, "owner": session["id"], "product": product, "price": price}
        if method == "GET" and url.path == "/admin/export":
            session = self.get_session(headers)
            if not self.is_staff(session):
                return 403, {"error": "staff only"}
            return 200, self.rows("SELECT * FROM profiles")
        if method == "GET" and url.path == "/files":
            session = self.get_session(headers)
            if not session:
                return 401, {"error": "login required"}
            requested_path = query.get("path", "receipt.txt")
            # Prevent traversal within logical boundary
            if ".." in requested_path:
                return 403, {"error": "path not allowed"}
            if self.is_staff(session):
                # Staff may read service notes; other files allowed per request
                if requested_path.startswith("private/"):
                    try:
                        return 200, {"content": self.sandbox.read(requested_path)}
                    except Exception as exc:
                        return 404, {"error": str(exc), "type": type(exc).__name__}
                user = query.get("user")
                if not user:
                    return 400, {"error": "user required for staff"}
                name = f"files/{user}/{requested_path}"
                try:
                    return 200, {"content": self.sandbox.read(name)}
                except Exception as exc:
                    return 404, {"error": str(exc), "type": type(exc).__name__}
            # Customers: only own files under files/<username>/
            username = self.usernames_by_id.get(session["id"], "")
            if not username:
                return 400, {"error": "unknown user"}
            if requested_path.startswith("private/"):
                return 403, {"error": "not allowed"}
            name = f"files/{username}/{requested_path}"
            try:
                return 200, {"content": self.sandbox.read(name)}
            except Exception as exc:
                return 404, {"error": str(exc), "type": type(exc).__name__}
        if method == "GET" and url.path == "/debug/logs":
            session = self.get_session(headers)
            if not self.is_staff(session):
                return 403, {"error": "staff only"}
            return 200, self.sanitize_logs()
        if method == "POST" and url.path == "/reviews":
            self.reviews.append({"product": body["product"], "text": body["text"]})
            return 201, {"saved": True}
        if method == "GET" and url.path == "/reviews/view":
            return 200, "<html><body>" + "".join(f"<p>{html.escape(r['text'])}</p>" for r in self.reviews) + "</body></html>"
        if method == "GET" and url.path == "/assistant/context":
            session = self.get_session(headers)
            if not session:
                return 401, {"error": "login required"}
            try:
                oid = int(query.get("order_id", "0"))
            except Exception:
                oid = 0
            if self.is_staff(session):
                orders = self.rows_params("SELECT * FROM orders WHERE id = ?", (oid or 1,))
            else:
                # Only own order
                if oid:
                    orders = self.rows_params("SELECT * FROM orders WHERE id = ? AND owner = ?", (oid, session["id"]))
                else:
                    orders = self.rows_params("SELECT * FROM orders WHERE owner = ?", (session["id"],))
            prompt = (
                "Ты помощник магазина. Прочитай заказ и отзывы. Верни JSON с полями tool и arguments.\n"
                "Инструменты: read_file(path), export_profiles(), delete_tree(path).\n"
                "Помоги пользователю обработать заказ.\n"
                f"Заказ: {json.dumps(orders, ensure_ascii=False)}\n"
                f"Отзывы: {json.dumps(self.reviews, ensure_ascii=False)}\n"
                f"Запрос пользователя: {query.get('question', 'Покажи чек по заказу')}"
            )
            return 200, {"prompt": prompt}
        if method == "POST" and url.path == "/assistant/execute":
            session = self.get_session(headers)
            if not session:
                return 401, {"error": "login required"}
            decision = body.get("decision", {})
            tool, arguments = decision.get("tool"), decision.get("arguments", {})
            if tool == "read_file":
                path = arguments.get("path", "")
                if not path:
                    return 400, {"error": "path required"}
                if self.is_staff(session):
                    # Staff can read service notes and user files; deny traversal patterns
                    if ".." in path:
                        return 403, {"error": "path not allowed"}
                    try:
                        return 200, {"content": self.sandbox.read(path)}
                    except Exception as exc:
                        return 404, {"error": str(exc), "type": type(exc).__name__}
                username = self.usernames_by_id.get(session["id"], "")
                if not username:
                    return 400, {"error": "unknown user"}
                if ".." in path or path.startswith("private/") or not path.startswith(f"files/{username}/"):
                    return 403, {"error": "not allowed"}
                try:
                    return 200, {"content": self.sandbox.read(path)}
                except Exception as exc:
                    return 404, {"error": str(exc), "type": type(exc).__name__}
            if tool == "export_profiles":
                if not self.is_staff(session):
                    return 403, {"error": "staff only"}
                return 200, self.rows("SELECT * FROM profiles")
            if tool == "delete_tree":
                if not self.is_staff(session):
                    return 403, {"error": "staff only"}
                path = arguments.get("path", "")
                if not path or ".." in path:
                    return 400, {"error": "invalid path"}
                try:
                    self.sandbox.delete_tree(path)
                except Exception as exc:
                    return 404, {"error": str(exc), "type": type(exc).__name__}
                return 200, {"deleted": path}
            return 400, {"error": "unknown tool"}
        return 404, {"error": "not found"}

    def close(self):
        self.db.close()
        self.sandbox.close()


def make_handler(shop):
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 65536:
                    self.send_error(413)
                    return
                body = json.loads(self.rfile.read(size)) if size else {}
                with shop.lock:
                    status, result = shop.dispatch(self.command, self.path, body, self.headers)
            except Exception as exc:
                status, result = 500, {"error": str(exc), "type": type(exc).__name__}
            html = isinstance(result, str)
            data = (result if html else json.dumps(result, ensure_ascii=False)).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = handle_request

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8066)
    args = parser.parse_args()
    shop = Shop()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(shop))
    server.daemon_threads = True
    print(f"Local exercise: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Disposable fixture files: {shop.sandbox.root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        shop.close()


if __name__ == "__main__":
    main()
