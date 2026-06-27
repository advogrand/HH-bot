# Assisted Browser Apply Design

## Goal

Add a real-response fallback that sends hh.ru vacancy responses through a visible Playwright browser when the official API denies applicant negotiations.

## Chosen Approach

Use the existing `/browser_search` queue and `/auto_apply confirm` flow. When enabled, auto apply opens each queued vacancy URL in a visible browser profile, clicks only standard response controls, fills the configured cover letter when a message field is visible, and logs every attempt.

## Safety Rules

- Browser must be visible.
- User must already be logged in manually in the browser profile.
- The bot stops on captcha, tests, employer questions, login pages, access restrictions, missing response controls, or unexpected modal states.
- The bot keeps the current remote-only filter, relevance threshold, duplicate prevention, daily limit, and delay.
- The bot does not bypass captcha, tests, rate limits, or access restrictions.
- The bot never stores hh.ru login or password.

## User Flow

1. User runs `/browser_search <query>`.
2. Bot shows candidate vacancies and stores them in memory.
3. User runs `/auto_apply`.
4. Bot previews mode and limits.
5. User runs `/auto_apply confirm`.
6. Bot opens hh.ru in a visible browser and attempts responses one by one.
7. Bot sends a final Telegram summary and writes audit entries.

## Components

- `hh_browser_apply.py`: Playwright browser-assisted vacancy response logic.
- `hh_apply_runner.py`: Delegates real sending to browser-assisted mode when configured.
- `config.py`: Adds a setting for apply transport.
- `app.py`: Wires browser apply runner into the existing auto apply flow.
- Tests mock Playwright-facing code and do not call real hh.ru.

## Error Handling

Browser-assisted apply returns structured `ApplyResult` values:

- `sent` when a standard response completes.
- `failed` with `captcha_required`, `test_required`, `questions_required`, `not_logged_in`, `response_unavailable`, or `browser_error`.
- Fatal browser states stop the batch and appear in `/audit`.

## Testing

Unit tests cover successful browser apply, stop conditions, audit recording, config wiring, and auto-apply fatal-stop behavior. Existing API tests remain intact.
