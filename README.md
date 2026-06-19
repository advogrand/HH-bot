# HH Telegram Bot

Semi-automatic Telegram bot for finding relevant hh.ru vacancies, preparing safe cover letters, and collecting explicit user approval before any response is sent.

Current state: v1 dry-run foundation. It includes scoring, audit storage, Telegram message rendering, and hh.ru API error mapping. It does not send real hh.ru responses yet.

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
