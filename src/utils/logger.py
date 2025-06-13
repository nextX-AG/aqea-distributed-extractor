"""
Logging Configuration for AQEA Distributed Extractor

Provides structured logging with different output formats and levels.
"""

import logging
import logging.handlers
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'worker_id'):
            log_data['worker_id'] = record.worker_id
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'entries_processed'):
            log_data['entries_processed'] = record.entries_processed
        
        if hasattr(record, 'processing_rate'):
            log_data['processing_rate'] = record.processing_rate
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color to levelname
        original_levelname = record.levelname
        colored_levelname = f"{self.COLORS.get(record.levelname, '')}{record.levelname}{self.COLORS['RESET']}"
        record.levelname = colored_levelname
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return formatted


def setup_logging(level = "DEBUG"):
    """Configure logging with colored output."""
    # Convert string level to logging level
    if isinstance(level, int):
        numeric_level = level
    else:
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {level}")
        
    # Setup basic configuration
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # Log successful setup
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    logger.info(f"Log level: {numeric_level}")


class LoggerAdapter(logging.LoggerAdapter):
    """Enhanced logger adapter with context information."""
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any]):
        super().__init__(logger, extra)
    
    def process(self, msg, kwargs):
        # Add extra context to log record
        kwargs.setdefault('extra', {}).update(self.extra)
        return msg, kwargs
    
    def with_context(self, **context) -> 'LoggerAdapter':
        """Create a new adapter with additional context."""
        new_extra = {**self.extra, **context}
        return LoggerAdapter(self.logger, new_extra)


def get_worker_logger(worker_id: str) -> LoggerAdapter:
    """Get logger with worker context."""
    logger = logging.getLogger('aqea.worker')
    return LoggerAdapter(logger, {'worker_id': worker_id})


def get_coordinator_logger() -> logging.Logger:
    """Get logger for master coordinator."""
    return logging.getLogger('aqea.coordinator')


def get_extractor_logger(source: str) -> LoggerAdapter:
    """Get logger with data source context."""
    logger = logging.getLogger('aqea.extractor')
    return LoggerAdapter(logger, {'source': source})


class PerformanceLogger:
    """Performance logging utility."""
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
        self.context = {}
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            log_data = {
                'operation': self.operation,
                'duration_seconds': duration,
                **self.context
            }
            
            if exc_type:
                self.logger.error(f"Failed {self.operation}", extra=log_data)
            else:
                self.logger.info(f"Completed {self.operation}", extra=log_data)
    
    def add_context(self, **context):
        """Add context information to the performance log."""
        self.context.update(context)


def log_extraction_progress(
    logger: logging.Logger,
    worker_id: str,
    entries_processed: int,
    processing_rate: float,
    work_id: str
):
    """Log extraction progress with structured data."""
    logger.info(
        f"Worker {worker_id} progress",
        extra={
            'worker_id': worker_id,
            'work_id': work_id,
            'entries_processed': entries_processed,
            'processing_rate': processing_rate,
            'event_type': 'extraction_progress'
        }
    )


def log_work_completion(
    logger: logging.Logger,
    worker_id: str,
    work_id: str,
    success: bool,
    final_count: int,
    duration_seconds: float,
    errors: list = None
):
    """Log work completion with comprehensive data."""
    logger.info(
        f"Work unit {work_id} completed",
        extra={
            'worker_id': worker_id,
            'work_id': work_id,
            'success': success,
            'final_count': final_count,
            'duration_seconds': duration_seconds,
            'errors': errors or [],
            'event_type': 'work_completion'
        }
    )


def log_error_with_context(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any] = None
):
    """Log error with additional context."""
    logger.error(
        f"Error: {str(error)}",
        exc_info=True,
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'event_type': 'error'
        }
    ) 


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name) 