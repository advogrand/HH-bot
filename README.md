# HH Telegram Bot

Semi-automatic Telegram bot for finding relevant hh.ru vacancies, preparing safe cover letters, and collecting explicit user approval before any response is sent.

Current state: v1 dry-run foundation with real Telegram polling support. It includes scoring, audit storage, Telegram command handling, Telegram message rendering, and hh.ru API error mapping. It does not send real hh.ru responses yet.

## Safety Defaults

- Uses official hh.ru API only.
- Does not scrape hh.ru pages.
- Does not store hh.ru login/password.
- Does not send responses without explicit user approval.
- Treats captcha, tests, limits, and API restrictions as user-visible states.

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m unittest discover -s tests -v
```

Copy `.env.example` to `.env` and fill tokens only when real integrations are added.

Without installing the package first:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

## Run Dry-Run Check

```powershell
$env:PYTHONPATH='src'
python -m hh_bot.app
```

## Run Telegram Polling

Install dependencies first:

```powershell
python -m pip install -e .
```

Create `.env` from `.env.example`, set `TELEGRAM_BOT_TOKEN`, then run:

```powershell
$env:RUN_TELEGRAM_POLLING='1'
$env:TELEGRAM_BOT_TOKEN='123:abc'
$env:DEFAULT_RESUME_ID='local-dry-run-resume'
$env:DEFAULT_COVER_LETTER='Hello! I am interested in this vacancy and would be glad to discuss my experience.'
$env:INCLUDE_KEYWORDS='python,fastapi,telegram'
$env:EXCLUDE_KEYWORDS='php,1c'
$env:PYTHONPATH='src'
python -m hh_bot.app
```

Supported commands:

- `/start`
- `/connect`
- `/status`
- `/settings`
- `/search`
- `/approve <vacancy_id>`
- `/reject <vacancy_id>`
- `/stop`

In this version `/search` uses saved hh.ru OAuth token when present, fetches vacancies from official `GET https://api.hh.ru/vacancies`, scores them locally, and still records approvals as dry-run only. If no token is saved yet, `/search` falls back to the in-memory dry-run source.

## Run hh.ru OAuth Callback Server

Register an app at hh.ru/dev first and put values into `.env`:

```powershell
HH_CLIENT_ID=your-client-id
HH_CLIENT_SECRET=your-client-secret
HH_REDIRECT_URI=http://localhost:8000/oauth/hh/callback
HH_USER_AGENT=HHBot/0.1 (you@example.com)
OAUTH_START_URL=http://localhost:8000/oauth/hh/start
OAUTH_STATE=local-telegram-user
```

Run the local callback server:

```powershell
$env:RUN_OAUTH_SERVER='1'
python -m hh_bot.app
```

Then use `/connect` in Telegram. The bot returns a link like:

```text
http://localhost:8000/oauth/hh/start?state=local-telegram-user
```

That route redirects to hh.ru OAuth. After login and consent, hh.ru redirects back to `/oauth/hh/callback`, the app exchanges `code` for `access_token`/`refresh_token`, and saves the token pair in local SQLite.

Development storage note: OAuth tokens are currently stored in local SQLite for the developer machine only. Do not commit `*.sqlite3`, do not log token values, and replace this with encrypted/managed secret storage before production deployment.

## Configure hh.ru Vacancy Search

These values control the first real search slice:

```powershell
HH_SEARCH_TEXT=python
HH_SEARCH_AREA=1
HH_SEARCH_PER_PAGE=20
```

`HH_SEARCH_AREA=1` is Moscow in hh.ru dictionaries. Leave it empty to search across all areas available to the account. Search results are only used for local scoring and Telegram review; `/approve` still creates a dry-run audit entry and does not send a real hh.ru response.
