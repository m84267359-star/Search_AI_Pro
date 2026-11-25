# Search AI Pro

An advanced Flask learning/portfolio application with accounts, private chat history, live web search via OpenAI Responses API, streaming, citations, PDF/TXT/MD upload, browser speech input, PDF export, per-user settings, rate limiting, admin statistics and estimated token costs.

## Windows PowerShell setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python app.py
```

Open http://127.0.0.1:5000 and register. Configure `OPENAI_API_KEY`, `FLASK_SECRET_KEY` and `ADMIN_EMAIL` in `.env` **before** registering the admin account. Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`. API usage requires a separately billed OpenAI API account. For live web search, your API account/model must support the `web_search_preview` tool. Uncheck Live web search to send an ordinary AI chat request.

## Features

- Register/login/logout; password hashing; cookie sessions; CSRF protection; user-scoped chat/document data.
- Live web search and source citation links, streamed text, conversation memory, model choices, custom instructions.
- Search, rename, delete chat history; PDF conversation export.
- PDF/TXT/MD file upload and question answering using extracted text; document management.
- Browser speech recognition where supported (typically Chromium-based browsers); microphone permission required.
- Dark/light theme, token usage and estimated token cost, admin counts.
- Per-IP in-memory rate limiting, basic file validation, upload size limits, server-side API key.

## Important limits and production checklist

This is an **advanced educational starter**, not a production-audited service. Use HTTPS and `COOKIE_SECURE=true` for deployment; a production WSGI server and reverse proxy; a persistent Redis rate-limit store; stronger account security (email verification, password reset, MFA); logging/monitoring; database migrations and backups; malware scanning and isolated document processing; security reviews and tests; background jobs for large documents; token/context limits and billing budgets; prompt-injection defenses. The app sends selected uploaded text to OpenAI when queried. Browser speech recognition may use the browser vendor's speech service. Text extraction does not OCR scanned PDFs. PDF exports use basic fonts and may not render every Unicode character.

**Cost estimate:** the provided per-token prices are examples in `.env`, not a live price feed. They exclude web search tool fees and other charges. Actual OpenAI billing is authoritative.

**Streaming:** if the network disconnects mid-response, the user's message may remain saved without a complete AI answer. Retry by sending another message.

**Admin:** `ADMIN_EMAIL` grants admin status when that address registers. For public deployment, do not rely on email alone for admin provisioning: manually provision and verify admin accounts.

**Local-only:** Flask's built-in development server is not for production.

## Test

```powershell
python -m pytest -q
```
