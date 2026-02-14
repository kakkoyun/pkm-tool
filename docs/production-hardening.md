# Production Hardening Plan

## Progress Tracking

| Task | Status | Phase | Priority | Notes |
|------|--------|-------|----------|-------|
| Create architecture documentation | ✅ Done | 1 | High | docs/architecture.md |
| Create testing documentation | ✅ Done | 1 | High | docs/testing.md |
| Create production hardening plan | ✅ Done | 1 | High | This document |
| Implement domain exception hierarchy | ⏳ Pending | 2 | High | Task #2 |
| Extract shared date parsing module | ⏳ Pending | 2 | Medium | Task #4 |
| Add security scanning (pip-audit, bandit) | ⏳ Pending | 3 | High | Task #3 |
| Add transport abstraction to create_http_client | ⏳ Pending | 3 | Medium | Task #5 |
| Add request/response logging | ⏳ Pending | 4 | Medium | Structured logging for HTTP |
| Add retry logic with exponential backoff | ⏳ Pending | 4 | High | Transient failure handling |
| Add circuit breaker pattern | ⏳ Pending | 4 | Medium | Prevent cascading failures |
| Add rate limiting for API calls | ⏳ Pending | 4 | Low | Respect API quotas |
| Add metrics collection | ⏳ Pending | 5 | Medium | Prometheus/OpenTelemetry |
| Add distributed tracing | ⏳ Pending | 5 | Low | OpenTelemetry integration |
| Add health check endpoint improvements | ⏳ Pending | 5 | Medium | Detailed health checks |
| Create deployment documentation | ⏳ Pending | 6 | High | Docker, systemd, etc. |
| Add configuration validation at startup | ⏳ Pending | 6 | High | Fail fast on invalid config |
| Add graceful shutdown handling | ⏳ Pending | 6 | Medium | Server mode cleanup |

**Legend:**
- ✅ Done
- 🚧 In Progress
- ⏳ Pending
- ❌ Blocked

## Phase 1: Documentation (COMPLETED)

**Goal:** Establish comprehensive technical documentation for developers and operators.

**Status:** ✅ All tasks completed

### Tasks

#### ✅ Task 1.1: Create Architecture Documentation

**File:** `docs/architecture.md`

**Content:**
- System overview and data flow
- Module responsibilities
- Source interface contract
- Authentication flow
- Error handling philosophy
- Extension points

**Completion criteria:**
- Document covers all major components
- Includes architecture diagram
- Explains design decisions
- Provides examples for adding new sources

#### ✅ Task 1.2: Create Testing Documentation

**File:** `docs/testing.md`

**Content:**
- Testing philosophy and strategy
- Test structure and organization
- Fixture patterns
- Mocking strategies (respx, pytest-mock)
- Coverage expectations
- How to add tests for new sources
- Running tests (make commands)

**Completion criteria:**
- Document explains testing approach
- Includes step-by-step guide for new source tests
- Documents all fixture modules
- Explains CI integration

#### ✅ Task 1.3: Create Production Hardening Plan

**File:** `docs/production-hardening.md`

**Content:**
- Phased implementation plan
- Task breakdown with priorities
- Dependency graph
- Progress tracking table
- Critical files reference

**Completion criteria:**
- Comprehensive plan with 6 phases
- Clear task descriptions
- Progress tracking mechanism
- Aligned with current codebase

## Phase 2: Error Handling Improvements

**Goal:** Implement structured exception hierarchy and improve error handling consistency.

**Priority:** High

**Dependencies:** None

### Tasks

#### ⏳ Task 2.1: Implement Domain Exception Hierarchy

**Files to create:**
- `src/pkm_tool/exceptions.py`

**Implementation:**

```python
"""Domain-specific exception hierarchy."""

class PKMToolError(Exception):
    """Base exception for all PKM Tool errors."""
    pass

class ConfigurationError(PKMToolError):
    """Configuration-related errors."""
    pass

class AuthenticationError(PKMToolError):
    """Authentication and credential errors."""
    pass

class SourceError(PKMToolError):
    """Base error for data source issues."""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"{source}: {message}")

class SourceUnavailableError(SourceError):
    """Source is temporarily unavailable."""
    pass

class SourceAuthenticationError(SourceError):
    """Source authentication failed."""
    pass

class SourceRateLimitError(SourceError):
    """Source rate limit exceeded."""
    pass

class SourceNotFoundError(SourceError):
    """Requested resource not found."""
    pass

class FormattingError(PKMToolError):
    """Output formatting errors."""
    pass

class ValidationError(PKMToolError):
    """Data validation errors."""
    pass
```

**Changes required:**
- Update all sources to raise specific exceptions
- Update aggregator to catch specific exceptions
- Add exception metadata to AggregatedData
- Update CLI to display user-friendly error messages
- Add tests for exception hierarchy

**Acceptance criteria:**
- All sources use domain exceptions
- Errors are logged with structured context
- User sees helpful error messages
- Tests verify exception behavior

#### ⏳ Task 2.2: Extract Shared Date Parsing Module

**Files to create:**
- `src/pkm_tool/date_utils.py`

**Implementation:**

```python
"""Shared date parsing and validation utilities."""

from datetime import date, datetime, timedelta
from typing import Any

from dateutil import parser as dateutil_parser

def parse_date(date_input: str | date | datetime) -> date:
    """
    Parse date from multiple formats.

    Supports:
    - Relative dates: "yesterday", "today", "tomorrow"
    - ISO format: "2025-11-21"
    - Natural language: "Nov 21, 2025", "21 Nov 2025"

    Args:
        date_input: Date string, date, or datetime object

    Returns:
        Parsed date object

    Raises:
        ValidationError: If date cannot be parsed
    """
    # Implementation from cli.py parse_date_input
    pass

def is_weekend(target_date: date) -> bool:
    """Check if date is a weekend (Saturday or Sunday)."""
    return target_date.weekday() in (5, 6)

def date_range(start: date, end: date, exclude_weekends: bool = False) -> list[date]:
    """
    Generate list of dates in range.

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        exclude_weekends: Skip Saturdays and Sundays

    Returns:
        List of dates in range
    """
    dates = []
    current = start
    while current <= end:
        if not exclude_weekends or not is_weekend(current):
            dates.append(current)
        current += timedelta(days=1)
    return dates

def format_date(target_date: date, template: str) -> str:
    """
    Format date using template variables.

    Supported variables:
    - {date}: ISO format (2025-11-21)
    - {day_abbr}: Day abbreviation (Mon, Tue, ...)
    - {day_name}: Full day name (Monday, Tuesday, ...)
    - {month}: Month number (01-12)
    - {year}: Four-digit year (2025)

    Args:
        target_date: Date to format
        template: Template string with variables

    Returns:
        Formatted string
    """
    return template.format(
        date=target_date.isoformat(),
        day_abbr=target_date.strftime("%a"),
        day_name=target_date.strftime("%A"),
        month=target_date.strftime("%m"),
        year=target_date.strftime("%Y"),
    )
```

**Changes required:**
- Extract date parsing from cli.py
- Update cli.py to use date_utils
- Update formatters.py to use date_utils
- Add comprehensive tests for date utilities

**Acceptance criteria:**
- All date parsing uses shared module
- Tests cover all date formats
- Edge cases handled (leap years, invalid dates)
- Documentation updated

## Phase 3: Security Hardening

**Goal:** Add security scanning and improve credential handling.

**Priority:** High

**Dependencies:** Phase 2 complete (exception hierarchy needed)

### Tasks

#### ⏳ Task 3.1: Add Security Scanning with pip-audit

**Files to modify:**
- `Makefile`
- `.github/workflows/security.yml` (new)

**Implementation:**

**Makefile additions:**

```makefile
# Security section
.PHONY: security security/audit security/bandit security/all

security: security/audit security/bandit

security/audit:
	@echo "Running pip-audit for dependency vulnerabilities..."
	uv run pip-audit

security/bandit:
	@echo "Running bandit for security issues..."
	uv run bandit -r src/ -ll

security/all: security/audit security/bandit
```

**GitHub Actions workflow:**

```yaml
name: Security Scan

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run security audit
        run: make security/all
```

**Dependencies to add:**

```toml
[project.optional-dependencies]
security = [
    "pip-audit>=2.7.0",
    "bandit[toml]>=1.7.5",
]
```

**Acceptance criteria:**
- pip-audit checks for vulnerable dependencies
- bandit scans for security issues in code
- CI runs security checks on every PR
- Weekly scheduled security scans

#### ⏳ Task 3.2: Add Transport Abstraction to create_http_client

**Files to modify:**
- `src/pkm_tool/sources/common.py`

**Implementation:**

```python
"""Enhanced HTTP client with transport abstraction."""

from typing import Any, Protocol
import httpx
from pkm_tool.cache import get_cache_storage

class Transport(Protocol):
    """Transport protocol for dependency injection."""

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle HTTP request."""
        ...

class HTTPXTransport:
    """Default httpx transport."""

    def __init__(self, **kwargs: Any):
        self._transport = httpx.HTTPTransport(**kwargs)

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request using httpx."""
        return await self._transport.handle_request(request)

class CachedTransport:
    """Cached HTTP transport."""

    def __init__(self, storage: Any, **kwargs: Any):
        self._storage = storage
        self._base_transport = HTTPXTransport(**kwargs)

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with caching."""
        # Check cache first
        cached = self._storage.get(request)
        if cached:
            return cached

        # Make request and cache
        response = await self._base_transport.handle_request(request)
        self._storage.set(request, response)
        return response

def create_http_client(
    use_cache: bool = True,
    transport: Transport | None = None,
    **kwargs: Any
) -> httpx.Client:
    """
    Create HTTP client with optional caching and custom transport.

    Args:
        use_cache: Enable HTTP response caching
        transport: Custom transport (for testing)
        **kwargs: Additional httpx.Client arguments

    Returns:
        Configured HTTP client
    """
    if transport:
        # Use custom transport (testing)
        return httpx.Client(transport=transport, **kwargs)

    if use_cache:
        # Use cached transport
        storage = get_cache_storage()
        return httpx.Client(
            transport=CachedTransport(storage, **kwargs),
            **kwargs
        )

    # Use default transport
    return httpx.Client(**kwargs)
```

**Acceptance criteria:**
- Transport abstraction allows dependency injection
- Tests can inject mock transport
- Caching remains functional
- Backward compatible with existing code

#### ⏳ Task 3.3: Improve Token Security

**Files to modify:**
- `src/pkm_tool/auth/token_store.py`

**Improvements:**

- Add token expiry validation
- Implement secure token rotation
- Add audit logging for token access
- Implement token revocation support
- Add rate limiting for token refresh

**Acceptance criteria:**
- Tokens validated before use
- Expired tokens automatically refreshed
- Token access logged for security audit
- Tests verify security improvements

## Phase 4: Reliability and Resilience

**Goal:** Add retry logic, circuit breakers, and request/response logging.

**Priority:** Medium-High

**Dependencies:** Phase 2 (exception hierarchy), Phase 3 (transport abstraction)

### Tasks

#### ⏳ Task 4.1: Add Request/Response Logging

**Files to modify:**
- `src/pkm_tool/sources/common.py`
- `src/pkm_tool/logging.py`

**Implementation:**

```python
"""HTTP client with request/response logging."""

import structlog

logger = structlog.get_logger()

class LoggingTransport:
    """Transport with request/response logging."""

    def __init__(self, base_transport: Transport):
        self._base = base_transport

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle request with logging."""
        logger.info(
            "http_request",
            method=request.method,
            url=str(request.url),
            headers=dict(request.headers),  # Redact sensitive headers
        )

        start_time = time.monotonic()
        try:
            response = await self._base.handle_request(request)
            duration = time.monotonic() - start_time

            logger.info(
                "http_response",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration_seconds=duration,
            )
            return response

        except Exception as e:
            duration = time.monotonic() - start_time
            logger.error(
                "http_error",
                method=request.method,
                url=str(request.url),
                error=str(e),
                duration_seconds=duration,
            )
            raise
```

**Acceptance criteria:**
- All HTTP requests logged with structured context
- Response times tracked
- Errors logged with full context
- Sensitive headers redacted (Authorization, etc.)

#### ⏳ Task 4.2: Add Retry Logic with Exponential Backoff

**Files to create:**
- `src/pkm_tool/resilience.py`

**Implementation:**

```python
"""Resilience patterns: retry, circuit breaker, rate limiting."""

import time
from typing import Any, Callable, TypeVar
import structlog

logger = structlog.get_logger()

T = TypeVar("T")

def retry_with_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        retryable_exceptions: Exception types to retry

    Returns:
        Function result

    Raises:
        Last exception if all retries fail
    """
    attempt = 0
    while attempt < max_attempts:
        try:
            return func()
        except retryable_exceptions as e:
            attempt += 1
            if attempt >= max_attempts:
                logger.error(
                    "retry_exhausted",
                    func=func.__name__,
                    attempts=attempt,
                    error=str(e),
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
            if jitter:
                import random
                delay *= (0.5 + random.random())

            logger.warning(
                "retry_attempt",
                func=func.__name__,
                attempt=attempt,
                delay_seconds=delay,
                error=str(e),
            )
            time.sleep(delay)

    raise RuntimeError("Should not reach here")
```

**Acceptance criteria:**
- Transient failures automatically retried
- Exponential backoff prevents overwhelming services
- Jitter prevents thundering herd
- Configurable per source
- Tests verify retry behavior

#### ⏳ Task 4.3: Add Circuit Breaker Pattern

**Files to modify:**
- `src/pkm_tool/resilience.py`

**Implementation:**

```python
"""Circuit breaker to prevent cascading failures."""

from enum import Enum
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger()

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Circuit breaker for fault tolerance."""

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: datetime | None = None

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info("circuit_breaker_half_open")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                logger.info("circuit_breaker_closed")
                self.state = CircuitState.CLOSED
                self.successes = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failures += 1
        self.last_failure_time = datetime.now()
        self.successes = 0

        if self.failures >= self.failure_threshold:
            logger.warning(
                "circuit_breaker_open",
                failures=self.failures,
                threshold=self.failure_threshold,
            )
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if not self.last_failure_time:
            return False
        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.timeout_seconds
        )
```

**Acceptance criteria:**
- Circuit breaker prevents cascading failures
- Automatic recovery after timeout
- Half-open state tests recovery
- Per-source circuit breakers
- Tests verify state transitions

#### ⏳ Task 4.4: Add Rate Limiting for API Calls

**Files to modify:**
- `src/pkm_tool/resilience.py`

**Implementation:**

```python
"""Rate limiting to respect API quotas."""

import time
from collections import deque

class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: int, per: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()

    def acquire(self):
        """Acquire permission for one request, blocking if necessary."""
        current = time.monotonic()
        time_passed = current - self.last_check
        self.last_check = current

        self.allowance += time_passed * (self.rate / self.per)
        if self.allowance > self.rate:
            self.allowance = self.rate

        if self.allowance < 1.0:
            sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
            logger.debug("rate_limit_sleep", sleep_seconds=sleep_time)
            time.sleep(sleep_time)
            self.allowance = 0.0
        else:
            self.allowance -= 1.0
```

**Acceptance criteria:**
- API rate limits respected
- Configurable per source
- Prevents 429 rate limit errors
- Tests verify rate limiting behavior

## Phase 5: Observability

**Goal:** Add metrics, distributed tracing, and improved health checks.

**Priority:** Medium

**Dependencies:** Phase 4 (logging and resilience)

### Tasks

#### ⏳ Task 5.1: Add Metrics Collection

**Files to create:**
- `src/pkm_tool/metrics.py`

**Implementation:**

```python
"""Metrics collection for observability."""

from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    "pkm_http_requests_total",
    "Total HTTP requests",
    ["source", "method", "status"],
)

http_request_duration_seconds = Histogram(
    "pkm_http_request_duration_seconds",
    "HTTP request duration",
    ["source", "method"],
)

# Source metrics
source_fetch_duration_seconds = Histogram(
    "pkm_source_fetch_duration_seconds",
    "Source fetch duration",
    ["source"],
)

source_errors_total = Counter(
    "pkm_source_errors_total",
    "Total source errors",
    ["source", "error_type"],
)

# Cache metrics
cache_hits_total = Counter(
    "pkm_cache_hits_total",
    "Total cache hits",
    ["source"],
)

cache_misses_total = Counter(
    "pkm_cache_misses_total",
    "Total cache misses",
    ["source"],
)
```

**Acceptance criteria:**
- Prometheus metrics exposed
- Server mode exposes /metrics endpoint
- Metrics cover HTTP, sources, cache
- Grafana dashboard template provided

#### ⏳ Task 5.2: Add Distributed Tracing

**Files to create:**
- `src/pkm_tool/tracing.py`

**Implementation:**

```python
"""OpenTelemetry distributed tracing."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_tracing(service_name: str = "pkm-tool"):
    """Configure OpenTelemetry tracing."""
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

# Usage in aggregator:
@tracer.start_as_current_span("aggregate_data")
def aggregate_data(target_date: date, config: Config) -> AggregatedData:
    with tracer.start_as_current_span("fetch_github"):
        # Fetch GitHub data
        pass
```

**Acceptance criteria:**
- OpenTelemetry integration
- Traces for aggregation, sources, HTTP
- Jaeger/Tempo compatibility
- Configurable trace sampling

#### ⏳ Task 5.3: Add Health Check Endpoint Improvements

**Files to modify:**
- `src/pkm_tool/server/api.py`

**Implementation:**

```python
"""Enhanced health check endpoint."""

@app.get("/health")
async def health():
    """Comprehensive health check."""
    checks = {
        "database": check_token_store(),
        "cache": check_cache_storage(),
        "github": check_github_availability(),
        "wakatime": check_wakatime_availability(),
        # ... other sources
    }

    healthy = all(check["status"] == "ok" for check in checks.values())
    status_code = 200 if healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if healthy else "degraded",
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        },
    )

def check_token_store() -> dict:
    """Check token store accessibility."""
    try:
        # Attempt to open token store
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Acceptance criteria:**
- Health check tests all dependencies
- Returns detailed status per component
- Kubernetes-compatible (liveness, readiness)
- Tests verify health check behavior

## Phase 6: Deployment and Operations

**Goal:** Production deployment guides, configuration validation, graceful shutdown.

**Priority:** Medium-Low

**Dependencies:** All previous phases

### Tasks

#### ⏳ Task 6.1: Create Deployment Documentation

**Files to create:**
- `docs/deployment.md`
- `docs/docker.md`
- `docs/systemd.md`

**Content:**

- Docker container setup
- Docker Compose configuration
- systemd service unit file
- Environment variable reference
- Configuration management
- Secrets management (vault, AWS Secrets Manager)
- Monitoring and alerting setup
- Backup and recovery procedures

**Acceptance criteria:**
- Complete deployment guides
- Docker image builds successfully
- systemd service runs reliably
- Production checklist provided

#### ⏳ Task 6.2: Add Configuration Validation at Startup

**Files to modify:**
- `src/pkm_tool/config.py`
- `src/pkm_tool/cli.py`

**Implementation:**

```python
"""Comprehensive configuration validation."""

def validate_config(config: Config) -> list[str]:
    """
    Validate configuration for production readiness.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required credentials
    if config.github.enabled and not has_github_credentials(config):
        errors.append("GitHub enabled but no credentials configured")

    # Check file paths exist
    if config.cache.enabled:
        if not Path(config.cache.directory).exists():
            errors.append(f"Cache directory does not exist: {config.cache.directory}")

    # Check token store
    token_store_path = get_token_store_path()
    if token_store_path.exists():
        # Verify encryption key
        try:
            TokenStore()
        except Exception as e:
            errors.append(f"Token store validation failed: {e}")

    return errors

# In cli.py startup:
errors = validate_config(config)
if errors:
    for error in errors:
        logger.error("config_validation_error", error=error)
    sys.exit(1)
```

**Acceptance criteria:**
- Configuration validated at startup
- Fail fast with clear error messages
- Production readiness checklist
- Tests verify validation logic

#### ⏳ Task 6.3: Add Graceful Shutdown Handling

**Files to modify:**
- `src/pkm_tool/server/api.py`

**Implementation:**

```python
"""Graceful shutdown for server mode."""

import signal
import asyncio

shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_event.set()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("server_shutdown_started")

    # Close HTTP clients
    await close_all_http_clients()

    # Flush metrics
    await flush_metrics()

    # Close database connections
    close_token_store()

    logger.info("server_shutdown_complete")
```

**Acceptance criteria:**
- SIGTERM/SIGINT handled gracefully
- In-flight requests completed
- Resources cleaned up (connections, files)
- Tests verify shutdown behavior

## Dependency Graph

```
Phase 1 (Documentation)
    ↓
Phase 2 (Error Handling)
    ↓
Phase 3 (Security)
    ├─→ Phase 4 (Reliability)
    │       ↓
    │   Phase 5 (Observability)
    │       ↓
    └───────→ Phase 6 (Deployment)
```

## Critical Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| `src/pkm_tool/exceptions.py` | Domain exception hierarchy | 2 |
| `src/pkm_tool/date_utils.py` | Shared date utilities | 2 |
| `src/pkm_tool/sources/common.py` | HTTP client factory | 3 |
| `src/pkm_tool/resilience.py` | Retry, circuit breaker, rate limit | 4 |
| `src/pkm_tool/metrics.py` | Prometheus metrics | 5 |
| `src/pkm_tool/tracing.py` | OpenTelemetry tracing | 5 |
| `docs/deployment.md` | Deployment guide | 6 |

## Testing Requirements

Each phase must include comprehensive tests:

- **Phase 2:** Exception hierarchy tests, date parsing tests
- **Phase 3:** Security scan CI, transport abstraction tests
- **Phase 4:** Retry tests, circuit breaker tests, rate limit tests
- **Phase 5:** Metrics tests, tracing tests, health check tests
- **Phase 6:** Configuration validation tests, shutdown tests

## Success Metrics

Track these metrics to measure production readiness:

- **Reliability:** Source fetch success rate >95%
- **Performance:** P95 aggregation latency <5s
- **Error handling:** Zero unhandled exceptions
- **Security:** Zero critical vulnerabilities (pip-audit)
- **Test coverage:** Maintain >80%
- **Documentation:** All phases documented
- **Observability:** All critical paths instrumented

## Timeline Estimate

Conservative estimates for each phase:

- **Phase 1:** ✅ Complete
- **Phase 2:** 2-3 days (exception hierarchy, date utils)
- **Phase 3:** 3-4 days (security scanning, transport abstraction)
- **Phase 4:** 4-5 days (retry, circuit breaker, rate limiting)
- **Phase 5:** 3-4 days (metrics, tracing, health checks)
- **Phase 6:** 2-3 days (deployment docs, validation, shutdown)

**Total:** 14-19 days (excluding Phase 1)

## Review Checkpoints

**After each phase:**

1. Code review by team
2. Run full test suite
3. Update documentation
4. Verify acceptance criteria
5. Deploy to staging environment
6. Monitor for issues
7. Get approval before next phase

## Rollback Plan

If issues arise during implementation:

1. **Immediate:** Revert problematic commits
2. **Short-term:** Disable new features via feature flags
3. **Long-term:** Fix issues in separate branch, merge when stable

## References

- [Retry patterns](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Circuit breaker pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Production readiness checklist](https://gruntwork.io/devops-checklist/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Prometheus best practices](https://prometheus.io/docs/practices/)
