import logging
import os
import sys
import structlog
from structlog.stdlib import add_log_level, add_logger_name
from structlog.processors import JSONRenderer, TimeStamper, StackInfoRenderer, format_exc_info
from structlog.dev import ConsoleRenderer
from structlog.contextvars import bind_contextvars, clear_contextvars, merge_contextvars
from rich.logging import RichHandler
from typing import Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import uuid

# Determine the root directory of the project. 
# Assumes this script is in: src/utils/log.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(ROOT_DIR, "logs")

# Configure structlog
def configure_structlog():
    """Configure structlog with appropriate processors and renderers"""
    
    # Check if we're in development mode
    is_dev = os.getenv("ENVIRONMENT", "development").lower() in ["development", "dev", "local"]
    
    # Common processors for all environments
    processors = [
        structlog.contextvars.merge_contextvars,  # Merge context variables
        structlog.stdlib.add_log_level,           # Add log level
        structlog.stdlib.add_logger_name,         # Add logger name
        structlog.processors.StackInfoRenderer(), # Add stack info
        structlog.processors.format_exc_info,     # Format exceptions
        structlog.processors.TimeStamper(fmt="iso"),  # Add timestamp
    ]
    
    if is_dev:
        # Development: Human-readable console output
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
    else:
        # Production: JSON output
        processors.append(
            structlog.processors.JSONRenderer()
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure stdlib logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if is_dev else logging.WARNING,
    )

# Initialize structlog configuration
configure_structlog()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to add request-scoped context to structlog"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request_id
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Bind request context to structlog
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path
        )
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Clear context at request end
            clear_contextvars()


def setup_logger(name: str, file_path: str = "app.log", level=logging.DEBUG) -> structlog.BoundLogger:
    """
    Sets up a structlog logger with:
    - Single centralized file logging (JSON format for structured logging)
    - RichHandler for colored console output
    - Request-scoped context binding

    Args:
        name (str): Logger name (usually module name).
        file_path (str): Log file name (default: "app.log" - all services use same file).
        level (int): Logging level (e.g., logging.INFO).

    Returns:
        structlog.BoundLogger: Configured structlog logger instance.
    """
    # Create structlog logger
    logger = structlog.get_logger(name)
    
    # Setup single centralized file handler for all services
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file_path = os.path.join(LOGS_DIR, file_path)
    
    # Configure file handler with JSON formatter
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(level)
    
    # Use JSON formatter for file output
    json_formatter = structlog.processors.JSONRenderer()
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Get the underlying stdlib logger for handler management
    stdlib_logger = logging.getLogger()
    stdlib_logger.setLevel(level)
    
    # Avoid adding multiple handlers on repeated calls
    if not stdlib_logger.handlers:
        stdlib_logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structlog logger instance with file logging configured.
    
    Args:
        name (str): Logger name (usually module name).
    
    Returns:
        structlog.BoundLogger: Configured structlog logger instance.
    """
    # Ensure the logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file_path = os.path.join(LOGS_DIR, "app.log")
    
    # Get the root logger and ensure it has a file handler
    root_logger = logging.getLogger()
    
    # Check if we already have a file handler for app.log
    has_file_handler = any(
        isinstance(handler, logging.FileHandler) and 
        handler.baseFilename == log_file_path
        for handler in root_logger.handlers
    )
    
    if not has_file_handler:
        # Add file handler to root logger
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(file_handler)
    
    return structlog.get_logger(name)


def bind_context(**kwargs):
    """
    Bind additional context variables to the current logger context.
    
    Args:
        **kwargs: Key-value pairs to bind to the context.
    """
    bind_contextvars(**kwargs)


def clear_context():
    """Clear all context variables."""
    clear_contextvars()
