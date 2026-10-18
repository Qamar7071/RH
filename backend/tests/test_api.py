"""Automated tests for the RH Labs backend.  Run:  python -m pytest -q"""
import base64
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DATABASE_URL", "sqlite://")  # keep the module-level app off disk

import app as app_module  # noqa: E402
import chat  # noqa: E402
import mailer  # noqa: E402
from config import Config  # noqa: E402

VALID = {"name": "Ali Khan", "email": "ali@example.com", "company": "Khan Traders", "service": "AI Chatbot",
         "budget": "$300 to $1,000", "deadline": "Within 1 month",
         "details": "We need a WhatsApp chatbot for our shop that answers price questions."}


def make_cfg(tmp_path, **overrides):
    cfg = Config()
    cfg.DATABASE_URL = f"sqlite:///{tmp_path / 'test.db'}"
    cfg.LLM_API_KEY = ""
    cfg.SMTP_USER = cfg.SMTP_PASSWORD = cfg.NOTIFY_EMAIL = ""
    cfg.ADMIN_PASSWORD = ""
    cfg.ALLOWED_ORIGINS = []
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


@pytest.fixture
def make_client(tmp_path):
    def _make(**overrides):
        application = app_module.create_app(make_cfg(tmp_path, **overrides))
        application.testing = True
        return application, application.test_client()
    return _make


def basic(user, pw):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}


# ---------------------------------------------------------------- general
def test_health(make_client):
    _, c = make_client()
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json["ok"] and r.json["database"] is True
    assert r.json["chat_ai"] is False and r.headers["X-Content-Type-Options"] == "nosniff"


def test_index_served(make_client):
    _, c = make_client()
    r = c.get("/")
    assert r.status_code == 200 and b"RH Labs" in r.data


def test_unknown_api_returns_json_404(make_client):
    _, c = make_client()
    r = c.get("/api/nope")
    assert r.status_code == 404 and r.json["ok"] is False


# ---------------------------------------------------------------- contact
def test_contact_saves_lead(make_client):
    application, c = make_client()
    r = c.post("/api/contact", json=VALID)
    assert r.status_code == 200 and r.json["ok"] and r.json["id"] == 1
    lead = application.extensions["rh_store"].list_leads()[0]
    assert lead["email"] == "ali@example.com" and lead["service"] == "AI Chatbot" and lead["status"] == "new"


def test_contact_validation_errors(make_client):
    _, c = make_client()
    r = c.post("/api/contact", json={**VALID, "email": "not-an-email", "service": "Hacking", "details": "short"})
    assert r.status_code == 400
    assert set(r.json["fields"]) == {"email", "service", "details"}


def test_contact_rejects_non_json(make_client):
    _, c = make_client()
    r = c.post("/api/contact", data="name=x", content_type="application/x-www-form-urlencoded")
    assert r.status_code == 400


def test_contact_honeypot_not_saved(make_client):
    application, c = make_client()
    r = c.post("/api/contact", json={**VALID, "website": "http://spam.example"})
    assert r.status_code == 200 and r.json["ok"]
    assert application.extensions["rh_store"].count_leads() == 0


def test_contact_rate_limit(make_client):
    _, c = make_client()
    codes = [c.post("/api/contact", json=VALID).status_code for _ in range(6)]
    assert codes[:5] == [200] * 5 and codes[5] == 429


def test_contact_too_large(make_client):
    _, c = make_client()
    r = c.post("/api/contact", json={**VALID, "details": "x" * 70000})
    assert r.status_code == 413


def test_contact_sends_email_when_enabled(make_client, monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "_send_async", lambda cfg, msg: sent.append(msg))
    _, c = make_client(SMTP_USER="me@gmail.com", SMTP_PASSWORD="app-pass", NOTIFY_EMAIL="me@gmail.com")
    assert c.post("/api/contact", json=VALID).status_code == 200
    assert len(sent) == 1
    assert sent[0]["Reply-To"] == "ali@example.com" and "AI Chatbot" in sent[0]["Subject"]


def test_name_newlines_cannot_inject_headers(make_client, monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "_send_async", lambda cfg, msg: sent.append(msg))
    _, c = make_client(SMTP_USER="me@gmail.com", SMTP_PASSWORD="x", NOTIFY_EMAIL="me@gmail.com")
    r = c.post("/api/contact", json={**VALID, "name": "Ali\r\nBcc: victim@example.com"})
    assert r.status_code == 200
    assert "\n" not in sent[0]["Subject"] and sent[0]["Bcc"] is None


# ---------------------------------------------------------------- chat
def test_chat_not_configured(make_client):
    _, c = make_client()
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 503 and r.json["ok"] is False


def test_chat_validation(make_client):
    _, c = make_client(LLM_API_KEY="k")
    assert c.post("/api/chat", json={"messages": []}).status_code == 400
    assert c.post("/api/chat", json={"messages": [{"role": "system", "content": "x"}]}).status_code == 400
    assert c.post("/api/chat", json={"messages": [{"role": "user", "content": "x" * 1001}]}).status_code == 400
    assert c.post("/api/chat", json={"messages": [{"role": "assistant", "content": "hello"}]}).status_code == 400


def test_chat_reply_and_log(make_client, monkeypatch):
    seen = {}

    def fake_ask(cfg, messages):
        seen["messages"] = messages
        return "We build AI chatbots, AI agents and websites."
    monkeypatch.setattr(chat, "ask", fake_ask)
    application, c = make_client(LLM_API_KEY="k")
    r = c.post("/api/chat", json={"session_id": "abc12345", "messages": [
        {"role": "assistant", "content": "Hi! How can I help?"}, {"role": "user", "content": "What do you do?"}]})
    assert r.status_code == 200 and r.json["reply"].startswith("We build") and r.json["session_id"] == "abc12345"
    logs = application.extensions["rh_store"].recent_chats()
    assert logs[0]["question"] == "What do you do?"


def test_chat_provider_failure_returns_502(make_client, monkeypatch):
    def boom(cfg, messages):
        raise chat.LLMError("HTTP 500")
    monkeypatch.setattr(chat, "ask", boom)
    _, c = make_client(LLM_API_KEY="k")
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "hello"}]})
    assert r.status_code == 502 and r.json["ok"] is False


# ---------------------------------------------------------------- LLM adapters
class FakeResp:
    def __init__(self, status, data):
        self.status_code, self._data, self.text = status, data, str(data)

    def json(self):
        return self._data


def provider_cfg(tmp_path, provider, **kw):
    return make_cfg(tmp_path, LLM_PROVIDER=provider, LLM_API_KEY="secret", **kw)


def test_gemini_adapter(tmp_path, monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return FakeResp(200, {"candidates": [{"content": {"parts": [{"text": "**Hello** from Gemini"}]}}]})
    monkeypatch.setattr(chat.requests, "post", fake_post)
    out = chat.ask(provider_cfg(tmp_path, "gemini"), [{"role": "user", "content": "hi"}])
    url, headers, body = calls[0]
    assert out == "Hello from Gemini"
    assert "gemini-flash-latest:generateContent" in url and headers["x-goog-api-key"] == "secret"
    assert "RH Labs" in body["systemInstruction"]["parts"][0]["text"]
    assert body["contents"] == [{"role": "user", "parts": [{"text": "hi"}]}]


def test_openai_compatible_adapter(tmp_path, monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, json))
        return FakeResp(200, {"choices": [{"message": {"content": "Hi from Groq"}}]})
    monkeypatch.setattr(chat.requests, "post", fake_post)
    out = chat.ask(provider_cfg(tmp_path, "groq", LLM_MODEL="some-model"), [{"role": "user", "content": "hi"}])
    assert out == "Hi from Groq"
    assert calls[0][0] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls[0][1]["messages"][0]["role"] == "system"


def test_anthropic_adapter(tmp_path, monkeypatch):
    calls = []

    def fake_post(url, headers, json, timeout):
        calls.append((url, headers, json))
        return FakeResp(200, {"content": [{"type": "text", "text": "Hi from Claude"}]})
    monkeypatch.setattr(chat.requests, "post", fake_post)
    out = chat.ask(provider_cfg(tmp_path, "anthropic"), [{"role": "user", "content": "hi"}])
    url, headers, body = calls[0]
    assert out == "Hi from Claude" and headers["anthropic-version"] == "2023-06-01"
    assert body["model"] == "claude-haiku-5-5" and body["messages"] == [{"role": "user", "content": "hi"}]


def test_retry_once_on_server_error(tmp_path, monkeypatch):
    responses = [FakeResp(503, {"error": "busy"}), FakeResp(200, {"choices": [{"message": {"content": "ok"}}]})]
    monkeypatch.setattr(chat.requests, "post", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(chat.time, "sleep", lambda s: None)
    assert chat.ask(provider_cfg(tmp_path, "openai", LLM_MODEL="m"), [{"role": "user", "content": "hi"}]) == "ok"


def test_no_retry_on_bad_key(tmp_path, monkeypatch):
    calls = []

    def fake_post(*a, **k):
        calls.append(1)
        return FakeResp(401, {"error": "bad key"})
    monkeypatch.setattr(chat.requests, "post", fake_post)
    with pytest.raises(chat.LLMError):
        chat.ask(provider_cfg(tmp_path, "openai", LLM_MODEL="m"), [{"role": "user", "content": "hi"}])
    assert len(calls) == 1


def test_normalize_messages():
    msgs = [{"role": "assistant", "content": "greeting"}, {"role": "user", "content": "a"},
            {"role": "user", "content": "b"}, {"role": "assistant", "content": "c"}, {"role": "user", "content": "d"}]
    assert chat.normalize(msgs) == [{"role": "user", "content": "a\n\nb"}, {"role": "assistant", "content": "c"},
                                    {"role": "user", "content": "d"}]


def test_knowledge_comments_removed():
    text = chat.load_knowledge()
    assert "Hostel City" in text and "<!--" not in text and "Example if you decide" not in text


# ---------------------------------------------------------------- admin
def test_admin_disabled_without_password(make_client):
    _, c = make_client()
    assert c.get("/admin").status_code == 404


def test_admin_login_and_csv(make_client):
    _, c = make_client(ADMIN_PASSWORD="s3cret")
    c.post("/api/contact", json={**VALID, "name": "=HYPERLINK(evil)"})
    assert c.get("/admin").status_code == 401
    assert c.get("/admin", headers=basic("admin", "wrong")).status_code == 401
    page = c.get("/admin", headers=basic("admin", "s3cret"))
    assert page.status_code == 200 and b"Project requests" in page.data
    csv_resp = c.get("/admin/leads.csv", headers=basic("admin", "s3cret"))
    assert csv_resp.status_code == 200 and "'=HYPERLINK(evil)" in csv_resp.get_data(as_text=True)


def test_admin_escapes_html(make_client):
    _, c = make_client(ADMIN_PASSWORD="pw")
    c.post("/api/contact", json={**VALID, "details": "<script>alert(1)</script> please build"})
    page = c.get("/admin", headers=basic("admin", "pw")).get_data(as_text=True)
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page


def test_cors_only_for_allowed_origin(make_client):
    _, c = make_client(ALLOWED_ORIGINS=["https://rhlabs.github.io"])
    ok = c.get("/api/health", headers={"Origin": "https://rhlabs.github.io"})
    bad = c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "https://rhlabs.github.io"
    assert bad.headers.get("Access-Control-Allow-Origin") is None
