# AGENTS.md - HH Telegram Bot

## Project Context

This project is a Telegram bot for helping one applicant find relevant vacancies on hh.ru and send responses using the applicant's resume.

Default product mode is semi-automatic:

- The bot searches vacancies on hh.ru.
- The bot scores vacancy relevance against the user's resume and configured search rules.
- The bot shows suitable vacancies in Telegram with score, reasons, and proposed cover letter.
- The bot sends a response only after explicit user approval in Telegram.

Default tech stack:

- Python.
- `aiogram` for Telegram bot UI.
- `FastAPI` for OAuth callback and service endpoints.
- SQLite for local state, audit log, settings, and deduplication.

Default matching approach:

- Hard filters first.
- LLM scoring second.
- Only vacancies above configured threshold are shown to the user.

## HH.ru Integration Rules

Use only official hh.ru API and OAuth flows.

Allowed:

- OAuth user authorization for applicant account access.
- API requests to search vacancies, read vacancy details, read suitable resumes, read negotiations, and apply to vacancies.
- `Authorization: Bearer <access_token>` header for authenticated API calls.
- Correct `User-Agent` in the format expected by hh.ru, for example `HHBot/0.1 (email@example.com)`.

Forbidden:

- Scraping hh.ru pages.
- Browser automation that simulates user actions on hh.ru.
- Parsing private hh.ru web pages outside the official API.
- Storing or asking for hh.ru login/password.
- Bypassing captcha, tests, account restrictions, rate limits, or API access limits.
- Sending misleading, spammy, or invented information to employers.

Official references:

- https://github.com/hhru/api
- https://raw.githubusercontent.com/hhru/api/master/docs/authorization.md
- https://raw.githubusercontent.com/hhru/api/master/docs/vacancies_for_applicant.md
- https://raw.githubusercontent.com/hhru/api/master/docs/negotiations.md
- https://raw.githubusercontent.com/hhru/api/master/docs/errors.md
- https://hh.ru/article/29030

## Response Safety Rules

The bot must not send automatic responses by default.

Response flow:

1. Find candidate vacancy.
2. Apply hard filters.
3. Score relevance.
4. Generate or select short cover letter.
5. Show candidate in Telegram.
6. Wait for `/approve` or explicit approve button.
7. Send response through hh.ru API.
8. Save audit log entry.

Automatic responses are allowed only if a later implementation explicitly adds a strict auto mode and the user enables it in settings.

Strict auto mode, if ever implemented, must require:

- High relevance score threshold.
- Daily response limit.
- Stop filters for excluded companies, titles, keywords, salary, location, schedule, and employment type.
- Dry-run preview mode before first real send.
- `/stop` command that immediately disables sending.

## Telegram Interface

Plan for these commands:

- `/start` - connect or explain setup.
- `/status` - show OAuth status, daily limits, queue size, and last run.
- `/settings` - edit filters, resume, threshold, cover letter, and mode.
- `/search` - run vacancy search manually.
- `/approve` - approve selected response.
- `/reject` - reject selected vacancy and record reason when available.
- `/stop` - stop current sending/searching and disable auto mode if enabled.

Telegram messages for vacancy candidates must include:

- Vacancy title.
- Company name.
- Salary, location, schedule, and employment type when available.
- hh.ru vacancy URL.
- Relevance score.
- Short reason why it matched.
- Stop-filter warnings if any.
- Cover letter text that will be sent.

## Scoring Rules

Use a hybrid scoring pipeline:

1. Hard filters reject clearly unsuitable vacancies.
2. LLM evaluates remaining vacancies against resume and user preferences.
3. Result includes numeric score and concise reason.
4. User sees only vacancies above display threshold.

Hard filters should cover:

- Keywords to include and exclude.
- Professional role or title patterns.
- Area/location.
- Remote, hybrid, or office preference.
- Salary requirements when salary is present.
- Experience level.
- Employment type and schedule.
- Companies to exclude.
- Vacancies already applied to.

LLM scoring must not invent resume facts. It may summarize fit based only on resume data, vacancy data, and user settings.

## Cover Letter Rules

Default cover letter source is the user setting.

The bot may adapt the letter only when the implementation explicitly supports this and the user enables it.

Cover letters must:

- Stay short.
- Be truthful.
- Use only facts from the user's resume/settings.
- Avoid fake experience, fake skills, fake achievements, and fake motivation.
- Be shown to the user before sending in semi-automatic mode.

If hh.ru reports that a message is required and no cover letter is configured, the bot must ask the user to set one instead of sending an empty response.

## Error And Limit Handling

Do not bypass hh.ru restrictions. Show the user clear Telegram status for these cases:

- `already_applied` - vacancy already has a response for this resume.
- `test_required` - vacancy requires a test; API response is not available.
- `limit_exceeded` - response limit reached.
- `captcha_required` - captcha is required; show official fallback/captcha URL when API provides it.
- `token_expired` - refresh token or ask user to reconnect, depending on OAuth state.
- `token_revoked` or `bad_authorization` - ask user to reconnect.
- `resume_not_found` or `resume_deleted` - ask user to choose an active resume.
- `invalid_vacancy` or archived vacancy - skip and log.
- `too_long_message` - ask user to shorten cover letter.
- `empty_message` - ask user to set cover letter when required.

Every API error should be logged with:

- API operation.
- HTTP status.
- hh.ru error `type` and `value` when present.
- Safe context such as vacancy id and resume id.

Never log access tokens, refresh tokens, authorization codes, Telegram tokens, or full personal contact data.

## Data And Secret Rules

Secrets belong only in `.env` or a secret manager.

Never commit:

- Telegram bot token.
- hh.ru client secret.
- OAuth access token.
- OAuth refresh token.
- Authorization code.
- Personal resume contact data dumps.

SQLite may store:

- User settings.
- Resume id selected by user.
- Vacancy ids.
- Scores and reasons.
- Response status.
- Audit logs.
- OAuth token metadata needed for refresh.

SQLite must not store raw tokens in plaintext unless no secure storage exists and the local-only risk is explicitly accepted in documentation.

## Audit Log Requirements

Each response attempt must create an audit entry:

- Timestamp.
- Vacancy id and URL.
- Vacancy title.
- Employer name when available.
- Resume id.
- Score.
- Match reason.
- Cover letter sent or proposed.
- User action: approved, rejected, skipped, auto-sent if strict auto mode exists.
- API status: sent, failed, skipped.
- API error type/value when failed.

Audit log is required for debugging and for preventing duplicate responses.

## Development Rules

Keep implementation small and testable.

Prefer modules with clear responsibilities:

- Telegram handlers.
- hh.ru API client.
- OAuth flow.
- Vacancy search.
- Scoring.
- Cover letter handling.
- Persistence.
- Background jobs.

Before adding behavior:

- Add or update tests for matching, filters, cover letters, API error mapping, and duplicate prevention.
- Mock external APIs in tests.
- Do not call real hh.ru or Telegram APIs in automated tests.

When changing API integration:

- Check current official hh.ru API docs.
- Keep User-Agent and OAuth behavior compliant.
- Treat new API errors as user-visible states, not crashes.

## Product Defaults

Default mode: semi-automatic.

Default send behavior:

- Do not send without user approval.
- Do not retry failed sends blindly.
- Do not respond to vacancies with required tests.
- Do not respond twice to the same `resume_id` + `vacancy_id`.

Default user safety:

- `/stop` must stop sending/searching work.
- User can inspect queued vacancies before sending.
- User can reject a vacancy and avoid seeing it again.

