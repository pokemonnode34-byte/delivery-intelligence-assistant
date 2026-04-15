## Document Purpose

This document is the authoritative instruction set for Phase 1 of the AI Delivery Intelligence Assistant project. It is written for an LLM coder that will implement each step sequentially. Every step includes precise requirements, expected file outputs, acceptance criteria, a definition of done, a validation command checklist, and a development status tracker.

This document also includes the complete LLM Coder Operating Manual: the Step Verification Protocol, Silent Error Prevention Policy, and all Coder Guardrails. These policies apply to every step in every phase. They are included here so the LLM coder has a single, self-contained reference.

**Do not skip steps. Do not reorder steps. Each step depends on the one before it.**

-----

## Revision History

|Version|Date      |Changes                                                                                                                                                                                                                 |
|-------|----------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|v1.0   |2026-04-15|Initial specification                                                                                                                                                                                                   |
|v1.1   |2026-04-15|Architecture review fixes: locked pagination/retry integration, concurrency semaphore, webhook ordering contract, work item detection caching, custom error hierarchy, request metrics, correlation IDs, timeout tiering|
|v1.2   |2026-04-15|Consolidated with: Step Verification Protocol, Silent Error Prevention Policy, LLM Coder Guardrails (52 rules). Added VERIFYING status. Updated Definition of Done. Single-document delivery for LLM coder.             |

-----

## Phase 0 Dependency

Phase 1 assumes Phase 0 is `COMPLETE`. The following Phase 0 artifacts are used directly:

|Phase 0 Artifact                                                                                   |Used By Phase 1                                              |
|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
|`AppSettings` / `GitLabSettings`                                                                   |Client configuration (URL, token, timeout, retries, per_page)|
|`GitLabAuth` / `create_auth()`                                                                     |Authentication headers and base URL assembly                 |
|`Container` / `create_container()`                                                                 |Dependency injection — the GitLab client is registered here  |
|`setup_logging()` / `get_logger()`                                                                 |All operational logging in the GitLab layer                  |
|`load_settings()` / `load_environment()`                                                           |Configuration loading at bootstrap                           |
|Domain models (`Project`, `Issue`, `MergeRequest`, `Pipeline`, `Milestone`, `Contributor`)         |Target types for response mapping                            |
|`BaseEntity`, `UTCDatetime`, enums (`EntityStatus`, `Priority`, `PipelineStatus`, `MilestoneState`)|Base types and enums used by mappers                         |

**If any Phase 0 artifact is missing, broken, or incomplete, Phase 1 cannot proceed. Verify Phase 0 completion first.**

-----

## Phase 1 Overview

**Goal:** Build a reliable, async GitLab data ingestion layer that fetches, paginates, rate-limits, retries, and normalizes all core GitLab entities into the domain models defined in Phase 0.

**What this phase produces:**

- An async HTTP client built on `httpx.AsyncClient` with configurable timeouts, connection pooling, correlation IDs, and request metrics
- A custom error hierarchy that normalizes HTTP failures into typed, actionable exceptions
- Automatic pagination that transparently handles GitLab’s keyset and offset pagination via an injected request function (not a raw client call)
- Rate-limit detection and backoff that respects GitLab’s `RateLimit-*` response headers
- Configurable retry logic with exponential backoff for transient failures
- Typed fetcher methods for: projects, issues, merge requests, pipelines, milestones, contributors — with concurrency-limited parallel fetching
- Response mappers that transform raw GitLab JSON into Phase 0 domain models
- A Work Item / Issue detection mechanism with per-project in-memory caching for the container lifetime
- Webhook payload ingestion and validation for real-time event processing, with an explicit out-of-order delivery contract
- Container registration of the GitLab client as a new dependency

**What this phase does NOT produce:**

- No business logic or analytics (that is Phase 2+)
- No state persistence or caching beyond in-memory Work Item detection results (that is Phase 2)
- No dependency graph construction (that is Phase 4)
- No LLM integration (that is Phase 8)
- No webhook HTTP server or endpoint (the server is external; this phase handles payload parsing only)
- No database writes
- No CLI commands beyond the existing `bootstrap()`

-----

## Anti-Drift Rules

The LLM coder must not introduce anything outside the defined scope. Specifically:

1. **Do not add frameworks not listed in the Technology Stack.** No FastAPI, no Flask, no aiohttp, no Celery, no Redis, no SQLAlchemy.
1. **Do not add an HTTP server or webhook listener.** Phase 1 builds webhook payload *parsers*, not an HTTP endpoint. The server is an external concern.
1. **Do not add caching layers** beyond the in-memory Work Item detection cache specified in Step 8. No Redis, no file-based caches, no general-purpose request caches. Every data fetch hits the API. General caching belongs in Phase 2.
1. **Do not add database persistence.** Fetched data is returned to callers as domain model instances. Storage belongs in Phase 2.
1. **Do not create utility modules, helper files, or “common” packages** not listed in the directory structure below.
1. **Do not add business logic.** No risk scoring, no velocity computation, no trend detection. This phase fetches and normalizes data. Period.
1. **Do not modify Phase 0 domain models** unless explicitly instructed in a step. If a model field is missing, document the gap and propose it for review — do not silently add fields.
1. **Do not add synchronous wrappers around async code.** The GitLab client is async. Callers must use `await`. The only exception is test helpers using `pytest-asyncio`.
1. **Do not rename modules, restructure directories, or deviate from the defined project layout.**
1. **Do not add GraphQL support.** Phase 1 uses the GitLab REST API v4 exclusively.
1. **Do not bypass the retry/rate-limit layers.** Every API request from a fetcher must flow through `retry_request()` which integrates the rate limiter. Raw `client.get()` calls in fetchers are prohibited.

If a step does not mention it, do not build it.

-----

## Technology Stack (Phase 1 Additions)

Phase 1 uses the same stack as Phase 0, plus the following activated or newly relevant components:

|Component       |Choice             |Rationale                                                             |
|----------------|-------------------|----------------------------------------------------------------------|
|HTTP Client     |`httpx.AsyncClient`|Async-capable, connection pooling, timeout control, response streaming|
|Async Testing   |`pytest-asyncio`   |Already declared as a Phase 0 dev dependency                          |
|Response Mocking|`respx`            |Mock `httpx` requests in tests without hitting real APIs              |

**New dev dependency to add to `pyproject.toml`:** `respx>=0.21` under `[project.optional-dependencies] dev`.

No other new dependencies are permitted in Phase 1.

-----

## Development Status Legend

Each step tracks its status using the following values. The LLM must update the status after completing each step.

|Status        |Meaning                                                                                         |
|--------------|------------------------------------------------------------------------------------------------|
|`NOT_STARTED` |Work has not begun                                                                              |
|`IN_PROGRESS` |Implementation is underway                                                                      |
|`VERIFYING`   |Code written, tests passing — self-verification loop active (see Step Verification Protocol)    |
|`COMPLETE`    |Code verified, tests passing, lint clean, no major/medium issues remaining                      |
|`BLOCKED`     |Cannot proceed — dependency or issue documented                                                 |
|`NEEDS_REVIEW`|Code written but requires human review (e.g., verification loop exhausted with remaining issues)|

### Step Lifecycle

```
NOT_STARTED
    │
    ▼
IN_PROGRESS  ← (writing code and tests)
    │
    ▼
 [Run tests, lint, mypy — all must pass]
    │
    ▼
VERIFYING  ← (self-verification loop begins — max 5 iterations)
    │
    ├──► Verification Pass
    │       │
    │       ├─ MAJOR/MEDIUM issues found → Fix → Re-run tests → Re-verify (loop)
    │       │
    │       └─ No MAJOR/MEDIUM issues → Exit loop
    │
    ▼
COMPLETE  ← (only after clean verification pass)
```

-----

## File Ownership Boundaries

Phase 1 populates the `gitlab/` package. Boundaries from Phase 0 remain enforced.

|Package  |Owns                                                                                                                                                                          |Does NOT Own                                                                                            |
|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
|`gitlab/`|Async HTTP client, custom exceptions, pagination, rate-limiting, retry logic, entity fetchers, response mappers, webhook payload parsing, work item detection, request metrics|Domain model definitions, settings models, logging setup, auth construction, business logic, persistence|
|`config/`|Settings models (unchanged from Phase 0)                                                                                                                                      |GitLab API client, response mapping                                                                     |
|`core/`  |Logging, environment, auth, container (extended with GitLab client registration)                                                                                              |GitLab API calls, response parsing, business logic                                                      |
|`models/`|Domain entities (unchanged from Phase 0, unless a step explicitly modifies them)                                                                                              |API response parsing, raw JSON handling                                                                 |

-----

## Definition of Done (applies to every step)

A step is `COMPLETE` only when ALL of the following are true:

1. All code for the step is written and saved.
1. All tests for the step are written and saved.
1. All tests pass: `pytest {test_path} -v`
1. No import errors: `python -c "import delivery_intelligence"`
1. No lint errors on touched files: `ruff check src/ tests/`
1. Type checking passes on touched files: `mypy src/delivery_intelligence/{module}`
1. All Phase 0 tests still pass: `pytest tests/ -v`
1. **Step has passed the Verification Protocol with 0 MAJOR and 0 MEDIUM issues.**
1. Status table is updated to `COMPLETE` with the current date.

If any item fails, the step remains `IN_PROGRESS` or `VERIFYING` until resolved.

-----

## Directory Structure (Phase 1 Target)

After Phase 1 is complete, the `gitlab/` package and test directory will contain:

```
src/delivery_intelligence/
└── gitlab/
    ├── __init__.py
    ├── exceptions.py
    ├── client.py
    ├── pagination.py
    ├── rate_limiter.py
    ├── retry.py
    ├── fetchers.py
    ├── mappers.py
    ├── webhooks.py
    └── work_items.py

tests/
├── test_gitlab/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_exceptions.py
│   ├── test_client.py
│   ├── test_pagination.py
│   ├── test_rate_limiter.py
│   ├── test_retry.py
│   ├── test_fetchers.py
│   ├── test_mappers.py
│   ├── test_webhooks.py
│   ├── test_work_items.py
│   └── test_integration.py
└── fixtures/
    └── gitlab/
        ├── project.json
        ├── issue.json
        ├── merge_request.json
        ├── pipeline.json
        ├── milestone.json
        ├── contributor.json
        ├── paginated_response.json
        ├── webhook_push.json
        ├── webhook_issue.json
        ├── webhook_merge_request.json
        ├── webhook_pipeline.json
        └── work_items_response.json
```

**The `tests/fixtures/gitlab/` directory contains static JSON fixtures representing real GitLab API responses. These are used by tests to avoid network calls and to guarantee deterministic, reproducible test data.**

-----

## GitLab API Reference (Authoritative for Phase 1)

All API calls target the GitLab REST API v4. The base URL is assembled by `GitLabAuth.get_base_url()` (e.g., `https://gitlab.example.com/api/v4`).

|Entity                   |Endpoint                              |Docs Reference                      |
|-------------------------|--------------------------------------|------------------------------------|
|Projects                 |`GET /projects/:id` or `GET /projects`|GitLab Projects API                 |
|Issues                   |`GET /projects/:id/issues`            |GitLab Issues API                   |
|Merge Requests           |`GET /projects/:id/merge_requests`    |GitLab Merge Requests API           |
|Pipelines                |`GET /projects/:id/pipelines`         |GitLab Pipelines API                |
|Milestones               |`GET /projects/:id/milestones`        |GitLab Milestones API               |
|Members / Contributors   |`GET /projects/:id/members/all`       |GitLab Members API                  |
|Work Items (if available)|`GET /projects/:id/work_items`        |GitLab Work Items API (experimental)|

### Pagination Headers

GitLab returns pagination metadata in response headers:

|Header         |Purpose                                                     |
|---------------|------------------------------------------------------------|
|`x-page`       |Current page number                                         |
|`x-per-page`   |Items per page                                              |
|`x-total`      |Total number of items (may be absent for large collections) |
|`x-total-pages`|Total number of pages (may be absent for large collections) |
|`x-next-page`  |Next page number (empty if on last page)                    |
|`link`         |RFC 5988 link header with `rel="next"` for keyset pagination|

### Rate-Limit Headers

|Header               |Purpose                                                   |
|---------------------|----------------------------------------------------------|
|`RateLimit-Limit`    |Maximum requests per interval                             |
|`RateLimit-Remaining`|Remaining requests in current interval                    |
|`RateLimit-Reset`    |Unix timestamp when the rate limit resets                 |
|`Retry-After`        |Seconds to wait before retrying (present on 429 responses)|

-----

## Architectural Invariants

The following invariants apply across all of Phase 1. They are not step-specific — they are system-wide contracts.

### Invariant 1 — Request Flow Architecture (LOCKED)

Every API request from a fetcher MUST follow this exact call chain:

```
fetcher
  → retry_request(request_fn, ...)
    → rate_limiter.wait_if_needed()
    → request_fn(method, path, params)  # calls client.request()
    → rate_limiter.update(response)
  → return response
```

For paginated endpoints, the flow is:

```
fetcher
  → paginate(request_fn, path, params)
    → for each page:
        → request_fn(method, path, page_params)  # this IS retry_request
        → yield page items
```

`paginate()` accepts a `request_fn: Callable` — NOT a `GitLabClient` instance. The fetcher constructs a `request_fn` that wraps `retry_request()` with the rate limiter, then passes that function to `paginate()`.

This ensures:

- Every page request gets retry protection.
- Every page request gets rate-limit protection.
- Pagination is decoupled from retry/rate-limit internals.

**Violating this invariant is a critical defect.**

### Invariant 2 — Webhook Ordering Contract

GitLab does NOT guarantee webhook delivery order. Events may arrive out-of-order, duplicated, or delayed.

All Phase 1 webhook parsers MUST:

- Attach a `received_at: datetime` timestamp (UTC) to every parsed event.
- Never assume sequential delivery.
- Never reject events based on perceived ordering.

All downstream consumers (Phase 2+) MUST:

- Use the entity’s `updated_at` timestamp (from the payload data) as the authoritative state timestamp, not the webhook arrival order.
- Handle duplicate events idempotently.

This invariant is documented here and enforced in the webhook module.

### Invariant 3 — Secrets Never Logged

Tokens, passwords, credentials, and authorization values MUST never appear in:

- Log output (any level)
- `repr()` or `str()` output
- Error messages or exception args
- Test output or fixtures

This was established in Phase 0 and remains enforced in Phase 1.

### Invariant 4 — Mapping Failures Are Isolated

When mapping a batch of API responses to domain models, a failure in one item MUST NOT crash the entire batch. The mapper logs the error at `ERROR` level (including entity type and ID if available), skips the item, and continues with remaining items. The caller receives a list of successfully mapped items plus a count of failures via `FetchResult`.

-----

# LLM CODER OPERATING MANUAL

The following sections define the complete operating discipline for the LLM coder. These policies are not guidelines — they are mandatory rules that apply to every step in every phase. Violations are defects.

-----

## Step Verification Protocol

### Purpose

This protocol defines a mandatory self-verification loop that the LLM coder must execute after writing code and tests for each step, but BEFORE marking the step as `COMPLETE`. It catches major and medium logic errors that pass syntax checks, linting, and even tests — but would cause failures in downstream phases.

### Issue Severity Classification

The LLM must classify every issue found during verification into one of three severity levels:

**MAJOR — Must fix before proceeding.**
Logic errors that will cause incorrect behavior, data corruption, or downstream phase failures.

Examples:

- Incorrect control flow: A retry loop that never actually retries, or retries on non-retryable errors.
- Data loss: A mapper that silently drops required fields instead of raising.
- Race condition: An async operation that mutates shared state without protection.
- Contract violation: A function that returns a different type than its signature promises.
- Security flaw: A token or secret that leaks into logs, exceptions, or repr output.
- Broken invariant: A fetcher that calls `client.get()` directly, bypassing the retry/rate-limit chain (violates Invariant 1).
- Missing error handling: An exception path that crashes instead of degrading gracefully per spec.
- Wrong default: An enum fallback that maps to a dangerous default instead of a safe one.

**MEDIUM — Must fix before proceeding.**
Logic issues that don’t immediately break the system but will cause subtle bugs, maintenance problems, or test fragility.

Examples:

- Off-by-one: Pagination that skips the last page or fetches one extra.
- Missing edge case: A datetime parser that handles `Z` suffix but not `+00:00`.
- Incomplete mapping: A mapper that extracts `assignee.id` but doesn’t handle `assignees: null`.
- Weak validation: A function that checks for empty string but not `None`.
- Log quality: A log statement that says “error occurred” without including the entity ID or error type.
- Test gap: A test that asserts success but doesn’t verify the actual output values.
- Resource leak: An async context manager that doesn’t close on exception paths.
- Metric drift: A counter that increments on retry but not on the initial attempt.

**MINOR — Note but do not fix in this loop.**
Style, naming, or documentation issues that don’t affect correctness. Noted for future cleanup but do NOT block the step from completing.

Examples:

- Docstring could be more descriptive.
- Variable name could be clearer.
- Import order is suboptimal.
- Comment is redundant.

**MINOR issues do not count toward the “issues found” determination. Only MAJOR and MEDIUM issues trigger a fix iteration.**

### Verification Checklist

During each verification pass, the LLM must systematically check the following categories. Each category must be explicitly evaluated.

**1. Contract Compliance**

- Does every public function match its documented signature (params, return type)?
- Does every function fulfill its docstring promise?
- Are all acceptance criteria from the step actually satisfied by the code?
- Are all architectural invariants respected?

**2. Error Handling**

- Does every function handle the failure modes described in the spec?
- Are exceptions raised with descriptive messages (including entity type/ID where applicable)?
- Is there any exception path that could leak secrets?
- Are all error log statements using structured key-value format (not f-strings)?

**3. Edge Cases**

- What happens with `None` inputs where the spec says “nullable”?
- What happens with empty strings, empty lists, empty dicts?
- What happens when an optional nested object is missing entirely (not just null)?
- What happens with zero-value numerics (0 retries, 0 timeout, 0 per_page)?

**4. Async Correctness**

- Are all `await` calls present where needed?
- Is there any shared mutable state accessed from concurrent coroutines without protection?
- Do context managers properly clean up on exception?
- Is `asyncio.gather()` used with `return_exceptions=True` where partial failure is acceptable?

**5. Security**

- Do any log statements include secret values (token, password, credential)?
- Do any `__repr__` or `__str__` methods expose secrets?
- Do any exception messages include secrets?
- Does webhook token validation use constant-time comparison?

**6. Test Quality**

- Does every test assert something meaningful (not just “no exception raised”)?
- Are edge cases tested, not just the happy path?
- Do tests use the correct assertion (e.g., `assert result.failures == 1`, not just `assert result`)?
- Are async tests properly decorated with `@pytest.mark.asyncio`?
- Do tests clean up state (fixtures, mocks) to avoid cross-test contamination?

**7. Integration Fit**

- Will the output of this step work as input for the next step?
- Are imports correct and non-circular?
- Does this step’s code respect file ownership boundaries?
- Are all new public symbols exported in `__init__.py`?

**8. Silent Error Detection**

- Are there any bare `except: pass` or `except Exception: pass` blocks?
- Are there any `except` blocks that return a default value without logging AND without a caller-visible failure signal?
- Does every batch operation return a result type that encodes failure count?
- Does every `Optional` return have documented `None` semantics distinguishing “no value” from “error”?
- Does every `asyncio.gather(return_exceptions=True)` explicitly handle and log each exception in the results?
- Does every error log include entity type, entity ID (if applicable), error type, and error message?
- Are there any functions that `return` or `return None` inside an `except` block? (If yes — verify the caller can detect the failure.)
- Are there any validation checks that `return` early on invalid input without raising or logging?

**If ANY check in category 8 fails, it is a MAJOR issue that blocks the step from completing.**

### Verification Pass Procedure

For each verification pass, the LLM must:

1. **Set status to `VERIFYING`** with the iteration number (e.g., `VERIFYING (1/5)`).
1. **Re-read the full code** produced in the step. Not from memory — actually re-read the files using file-read tools.
1. **Walk through the verification checklist** above. For each category, state:
- `PASS` — No issues found in this category.
- `ISSUE(S) FOUND` — List each issue with severity (MAJOR/MEDIUM/MINOR) and a one-line description.
1. **Summarize findings** in a verification report:
   
   ```
   Verification Pass #N:
   - MAJOR issues: [count] — [one-line each]
   - MEDIUM issues: [count] — [one-line each]
   - MINOR issues: [count] — [noted, not blocking]
   - Verdict: PASS / NEEDS_FIX
   ```
1. **If NEEDS_FIX:** Apply fixes, re-run tests/lint/mypy, then start the next verification pass.
1. **If PASS:** Set status to `COMPLETE`.

### Loop Termination Rules

|Condition                                            |Action                                                         |
|-----------------------------------------------------|---------------------------------------------------------------|
|Verification pass finds 0 MAJOR and 0 MEDIUM issues  |Exit loop → `COMPLETE`                                         |
|5 verification iterations completed                  |Exit loop → `NEEDS_REVIEW` with summary of remaining issues    |
|A fix introduces a new MAJOR issue not present before|Count as a new iteration, continue loop                        |
|Tests fail after a fix                               |Stay in `VERIFYING`, fix the test failure first, then re-verify|

**If the loop exits at iteration 5 with remaining issues:** The step is marked `NEEDS_REVIEW` (not `COMPLETE`), and the LLM must document all remaining issues in the status table with a brief description. The human reviewer decides whether to proceed.

-----

## Silent Error Prevention Policy

### Zero-Tolerance Rule

A **silent error** occurs when:

1. An exception is caught and the code continues as if nothing happened — without logging, without notifying the caller, and without modifying the return value to indicate failure.
1. A function returns a default value (e.g., `None`, `[]`, `0`, `False`) on failure, and the caller has no way to distinguish “real default” from “failure occurred.”
1. An error is logged but the return value hides the failure — the caller receives what looks like a successful result.
1. A validation check fails but the code proceeds with invalid data instead of rejecting it.
1. A partial failure in a batch operation is neither counted, logged, nor surfaced to the caller.

**The core principle:** Every failure must produce at least TWO signals:

1. **A log entry** at `WARNING` or `ERROR` level with structured context (entity type, entity ID, error type, error message).
1. **A caller-visible signal** — either a raised exception, or a return type that explicitly encodes failure (e.g., `FetchResult.failures > 0`, `Optional` return with documented `None` semantics, a result object with an error field).

If a failure produces zero signals, that is a **CRITICAL defect**.
If a failure produces only a log entry but no caller signal, that is a **MAJOR defect**.

### Banned Patterns

The following code patterns are **strictly prohibited**:

**Pattern 1 — Bare except with pass:**

```python
# BANNED — failure is completely invisible
try:
    result = parse_datetime(value)
except Exception:
    pass
```

**Pattern 2 — Bare except with silent default:**

```python
# BANNED — caller cannot distinguish "no data" from "parsing failed"
try:
    result = parse_datetime(value)
except Exception:
    result = None
```

**Pattern 3 — Catch-log-return-default without caller signal:**

```python
# BANNED — the log helps operators, but the caller gets []
# and has no idea 15 out of 100 items failed
def map_all(items: list[dict]) -> list[Issue]:
    results = []
    for item in items:
        try:
            results.append(map_issue(item))
        except Exception as e:
            logger.error("mapping_failed", error=str(e))
    return results  # caller sees 85 items, doesn't know 15 failed
```

**Pattern 4 — Swallowed validation error:**

```python
# BANNED — invalid data enters the system silently
def process_event(data: dict) -> None:
    if "project_id" not in data:
        return  # silent exit — caller thinks processing succeeded
```

**Pattern 5 — Generic exception handler that hides the cause:**

```python
# BANNED — original error type and context are lost
try:
    response = await client.get(path)
except Exception:
    logger.error("request_failed")
    return None  # what failed? why? what was the path?
```

**Pattern 6 — Boolean return that hides error details:**

```python
# BANNED — caller knows it failed but not why
def validate_config(settings: AppSettings) -> bool:
    try:
        return True
    except Exception:
        return False  # what was invalid? which field?
```

**Pattern 7 — Partial failure in async gather without tracking:**

```python
# BANNED — exceptions are caught by gather but silently discarded
results = await asyncio.gather(*tasks, return_exceptions=True)
items = [r for r in results if not isinstance(r, Exception)]
# the exceptions are thrown away — no log, no count, no signal
```

### Required Patterns

Every error handling block must follow one of these approved patterns:

**Pattern A — Raise with context (preferred for non-batch operations):**

When a function cannot complete its contract, it raises an exception with full context.

```python
def parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 string to datetime. Returns None only for None input."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Cannot parse datetime from value: {value!r}"
        ) from e
```

**Rule:** `None` return is only valid when the *input* is `None`. `None` is never used to mean “error occurred.”

**Pattern B — Result object with failure tracking (required for batch operations):**

```python
@dataclass
class FetchResult:
    items: list[BaseEntity]
    failures: int
    total_raw: int

async def fetch_issues(self, project_id: int) -> FetchResult:
    raw_items = await paginate_all(request_fn, path, params)
    mapped = []
    failures = 0
    for raw in raw_items:
        try:
            mapped.append(map_issue(raw))
        except (ValueError, ValidationError) as e:
            failures += 1
            logger.error(
                "issue_mapping_failed",
                project_id=project_id,
                raw_id=raw.get("id", "unknown"),
                error_type=type(e).__name__,
                error=str(e),
            )
    return FetchResult(items=mapped, failures=failures, total_raw=len(raw_items))
```

**Rule:** The caller MUST be able to inspect `result.failures` to know if the batch was fully successful.

**Pattern C — Explicit optional with documented None semantics:**

```python
def map_webhook_to_model(payload: WebhookPayload) -> BaseEntity | None:
    """Map a webhook payload to a domain model.

    Returns None for event types that have no domain model mapping
    (PUSH, NOTE, UNKNOWN). This is not an error.

    Raises ValueError if the payload is for a mapped event type
    but the data is malformed.
    """
    if payload.event_type in (WebhookEvent.PUSH, WebhookEvent.NOTE, WebhookEvent.UNKNOWN):
        return None  # intentional — documented non-error case

    try:
        if payload.event_type == WebhookEvent.ISSUE:
            return map_issue(payload.raw["object_attributes"])
    except (KeyError, ValueError, ValidationError) as e:
        logger.error(
            "webhook_mapping_failed",
            event_type=payload.event_type.value,
            project_id=payload.project_id,
            error_type=type(e).__name__,
            error=str(e),
        )
        raise ValueError(
            f"Failed to map {payload.event_type.value} webhook: {e}"
        ) from e
```

**Rule:** If a function returns `Optional[X]`, the docstring MUST state when `None` is returned and confirm `None` means “no result” not “error.”

**Pattern D — Guarded gather with explicit error handling:**

```python
results = await asyncio.gather(*tasks, return_exceptions=True)
for key, result in zip(fetch_keys, results):
    if isinstance(result, Exception):
        logger.error(
            "fetch_failed",
            entity_type=key,
            project_id=project_id,
            error_type=type(result).__name__,
            error=str(result),
        )
        successful[key] = FetchResult(items=[], failures=0, total_raw=0)
    else:
        successful[key] = result
```

**Rule:** Exceptions from `gather()` are never silently filtered out. Each is logged with full context.

### Error Logging Requirements

Every error log statement must include structured context:

**For entity-level errors (mapping, validation):**

```python
logger.error("issue_mapping_failed", entity_type="issue",
    entity_id=raw.get("id", "unknown"), project_id=project_id,
    error_type=type(e).__name__, error=str(e))
```

**For request-level errors (HTTP, timeouts):**

```python
logger.error("request_failed", method=method, path=path,
    status_code=response.status_code, correlation_id=correlation_id,
    attempt=attempt_number, error_type=type(e).__name__, error=str(e))
```

**For system-level errors (startup, config):**

```python
logger.error("initialization_failed", component="gitlab_client",
    error_type=type(e).__name__, error=str(e))
```

**Absolute prohibition:** No error log may ever contain token values, passwords, secrets, credentials, or full response bodies (truncate to 200 chars max).

-----

## LLM Coder Guardrails

### Category 1 — Code Integrity

**1.1 — No Phantom Implementations.**
After writing every function, compare the function body against EVERY bullet point in that function’s spec. If the spec says the function does 7 things, the code must do all 7. No partial implementations. During verification: count spec behaviors, count code behaviors. Mismatch = MAJOR issue.

**1.2 — No Docstring-Code Drift.**
Docstrings are contracts. If code is changed, the docstring must be updated in the same edit. During verification, re-read every docstring and confirm it accurately describes the current code.

**1.3 — No Copy-Paste Adaptation Failures.**
When reusing a pattern, explicitly identify every element that must change for the new context. Example: a fetcher copied from `fetch_issues` must change the endpoint path, mapper function, log event name, and entity type. Never copy-paste and assume it works.

**1.4 — No Invented Interfaces.**
Before calling any method or accessing any attribute, verify that the target object actually has it — defined in the current step or a previous completed step. Never reference methods planned for future steps or from different projects.

### Category 2 — Type Safety

**2.1 — No Implicit Type Coercion.**
Every type coercion must be guarded. `str(None)` produces `"None"`. `int("abc")` raises `ValueError`. Check for `None` before coercing.

```python
# WRONG: url = str(raw.get("web_url"))
# CORRECT:
url = raw.get("web_url")
if url is None:
    raise ValueError("web_url is required but missing")
```

**2.2 — No Untyped Containers.**
Every container in a function signature must have type parameters: `dict[str, Any]` not `dict`, `list[int]` not `list`.

**2.3 — No `Any` Escape Hatch.**
`Any` is permitted ONLY for raw JSON data from external sources (`dict[str, Any]`). Prohibited for return types of functions that always return a known type, internal variables, or parameters where the caller always passes a known type.

### Category 3 — Test Quality

**3.1 — No Tautological Tests.**
Every test assertion must be falsifiable. `assert result is not None` proves nothing. Verify actual field values.

```python
# WRONG: assert result is not None
# CORRECT:
assert result.id == 42
assert result.name == "my-project"
assert result.created_at.tzinfo is not None
```

**3.2 — No Happy-Path-Only Tests.**
For every function with error handling, at least one test must exercise each error path. Minimum ratio: for every 2 happy-path tests, at least 1 error-path test.

**3.3 — No Mock-Everything Tests.**
Mock external boundaries only — HTTP calls (via `respx`), `asyncio.sleep`, environment variables. Do not mock internal classes, mappers, or domain models. If a fetcher test mocks the mapper, it doesn’t verify actual mapping.

**3.4 — No Fixture Fabrication.**
All JSON fixtures must be based on GitLab API documentation. Specific checks:

- GitLab uses `created_at`, not `createdAt`.
- GitLab uses `assignees` (list), not `assignee_ids`.
- GitLab nests `author: { id: 1, ... }`, not `author_id: 1` at the top level.
- GitLab uses `object_attributes` in webhooks, not `attributes`.
- GitLab returns state as `"opened"` not `"open"` for issues and MRs.

### Category 4 — Async Discipline

**4.1 — No Missing Awaits.**
Every call to an `async def` function must be preceded by `await`. During verification, check every call to `client.get()`, `client.request()`, `retry_request()`, `paginate_all()`, `rate_limiter.wait_if_needed()`, `client.close()`.

**4.2 — No Shared Mutable State in Concurrent Code.**
If `asyncio.gather()` runs multiple coroutines, each must write to its own isolated variable. Collect results from `gather()` return value.

**4.3 — No Sync Calls in Async Context.**
Use `asyncio.sleep()`, never `time.sleep()`. Use `httpx.AsyncClient`, never `httpx.Client` or `requests`.

### Category 5 — Naming and Consistency

**5.1 — No Synonym Drift.**
The following terms are canonical and must be used consistently everywhere:

|Concept                  |Canonical Term  |Never Use                                                         |
|-------------------------|----------------|------------------------------------------------------------------|
|GitLab project identifier|`project_id`    |`proj_id`, `pid`, `project` (when meaning ID)                     |
|Internal issue number    |`iid`           |`internal_id`, `issue_number`                                     |
|Fetch data from API      |`fetch_*`       |`get_*` (reserved for container accessors), `retrieve_*`, `load_*`|
|Transform JSON to model  |`map_*`         |`convert_*`, `transform_*`, `parse_*` (except `parse_datetime`)   |
|Container accessor       |`get_*`         |`fetch_*`, `retrieve_*`                                           |
|API request function     |`request_fn`    |`req_func`, `make_request`, `caller`                              |
|Rate limit remaining     |`remaining`     |`remaining_calls`, `calls_left`, `quota`                          |
|Retry attempt counter    |`attempt`       |`try_number`, `retry_count`, `n`                                  |
|Correlation ID           |`correlation_id`|`request_id`, `trace_id`, `req_id`                                |

**5.2 — No Magic Values.**
Every hardcoded value that controls behavior must be a named constant or configuration value.

```python
# WRONG: if remaining < 5:
# CORRECT:
_RATE_LIMIT_BUFFER_THRESHOLD: int = 5
```

**5.3 — No Inconsistent Error Message Formats.**
All error event names in structured logs must use `snake_case` past tense:

```python
# CORRECT: "issue_mapping_failed", "request_failed", "rate_limit_exceeded"
# WRONG: "Failed to map issue", "Error in request", "RATE LIMIT!"
```

### Category 6 — Resource and State Management

**6.1 — No Resource Leaks.**
Every resource that needs closing must use a context manager (`async with`) or be closed in a `finally` block.

**6.2 — No Input Mutation.**
Functions must never mutate their input arguments. Create copies before modifying dicts.

```python
# WRONG: params["page"] = 1  (mutates caller's dict)
# CORRECT: page_params = {**(params or {}), "page": 1, "per_page": per_page}
```

**6.3 — No Stale State Reads.**
If a value is read from shared mutable state, and an `await` happens before the value is used, re-read after the `await` or use the value atomically before yielding.

### Category 7 — Spec Compliance Discipline

**7.1 — No Spec Interpretation Without Declaration.**
When the spec is ambiguous: choose the most conservative interpretation, add `# ASSUMPTION: ...` comment, mention in verification report. Never silently interpret.

**7.2 — No Forward References in Implementation.**
Code in Step N may only import and use artifacts from Steps 1 through N-1 (and Phase 0). Never reference artifacts from future steps.

**7.3 — No Gratuitous Abstraction.**
Implement exactly what the spec describes. No unnecessary base classes, factory patterns, or strategy patterns. If you can remove an abstraction and the system still works, it was gratuitous.

**7.4 — No Speculative Future-Proofing.**
Do not add parameters, configuration options, or code paths “in case we need them later” that are not in the spec.

### Category 8 — Defensive Coding

**8.1 — No Truthy/Falsy Confusion.**
Use `if value is not None:` when checking existence. `if value:` fails for `0`, `""`, `[]`, `False` — all of which may be valid values.

```python
# WRONG: if raw.get("blocking_issues_count"):
# CORRECT:
raw_blocking = raw.get("blocking_issues_count")
blocking = int(raw_blocking) if raw_blocking is not None else 0
```

**8.2 — No Unguarded Dict Access.**
For required fields from external data, use `raw["field"]` inside try/except with context:

```python
try:
    project_id = raw["project"]["id"]
except KeyError as e:
    raise ValueError(f"Missing required field in project response: {e}") from e
```

For optional fields, use `.get()` with a default.

**8.3 — No Assumed Collection Types.**
Verify intermediate value type before drilling deeper into nested structures:

```python
author = raw.get("author")
if author is None or not isinstance(author, dict):
    raise ValueError("Issue response missing 'author' object")
author_id = author.get("id")
```

### Category 9 — Context and Memory Discipline

**9.1 — No Decision Amnesia.**
Before writing code for any step, re-read: (1) Architectural Invariants, (2) current step’s full spec, (3) public interface of imported modules — by reading actual files, not from memory.

**9.2 — No Terminology Drift Across Steps.**
Before referencing any class, method, or attribute from a previous step, verify the exact name by reading the source file. Names are exact — not approximate.

**9.3 — No Assumption Accumulation.**
All assumptions use the literal prefix `# ASSUMPTION:` so they can be grep’d. If a new step encounters the same ambiguity, use the same interpretation as the first step that resolved it. During verification, search for all `# ASSUMPTION:` comments and verify none contradict each other.

### Category 10 — Regression Prevention

**10.1 — No Behavioral Regression on Modification.**
When modifying code from a previous step: read the entire existing function first, identify behaviors to preserve, make the minimum change, run ALL existing tests. Never rewrite an entire function when the spec only asks to add one behavior.

**10.2 — No Signature Changes Without Caller Audit.**
When changing any function signature: `grep -r "function_name" src/ tests/` to find all callers. Update every caller. During verification, list all callers and confirm each was updated.

**10.3 — No Test Regression Tolerance.**
Zero test failures tolerated. If a test fails after a code change: determine if the test or code is wrong, fix accordingly, never delete or skip a failing test without replacement.

### Category 11 — Import and Dependency Hygiene

**11.1 — No Circular Import Chains.**
The dependency direction within `gitlab/` is strict:

```
exceptions.py       ← depends on nothing (within gitlab/)
client.py           ← depends on exceptions
rate_limiter.py     ← depends on nothing (within gitlab/)
pagination.py       ← depends on nothing (within gitlab/)
retry.py            ← depends on client, rate_limiter, exceptions
mappers.py          ← depends on nothing (within gitlab/)
fetchers.py         ← depends on client, pagination, retry, rate_limiter, mappers, exceptions
work_items.py       ← depends on client, retry, rate_limiter, pagination, mappers
webhooks.py         ← depends on mappers
```

After every step: `python -c "import delivery_intelligence.gitlab"` must succeed.

**11.2 — No Wrong-Direction Dependencies.**
Dependencies flow downward only: `gitlab/` → `models/`, `core/`, `config/`. The only exception: `core/container.py` imports from `gitlab/` for construction.

**11.3 — No Unused Imports.**
Every import must be used. Never add an import “for future use.”

### Category 12 — Log Level Semantics

**12.1 — Log Level Contract:**

|Level     |Use When                                                                                |
|----------|----------------------------------------------------------------------------------------|
|`DEBUG`   |Request/response details, pagination progress, cache hits, internal state changes       |
|`INFO`    |System startup, fetch summaries, detection results, shutdown                            |
|`WARNING` |Pre-emptive throttling, unknown enum defaults, approaching rate limits, retries starting|
|`ERROR`   |Mapping failures, exhausted retries, rate limit exceeded, webhook validation failures   |
|`CRITICAL`|Authentication failure, missing production config, container init failure               |

### Category 13 — Temporal Coupling Prevention

**13.1 — No Hidden Call-Order Dependencies.**
If function B requires function A first, B must verify this and fail loudly. The Container manages initialization order — individual components don’t enforce among each other.

**13.2 — No Time-Sensitive Defaults.**
Timestamps must be generated at call time, never at import or definition time. Never use module-level `datetime.now()`.

### Category 14 — Dead Code and Unreachable Paths

**14.1 — No Dead Code.**
Every function must have a caller. Every variable must be read. Every branch must be reachable.

**14.2 — No Defensive Code Against Impossible States.**
Defensive checks are for external inputs and state transitions. Do not check conditions the type system already prevents.

### Category 15 — String and URL Construction

**15.1 — No Manual URL Assembly.**
API paths are relative starting with `/`. For keyset pagination absolute URLs, use `urllib.parse.urlparse()` — never regex or string splitting.

**15.2 — No String-Based Query Parameter Assembly.**
Query parameters must be `dict` objects passed to `params`. Never concatenate into URL strings.

### Category 16 — Exception Chain Discipline

**16.1 — Always Preserve Exception Chains.**
When re-raising a different exception type, always use `raise NewError(msg) from e`. Never lose the original traceback.

**16.2 — No Bare Except Clauses.**
Always catch specific exception types. `except Exception` only in top-level handlers (`main.py`) and `asyncio.gather()` result processing.

### Category 17 — Test Isolation

**17.1 — No Test Pollution.**
Every test sets up its own state and tears it down. Use `monkeypatch` for env vars. Rate limiter and work item cache must not leak between tests.

**17.2 — No Test Interdependencies.**
Every test must pass when run alone: `pytest path/to/test.py::test_name -v`.

**17.3 — No Time-Dependent Tests.**
Assert timestamp properties (`.tzinfo is not None`, `<= datetime.now(UTC)`), not exact values. Mock `datetime.now()` when exact values are needed.

### Category 18 — Memory and Performance Awareness

**18.1 — No Unbounded Accumulation.**
`paginate_all()` has a 1000-page safety ceiling. Document the memory limitation for very large projects.

**18.2 — No N+1 Request Patterns.**
Use list endpoints with filters when fetching many items. Use individual endpoints only when fetching specific items by ID.

### Category 19 — Secret Propagation Chains

**19.1 — No Indirect Secret Leakage.**
Never log raw `httpx` exception `str()` — it may contain headers with tokens. Log only sanitized fields: `type(e).__name__`, `status_code`, `str(e.request.url)`.

**19.2 — No Secrets in Dataclass/Model Repr.**
Any dataclass storing sensitive data must use `repr=False` on sensitive fields or define custom `__repr__`.

### Category 20 — Python Version Discipline

**20.1 — No Post-3.11 Features.**
Code must work on Python 3.11. Available: `datetime.fromisoformat()` with Z suffix, `StrEnum`, `Self` type. Not available: `type` statement (3.12+), `override` decorator (3.12+). Use `TypeAlias` from `typing` for type aliases.

-----

## Step-by-Step Implementation

-----

### Step 1 — Define Custom Exception Hierarchy

> **Status: `NOT_STARTED`**

#### Objective

Create a typed exception hierarchy that normalizes raw HTTP errors into actionable, domain-specific exceptions. This simplifies error handling in all downstream code — fetchers, Phase 2 consumers, and eventually the reporting layer.

#### Instructions

1. Add `respx>=0.21` to the `dev` optional dependencies in `pyproject.toml`. Run `pip install -e ".[dev]"` to install.
1. Create `src/delivery_intelligence/gitlab/__init__.py` that exports the public API of the package (will be extended in later steps).
1. Create `src/delivery_intelligence/gitlab/exceptions.py` containing:
   
   **`GitLabAPIError(Exception)`:**
- Base exception for all GitLab API errors.
- Constructor accepts: `message: str`, `status_code: int | None = None`, `response_body: str | None = None`, `request_url: str | None = None`, `correlation_id: str | None = None`.
- Stores all arguments as attributes.
- `__str__()` returns: `"GitLabAPIError({status_code}): {message} [correlation_id={correlation_id}]"`. Omits `correlation_id` part if `None`.
- Must never include tokens or auth headers in any attribute or string representation.
   
   **`GitLabAuthError(GitLabAPIError)`:**
- Raised on HTTP 401 (Unauthorized).
- Default message: `"Authentication failed. Verify your GitLab token."`.
- Must never include the token value in the error.
   
   **`GitLabForbiddenError(GitLabAPIError)`:**
- Raised on HTTP 403 (Forbidden).
- Default message: `"Access forbidden. Check project permissions."`.
   
   **`GitLabNotFoundError(GitLabAPIError)`:**
- Raised on HTTP 404 (Not Found).
- Default message: `"Resource not found."`.
- Constructor also accepts optional `resource_type: str` and `resource_id: int | str` for descriptive messages like `"Project 123 not found."`.
   
   **`GitLabRateLimitError(GitLabAPIError)`:**
- Raised on HTTP 429 (Rate Limited) when all retries are exhausted.
- Constructor also accepts: `retry_after: float | None = None`, `reset_at: float | None = None`.
- These values are extracted from response headers before raising.
   
   **`GitLabServerError(GitLabAPIError)`:**
- Raised on HTTP 5xx after all retries are exhausted.
- Captures the final status code.
   
   **`GitLabConnectionError(GitLabAPIError)`:**
- Raised when all retries are exhausted on connection failures (timeouts, DNS, refused).
- Wraps the underlying `httpx` exception.
- Constructor accepts `cause: Exception` and stores it.
   
   **`raise_for_status(response: httpx.Response, correlation_id: str | None = None) -> None`:**
- Free function that inspects an `httpx.Response` and raises the appropriate typed exception.
- 2xx → returns (no exception).
- 401 → raises `GitLabAuthError`.
- 403 → raises `GitLabForbiddenError`.
- 404 → raises `GitLabNotFoundError`.
- 429 → raises `GitLabRateLimitError` (with `retry_after` and `reset_at` from headers).
- 5xx → raises `GitLabServerError`.
- Other 4xx → raises `GitLabAPIError` with the status code and response body (truncated to 500 chars).
- All raised exceptions include `status_code`, `request_url` (from `response.request.url` — safe, no tokens in URL path), and `correlation_id`.
1. Create `tests/test_gitlab/__init__.py` (empty).
1. Create `tests/test_gitlab/test_exceptions.py` with tests covering:
- Each exception type has correct attributes and string representation.
- `raise_for_status()` raises `GitLabAuthError` on 401.
- `raise_for_status()` raises `GitLabForbiddenError` on 403.
- `raise_for_status()` raises `GitLabNotFoundError` on 404.
- `raise_for_status()` raises `GitLabRateLimitError` on 429 with parsed `retry_after`.
- `raise_for_status()` raises `GitLabServerError` on 500, 502, 503.
- `raise_for_status()` does not raise on 200, 201.
- `GitLabNotFoundError` with `resource_type` and `resource_id` produces a descriptive message.
- `GitLabConnectionError` wraps the cause exception.
- No exception `str()` or `repr()` contains token values.

#### Acceptance Criteria

- Every HTTP error code has a typed exception with structured attributes.
- `raise_for_status()` maps status codes to the correct exception type.
- Correlation IDs are threaded into exceptions for traceability.
- No exception reveals tokens or auth headers.
- Downstream code (retry, fetcher) can catch specific exception types for targeted handling.

#### Validation Commands

```bash
pip install -e ".[dev]"
pytest tests/test_gitlab/test_exceptions.py -v
ruff check src/delivery_intelligence/gitlab/exceptions.py
mypy src/delivery_intelligence/gitlab/exceptions.py
```

#### Files Created or Modified

- `pyproject.toml` (add `respx` to dev dependencies)
- `src/delivery_intelligence/gitlab/__init__.py`
- `src/delivery_intelligence/gitlab/exceptions.py`
- `tests/test_gitlab/__init__.py`
- `tests/test_gitlab/test_exceptions.py`

-----

### Step 2 — Build Async GitLab HTTP Client

> **Status: `NOT_STARTED`**

#### Objective

Create the foundational async HTTP client that all GitLab API calls will flow through. This client wraps `httpx.AsyncClient` with authentication, tiered timeouts, structured logging with correlation IDs, request metrics, and connection lifecycle management.

#### Timeout Tiering Strategy

|Tier             |Default Value               |Used For                                    |
|-----------------|----------------------------|--------------------------------------------|
|`default_timeout`|`settings.timeout` (30s)    |Single-resource fetches, metadata calls     |
|`long_timeout`   |`settings.timeout * 2` (60s)|Paginated list endpoints with large payloads|

#### Instructions

1. Create `src/delivery_intelligence/gitlab/client.py` containing:
   
   **`RequestMetrics` dataclass:**
- `total_requests: int = 0`
- `successful_requests: int = 0`
- `retries: int = 0`
- `rate_limit_waits: int = 0`
- `failures: int = 0`
   
   **`GitLabClient` class:**
- Constructor accepts: `auth: GitLabAuth`, `settings: GitLabSettings`, and optional `http_client: httpx.AsyncClient | None = None`.
- If `http_client` is `None`, creates its own `httpx.AsyncClient` with: `base_url` from `auth.get_base_url()`, `headers` from `auth.get_headers()`, `timeout` from `httpx.Timeout(settings.timeout)`, `limits` from `httpx.Limits(max_connections=20, max_keepalive_connections=10)`.
- If `http_client` is provided (for testing), use it directly.
- Stores `default_timeout = settings.timeout` and `long_timeout = settings.timeout * 2`.
- Stores a logger via `get_logger("gitlab.client")`.
- Initializes `metrics: RequestMetrics`.
- Tracks whether the client owns the `httpx.AsyncClient`.
   
   **`async request(method: str, path: str, params: dict[str, Any] | None = None, timeout: float | None = None, correlation_id: str | None = None) -> httpx.Response`:**
- If `correlation_id` is `None`, generates one via `uuid.uuid4().hex[:12]`.
- `path` is relative to base URL (e.g., `/projects/123/issues`).
- If `timeout` is provided, overrides the client default for this request.
- Logs request at `DEBUG`: method, path, params (secrets never logged), correlation_id.
- Executes request. Increments `metrics.total_requests`.
- Logs response at `DEBUG`: status code, path, response time in ms, correlation_id.
- If 2xx: increments `metrics.successful_requests`.
- Returns raw `httpx.Response`. Does NOT call `raise_for_status()` — retry layer handles that.
- On `httpx.HTTPError`: logs at `ERROR` with correlation_id, increments `metrics.failures`, re-raises.
   
   **`async get(path: str, params: dict[str, Any] | None = None, timeout: float | None = None, correlation_id: str | None = None) -> httpx.Response`:**
- Convenience method: calls `self.request("GET", path, params, timeout, correlation_id)`.
   
   **`get_metrics() -> RequestMetrics`:** Returns a copy of current metrics.
   
   **`async close() -> None`:** Closes owned client. Does NOT close injected client. Logs at `INFO`.
   
   **`async __aenter__()` / `async __aexit__()`:** Context manager support.
1. Create `tests/test_gitlab/conftest.py` with fixtures: `gitlab_settings`, `gitlab_auth`, `mock_transport`.
1. Create `tests/test_gitlab/test_client.py` covering: construction, GET requests, logging with correlation_id, error handling, close lifecycle, metrics, timeout tiering.

#### Acceptance Criteria

- Client sends requests to correct URL with auth headers.
- Connection errors are logged and re-raised.
- Tokens never appear in log output.
- `respx` mocking works with injected `http_client`.
- Metrics track all request outcomes.
- Correlation IDs attached to every log entry.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_client.py -v
ruff check src/delivery_intelligence/gitlab/ tests/test_gitlab/
mypy src/delivery_intelligence/gitlab/client.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/client.py`
- `tests/test_gitlab/conftest.py`
- `tests/test_gitlab/test_client.py`

-----

### Step 3 — Implement Pagination Support

> **Status: `NOT_STARTED`**

#### Objective

Build a pagination engine that transparently fetches all pages, handling both offset and keyset pagination, yielding results as async iterators. Pagination is decoupled from retry and rate-limiting — it accepts a request function, not a client.

#### Critical Design Rule — Request Function Injection

`paginate()` accepts a `request_fn: Callable` — NOT a `GitLabClient` instance. The request function signature is:

```python
RequestFn = Callable[[str, str, dict[str, Any] | None], Awaitable[httpx.Response]]
# (method, path, params) -> Response
```

**`paginate()` must NEVER import or reference `GitLabClient`, `retry_request`, or `RateLimiter` directly.**

#### Instructions

1. Create `src/delivery_intelligence/gitlab/pagination.py` containing:
   
   **Type alias:** `RequestFn = Callable[[str, str, dict[str, Any] | None], Awaitable[httpx.Response]]`
   
   **`PaginatedResponse` dataclass:**
- `items: list[dict[str, Any]]`, `page: int`, `per_page: int`, `total: int | None`, `total_pages: int | None`, `next_page: int | None`, `next_url: str | None`, `has_next: bool`.
   
   **`parse_pagination_headers(response: httpx.Response) -> PaginatedResponse`:**
- Extracts pagination metadata from headers. Parses body as JSON list.
- Parses `x-page`, `x-per-page`, `x-total`, `x-total-pages`, `x-next-page` — all optional, safe defaults.
- Parses `Link` header for `rel="next"` URL.
- `has_next = True` if `next_page` or `next_url` is set.
   
   **`async paginate(request_fn: RequestFn, path: str, params: dict[str, Any] | None = None, per_page: int = 100, max_pages: int | None = None) -> AsyncIterator[list[dict[str, Any]]]`:**
- Async generator yielding one page at a time.
- Calls `await request_fn("GET", path, page_params)` per page.
- For keyset pagination: parses absolute `next_url` to extract relative path and query params using `urllib.parse.urlparse()`.
- Safety ceiling: 1000 pages. Logs `WARNING` if hit.
   
   **`async paginate_all(request_fn: RequestFn, ...) -> list[dict[str, Any]]`:**
- Collects all pages into a flat list.
1. Create `tests/fixtures/gitlab/paginated_response.json`.
1. Create `tests/test_gitlab/test_pagination.py` covering: single-page, multi-page offset, keyset via Link header, max_pages, missing headers, empty response, safety ceiling, `paginate_all`, zero coupling to client/retry/rate-limit.

#### Acceptance Criteria

- Accepts `request_fn` callable, not a client.
- Both pagination modes work. Missing headers don’t crash.
- Safety ceiling prevents runaway pagination.
- Zero coupling to retry or rate-limit modules.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_pagination.py -v
ruff check src/delivery_intelligence/gitlab/pagination.py
mypy src/delivery_intelligence/gitlab/pagination.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/pagination.py`
- `tests/test_gitlab/test_pagination.py`
- `tests/fixtures/gitlab/paginated_response.json`

-----

### Step 4 — Add Rate-Limit Handling

> **Status: `NOT_STARTED`**

#### Objective

Build a rate-limit handler that detects GitLab rate-limit headers, pauses when limits are approaching or exhausted, and resumes after the reset window. Tracks wait events for metrics.

#### Instructions

1. Create `src/delivery_intelligence/gitlab/rate_limiter.py` containing:
   
   **`RateLimitState` dataclass:** `limit`, `remaining`, `reset_at`, `retry_after` — all `int | None` or `float | None`.
   
   **`RateLimiter` class:**
- Constructor: `buffer_threshold: int = 5`.
- Logger: `get_logger("gitlab.rate_limiter")`.
- Internal `_state: RateLimitState`, `_wait_count: int = 0`.
   
   **`update(response: httpx.Response) -> None`:** Parse rate-limit headers. Parse `Retry-After` on 429. Log at `DEBUG`/`WARNING`.
   
   **`async wait_if_needed() -> bool`:** Returns `True` if slept, `False` otherwise. Handles: 429 retry-after, remaining=0, pre-emptive throttle below buffer. Logs at `INFO` with wait duration and reason.
   
   **`is_rate_limited() -> bool`**, **`get_state() -> RateLimitState`**, **`get_wait_count() -> int`**.
1. Create `tests/test_gitlab/test_rate_limiter.py` covering: header parsing, sleep on remaining=0, retry-after on 429, immediate return when healthy, pre-emptive throttle, `_wait_count`, missing headers.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_rate_limiter.py -v
ruff check src/delivery_intelligence/gitlab/rate_limiter.py
mypy src/delivery_intelligence/gitlab/rate_limiter.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/rate_limiter.py`
- `tests/test_gitlab/test_rate_limiter.py`

-----

### Step 5 — Add Retry Logic

> **Status: `NOT_STARTED`**

#### Objective

Build retry with exponential backoff and jitter. Uses custom exceptions from Step 1, integrates with rate limiter from Step 4.

#### Retryable: 429, 500, 502, 503, 504, `ConnectTimeout`, `ReadTimeout`, `ConnectError`.

#### Not retryable: 400, 401, 403, 404, other 4xx.

#### Instructions

1. Create `src/delivery_intelligence/gitlab/retry.py` containing:
   
   **`RetryConfig` dataclass:** `max_retries`, `base_delay=1.0`, `max_delay=60.0`, `exponential_base=2.0`, `jitter=True`.
   
   **`calculate_delay(attempt: int, config: RetryConfig) -> float`:** Exponential with optional jitter (0.5–1.5 multiplier). Capped at `max_delay`.
   
   **`is_retryable_status(status_code: int) -> bool`**, **`is_retryable_exception(exc: Exception) -> bool`**.
   
   **`async retry_request(client: GitLabClient, method: str, path: str, params: dict[str, Any] | None = None, config: RetryConfig | None = None, rate_limiter: RateLimiter | None = None, timeout: float | None = None, correlation_id: str | None = None) -> httpx.Response`:**
- Generates consistent `correlation_id` across all retries.
- Before each attempt: `rate_limiter.wait_if_needed()` → if True, increments `client.metrics.rate_limit_waits`.
- After each response: `rate_limiter.update(response)`.
- Retryable response: log `WARNING`, increment `client.metrics.retries`, sleep, retry.
- Retryable exception: log `WARNING`, increment `client.metrics.retries`, sleep, retry.
- Exhausted retries on HTTP error: raise typed exception via `raise_for_status()`, increment `client.metrics.failures`.
- Exhausted retries on connection error: raise `GitLabConnectionError`, increment `client.metrics.failures`.
- Non-retryable 4xx: `raise_for_status()` immediately, increment `client.metrics.failures`.
- Success: return response.
1. Create `tests/test_gitlab/test_retry.py` covering: success first attempt, retry on 500, exhausted retries (raises `GitLabServerError`), retry on timeout, no retry on 401 (`GitLabAuthError`), no retry on 404 (`GitLabNotFoundError`), 429 with rate limiter, delay calculations, jitter, metrics, consistent correlation_id.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_retry.py -v
ruff check src/delivery_intelligence/gitlab/retry.py
mypy src/delivery_intelligence/gitlab/retry.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/retry.py`
- `tests/test_gitlab/test_retry.py`

-----

### Step 6 — Build Response Mappers

> **Status: `NOT_STARTED`**

#### Objective

Build mappers that transform raw GitLab JSON into Phase 0 domain models. Handle field extraction, type coercion, enum mapping, datetime parsing, missing optional fields.

#### Mapping Rules (apply to ALL mappers)

1. Datetimes: Parse ISO 8601 → timezone-aware `datetime`. `UTCDatetime` validator handles UTC normalization.
1. Enums: Map GitLab states to Phase 0 enums. Unknown → safe default + `WARNING` log.
1. Optional fields: Missing/null → `None`. Never empty strings as sentinels.
1. IDs: Always `int`. Coerce strings.
1. Nested objects: Flatten (e.g., `author.id` → `author_id`).
1. Unknown fields: Silently ignored.
1. Validation failures: Log `ERROR` with entity type/ID, raise `ValueError`.

#### Instructions

1. Create `src/delivery_intelligence/gitlab/mappers.py` with:
   
   **`map_project(raw)`**, **`map_issue(raw)`**, **`map_merge_request(raw)`**, **`map_pipeline(raw)`**, **`map_milestone(raw)`**, **`map_contributor(raw)`**, **`parse_datetime(value)`**, **`parse_date(value)`**.
   
   Detailed field mappings are specified in the v1.1 Step 6 instructions (retained here by reference — the mappings are unchanged).
   
   Key mappings:
- Issue state: `"opened"` → `OPEN`, `"closed"` → `CLOSED`. Unknown → `OPEN`.
- Priority: Extract from labels with `"priority::"` prefix (case-insensitive).
- MR state: adds `"merged"` → `MERGED`, `"locked"` → `LOCKED`.
- Pipeline status: case-insensitive map to `PipelineStatus`. Unknown → `CREATED`.
- `changes_count`: coerce string to `int`.
- `assignee_ids`/`reviewer_ids`: extract from `assignees`/`reviewers` list.
- `author_id`: extract from `author.id`.
- `milestone_id`/`pipeline_id`: extract from nested object `.id`.
1. Create JSON fixtures in `tests/fixtures/gitlab/`: `project.json`, `issue.json`, `merge_request.json`, `pipeline.json`, `milestone.json`, `contributor.json`.
1. Create `tests/test_gitlab/test_mappers.py` covering: valid mapping per fixture, missing optionals, unknown enum states, nested extraction, priority from labels, datetime Z suffix, changes_count coercion, invalid data raises ValueError, serialization round-trip.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_mappers.py -v
ruff check src/delivery_intelligence/gitlab/mappers.py
mypy src/delivery_intelligence/gitlab/mappers.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/mappers.py`
- `tests/fixtures/gitlab/*.json` (6 fixture files)
- `tests/test_gitlab/test_mappers.py`

-----

### Step 7 — Build Entity Fetchers

> **Status: `NOT_STARTED`**

#### Objective

Build high-level fetchers combining client, pagination, retry, rate limiter, and mappers. Uses concurrency-limited parallel fetching and the locked request flow architecture.

#### Critical Design Rule — Request Function Construction

Each fetcher constructs a `request_fn` that wraps `retry_request()`, then passes it to `paginate()`:

```python
async def _make_request(method: str, path: str, params: dict | None = None) -> httpx.Response:
    return await retry_request(
        client=self._client, method=method, path=path, params=params,
        config=self._retry_config, rate_limiter=self._rate_limiter,
        timeout=self._client.long_timeout,
    )
items = await paginate_all(_make_request, path, params, per_page=self._per_page)
```

**Fetchers must NEVER call `client.get()` or `client.request()` directly.**

#### Concurrency: `_MAX_CONCURRENT_FETCHES: int = 5`

#### Instructions

1. Create `src/delivery_intelligence/gitlab/fetchers.py` containing:
   
   **`FetchResult` dataclass:** `items: list[BaseEntity]`, `failures: int`, `total_raw: int`.
   
   **`GitLabFetcher` class:** Constructor takes `client`, `rate_limiter`, `retry_config`, `per_page`.
   
   **`_make_request_fn(timeout: float | None = None) -> RequestFn`:** Returns callable wrapping `retry_request()`.
   
   **Fetcher methods** (all return `FetchResult` except `fetch_project` which returns `Project`):
- `fetch_project(project_id)` — single resource, `default_timeout`, raises `GitLabNotFoundError` on 404.
- `fetch_projects(project_ids | None, owned, membership)` — list or individual.
- `fetch_issues(project_id, state?, updated_after?)` — paginated.
- `fetch_merge_requests(project_id, state?, updated_after?)` — paginated.
- `fetch_pipelines(project_id, ref?, updated_after?)` — paginated.
- `fetch_milestones(project_id, state?)` — paginated.
- `fetch_contributors(project_id)` — paginated.
- `fetch_all_project_data(project_id)` — concurrent with `asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)`, `asyncio.gather(*tasks, return_exceptions=True)`. Failed fetches → empty `FetchResult` + `ERROR` log.
1. Create `tests/test_gitlab/test_fetchers.py` covering: all fetchers with mocked responses, 404 handling, pagination, filters, mapping failures, empty responses, semaphore, request flow through `retry_request`.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_fetchers.py -v
ruff check src/delivery_intelligence/gitlab/fetchers.py
mypy src/delivery_intelligence/gitlab/fetchers.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/fetchers.py`
- `tests/test_gitlab/test_fetchers.py`

-----

### Step 8 — Implement Work Item Detection

> **Status: `NOT_STARTED`**

#### Objective

Detect whether the target GitLab supports Work Items. Cache results per project for container lifetime.

#### Caching Strategy

- Cache: `dict[int, WorkItemDetectionResult]` keyed by `project_id`.
- Lifetime: container lifetime (in-memory only).
- Hit: return immediately, no API call.
- Invalidation: `Container.shutdown()`.

#### Instructions

1. Create `src/delivery_intelligence/gitlab/work_items.py` containing:
   
   **`WorkItemSupport` str enum:** `ISSUES_ONLY`, `WORK_ITEMS_AVAILABLE`, `UNKNOWN`.
   
   **`WorkItemDetectionResult` dataclass:** `support`, `work_item_types: list[str]`, `message: str`, `detected_at: datetime`.
   
   **`WorkItemDetector` class:** Constructor takes `client`, `rate_limiter`, `retry_config`. Maintains `_cache: dict[int, WorkItemDetectionResult]`.
   
   **`async detect(project_id) -> WorkItemDetectionResult`:** Cache check → API probe (`max_retries=1`) → 200=AVAILABLE, 404/400=ISSUES_ONLY, other=UNKNOWN. Non-fatal. Cache result.
   
   **`get_cached_result(project_id)`, `clear_cache()`.**
   
   **`async fetch_work_items(project_id, per_page) -> list[Issue]`:** Maps to Issue domain models.
1. Create `tests/fixtures/gitlab/work_items_response.json`.
1. Create `tests/test_gitlab/test_work_items.py` covering: detection results, cache hit/miss, clear_cache, fetch mapping, non-fatal failure.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_work_items.py -v
ruff check src/delivery_intelligence/gitlab/work_items.py
mypy src/delivery_intelligence/gitlab/work_items.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/work_items.py`
- `tests/fixtures/gitlab/work_items_response.json`
- `tests/test_gitlab/test_work_items.py`

-----

### Step 9 — Implement Webhook Ingestion

> **Status: `NOT_STARTED`**

#### Objective

Build webhook payload parsers with ordering metadata per Invariant 2. Parsing only — no HTTP server.

#### Event Types: Push, Issue, Merge Request, Pipeline, Note.

#### Instructions

1. Create `src/delivery_intelligence/gitlab/webhooks.py` containing:
   
   **`WebhookEvent` str enum:** `PUSH`, `ISSUE`, `MERGE_REQUEST`, `PIPELINE`, `NOTE`, `UNKNOWN`.
   
   **`WebhookPayload` dataclass:** `event_type`, `project_id: int`, `object_kind: str`, `action: str | None`, `raw: dict`, `received_at: datetime` (UTC arrival time), `entity_updated_at: datetime | None` (authoritative state timestamp per Invariant 2).
   
   **`parse_webhook_event(headers, body) -> WebhookPayload`:** Maps `X-Gitlab-Event` header. Extracts `project_id`, `object_kind`, `action`. Sets `received_at` to `datetime.now(UTC)`. Extracts `entity_updated_at` from `object_attributes.updated_at`. Unknown events → `UNKNOWN` + `WARNING` log.
   
   **`validate_webhook_token(headers, expected_token) -> bool`:** `hmac.compare_digest()`. Never logs token values.
   
   **`map_webhook_to_model(payload) -> BaseEntity | None`:** ISSUE → `map_issue()`, MR → `map_merge_request()`, PIPELINE → `map_pipeline()`. PUSH/NOTE/UNKNOWN → `None`. Failure → log `ERROR`, raise `ValueError`.
1. Create webhook fixture files (4).
1. Create `tests/test_gitlab/test_webhooks.py` covering: event parsing, unknown events, missing project_id, received_at, entity_updated_at, token validation, model mapping, malformed payloads.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_webhooks.py -v
ruff check src/delivery_intelligence/gitlab/webhooks.py
mypy src/delivery_intelligence/gitlab/webhooks.py
```

#### Files Created or Modified

- `src/delivery_intelligence/gitlab/webhooks.py`
- `tests/fixtures/gitlab/webhook_*.json` (4 files)
- `tests/test_gitlab/test_webhooks.py`

-----

### Step 10 — Register GitLab Client in Container

> **Status: `NOT_STARTED`**

#### Objective

Extend the container to provide GitLab client, fetcher, rate limiter, and work item detector as managed dependencies.

#### Instructions

1. Modify `src/delivery_intelligence/core/container.py`:
- Add private attributes: `_gitlab_client`, `_rate_limiter`, `_fetcher`, `_work_item_detector` (all `None` initially).
- In `initialize()`: create RateLimiter, GitLabClient, RetryConfig, GitLabFetcher, WorkItemDetector. Log “GitLab client initialized” with base URL (no token).
- Add accessors: `get_gitlab_client()`, `get_fetcher()`, `get_rate_limiter()`, `get_work_item_detector()` — all require `_initialized`.
- Add `async detect_work_items(project_id)` — delegates to detector.
- Make `shutdown()` async: close GitLab client, clear work item cache, set attributes to None.
1. Update `main.py` for async shutdown if needed.
1. Update `gitlab/__init__.py` with complete exports.
1. Update `tests/conftest.py` with `test_gitlab_client` and `test_fetcher` fixtures.
1. Extend `tests/test_core/test_container.py`: new accessors work, pre-init raises RuntimeError, shutdown closes client and clears cache, all Phase 0 tests pass.

#### Validation Commands

```bash
pytest tests/test_core/test_container.py -v
pytest tests/ -v
ruff check src/ tests/
mypy src/delivery_intelligence/core/container.py
mypy src/delivery_intelligence/gitlab/
```

#### Files Created or Modified

- `src/delivery_intelligence/core/container.py` (extended)
- `src/delivery_intelligence/main.py` (minor update)
- `src/delivery_intelligence/gitlab/__init__.py` (exports)
- `tests/conftest.py` (new fixtures)
- `tests/test_core/test_container.py` (extended)

-----

### Step 11 — Integration Test and Response Normalization Validation

> **Status: `NOT_STARTED`**

#### Objective

End-to-end integration test validating the entire pipeline: client → retry → rate-limit → pagination → fetch → map → domain model.

#### Instructions

1. Create `tests/test_gitlab/test_integration.py` containing:
   
   **`test_full_fetch_pipeline`** — Mocked endpoints with pagination, one 429, one 503. Calls `fetch_all_project_data()`. Asserts typed models, UTC datetimes, enum values, item counts, request metrics.
   
   **`test_webhook_to_domain_model_pipeline`** — Parse webhook, verify `received_at` and `entity_updated_at`, map to model, assert valid.
   
   **`test_graceful_degradation_on_mapping_failures`** — Mix of valid/invalid items. Assert `FetchResult.failures` counts skipped items.
   
   **`test_work_item_detection_integration`** — Detect with 200, detect again (cache hit — verify via `respx` call count), detect different project with 404.
   
   **`test_container_lifecycle`** — Init → use → shutdown → verify RuntimeError on post-shutdown access.
   
   **`test_request_flow_invariant`** — Mock 503→200. Verify `metrics.retries >= 1`, `metrics.total_requests >= 2`.
   
   **`test_concurrency_limit`** — Verify `fetch_all_project_data()` respects semaphore.
   
   **Response normalization contract tests:** Every entity has minimum required fields for Phase 2 populated: `id`, `iid` (where applicable), `project_id`, `title` (where applicable), `state`/`status`, `created_at`, `updated_at`.

#### Acceptance Criteria

- Full pipeline works end-to-end. Rate limiting, retries, pagination integrate per Invariant 1.
- Metrics reflect all interactions. Webhook ordering metadata present.
- Graceful degradation verified. Work item caching verified.
- Container lifecycle verified. Concurrency semaphore effective.
- Phase 2 normalization contract validated.
- All Phase 0 tests still pass.

#### Validation Commands

```bash
pytest tests/test_gitlab/test_integration.py -v
pytest tests/ -v
ruff check src/ tests/
mypy src/delivery_intelligence/gitlab/
```

#### Files Created or Modified

- `tests/test_gitlab/test_integration.py`

-----

## Phase 1 Completion Checklist

|# |Check                                                                                              |Verified|
|--|---------------------------------------------------------------------------------------------------|--------|
|1 |All Phase 1 directories and files exist                                                            |`NO`    |
|2 |`pip install -e ".[dev]"` succeeds with `respx`                                                    |`NO`    |
|3 |`python -c "import delivery_intelligence.gitlab"` succeeds                                         |`NO`    |
|4 |Custom exception hierarchy maps all HTTP error codes                                               |`NO`    |
|5 |`raise_for_status()` raises typed exceptions with correlation IDs                                  |`NO`    |
|6 |`GitLabClient` constructs and closes without errors                                                |`NO`    |
|7 |GET requests use correct auth headers and base URL                                                 |`NO`    |
|8 |Connection errors logged and re-raised                                                             |`NO`    |
|9 |Metrics track total, success, retry, rate-limit, failure counts                                    |`NO`    |
|10|Correlation IDs on every request log entry                                                         |`NO`    |
|11|Timeout tiering available and configurable                                                         |`NO`    |
|12|Pagination accepts `request_fn` callable — NOT client                                              |`NO`    |
|13|Offset pagination works correctly                                                                  |`NO`    |
|14|Keyset pagination follows `Link` header                                                            |`NO`    |
|15|Pagination safety ceiling (1000 pages) enforced                                                    |`NO`    |
|16|Rate-limit headers parsed from responses                                                           |`NO`    |
|17|Rate limiter sleeps when `remaining` is 0                                                          |`NO`    |
|18|Rate limiter handles `Retry-After` on 429                                                          |`NO`    |
|19|Pre-emptive throttling below buffer threshold                                                      |`NO`    |
|20|`wait_if_needed()` returns bool for metrics                                                        |`NO`    |
|21|Retry on 500, 502, 503, 504                                                                        |`NO`    |
|22|Retry on connection timeouts                                                                       |`NO`    |
|23|No retry on 401, 403, 404                                                                          |`NO`    |
|24|Exponential backoff with jitter                                                                    |`NO`    |
|25|Exhausted retries raise typed exceptions                                                           |`NO`    |
|26|All mappers produce valid domain models                                                            |`NO`    |
|27|Datetimes are timezone-aware UTC after mapping                                                     |`NO`    |
|28|Unknown enums → safe defaults + warnings                                                           |`NO`    |
|29|Missing optional fields don’t crash                                                                |`NO`    |
|30|Malformed input → `ValueError`                                                                     |`NO`    |
|31|`fetch_project()` returns mapped `Project`                                                         |`NO`    |
|32|`fetch_issues()` returns `FetchResult` with failures count                                         |`NO`    |
|33|`fetch_merge_requests()` returns `FetchResult`                                                     |`NO`    |
|34|`fetch_pipelines()` returns `FetchResult`                                                          |`NO`    |
|35|`fetch_milestones()` returns `FetchResult`                                                         |`NO`    |
|36|`fetch_contributors()` returns `FetchResult`                                                       |`NO`    |
|37|`fetch_all_project_data()` concurrent with semaphore                                               |`NO`    |
|38|All fetcher requests through `retry_request()`                                                     |`NO`    |
|39|Mapping failures skip items, not crash batches                                                     |`NO`    |
|40|Work item detection: `ISSUES_ONLY` on 404                                                          |`NO`    |
|41|Work item detection: `WORK_ITEMS_AVAILABLE` on 200                                                 |`NO`    |
|42|Work item detection: non-fatal `UNKNOWN` on error                                                  |`NO`    |
|43|Work item detection cached per project                                                             |`NO`    |
|44|Cache prevents redundant API calls                                                                 |`NO`    |
|45|Webhook events parsed from headers                                                                 |`NO`    |
|46|Webhook token validation constant-time                                                             |`NO`    |
|47|Webhooks include `received_at` and `entity_updated_at`                                             |`NO`    |
|48|Webhooks map to domain models                                                                      |`NO`    |
|49|Unknown webhooks don’t crash                                                                       |`NO`    |
|50|Container: `get_gitlab_client()`, `get_fetcher()`, `get_rate_limiter()`, `get_work_item_detector()`|`NO`    |
|51|Container `shutdown()` closes client, clears cache                                                 |`NO`    |
|52|All Phase 0 tests pass                                                                             |`NO`    |
|53|All Phase 1 tests pass                                                                             |`NO`    |
|54|`ruff check src/ tests/` clean                                                                     |`NO`    |
|55|No circular imports                                                                                |`NO`    |
|56|Tokens never in logs, repr, errors                                                                 |`NO`    |
|57|Integration test: full pipeline end-to-end                                                         |`NO`    |
|58|Integration test: request flow invariant                                                           |`NO`    |
|59|Integration test: concurrency semaphore                                                            |`NO`    |
|60|Phase 2 normalization contract validated                                                           |`NO`    |

-----

## Status Summary

|Step   |Name                                         |Status       |Last Updated|
|-------|---------------------------------------------|-------------|------------|
|Step 1 |Define Custom Exception Hierarchy            |`NOT_STARTED`|—           |
|Step 2 |Build Async GitLab HTTP Client               |`NOT_STARTED`|—           |
|Step 3 |Implement Pagination Support                 |`NOT_STARTED`|—           |
|Step 4 |Add Rate-Limit Handling                      |`NOT_STARTED`|—           |
|Step 5 |Add Retry Logic                              |`NOT_STARTED`|—           |
|Step 6 |Build Response Mappers                       |`NOT_STARTED`|—           |
|Step 7 |Build Entity Fetchers                        |`NOT_STARTED`|—           |
|Step 8 |Implement Work Item Detection                |`NOT_STARTED`|—           |
|Step 9 |Implement Webhook Ingestion                  |`NOT_STARTED`|—           |
|Step 10|Register GitLab Client in Container          |`NOT_STARTED`|—           |
|Step 11|Integration Test and Normalization Validation|`NOT_STARTED`|—           |

**Phase 1 Overall Status: `NOT_STARTED`**

-----

## Implementation Advice (Read Before Starting)

1. Follow the spec literally. Do not infer extra features.
1. Keep Phase 1 data-ingestion only. No analytics, no persistence, no caching (except Work Item detection).
1. Every API call must go through `retry_request()` which integrates the rate limiter. No raw `client.get()` in fetchers. Violating this is a critical defect per Invariant 1.
1. Pagination accepts a `request_fn` callable, not a client. This is the locked architecture.
1. Use `respx` for all HTTP mocking. Do not mock `httpx` internals directly.
1. Keep secrets masked everywhere. Tokens never appear in logs, repr, str, exceptions, or test output.
1. All async code uses `pytest-asyncio` with `@pytest.mark.asyncio`.
1. Test edge cases aggressively. Empty responses, missing fields, malformed JSON, network failures, rate limits, pagination boundaries.
1. Mappers must be resilient. One bad record does not crash the batch. Track failures in `FetchResult`.
1. Avoid circular imports. Follow the dependency direction in Guardrail 11.1.
1. Do not modify Phase 0 domain models unless a step explicitly permits it.
1. JSON fixtures must match real GitLab API structure. Do not invent field names.
1. Update the status table only after code, tests, lint, mypy, AND verification protocol all pass.
1. Use typed exceptions from Step 1 everywhere. Never raise raw `httpx.HTTPStatusError`.
1. Attach correlation IDs to every request. Thread through logs, retries, and exceptions.
1. Run the full Verification Protocol (8 categories, max 5 iterations) before marking any step COMPLETE.
1. Apply the Silent Error Prevention Policy to every `try/except` block. Every failure = log + caller signal.
1. Follow all 52 Guardrails. When in doubt: raise. It is always safer to surface an error loudly than to hide it quietly.

-----

## Rules for the LLM Coder

1. **Execute steps in order.** Do not jump ahead.
1. **Run the Verification Protocol** after tests pass — before marking `COMPLETE`.
1. **Update the status table** after completing each step.
1. **Run all validation commands.** All must pass before marking `COMPLETE`.
1. **Never use f-strings in log calls.** Always use structlog’s key-value binding.
1. **Never expose secrets.** Token values must never appear in logs, repr, str, or error messages.
1. **Use type hints everywhere.** Every function signature must be fully typed.
1. **Write defensive code.** Validate inputs. Handle errors explicitly. Fail loudly on bad state.
1. **Keep functions small.** One function, one responsibility.
1. **Write meaningful docstrings.** Every public class and function gets a docstring explaining what it does.
1. **No placeholder code.** Every line must be production-ready. No `pass`, no `TODO`, no `# implement later`.
1. **No global mutable state.** Configuration and dependencies flow through the container.
1. **Test edge cases.** Empty responses, missing fields, rate limits, pagination edges, malformed payloads.
1. **Do not introduce frameworks, libraries, or tools not listed in the Technology Stack.**
1. **Do not create files or modules not listed in the Directory Structure.**
1. **All Phase 0 tests must still pass after every step.**
1. **No silent errors.** Every failure produces both a structured log entry AND a caller-visible signal. Catching an exception and returning a default that looks like success is a critical defect. When in doubt: raise.
1. **Re-read source files before each step.** Do not reference classes, methods, or attributes from memory. Verify exact names from the actual code.
1. **Follow all 52 Guardrails** in the LLM Coder Operating Manual above. They are mandatory, not advisory.

-----

## What Comes Next

After Phase 1 is complete, Phase 2 (Project State Engine) begins. Phase 2 will:

- Consume the `FetchResult` instances produced by Phase 1 fetchers
- Build and maintain a structured, in-memory project state
- Track relationships between entities (issues → milestones, MRs → pipelines, etc.)
- Implement incremental update mechanisms using webhook events from Phase 1, respecting the out-of-order delivery contract (Invariant 2) by comparing `entity_updated_at` timestamps
- Store normalized state for consumption by the Time-Series Engine (Phase 3), Dependency Graph Engine (Phase 4), and all downstream phases
- Use the container to access the fetcher, work item detector, and all Phase 0/1 infrastructure
- Optionally persist Work Item detection results to avoid re-probing on restart

Every decision made in Phase 1 directly enables Phase 2. Reliable data ingestion is the foundation of all intelligence.
