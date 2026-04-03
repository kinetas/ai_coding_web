# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend**
```bash
# Setup (first time)
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.app.init_db

# Run backend
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend**
```bash
cd frontend
python -m http.server 5500
```

**ETL pipeline**
```bash
python etl_demo.py                                    # Demo with random data
python etl_supabase.py --mode crawl --all             # Full crawl + ingest
python etl_supabase.py --mode crawl --category agri   # Single category
python etl_supabase.py --dry-run                      # Preview without writing
```

**No test suite exists.** Validate manually via the API endpoints or frontend.

## Architecture

This is a FastAPI backend + vanilla JS frontend project with a dual-storage abstraction (SQLite for local dev, Supabase/PostgreSQL for production).

### Layered structure (backend)
```
Controllers  →  HTTP routing, request/response serialization
Services     →  Business logic
Repositories →  Storage abstraction
```

All layers live under `backend/app/`. The `CONTENT_SOURCE` env var (`local` | `supabase`) switches the repository implementation used at runtime — both implement the `ContentAccess` interface in `repositories/content_access.py`.

### Authentication (dual system)
- **Supabase Auth (production)**: JWT HS256/RS256 via Bearer token. Validated in `auth.py:get_current_user()`. Proxied through `/api/auth/supabase/*` endpoints.
- **Local sessions (dev/demo)**: SQLite-backed session cookies. Endpoints at `/api/auth/login`, `/register`, `/logout`. Demo credentials: `demo@et.ai / etl1234` (seeded when `AUTH_SEED_DEMO_USER=true`).
- **ETL ingest**: Shared secret via `X-ETL-Token` header, checked by `require_etl_token()`.

Protected routes: `/api/builder/*` requires user auth; `/api/ingest/*` requires ETL token.

### Database
- SQLite path is always relative to **project root** regardless of cwd — normalized in `config.py:_normalize_database_url()`.
- Schema created/migrated in `bootstrap.py`. Lightweight column migrations for SQLite run in `_migrate_sqlite_schema()`.
- Supabase schema changes use SQL scripts in `scripts/`.
- Key models: `User`, `AuthSession`, `AnalysisSnapshot`, `WordcloudTerm`, `SavedBuilderAnalysis`, `EtlRun`.

### ETL data flow
1. `crawler/` modules fetch Google News RSS, agricultural price data (data.go.kr), and public category data.
2. ML keyword scoring via scikit-learn in `crawler/term_category_ml.py`.
3. Results POSTed to `/api/ingest/wordcloud` or `/api/ingest/analysis` with `X-ETL-Token`.
4. Every ingest is audit-logged to the `etl_runs` table.

### Frontend
Static HTML pages in `frontend/`. All API calls use `API_BASE_URL` from `assets/js/config.js` (default: `http://127.0.0.1:8000`). Public pages (`analysis-1.html` through `analysis-5.html`, `agri-analytics.html`, public category pages) require no login. Pages under `my-*.html` and `mypage.html` require auth.

## Key environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLite (dev) or `postgresql+psycopg://...` (prod) |
| `CONTENT_SOURCE` | `local` or `supabase` |
| `SUPABASE_URL` / `SUPABASE_JWT_SECRET` / `SUPABASE_ANON_KEY` | Supabase integration |
| `ETL_SHARED_SECRET` | Protects ingest endpoints |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |
| `AUTH_SEED_DEMO_USER` | Seed demo account on init |
| `AUTH_COOKIE_SECURE` / `AUTH_COOKIE_SAMESITE` | Cookie policy (set for cross-domain prod) |

See `.env.example` for the full list with defaults.

## gstack

Use /browse from gstack for all web browsing. Never use mcp__claude-in-chrome__* tools.
Available skills: /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review,
/design-consultation, /design-shotgun, /design-html, /review, /ship, /land-and-deploy,
/canary, /benchmark, /browse, /connect-chrome, /qa, /qa-only, /design-review,
/setup-browser-cookies, /setup-deploy, /retro, /investigate, /document-release, /codex,
/cso, /autoplan, /careful, /freeze, /guard, /unfreeze, /gstack-upgrade, /learn.
If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills.

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
