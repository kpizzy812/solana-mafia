"""
Structured logging setup using structlog.
Provides consistent logging across all modules.
"""

import sys
import logging
from typing import Optional
from pathlib import Path

import structlog
from rich.console import Console
from rich.logging import RichHandler

from .config import settings


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_file: Optional path to log file
    """
    # Clear any existing handlers
    logging.getLogger().handlers.clear()
    
    # Configure timestamper
    timestamper = structlog.processors.TimeStamper(fmt="ISO")
    
    # Configure processors based on format
    if settings.log_format == "json":
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Setup handlers
    handlers = []
    
    # Console handler with Rich for development
    if settings.is_development and settings.log_format != "json":
        console = Console(file=sys.stderr)
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        rich_handler.setLevel(getattr(logging, settings.log_level))
        handlers.append(rich_handler)
    else:
        # Standard stream handler for production
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(getattr(logging, settings.log_level))
        
        if settings.log_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        stream_handler.setFormatter(formatter)
        handlers.append(stream_handler)
    
    # File handler if specified
    if log_file or settings.log_file:
        file_path = Path(log_file or settings.log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, settings.log_level))
        
        if settings.log_format == "json":
            formatter = logging.Formatter('%(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        handlers=handlers,
        force=True
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    

def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


# Module-level logger for this file
logger = get_logger(__name__)