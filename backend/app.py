"""RH Labs backend: project request form, AI chatbot and a small admin panel.

Run locally:   python app.py            (http://127.0.0.1:5000)
Production:    gunicorn app:app
"""
import csv
import hmac
import io
import logging
import os
import re
import secrets
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from markupsafe import escape
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import chat
import mailer
from config import Config
from storage import Storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("rh_labs")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

SERVICES = ("AI Chatbot", "AI Agent", "Website or Web App", "Website with AI Chatbot", "Not sure yet")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
MAX_USER_CHARS = 1000
MAX_ASSISTANT_CHARS = 4000
MAX_HISTORY = 12


# ---------------------------------------------------------------- validation
def _text(value, max_len, multiline=False):
    """Clean a value; returns (text, too_long)."""
    s = CONTROL_RE.sub("", "" if value is None else str(value)).strip()
    if not multiline:
        s = " ".join(s.split())
    return s, len(s) > max_len


def validate_lead(data):
    if not isinstance(data, dict):
        return None, {"form": "Invalid request."}
    errors = {}
    name, too_long = _text(data.get("name"), 100)
    if len(name) < 2 or too_long:
        errors["name"] = "Please enter your name (2 to 100 characters)."
    email, too_long = _text(data.get("email"), 200)
    if too_long or not EMAIL_RE.match(email):
        errors["email"] = "Please enter a valid email address."
    company, too_long = _text(data.get("company"), 150)
    if too_long:
        errors["company"] = "Company name is too long."
    service, _ = _text(data.get("service"), 60)
    if service not in SERVICES:
        errors["service"] = "Please choose a service."
    budget, too_long = _text(data.get("budget"), 60)
    if too_long:
        errors["budget"] = "Please choose a budget from the list."
    deadline, too_long = _text(data.get("deadline"), 60)
    if too_long:
        errors["deadline"] = "Please choose a timeline from the list."
    details, too_long = _text(data.get("details"), 5000, multiline=True)
    if len(details) < 10 or too_long:
        errors["details"] = "Please describe your project in 10 to 5,000 characters."
    if errors:
        return None, errors
    return {"name": name, "email": email.lower(), "company": company, "service": service,
            "budget": budget, "deadline": deadline, "details": details}, {}


def validate_chat(data):
    msgs = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(msgs, list) or not msgs:
        return None, "Send at least one message."
    clean = []
    for m in msgs[-MAX_HISTORY:]:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            return None, "Invalid message format."
        limit = MAX_USER_CHARS if m["role"] == "user" else MAX_ASSISTANT_CHARS
        content, too_long = _text(m.get("content"), limit, multiline=True)
        if too_long:
            if m["role"] == "user":
                return None, f"Messages can be up to {MAX_USER_CHARS} characters."
            content = content[:limit]
        if content:
            clean.append({"role": m["role"], "content": content})
    if not clean or clean[-1]["role"] != "user":
        return None, "The last message must come from the visitor."
    return clean, None


def csv_safe(value):
    """Stop spreadsheet formula injection when leads are opened in Excel."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


# ---------------------------------------------------------------- app factory
def create_app(cfg=None):
    cfg = cfg or Config()
    static = str(FRONTEND_DIR) if FRONTEND_DIR.is_dir() else None
    app = Flask(__name__, static_folder=static, static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB per request is plenty
    app.json.sort_keys = False

    if cfg.TRUST_PROXY:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    if cfg.ALLOWED_ORIGINS:
        CORS(app, resources={r"/api/*": {"origins": cfg.ALLOWED_ORIGINS}}, methods=["GET", "POST"],
             allow_headers=["Content-Type"], max_age=600)

    limiter = Limiter(get_remote_address, app=app, storage_uri=cfg.RATE_LIMIT_STORAGE,
                      default_limits=[], headers_enabled=True)
    store = Storage(cfg.DATABASE_URL)
    app.extensions["rh_store"] = store
    app.extensions["rh_config"] = cfg

    if not chat.is_configured(cfg):
        log.warning("AI chatbot is not configured (set LLM_API_KEY). The website will use its built-in answers.")
    if not mailer.enabled(cfg):
        log.warning("Email alerts are off (set SMTP_USER, SMTP_PASSWORD and NOTIFY_EMAIL).")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.path.startswith(("/api/", "/admin")):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    # ---------------- pages
    @app.get("/")
    def index():
        if static and (FRONTEND_DIR / "index.html").exists():
            return send_from_directory(static, "index.html")
        return jsonify(ok=True, service=f"{cfg.COMPANY_NAME} API")

    @app.get("/api/health")
    def health():
        return jsonify(ok=True, database=store.ping(), chat_ai=chat.is_configured(cfg), email_alerts=mailer.enabled(cfg))

    # ---------------- contact form
    @app.post("/api/contact")
    @limiter.limit(cfg.CONTACT_RATE_LIMIT)
    def contact():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(ok=False, error="Please send the form as JSON."), 400
        if str(data.get("website") or "").strip():  # hidden field only bots fill in
            log.info("Spam blocked (honeypot) from %s", get_remote_address())
            return jsonify(ok=True)
        lead, errors = validate_lead(data)
        if errors:
            return jsonify(ok=False, error="Please check the highlighted fields.", fields=errors), 400
        lead["ip"] = get_remote_address() or ""
        lead["user_agent"] = (request.headers.get("User-Agent") or "")[:300]

        lead_id = None
        try:
            lead_id = store.add_lead(lead)
        except Exception:
            log.exception("Could not save lead from %s", lead["email"])
        emailed = mailer.notify_new_lead(cfg, lead, lead_id)
        if lead_id is None and not emailed:
            return jsonify(ok=False, error="We could not save your request. Please contact us on WhatsApp."), 503
        mailer.send_auto_reply(cfg, lead)
        log.info("New lead #%s: %s (%s)", lead_id, lead["service"], lead["email"])
        return jsonify(ok=True, id=lead_id)

    # ---------------- chatbot
    @app.post("/api/chat")
    @limiter.limit(cfg.CHAT_RATE_LIMIT)
    def chat_api():
        data = request.get_json(silent=True)
        messages, error = validate_chat(data)
        if error:
            return jsonify(ok=False, error=error), 400
        if not chat.is_configured(cfg):
            return jsonify(ok=False, error="The AI assistant is not configured yet."), 503
        session_id = str(data.get("session_id") or "")
        if not SESSION_RE.match(session_id):
            session_id = secrets.token_hex(12)
        try:
            reply = chat.ask(cfg, messages)
        except chat.LLMError as exc:
            log.warning("AI provider error: %s", exc)
            return jsonify(ok=False, error="The assistant is busy right now. Please try again or message us on WhatsApp."), 502
        try:
            store.log_chat(session_id, messages[-1]["content"], reply)
        except Exception:
            log.exception("Could not save chat log")
        return jsonify(ok=True, reply=reply, session_id=session_id)

    # ---------------- admin
    def admin_allowed():
        if not cfg.ADMIN_PASSWORD:
            return None  # admin disabled
        auth = request.authorization
        if auth is None or auth.type != "basic":
            return False
        user_ok = hmac.compare_digest((auth.username or "").encode(), cfg.ADMIN_USER.encode())
        pass_ok = hmac.compare_digest((auth.password or "").encode(), cfg.ADMIN_PASSWORD.encode())
        return user_ok and pass_ok

    def admin_guard():
        allowed = admin_allowed()
        if allowed is None:
            return jsonify(ok=False, error="Not found."), 404
        if not allowed:
            return Response("Login required.", 401, {"WWW-Authenticate": 'Basic realm="RH Labs Admin", charset="UTF-8"'})
        return None

    @app.get("/admin")
    @limiter.limit("30 per minute")
    def admin():
        denied = admin_guard()
        if denied:
            return denied
        return Response(render_admin(cfg, store.list_leads(200), store.recent_chats(100), store.count_leads()), mimetype="text/html")

    @app.get("/admin/leads.csv")
    @limiter.limit("30 per minute")
    def admin_csv():
        denied = admin_guard()
        if denied:
            return denied
        buf = io.StringIO()
        writer = csv.writer(buf)
        cols = ["id", "created_at", "name", "email", "company", "service", "budget", "deadline", "details", "status"]
        writer.writerow(cols)
        for row in store.list_leads(100000):
            writer.writerow([csv_safe(row[c]) for c in cols])
        return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=rh-labs-leads.csv"})

    # ---------------- errors (JSON for the API)
    @app.errorhandler(HTTPException)
    def http_error(exc):
        if request.path.startswith("/api/"):
            messages = {404: "Not found.", 405: "Method not allowed.", 413: "Request is too large.",
                        429: "Too many requests. Please wait a moment and try again."}
            return jsonify(ok=False, error=messages.get(exc.code, exc.description)), exc.code
        return exc

    @app.errorhandler(Exception)
    def server_error(exc):
        log.exception("Unhandled error on %s", request.path)
        if request.path.startswith("/api/"):
            return jsonify(ok=False, error="Something went wrong. Please try again."), 500
        return Response("Something went wrong.", 500)

    return app


def render_admin(cfg, leads, chats, total):
    def cell(v):
        return escape("" if v is None else str(v))

    def when(v):
        return cell(v.strftime("%Y-%m-%d %H:%M") if hasattr(v, "strftime") else v)

    lead_rows = "".join(
        f"<tr><td>{r['id']}</td><td>{when(r['created_at'])}</td><td><strong>{cell(r['name'])}</strong><br>"
        f"<a href='mailto:{cell(r['email'])}'>{cell(r['email'])}</a><br><span class='m'>{cell(r['company'])}</span></td>"
        f"<td>{cell(r['service'])}<br><span class='m'>{cell(r['budget'])} · {cell(r['deadline'])}</span></td>"
        f"<td class='d'>{cell(r['details'])}</td></tr>" for r in leads
    ) or "<tr><td colspan='5' class='m'>No requests yet.</td></tr>"
    chat_rows = "".join(
        f"<tr><td>{when(r['created_at'])}</td><td class='d'>{cell(r['question'])}</td><td class='d m'>{cell(r['answer'])}</td></tr>"
        for r in chats
    ) or "<tr><td colspan='3' class='m'>No chats yet.</td></tr>"
    name = escape(cfg.COMPANY_NAME)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} Admin</title><style>
body{{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#F5F8FD;color:#0B1B33}}
header{{background:#1D5BF0;color:#fff;padding:18px 24px;display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:center}}
header a{{color:#fff;font-weight:600}} main{{padding:24px;max-width:1200px;margin:auto}}
h2{{margin:28px 0 12px}} .wrap{{overflow-x:auto;background:#fff;border:1px solid #E2E8F1;border-radius:12px}}
table{{border-collapse:collapse;width:100%;min-width:760px}} th,td{{text-align:left;vertical-align:top;padding:12px 14px;border-bottom:1px solid #E2E8F1}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#5A6A82;background:#FAFCFF}}
.d{{white-space:pre-wrap;max-width:460px}} .m{{color:#5A6A82}} a{{color:#1D5BF0}}
</style></head><body><header><strong>{name} Admin · {total} project requests</strong><a href="/admin/leads.csv">Download CSV</a></header>
<main><h2>Project requests</h2><div class="wrap"><table><tr><th>#</th><th>Date (UTC)</th><th>Client</th><th>Service</th><th>Details</th></tr>{lead_rows}</table></div>
<h2>Recent chatbot questions</h2><div class="wrap"><table><tr><th>Date (UTC)</th><th>Visitor asked</th><th>Assistant replied</th></tr>{chat_rows}</table></div></main></body></html>"""


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
