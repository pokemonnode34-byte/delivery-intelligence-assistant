# Phase 0 — Foundations (Authoritative Spec v2.1 — FROZEN)

## Document Purpose

This document is the authoritative instruction set for Phase 0 of the AI Delivery Intelligence Assistant project. It is written for an LLM coder that will implement each step sequentially. Every step includes precise requirements, expected file outputs, acceptance criteria, a definition of done, a validation command checklist, and a development status tracker.

**Do not skip steps. Do not reorder steps. Each step depends on the one before it.**

-----

## Phase 0 Overview

**Goal:** Create the infrastructure skeleton that every subsequent phase (1–11) will depend on.

**What this phase produces:**

- A clean, modular project structure
- A typed configuration system with environment support
- Structured logging across all modules
- Secure environment and secrets management
- GitLab API authentication scaffolding
- Base domain models for all core entities
- A configuration loader with validation
- A dependency injection pattern for testability

**What this phase does NOT produce:**

- No GitLab API calls (that is Phase 1)
- No business logic or analytics
- No LLM integration
- No UI or CLI interface
- No database ORM or migrations
- No async code unless explicitly required by a step

-----

## Anti-Drift Rules

The LLM coder must not introduce anything outside the defined scope. Specifically:

1. **Do not add frameworks not listed in the Technology Stack.** No FastAPI, no Click, no Typer, no SQLAlchemy, no Celery, no Redis.
1. **Do not add CLI entry points.** The only entry point is `main.py` with `bootstrap()`.
1. **Do not add database ORM or migrations.** `DatabaseSettings` is a placeholder only.
1. **Do not add async code in Phase 0.** All code is synchronous unless a step explicitly says otherwise.
1. **Do not create utility modules, helper files, or “common” packages.** If it is not in the directory structure, do not create it.
1. **Do not add third-party logging libraries** beyond `structlog`. No `loguru`, no `rich` logging.
1. **Do not add API endpoint code.** No HTTP servers, no route handlers.
1. **Do not rename modules, restructure directories, or deviate from the defined project layout.**

If a step does not mention it, do not build it.

-----

## Technology Stack

|Component           |Choice                                             |Rationale                                           |
|--------------------|---------------------------------------------------|----------------------------------------------------|
|Language            |Python 3.11+                                       |Type hints, async support, ecosystem                |
|Type Checking       |Pydantic v2                                        |Runtime validation, serialization, schema generation|
|Configuration       |Pydantic Settings v2 + YAML                        |Typed config with environment override support      |
|Logging             |Python `logging` + `structlog`                     |Structured, parameterized, JSON-capable logging     |
|Dependency Injection|Manual constructor injection                       |Simple, explicit, no magic frameworks               |
|Testing             |pytest                                             |Standard, extensible, fixture-based                 |
|Environment         |python-dotenv                                      |`.env` file loading with override rules             |
|Package Management  |pip with pyproject.toml                            |Editable install, no Poetry required in Phase 0     |
|HTTP Client         |httpx (dependency declared, not used until Phase 1)|Async-capable, modern API                           |
|Linting             |ruff                                               |Fast, comprehensive Python linter                   |
|Type Checker        |mypy                                               |Static type verification                            |

**Install path for this project:** `pip install -e ".[dev]"` using pyproject.toml optional dependencies. Do not use Poetry. Do not use setup.py.

-----

## Development Status Legend

Each step tracks its status using the following values. The LLM must update the status after completing each step.

|Status        |Meaning                                                |
|--------------|-------------------------------------------------------|
|`NOT_STARTED` |Work has not begun                                     |
|`IN_PROGRESS` |Implementation is underway                             |
|`COMPLETE`    |Code written, tests passing, lint clean, status updated|
|`BLOCKED`     |Cannot proceed — dependency or issue documented        |
|`NEEDS_REVIEW`|Code written but requires human review                 |

-----

## File Ownership Boundaries

Each package has a strict responsibility scope. Code must not bleed across boundaries.

|Package     |Owns                                                                 |Does NOT Own                                            |
|------------|---------------------------------------------------------------------|--------------------------------------------------------|
|`config/`   |Settings models, YAML loading, config merging, validation            |Logging setup, auth logic, domain models                |
|`core/`     |Logging infrastructure, environment detection, API auth, DI container|Business logic, data models, GitLab API calls           |
|`models/`   |Normalized domain entities, enums, validation rules                  |API response parsing, persistence, serialization formats|
|`gitlab/`   |(Empty in Phase 0) Will own API client, response mapping             |Everything — not populated until Phase 1                |
|`engines/`  |(Empty in Phase 0) Will own analytics engines                        |Everything — not populated until Phase 2+               |
|`llm/`      |(Empty in Phase 0) Will own LLM integration                          |Everything — not populated until Phase 8                |
|`reporting/`|(Empty in Phase 0) Will own report generation                        |Everything — not populated until Phase 10               |

-----

## Definition of Done (applies to every step)

A step is `COMPLETE` only when ALL of the following are true:

1. All code for the step is written and saved.
1. All tests for the step are written and saved.
1. All tests pass: `pytest {test_path} -v`
1. No import errors: `python -c "import delivery_intelligence"`
1. No lint errors on touched files: `ruff check src/ tests/`
1. Type checking passes on touched files: `mypy src/delivery_intelligence/{module}`
1. Status table is updated to `COMPLETE` with the current date.

If any item fails, the step remains `IN_PROGRESS` until resolved.

-----

## Project Directory Structure

This is the target directory layout after Phase 0 is complete. The LLM must create this structure in Step 1 and populate it progressively through Steps 2–8.

```
delivery-intelligence/
├── pyproject.toml
├── README.md
├── .env.example
├── .gitignore
├── config/
│   ├── default.yaml
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
├── src/
│   └── delivery_intelligence/
│       ├── __init__.py
│       ├── main.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── loader.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── logging.py
│       │   ├── environment.py
│       │   ├── auth.py
│       │   └── container.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── project.py
│       │   ├── issue.py
│       │   ├── merge_request.py
│       │   ├── pipeline.py
│       │   ├── milestone.py
│       │   └── contributor.py
│       ├── gitlab/
│       │   └── __init__.py
│       ├── engines/
│       │   └── __init__.py
│       ├── llm/
│       │   └── __init__.py
│       └── reporting/
│           └── __init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_config/
    │   ├── __init__.py
    │   └── test_settings.py
    ├── test_core/
    │   ├── __init__.py
    │   ├── test_logging.py
    │   ├── test_environment.py
    │   ├── test_auth.py
    │   └── test_container.py
    └── test_models/
        ├── __init__.py
        └── test_models.py
```

-----

## Step-by-Step Implementation

-----

### Step 1 — Define Project Structure

> **Status: `NOT_STARTED`**

#### Objective

Create the full directory layout, `pyproject.toml`, and all `__init__.py` files so the project is importable and installable from day one.

#### Instructions

1. Create every directory listed in the Project Directory Structure above.
1. Create empty `__init__.py` files in every Python package directory.
1. Create `pyproject.toml` with the following specification:
- Project name: `delivery-intelligence`
- Version: `0.1.0`
- Python requirement: `>=3.11`
- Core dependencies: `pydantic>=2.0`, `pydantic-settings>=2.0`, `pyyaml>=6.0`, `structlog>=23.0`, `python-dotenv>=1.0`, `httpx>=0.27`
- Optional dev dependencies under `[project.optional-dependencies] dev`: `pytest>=8.0`, `pytest-asyncio>=0.23`, `pytest-cov>=4.0`, `mypy>=1.8`, `ruff>=0.3`
- Source layout: `src/delivery_intelligence` via `[tool.setuptools.packages.find] where = ["src"]`
- Install command: `pip install -e ".[dev]"`
1. Create `.gitignore` covering: `__pycache__/`, `*.pyc`, `.env`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `dist/`, `*.egg-info/`, `.venv/`, `*.db`
1. Create `.env.example` with documented placeholder keys:
   
   ```
   # Environment: development | staging | production
   DI_ENV=development
   # GitLab Configuration
   DI_GITLAB__URL=https://gitlab.example.com
   DI_GITLAB__TOKEN=your-private-token-here
   # Logging
   DI_LOGGING__LEVEL=INFO
   DI_LOGGING__FORMAT=console
   ```
1. Create `README.md` with: project name, one-line description, setup instructions using `pip install -e ".[dev]"`, and a note that this is Phase 0.

#### Acceptance Criteria

- Running `pip install -e ".[dev]"` from project root succeeds.
- Running `python -c "import delivery_intelligence"` succeeds without error.
- All directories exist and contain `__init__.py` where required.
- `.gitignore` covers all standard Python artifacts.
- `.env.example` contains documented placeholders.

#### Validation Commands

```bash
pip install -e ".[dev]"
python -c "import delivery_intelligence"
ruff check src/ tests/
```

#### Files Created

- `pyproject.toml`
- `README.md`
- `.env.example`
- `.gitignore`
- All `__init__.py` files across the package tree

-----

### Step 2 — Setup Configuration System

> **Status: `NOT_STARTED`**

#### Objective

Build a typed, validated configuration system that supports multiple environments, YAML files, and environment variable overrides using a single consistent pattern.

#### Configuration Override Pattern (Authoritative)

This is the exact mechanism for configuration resolution. The LLM must implement this pattern and no other.

**Priority order (highest wins):**

1. Environment variables (via Pydantic Settings `env_prefix` and `env_nested_delimiter`)
1. Environment-specific YAML file (e.g., `production.yaml`)
1. Default YAML file (`default.yaml`)
1. Pydantic field defaults

**Implementation pattern:**

- `AppSettings` extends `pydantic_settings.BaseSettings` (not plain `BaseModel`).
- The config loader (Step 7) loads YAML files into a `dict`, merges them, and passes the merged dict into `AppSettings(**merged_dict)`.
- Pydantic Settings automatically applies environment variable overrides on top during model initialization.
- This means: YAML values are passed as constructor arguments, and env vars override them via Pydantic Settings internals.
- The loader does NOT manually read environment variables. That is Pydantic Settings’ job.
- **Fallback:** If direct constructor-based environment override behavior proves inconsistent during implementation, implement a custom `settings_customise_sources` method in `AppSettings` to control source priority explicitly, rather than manually reading environment variables in the loader.

#### Instructions

1. Create `src/delivery_intelligence/config/settings.py` containing:
   
   **GitLabSettings** (extends `BaseModel`):
- `url: str` — Base GitLab instance URL, not API URL. Example: `https://gitlab.example.com`. The API path (`/api/v4`) is NOT part of this value. It will be assembled by the auth/client layer.
- `token: SecretStr` — Private access token. Never logged or serialized in plain text.
- `api_version: str = "v4"` — API version string.
- `timeout: int = 30` — Request timeout in seconds. Must be > 0.
- `max_retries: int = 3` — Retry attempts. Must be >= 0.
- `per_page: int = 100` — Pagination page size. Must be between 1 and 100 inclusive.
- Add a `field_validator` for `url` that strips trailing slashes.
- Add a `field_validator` for `per_page` that enforces range 1–100.
- Add a `field_validator` for `timeout` that enforces > 0.
   
   **LoggingSettings** (extends `BaseModel`):
- `level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"` — Constrained to valid Python logging levels. Not a plain `str`. Invalid values will be rejected by Pydantic automatically.
- `format: Literal["json", "console"] = "json"` — Output format.
- `output: Literal["stdout", "file"] = "stdout"` — Output destination.
- `file_path: Optional[Path] = None` — Required only when `output="file"`.
- Add a `model_validator` that raises `ValueError` if `output="file"` and `file_path` is `None`.
   
   **DatabaseSettings** (extends `BaseModel`):
- `url: str = "sqlite:///delivery_intelligence.db"` — Placeholder for future persistence. Not used in Phase 0.
- `echo: bool = False`
   
   **AppSettings** (extends `pydantic_settings.BaseSettings`):
- `env: Literal["development", "staging", "production"] = "development"`
- `app_name: str = "delivery-intelligence"`
- `version: str = "0.1.0"`
- `debug: bool = False`
- `gitlab: GitLabSettings = GitLabSettings(url="https://gitlab.example.com", token=SecretStr("not-set"))`
- `logging: LoggingSettings = LoggingSettings()`
- `database: DatabaseSettings = DatabaseSettings()`
- Model config: `env_prefix = "DI_"`, `env_nested_delimiter = "__"`, `case_sensitive = False`
1. All sub-settings (`GitLabSettings`, `LoggingSettings`, `DatabaseSettings`) extend plain `BaseModel`, NOT `BaseSettings`. Only `AppSettings` extends `BaseSettings`.
1. The default `token` value `"not-set"` is intentional. It allows `AppSettings()` to instantiate in development without a real token. Environment validation (Step 4) will enforce real tokens in staging/production.

#### Acceptance Criteria

- `AppSettings()` can be instantiated with default values in development mode.
- Setting `DI_GITLAB__URL=https://custom.gitlab.com` overrides the default URL.
- Setting `DI_LOGGING__LEVEL=DEBUG` overrides the logging level.
- Setting `DI_LOGGING__LEVEL=INVALID` raises `ValidationError`.
- `GitLabSettings.token` is never exposed as plain text in `repr()` or `str()`.
- `AppSettings.model_dump()` serializes cleanly (token value is masked via `SecretStr`).
- `LoggingSettings(output="file", file_path=None)` raises `ValidationError`.
- `GitLabSettings(url="https://gitlab.example.com/", ...)` stores URL without trailing slash.
- `GitLabSettings(per_page=200)` raises `ValidationError`.

#### Validation Commands

```bash
pytest tests/test_config/test_settings.py -v
ruff check src/delivery_intelligence/config/
mypy src/delivery_intelligence/config/settings.py
```

#### Files Created or Modified

- `src/delivery_intelligence/config/settings.py`
- `tests/test_config/test_settings.py`

-----

### Step 3 — Setup Logging

> **Status: `NOT_STARTED`**

#### Objective

Establish structured, parameterized logging that every module in the system will use. Logging must be consistent, configurable, production-ready, and idempotent.

#### Instructions

1. Create `src/delivery_intelligence/core/logging.py` containing:
   
   **`setup_logging(settings: LoggingSettings) -> None`**
- Configures `structlog` with processors for:
  - Timestamp injection (ISO 8601 UTC)
  - Log level injection
  - Logger name injection
  - Sensitive field redaction (see below)
  - JSON rendering for `format="json"`
  - Pretty console rendering for `format="console"`
- Integrates with Python stdlib `logging` so third-party libraries route through structlog.
- Sets the root logger level based on `settings.level`.
- **Must be idempotent.** Calling `setup_logging()` multiple times must not add duplicate handlers or processors. Use a module-level `_logging_configured: bool` flag. If already configured, log a debug message and return immediately. Provide a `force: bool = False` parameter to re-initialize if explicitly needed (e.g., during tests).
   
   **`get_logger(name: str) -> structlog.BoundLogger`**
- Returns a structlog bound logger with the `logger_name` key pre-attached.
- Does NOT cache loggers. The structlog framework handles this internally. The container does NOT need to cache logger instances.
   
   **Sensitive field redaction processor:**
- Implement a custom structlog processor function.
- Any key in the log event whose name contains: `token`, `password`, `secret`, `authorization`, `credential` (case-insensitive check) must have its value replaced with `"****REDACTED****"`.
- This processor runs before the final renderer.
1. Logging must use parameterized key-value messages. Never use f-strings or `.format()` in log calls.
   
   ```python
   # CORRECT
   logger.info("processing_project", project_id=project_id, status="active")
   
   # WRONG — never do this
   logger.info(f"Processing project {project_id}")
   ```
1. Every log entry in JSON mode must include: `timestamp`, `level`, `logger_name`, `event`, and any bound context.

#### Acceptance Criteria

- `setup_logging()` configures structlog without errors.
- `get_logger("test")` returns a logger that outputs structured JSON in production mode.
- Console mode produces human-readable output.
- Sensitive field names are redacted in output.
- **Calling `setup_logging()` twice does not produce duplicate log entries.** This is a critical test.
- **Tests must reset logging state between test cases when needed.** Use the `force=True` parameter or reset the `_logging_configured` flag in test fixtures to avoid flaky test interactions.
- A unit test validates: logger creation, JSON output structure, sensitive field redaction, idempotency (call setup twice then log once — verify only one output line).

#### Validation Commands

```bash
pytest tests/test_core/test_logging.py -v
ruff check src/delivery_intelligence/core/logging.py
mypy src/delivery_intelligence/core/logging.py
```

#### Files Created or Modified

- `src/delivery_intelligence/core/logging.py`
- `tests/test_core/test_logging.py`

-----

### Step 4 — Setup Environment Management

> **Status: `NOT_STARTED`**

#### Objective

Build a robust environment management module that handles `.env` loading, environment detection, secret validation, and fail-fast behavior on missing required values.

#### Instructions

1. Create `src/delivery_intelligence/core/environment.py` containing:
   
   **`load_environment() -> str`**
- Loads `.env` file using `python-dotenv` if present. Does not fail if `.env` is absent.
- Reads the `DI_ENV` environment variable. Defaults to `"development"` if not set.
- Validates that the value is one of: `"development"`, `"staging"`, `"production"`. Raises `ValueError` if invalid.
- Returns the environment name as a string.
   
   **`validate_required_env_vars(env: str) -> None`**
- Defines required variables per environment:
  - `development`: **no required vars** — the system runs with defaults. Missing GitLab credentials produce a warning log, not an error.
  - `staging`: `DI_GITLAB__URL`, `DI_GITLAB__TOKEN`
  - `production`: `DI_GITLAB__URL`, `DI_GITLAB__TOKEN`
- Checks each required variable exists in `os.environ` and is non-empty.
- If any are missing, raises `EnvironmentError` with a message listing **ALL** missing variables, not just the first.
- **Explicit behavior:** `validate_required_env_vars("development")` always succeeds. It never raises, regardless of what variables are set or missing. It may log warnings for missing GitLab credentials.
   
   **`get_environment_summary() -> dict[str, str]`**
- Returns a dict with: `env`, `python_version`, `platform`, `debug`.
- All values are strings. `debug` is stringified as `"true"` or `"false"` (reads `DI_DEBUG` or defaults to `"false"`).
- Must never include secret values. Only variable names, never values.
1. The module must never print or log secret values. Error messages reference variable names only.

#### Acceptance Criteria

- `load_environment()` returns `"development"` when no `DI_ENV` is set.
- `load_environment()` raises `ValueError` for `DI_ENV=invalid`.
- `validate_required_env_vars("development")` succeeds even when no env vars are set.
- `validate_required_env_vars("production")` raises `EnvironmentError` when `DI_GITLAB__TOKEN` is missing.
- Error message from production validation lists all missing vars.
- `get_environment_summary()` returns a clean dict with no secrets.

#### Validation Commands

```bash
pytest tests/test_core/test_environment.py -v
ruff check src/delivery_intelligence/core/environment.py
mypy src/delivery_intelligence/core/environment.py
```

#### Files Created or Modified

- `src/delivery_intelligence/core/environment.py`
- `tests/test_core/test_environment.py`

-----

### Step 5 — Setup API Authentication

> **Status: `NOT_STARTED`**

#### Objective

Create a secure, reusable authentication module for GitLab API access. This module does not make API calls — it prepares and validates credentials for use by the GitLab client in Phase 1.

#### Instructions

1. Create `src/delivery_intelligence/core/auth.py` containing:
   
   **`GitLabAuth` class:**
- Constructor accepts: `token: SecretStr`, `url: str`, `api_version: str = "v4"`
- All attributes are set in `__init__` and must not have public setter methods. The object is effectively immutable after construction.
- **`get_headers() -> dict[str, str]`** — Returns `{"PRIVATE-TOKEN": token.get_secret_value()}`. The plain token is computed on each call, never stored as a plain string attribute.
- **`get_base_url() -> str`** — Returns the full API base URL assembled from `url` and `api_version`. Example: if `url="https://gitlab.example.com"` and `api_version="v4"`, returns `"https://gitlab.example.com/api/v4"`. Handles trailing slashes on `url` gracefully.
- **`validate() -> bool`** — Returns `True` if token is non-empty (after `get_secret_value()`) and URL is non-empty. Does not make network calls. Network validation belongs in Phase 1.
- **`__repr__() -> str`** — Returns `GitLabAuth(url=https://..., api_version=v4, token=****)`. Token is always masked.
- **`__str__() -> str`** — Same as `__repr__`.
   
   **`create_auth(settings: GitLabSettings) -> GitLabAuth`** — Factory function that constructs `GitLabAuth` from `GitLabSettings`, passing `url`, `token`, and `api_version`.
1. The token must never be logged, printed, or serialized in plain text anywhere.
1. `api_version` is included in `GitLabAuth` because it is part of the connection context, not business logic.

#### Acceptance Criteria

- `GitLabAuth` can be constructed from `GitLabSettings` via `create_auth()`.
- `get_headers()` returns the correct authentication header with the real token value.
- `get_base_url()` returns `"https://gitlab.example.com/api/v4"` for default settings.
- `get_base_url()` handles trailing slashes: `url="https://gitlab.example.com/"` still returns a clean URL without double slashes.
- `repr()` and `str()` never expose the token value.
- `validate()` returns `False` for empty token (`SecretStr("")`).
- `validate()` returns `True` for valid token and URL.

#### Validation Commands

```bash
pytest tests/test_core/test_auth.py -v
ruff check src/delivery_intelligence/core/auth.py
mypy src/delivery_intelligence/core/auth.py
```

#### Files Created or Modified

- `src/delivery_intelligence/core/auth.py`
- `tests/test_core/test_auth.py`

-----

### Step 6 — Define Base Domain Models

> **Status: `NOT_STARTED`**

#### Objective

Define the core domain models that represent GitLab entities in the system’s own language. These are normalized, typed, validated objects used by every engine from Phase 2 onward.

#### Critical Design Rules

These rules apply to ALL models in this step:

1. **Immutability:** All domain models use `frozen=True` in model config. Mutations happen by creating new instances via `model.model_copy(update={...})`.
1. **No partial construction:** All required fields must be provided at instantiation. Normalization and mapping happen BEFORE model construction, not after. Phase 1 will build mapper functions that transform raw GitLab API responses into fully populated model instances.
1. **UTC enforcement:** All `datetime` fields must use timezone-aware UTC datetimes. Implement a reusable `field_validator` (or use `BeforeValidator` in `Annotated` type) on every `datetime` field across all models that:
- Rejects naive datetimes (no timezone info) with a clear `ValueError`
- Normalizes timezone-aware non-UTC datetimes to UTC (converts, does not reject)
- Passes through UTC datetimes unchanged
1. **Serialization:** `model_dump()` and `model_dump_json()` must preserve timezone-aware ISO 8601 format for all datetime fields.
1. **IDs are always `int`.** Never `str`.
1. **`Optional` fields default to `None`.** Never empty strings or zero as sentinel values.
1. **List defaults must use `Field(default_factory=list)`.** Never use bare `= []` as a default value. This applies to every `list` field across all models. Example: `labels: list[str] = Field(default_factory=list)`.

#### Instructions

1. Create `src/delivery_intelligence/models/base.py` containing:
- A `BaseEntity` class extending Pydantic `BaseModel` with shared config: `from_attributes = True`, `populate_by_name = True`, `frozen = True`.
- A reusable `UTCDatetime` annotated type that applies the UTC validation/normalization described above. All datetime fields across all models must use this type instead of plain `datetime`.
- A `TimestampMixin` (as a BaseModel) providing `created_at: UTCDatetime`, `updated_at: UTCDatetime`.
- An `EntityStatus` str enum: `OPEN`, `CLOSED`, `MERGED`, `LOCKED`, `IN_PROGRESS`, `BLOCKED`.
- A `Priority` str enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE`.
- A `RiskLevel` str enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `NONE`.
1. Create `src/delivery_intelligence/models/project.py`:
- `Project(BaseEntity)` with fields: `id: int`, `name: str`, `path_with_namespace: str`, `description: Optional[str] = None`, `web_url: str`, `default_branch: str = "main"`, `visibility: str`, `created_at: UTCDatetime`, `updated_at: UTCDatetime`, `last_activity_at: Optional[UTCDatetime] = None`.
1. Create `src/delivery_intelligence/models/issue.py`:
- `Issue(BaseEntity)` with fields: `id: int`, `iid: int`, `project_id: int`, `title: str`, `description: Optional[str] = None`, `state: EntityStatus`, `priority: Priority = Priority.NONE`, `labels: list[str] = Field(default_factory=list)`, `assignee_ids: list[int] = Field(default_factory=list)`, `author_id: int`, `milestone_id: Optional[int] = None`, `due_date: Optional[date] = None`, `weight: Optional[int] = None`, `time_estimate: Optional[int] = None` (seconds), `time_spent: Optional[int] = None` (seconds), `blocking_issues_count: int = 0`, `created_at: UTCDatetime`, `updated_at: UTCDatetime`, `closed_at: Optional[UTCDatetime] = None`.
1. Create `src/delivery_intelligence/models/merge_request.py`:
- `MergeRequest(BaseEntity)` with fields: `id: int`, `iid: int`, `project_id: int`, `title: str`, `description: Optional[str] = None`, `state: EntityStatus`, `source_branch: str`, `target_branch: str`, `author_id: int`, `assignee_ids: list[int] = Field(default_factory=list)`, `reviewer_ids: list[int] = Field(default_factory=list)`, `labels: list[str] = Field(default_factory=list)`, `milestone_id: Optional[int] = None`, `pipeline_id: Optional[int] = None`, `has_conflicts: bool = False`, `draft: bool = False`, `changes_count: Optional[int] = None`, `created_at: UTCDatetime`, `updated_at: UTCDatetime`, `merged_at: Optional[UTCDatetime] = None`, `closed_at: Optional[UTCDatetime] = None`.
1. Create `src/delivery_intelligence/models/pipeline.py`:
- `PipelineStatus` str enum: `CREATED`, `WAITING_FOR_RESOURCE`, `PREPARING`, `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELED`, `SKIPPED`, `MANUAL`, `SCHEDULED`.
- `Pipeline(BaseEntity)` with fields: `id: int`, `project_id: int`, `ref: str`, `sha: str`, `status: PipelineStatus`, `source: str`, `duration: Optional[int] = None` (seconds), `queued_duration: Optional[int] = None` (seconds), `started_at: Optional[UTCDatetime] = None`, `finished_at: Optional[UTCDatetime] = None`, `created_at: UTCDatetime`, `updated_at: UTCDatetime`.
1. Create `src/delivery_intelligence/models/milestone.py`:
- `MilestoneState` str enum: `ACTIVE`, `CLOSED`.
- `Milestone(BaseEntity)` with fields: `id: int`, `iid: int`, `project_id: int`, `title: str`, `description: Optional[str] = None`, `state: MilestoneState`, `due_date: Optional[date] = None`, `start_date: Optional[date] = None`, `expired: bool = False`, `created_at: UTCDatetime`, `updated_at: UTCDatetime`.
1. Create `src/delivery_intelligence/models/contributor.py`:
- `Contributor(BaseEntity)` with fields: `id: int`, `username: str`, `name: str`, `email: Optional[str] = None`, `avatar_url: Optional[str] = None`, `web_url: Optional[str] = None`, `is_active: bool = True`.
- Note: `Contributor` has no datetime fields. It still extends `BaseEntity` for config consistency.
1. Create `src/delivery_intelligence/models/__init__.py` that exports all models and enums:
   
   ```python
   from delivery_intelligence.models.base import BaseEntity, EntityStatus, Priority, RiskLevel, UTCDatetime
   from delivery_intelligence.models.project import Project
   from delivery_intelligence.models.issue import Issue
   from delivery_intelligence.models.merge_request import MergeRequest
   from delivery_intelligence.models.pipeline import Pipeline, PipelineStatus
   from delivery_intelligence.models.milestone import Milestone, MilestoneState
   from delivery_intelligence.models.contributor import Contributor
   ```

#### Future-Proofing Note

The models defined here use `Issue` as the primary planning entity because that matches the current GitLab scope. However, GitLab is evolving toward Work Items and Tasks as first-class entities. **Phase 1 must verify whether the target GitLab workspace uses Issues, Work Items, or Tasks, and must normalize them into internal planning entities without assuming Issues are the only work unit.** The domain models may need to be extended or abstracted at that point. Phase 0 does not solve this — it only acknowledges it.

#### Acceptance Criteria

- All models can be instantiated with valid data including timezone-aware UTC datetimes.
- Invalid data (wrong types, missing required fields) raises `ValidationError`.
- **Naive datetimes are rejected** with `ValidationError`.
- **Non-UTC timezone-aware datetimes are normalized to UTC** (e.g., `2024-01-01T12:00:00+05:00` becomes `2024-01-01T07:00:00+00:00`).
- `model_dump()` and `model_dump_json()` produce clean output with timezone-aware ISO 8601 datetimes.
- All enums serialize to their string value.
- Frozen models reject attribute assignment after construction.
- `model_copy(update={...})` creates modified copies correctly.

#### Validation Commands

```bash
pytest tests/test_models/test_models.py -v
ruff check src/delivery_intelligence/models/
mypy src/delivery_intelligence/models/
```

#### Files Created or Modified

- `src/delivery_intelligence/models/base.py`
- `src/delivery_intelligence/models/project.py`
- `src/delivery_intelligence/models/issue.py`
- `src/delivery_intelligence/models/merge_request.py`
- `src/delivery_intelligence/models/pipeline.py`
- `src/delivery_intelligence/models/milestone.py`
- `src/delivery_intelligence/models/contributor.py`
- `src/delivery_intelligence/models/__init__.py`
- `tests/test_models/test_models.py`

-----

### Step 7 — Create Configuration Loader

> **Status: `NOT_STARTED`**

#### Objective

Build a configuration loader that reads YAML files, merges environment-specific overrides, validates the result, and produces a fully typed `AppSettings` object. This is the single entry point for all configuration.

#### How It Works (Authoritative Flow)

```
1. load_environment() → detects env name (e.g., "production")
2. Load config/default.yaml → base dict
3. Load config/{env}.yaml → override dict (optional, may not exist)
4. Deep-merge: override dict over base dict → merged dict
5. Pass merged dict into AppSettings(**merged_dict)
6. Pydantic Settings applies env var overrides automatically during init
7. Validation runs → returns typed AppSettings or raises
```

The loader does NOT manually read environment variables. Pydantic Settings handles that internally when `AppSettings` is instantiated.

#### Instructions

1. Create `src/delivery_intelligence/config/loader.py` containing:
   
   **`load_yaml(path: Path) -> dict`**
- Reads a YAML file and returns its contents as a dict.
- Raises `FileNotFoundError` with a clear message including the file path if the file does not exist.
- Raises `ValueError` with a clear message if the YAML is malformed.
- Returns an empty dict if the file is empty.
   
   **`merge_configs(base: dict, override: dict) -> dict`**
- Deep-merges two config dicts. Override values replace base values.
- Nested dicts are merged recursively.
- Lists are replaced entirely, not appended.
- `None` values in override DO replace base values (explicit null).
- Returns a new dict — does not mutate inputs.
   
   **`load_settings(config_dir: Path | None = None, env: str | None = None) -> AppSettings`**
   1. Calls `load_environment()` to detect the environment (or uses the `env` parameter if provided).
   1. Resolves `config_dir` to the project’s `config/` directory if not provided.
   1. Loads `config/default.yaml` as the base config. This file MUST exist. Raise `FileNotFoundError` if missing.
   1. Loads `config/{env}.yaml` as the environment override. This file is OPTIONAL. If it does not exist, skip silently.
   1. Deep-merges environment config over default config.
   1. Passes the merged dict into `AppSettings(**merged_dict)`.
   1. Pydantic Settings applies environment variable overrides during this initialization.
   1. Logs the loaded configuration at `INFO` level with secrets masked.
   1. Returns the `AppSettings` instance.
1. Create `config/default.yaml`:
   
   ```yaml
   env: development
   app_name: delivery-intelligence
   version: "0.1.0"
   debug: false
   gitlab:
     url: "https://gitlab.example.com"
     token: "not-set"
     api_version: "v4"
     timeout: 30
     max_retries: 3
     per_page: 100
   logging:
     level: "INFO"
     format: "json"
     output: "stdout"
   database:
     url: "sqlite:///delivery_intelligence.db"
     echo: false
   ```
1. Create `config/development.yaml`:
   
   ```yaml
   debug: true
   logging:
     level: "DEBUG"
     format: "console"
   ```
1. Create `config/staging.yaml`:
   
   ```yaml
   env: staging
   logging:
     level: "INFO"
     format: "json"
   ```
1. Create `config/production.yaml`:
   
   ```yaml
   env: production
   logging:
     level: "WARNING"
     format: "json"
   ```

#### Acceptance Criteria

- `load_settings()` with no arguments returns a valid `AppSettings` with development defaults.
- `load_settings(env="production")` merges production overrides correctly (logging level is `WARNING`).
- `load_settings(env="development")` merges development overrides correctly (debug is `true`, logging format is `console`).
- Environment variables override YAML values (e.g., `DI_LOGGING__LEVEL=ERROR` overrides YAML).
- Missing environment-specific YAML files do not cause errors.
- Missing `default.yaml` raises `FileNotFoundError`.
- Malformed YAML raises `ValueError`.
- `merge_configs` does not mutate input dicts.
- Deep merge handles nested dicts correctly.

#### Validation Commands

```bash
pytest tests/test_config/test_settings.py -v
ruff check src/delivery_intelligence/config/
mypy src/delivery_intelligence/config/
```

#### Files Created or Modified

- `src/delivery_intelligence/config/loader.py`
- `config/default.yaml`
- `config/development.yaml`
- `config/staging.yaml`
- `config/production.yaml`
- `tests/test_config/test_settings.py` (extended with loader tests)

-----

### Step 8 — Setup Dependency Injection Pattern

> **Status: `NOT_STARTED`**

#### Objective

Create a dependency injection container that wires together configuration, logging, authentication, and future engine modules. This enables testability and module isolation across all phases.

#### Instructions

1. Create `src/delivery_intelligence/core/container.py` containing:
   
   **`Container` class:**
- Constructor accepts `settings: AppSettings` and stores it.
- Sets `_initialized: bool = False` in constructor.
- **`initialize() -> None`:**
   1. Calls `setup_logging(settings.logging)` — idempotent, safe to call again.
   1. Creates `GitLabAuth` via `create_auth(settings.gitlab)` and stores it.
   1. Gets a logger via `get_logger("container")` and logs a startup summary including: app name, version, environment. No secrets.
   1. Sets `_initialized = True`.
- **`get_settings() -> AppSettings`** — Returns settings. Does not require initialization (settings are available immediately).
- **`get_logger(name: str) -> BoundLogger`** — Returns `get_logger(name)` from the logging module. Does NOT cache logger instances — structlog manages this internally. Requires `_initialized` to be `True` (logging must be set up first).
- **`get_auth() -> GitLabAuth`** — Returns the stored `GitLabAuth` instance. Requires `_initialized`.
- **`_check_initialized() -> None`** — Private method. Raises `RuntimeError("Container not initialized. Call initialize() first.")` if `_initialized` is `False`. Called at the top of `get_logger()` and `get_auth()`.
- **`shutdown() -> None`** — Logs “Shutting down” and performs any future cleanup. Sets `_initialized = False`.
- The container must be designed for extension. In Phase 1, a GitLab client will be registered. In Phase 2+, engine instances will be added. Adding new dependencies must only require adding a new attribute and accessor method — no restructuring.
   
   **`create_container(settings: AppSettings) -> Container`** — Factory function that creates and returns a `Container`. Does NOT call `initialize()` — that is the caller’s responsibility.
1. Create `src/delivery_intelligence/main.py` containing:
   
   **`bootstrap(config_dir: Path | None = None) -> Container`:**
   1. Calls `load_environment()` to get the env name.
   1. Calls `validate_required_env_vars(env)` — succeeds silently in development.
   1. Calls `load_settings(config_dir=config_dir, env=env)` to get typed settings.
   1. Calls `create_container(settings)` to build the container.
   1. Calls `container.initialize()`.
   1. Logs `"Delivery Intelligence system initialized"` with environment and version.
   1. Returns the container.
   
   **`main() -> None`:**
- Calls `bootstrap()` inside a try/except.
- On success: logs that the system is ready.
- On `EnvironmentError`: logs the error and exits with code 1.
- On `Exception`: logs the unexpected error and exits with code 1.
- Guard: `if __name__ == "__main__": main()`
1. Create `tests/conftest.py` with shared fixtures:
- `test_settings` fixture: returns `AppSettings()` with development defaults.
- `test_container` fixture: returns an initialized `Container` with test settings.

#### Design Rules

- No global singletons. The container is passed explicitly to modules that need it.
- No service locator anti-pattern. Dependencies are accessed through typed methods, not string keys.
- Every dependency the container provides must be mockable in tests by constructing a container with substitute settings.

#### Acceptance Criteria

- `create_container(settings)` returns a functional container.
- `container.initialize()` completes without error in development mode.
- `container.get_auth()` returns a valid `GitLabAuth` instance.
- `container.get_logger("test")` returns a bound logger.
- Calling `container.get_auth()` before `initialize()` raises `RuntimeError` with a clear message.
- Calling `container.get_logger("test")` before `initialize()` raises `RuntimeError`.
- `container.get_settings()` works even before `initialize()`.
- `bootstrap()` runs end-to-end in development mode with no `.env` file.
- `bootstrap()` in production mode with missing env vars raises `EnvironmentError`.
- `shutdown()` sets `_initialized` to `False`.

#### Validation Commands

```bash
pytest tests/test_core/test_container.py -v
pytest tests/ -v  # full suite — all tests must still pass
ruff check src/ tests/
mypy src/delivery_intelligence/core/container.py
mypy src/delivery_intelligence/main.py
python -m delivery_intelligence.main  # bootstrap sanity check — must complete without error in development mode
```

#### Files Created or Modified

- `src/delivery_intelligence/core/container.py`
- `src/delivery_intelligence/main.py`
- `tests/conftest.py`
- `tests/test_core/test_container.py`

-----

## Phase 0 Completion Checklist

The LLM must verify every item below before declaring Phase 0 complete.

|# |Check                                                                           |Verified|
|--|--------------------------------------------------------------------------------|--------|
|1 |All directories and files from the project structure exist                      |`NO`    |
|2 |`pip install -e ".[dev]"` succeeds                                              |`NO`    |
|3 |`python -c "import delivery_intelligence"` succeeds                             |`NO`    |
|4 |`AppSettings()` loads with development defaults                                 |`NO`    |
|5 |Environment variable overrides work with `DI_` prefix                           |`NO`    |
|6 |`DI_LOGGING__LEVEL=INVALID` raises `ValidationError`                            |`NO`    |
|7 |`GitLabSettings.token` is never exposed in logs or repr                         |`NO`    |
|8 |Structured logging outputs valid JSON in production mode                        |`NO`    |
|9 |Console logging outputs readable format in development mode                     |`NO`    |
|10|Sensitive fields are redacted in log output                                     |`NO`    |
|11|`setup_logging()` called twice does not duplicate log entries                   |`NO`    |
|12|`.env` loading works when file exists                                           |`NO`    |
|13|Missing `.env` does not crash the system                                        |`NO`    |
|14|`validate_required_env_vars("development")` always succeeds                     |`NO`    |
|15|`validate_required_env_vars("production")` fails correctly when vars are missing|`NO`    |
|16|`GitLabAuth` masks token in `repr()`                                            |`NO`    |
|17|`GitLabAuth.get_base_url()` assembles URL from url + api_version correctly      |`NO`    |
|18|`GitLabAuth.get_base_url()` handles trailing slashes without double slashes     |`NO`    |
|19|All domain models instantiate with valid UTC datetimes                          |`NO`    |
|20|All domain models reject naive datetimes                                        |`NO`    |
|21|Non-UTC datetimes are normalized to UTC                                         |`NO`    |
|22|All domain models reject invalid data with `ValidationError`                    |`NO`    |
|23|All models serialize cleanly to dict and JSON                                   |`NO`    |
|24|Frozen models reject attribute mutation                                         |`NO`    |
|25|Config loader merges YAML files in correct priority order                       |`NO`    |
|26|Missing env-specific YAML does not crash                                        |`NO`    |
|27|Missing default.yaml raises `FileNotFoundError`                                 |`NO`    |
|28|`bootstrap()` runs end-to-end in development mode                               |`NO`    |
|29|`python -m delivery_intelligence.main` completes without error in development   |`NO`    |
|30|Container raises `RuntimeError` when accessed before `initialize()`             |`NO`    |
|31|`container.get_settings()` works before `initialize()`                          |`NO`    |
|32|All tests pass with `pytest tests/ -v`                                          |`NO`    |
|33|`ruff check src/ tests/` reports no errors                                      |`NO`    |
|34|No circular imports exist                                                       |`NO`    |

-----

## Status Summary

This table is the LLM’s progress tracker. Update it after completing each step.

|Step  |Name                              |Status       |Last Updated|
|------|----------------------------------|-------------|------------|
|Step 1|Define Project Structure          |`NOT_STARTED`|—           |
|Step 2|Setup Configuration System        |`NOT_STARTED`|—           |
|Step 3|Setup Logging                     |`NOT_STARTED`|—           |
|Step 4|Setup Environment Management      |`NOT_STARTED`|—           |
|Step 5|Setup API Authentication          |`NOT_STARTED`|—           |
|Step 6|Define Base Domain Models         |`NOT_STARTED`|—           |
|Step 7|Create Configuration Loader       |`NOT_STARTED`|—           |
|Step 8|Setup Dependency Injection Pattern|`NOT_STARTED`|—           |

**Phase 0 Overall Status: `NOT_STARTED`**

-----

## Implementation Advice (Read Before Starting)

1. Follow the spec literally. Do not infer extra features.
1. Keep Phase 0 infrastructure-only. No API calls, no async client, no analytics.
1. Prefer simple, explicit code over clever abstractions.
1. Use `Field(default_factory=list)` for all list defaults in models.
1. Keep secrets masked everywhere: logs, repr, str, exceptions, test output.
1. Make logging setup idempotent and make tests robust against repeated setup.
1. Treat UTC validation as strict: reject naive datetimes, normalize aware datetimes to UTC.
1. Avoid circular imports by keeping package boundaries strict:
- `config` does not import `core`
- `models` does not import `config`
- `core` does not import `gitlab`
1. Update the status table only after code, tests, lint, and mypy all pass.
1. Do not optimize for future phases at the cost of clarity in Phase 0.
1. Keep the design extensible for GitLab Tasks/Work Items in Phase 1; do not assume Issues are the only planning entity long-term.
1. If a spec detail is ambiguous, choose the most conservative, testable implementation and document the assumption briefly.

-----

## Rules for the LLM Coder

1. **Execute steps in order.** Do not jump ahead. Each step builds on the previous one.
1. **Update the status table** after completing each step.
1. **Run tests after each step.** Do not proceed if tests fail.
1. **Run the validation commands** listed in each step. All must pass before marking `COMPLETE`.
1. **Never use f-strings in log calls.** Always use structlog’s key-value binding.
1. **Never expose secrets.** Token values must never appear in logs, repr, str, or error messages.
1. **Use type hints everywhere.** Every function signature must be fully typed.
1. **Write defensive code.** Validate inputs. Handle errors explicitly. Fail loudly on bad state.
1. **Keep functions small.** One function, one responsibility.
1. **Write meaningful docstrings.** Every public class and function gets a docstring explaining what it does, not how.
1. **No placeholder code.** Every line must be production-ready. No `pass`, no `TODO`, no `# implement later`.
1. **No global mutable state.** Configuration and dependencies flow through the container.
1. **Test edge cases.** Empty strings, None values, missing files, invalid types, naive datetimes — test them all.
1. **Do not introduce frameworks, libraries, or tools not listed in the Technology Stack.**
1. **Do not create files or modules not listed in the Project Directory Structure.**

-----

## What Comes Next

After Phase 0 is complete, Phase 1 (GitLab Integration Layer) begins. Phase 1 will:

- **Verify whether the target GitLab workspace uses Issues, Work Items, or Tasks** and normalize them into internal planning entities without assuming Issues are the only work unit
- Build an async GitLab API client using `httpx`
- Register it in the container as a new dependency
- Use the domain models defined here as the target for response mapping
- Use the `GitLabAuth` module (including `api_version`) for all API authentication
- Use the logging system defined here for all operational logging
- Use the configuration system defined here for all client settings

Every decision made in Phase 0 directly enables Phase 1. This is why foundations matter.
