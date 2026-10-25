# JobButler Agent

A local, privacy-first job-search assistant. It watches your inbox for recruiting emails, matches your background against job descriptions with RAG, drafts cover letters, and coaches you for interviews using the STAR method.

## Features

- **Email listener** – pulls recent emails over IMAP, pre-filters by headers (`BODY.PEEK[HEADER]`) so only likely recruiting emails are downloaded in full, then uses an LLM to extract company, role, sender and next step into a job-tracking board. Supports an HTTP CONNECT proxy for IMAP.
- **Resume–JD matching (RAG)** – project notes are embedded into a lightweight JSON vector store (cosine similarity, no C++ build chain needed). Given a job description, the most relevant experience is retrieved and scored, with pros, cons and suggested resume edits.
- **Cover letter generator** – drafts a tailored letter from the retrieved experience.
- **STAR interview coach** – generates behavioral and technical questions with STAR-structured answer outlines.
- **Resilience** – exponential back-off retries and a circuit breaker when the API quota is exhausted.

## Tech stack

FastAPI (backend) · Streamlit (frontend) · Google Gemini API (or OpenAI-compatible) · custom `SimpleVectorStore` · `imaplib` with proxy tunnelling

## Getting started

```bash
cp .env.example .env     # fill in GEMINI_API_KEY and, optionally, your IMAP email + app password
python run.py            # creates a venv, installs requirements, starts both services
```

The backend runs on `http://localhost:8000`; the Streamlit UI is started by `run.py` as well. For Gmail, use an app password rather than your account password.

## Your own data

The repository ships without any personal data. Put Markdown notes about your projects and experience in `projects_kb/` (created on first run); they are indexed into `cache/vector_store.json`. Email results are cached in `cache/emails.json`. Both folders, and `.env`, are git-ignored.
