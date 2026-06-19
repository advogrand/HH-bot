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
- `/status`
- `/settings`
- `/search`
- `/approve <vacancy_id>`
- `/reject <vacancy_id>`
- `/stop`

In this version `/search` uses an in-memory dry-run vacancy source. Real hh.ru search and OAuth will come in the next integration slice.
