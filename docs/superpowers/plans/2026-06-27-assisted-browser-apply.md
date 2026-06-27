# Assisted Browser Apply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build browser-assisted real hh.ru responses using the existing visible Playwright profile and `/auto_apply confirm` queue.

**Architecture:** Add a focused browser apply module that returns the same `ApplyResult` shape as the API client. Wire `HhApplyRunner` to choose API or browser transport from config while preserving audit logging and auto-apply limits.

**Tech Stack:** Python, aiogram, Playwright sync API inside `asyncio.to_thread`, SQLite audit log, unittest.

---

### Task 1: Browser Apply Module

**Files:**
- Create: `src/hh_bot/hh_browser_apply.py`
- Test: `tests/test_hh_browser_apply.py`

- [ ] **Step 1: Write tests for safe browser states**

Create tests with fake page/context objects for:

```python
async def test_browser_apply_success_returns_sent():
    runner = HhBrowserApplyRunner(config=HhBrowserApplyConfig(user_data_dir="profile"))
    result = await runner.apply(vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))
    self.assertTrue(result.ok)
    self.assertEqual(result.status, "sent")

async def test_browser_apply_stops_on_captcha():
    result = apply_visible_page(fake_page_with_text("captcha"), vacancy=_vacancy(), settings=UserSettings("resume-1", "Hello"))
    self.assertFalse(result.ok)
    self.assertEqual(result.error.value, "captcha_required")
```

- [ ] **Step 2: Implement browser apply types**

Add:

```python
@dataclass(frozen=True)
class HhBrowserApplyConfig:
    user_data_dir: str = ".hh-browser-profile"
    headless: bool = False
    timeout_ms: int = 60_000
```

Add `HhBrowserApplyRunner.apply(...)` that calls `run_browser_apply(...)` through `asyncio.to_thread`.

- [ ] **Step 3: Implement page-level logic**

Add `apply_visible_page(page, vacancy, settings) -> ApplyResult`:

- navigate to `vacancy.url`;
- stop if page text contains captcha/login/test/question markers;
- click a visible response button using known hh selectors and text fallback;
- fill message textarea if present;
- click final submit button if a modal appears;
- return `ApplyResult(ok=True, status="sent")` only after success markers or response button disappears.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_hh_browser_apply
```

Expected: PASS.

### Task 2: Apply Runner Transport Switch

**Files:**
- Modify: `src/hh_bot/hh_apply_runner.py`
- Modify: `src/hh_bot/config.py`
- Modify: `src/hh_bot/app.py`
- Test: `tests/test_hh_apply_runner.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Add config**

Add `apply_transport: str` to `Settings`, loaded from `HH_APPLY_TRANSPORT`, default `api`.

- [ ] **Step 2: Wire browser runner**

Change `HhApplyRunner.__init__` to accept `browser_apply_runner=None` and `apply_transport="api"`.

In `approve`, when `real_apply_enabled` and `apply_transport == "browser"`, call:

```python
result = await self.browser_apply_runner.apply(vacancy=vacancy, settings=settings)
```

Then record audit exactly as API results are recorded.

- [ ] **Step 3: Build from app**

In `app.py`, create browser apply runner with the existing browser profile settings and pass it to `HhApplyRunner`.

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m unittest tests.test_hh_apply_runner tests.test_app
```

Expected: PASS.

### Task 3: Auto Apply Reporting and Fatal Stops

**Files:**
- Modify: `src/hh_bot/auto_apply.py`
- Test: `tests/test_auto_apply.py`

- [ ] **Step 1: Confirm fatal browser errors stop batch**

Add test where browser apply returns `captcha_required`; expect:

```python
self.assertEqual(summary.failed, 1)
self.assertIn("Stopped:", summary.user_message)
```

- [ ] **Step 2: Include transport in preview**

Add optional `transport_label` to `AutoApplyRunner` and show it in `/auto_apply` preview:

```text
Mode: real, transport: browser.
```

- [ ] **Step 3: Run tests**

Run:

```powershell
python -m unittest tests.test_auto_apply tests.test_telegram_bot
```

Expected: PASS.

### Task 4: Local Runtime Switch

**Files:**
- Modify: `.env.example`
- Modify: local `.env`
- Modify: `README.md`

- [ ] **Step 1: Document browser transport**

Add:

```text
HH_APPLY_TRANSPORT=browser
```

Explain that `browser` uses visible assisted Playwright and stops on captcha/tests/questions.

- [ ] **Step 2: Set local runtime**

Set local `.env`:

```text
ENABLE_REAL_APPLY=1
HH_APPLY_TRANSPORT=browser
BROWSER_HEADLESS=0
```

- [ ] **Step 3: Full verification**

Run:

```powershell
python -m unittest discover -s tests
```

Expected: all tests pass.

### Task 5: Restart and Commit

**Files:**
- No code files beyond previous tasks.

- [ ] **Step 1: Restart bot and OAuth server**

Stop old `hh_bot.app` processes and start Telegram polling plus OAuth server.

- [ ] **Step 2: Check runtime settings**

Run a small local settings check and confirm:

```text
real_apply=True
apply_transport=browser
```

- [ ] **Step 3: Commit and push**

```powershell
git add .
git commit -m "feat: add assisted browser apply"
git push
```

## Self-Review

- Spec coverage: browser fallback, visible mode, stop conditions, audit, tests, and runtime switch are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: uses existing `ApplyResult`, `UserSettings`, `Vacancy`, and `HhApplyRunner` patterns.
