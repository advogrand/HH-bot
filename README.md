# HH Telegram Bot

Semi-automatic Telegram bot for finding relevant hh.ru vacancies, preparing safe cover letters, and collecting explicit user approval before any response is sent.

Current state: v1 dry-run foundation with real Telegram polling support. It includes scoring, audit storage, Telegram command handling, Telegram message rendering, hh.ru OAuth/search/resume loading, guarded apply flow, and user-editable Telegram settings. Real hh.ru responses stay disabled by default.

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
- `/resumes`
- `/use_resume <resume_id>`
- `/status`
- `/audit [limit]`
- `/settings`
- `/set_search <search phrase>`
- `/set_score <0-100>`
- `/set_resume <resume_id>`
- `/set_letter <cover letter text>`
- `/set_include <comma-separated keywords>`
- `/set_exclude <comma-separated keywords>`
- `/search`
- `/browser_search [search phrase]`
- `/approve <vacancy_id>`
- `/auto_apply confirm`
- `/reject <vacancy_id>`
- `/stop`

In this version `/search` uses saved hh.ru OAuth token when present, fetches vacancies from official `GET https://api.hh.ru/vacancies`, scores them locally, and still records approvals as dry-run only. If no token is saved yet, `/search` tries the same official vacancy search endpoint without an `Authorization` header. If hh.ru returns `403 forbidden`, the bot shows a user-visible message and waits for OAuth access after the app is approved.

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

`HH_SEARCH_AREA=1` is Moscow in hh.ru dictionaries. Leave it empty to search across all areas available to the account. Search results are only used for local scoring and Telegram review. Without an OAuth token the bot can only try public vacancy search and must respect `403 forbidden` or other API restrictions. It cannot read private account state, list resumes, or send real responses. `/approve` still creates a dry-run audit entry and does not send a real hh.ru response unless `ENABLE_REAL_APPLY=1` is explicitly enabled later.

## Apply Safety

By default approvals are dry-run only:

```powershell
ENABLE_REAL_APPLY=0
```

With this default, `/approve <vacancy_id>` writes an audit entry and does not call hh.ru apply endpoint. The code path for real apply is present and posts to official `POST https://api.hh.ru/negotiations` with `resume_id`, `vacancy_id`, and `message`, but it is armed only when this explicit flag is set:

```powershell
ENABLE_REAL_APPLY=1
HH_APPLY_TRANSPORT=api
```

Keep it off until OAuth, resume selection, search quality, and cover letter text are manually verified.

## Strict Auto Apply

Auto apply is guarded by explicit confirmation, remote-only filtering, a daily limit, and a delay:

```powershell
AUTO_APPLY_DAILY_LIMIT=25
AUTO_APPLY_DELAY_SECONDS=30
AUTO_APPLY_REMOTE_ONLY=1
ENABLE_REAL_APPLY=0
HH_APPLY_TRANSPORT=api
```

Flow:

```text
/browser_search digital дизайнер удаленно
/auto_apply
/auto_apply confirm
```

With `ENABLE_REAL_APPLY=0`, `/auto_apply confirm` records dry-run audit entries only. Set `ENABLE_REAL_APPLY=1` only after manually checking one full run. Use `HH_APPLY_TRANSPORT=browser` when the official API denies applicant responses. The runner skips non-remote vacancies, duplicates, low-score vacancies, and anything past the daily limit.

## Assisted Browser Search

When applicant API access is unavailable, enable visible Playwright-assisted search:

```powershell
ENABLE_BROWSER_SEARCH=1
BROWSER_SEARCH_LIMIT=10
BROWSER_HEADLESS=0
BROWSER_USER_DATA_DIR=.hh-browser-profile
```

Then use:

```text
/browser_search python backend
```

The bot opens a visible Chromium profile, navigates to hh.ru search, reads visible vacancy cards, scores them, and shows matches in Telegram. The user must log in, solve SMS/captcha, and handle any hh.ru restrictions manually. This mode must not use stealth, captcha bypass, hidden headless actions, or mass automatic responses.

## Assisted Browser Apply

When official hh.ru apply API returns `forbidden`, use visible browser-assisted apply:

```powershell
ENABLE_REAL_APPLY=1
HH_APPLY_TRANSPORT=browser
BROWSER_HEADLESS=0
BROWSER_USER_DATA_DIR=.hh-browser-profile
```

Flow:

```text
/browser_search графический дизайнер удаленно
/auto_apply
/auto_apply confirm
```

The bot opens each queued vacancy in the visible browser profile and tries only the standard hh.ru response controls. It stops on login pages, captcha, tests, employer questions, missing response controls, access restrictions, or other abnormal states. The user must resolve those states manually.

## Select Resume

After connecting hh.ru, run:

```text
/resumes
```

The bot calls official `GET https://api.hh.ru/resumes/mine`, lists available resume ids, and shows commands like:

```text
/use_resume resume-id
```

Selected resume id is saved in local SQLite and reused on next start. `/settings` shows hh connection state, selected resume id, search text, area, threshold, include keywords, and exclude keywords.

## Edit Settings from Telegram

Runtime settings are saved in local SQLite and reused on next start:

```text
/set_search python backend
/set_score 72
/set_resume resume-id
/set_letter Hello! I am interested in this vacancy and would be glad to discuss my experience.
/set_include designer, figma, photoshop
/set_exclude python, backend, developer
```

`/set_letter` stores exactly the text you provide. The bot must not invent facts for the cover letter.
