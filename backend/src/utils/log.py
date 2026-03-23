import logging
import os
import sys
import uuid
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars
from .config import config
from opentelemetry.sdk._logs import LoggingHandler
from opentelemetry._logs import get_logger_provider

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")

# ---------------------------------------------------------------------------
# Shared pre-render processors (run before the final renderer)
# These are format-agnostic — they add metadata to the event dict.
# ---------------------------------------------------------------------------
SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,      # Inject request-scoped context
    structlog.stdlib.add_log_level,               # "level": "info"
    structlog.stdlib.add_logger_name,             # "logger": "src.v1.service.user"
    structlog.processors.TimeStamper(fmt="iso"),  # "timestamp": "2026-02-28T..."
    structlog.processors.StackInfoRenderer(),     # Stack info if present
    structlog.processors.format_exc_info,         # Clean exception formatting
]


def configure_structlog() -> None:
    """
    Configure structlog with two output pipelines:
      - Console (stdout): ConsoleRenderer with colors (dev) or plain JSON (prod)
      - File (logs/app.log): Always clean JSON, no ANSI codes

    The key pattern: structlog renders nothing itself. It hands off to
    ProcessorFormatter which runs the final renderer per-handler.
    """
    is_dev = config.app_env

    # structlog is configured to stop just before rendering.
    # ProcessorFormatter (attached to each handler) does the final render.
    structlog.configure(
        processors=[
            *SHARED_PROCESSORS,
            # Hand off to stdlib logging — ProcessorFormatter takes it from here
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # --- Console handler ---
    console_formatter = structlog.stdlib.ProcessorFormatter(
        # foreign_pre_chain handles log records from stdlib loggers (uvicorn, etc.)
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(colors=is_dev),  # No colors in prod
        ],
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    # --- File handler: always clean JSON, never ANSI ---
    os.makedirs(LOGS_DIR, exist_ok=True)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),  # Pure JSON, no color codes
        ],
    )
    file_handler = logging.FileHandler(os.path.join(LOGS_DIR, "app.log"))
    file_handler.setFormatter(file_formatter)

    # --- OTel handler ---
    # Re-added explicitly after handlers.clear() to ensure the OTel LoggingHandler
    # is not wiped. setup_telemetry() runs at module level before this function,
    # so get_logger_provider() returns the already-registered OTel LoggerProvider.
    otel_handler = LoggingHandler(logger_provider=get_logger_provider())

    # --- Root logger: wire all three handlers ---
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove any handlers added before this call
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(otel_handler)
    root_logger.setLevel(logging.DEBUG if is_dev else logging.INFO)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)



# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
class RequestContextMiddleware(BaseHTTPMiddleware):
    """Binds request-scoped context to structlog for the lifetime of each request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]

        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
            return response
        finally:
            clear_contextvars()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger. Context bound via middleware or bind_context()
    is automatically merged into every log line.

    Usage:
        log = get_logger(__name__)
        log.info("user.created", user_id=42)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs) -> None:
    """Bind extra key-value pairs to the current request context."""
    bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables (called automatically by middleware)."""
    clear_contextvars()