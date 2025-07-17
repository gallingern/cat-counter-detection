"""Centralized logging configuration for the cat detection system."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter that adds structured information to log records."""
    
    def __init__(self, include_context: bool = True):
        self.include_context = include_context
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information."""
        # Base format
        base_format = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
        
        # Add context information if available
        if self.include_context and hasattr(record, 'context'):
            context_str = " | ".join([f"{k}={v}" for k, v in record.context.items()])
            base_format += f" | Context: {context_str}"
        
        # Add error information for error/critical levels
        if record.levelno >= logging.ERROR and record.exc_info:
            base_format += " | %(pathname)s:%(lineno)d"
        
        formatter = logging.Formatter(base_format)
        return formatter.format(record)


class ContextFilter(logging.Filter):
    """Filter that adds system context to log records."""
    
    def __init__(self, component_name: Optional[str] = None):
        super().__init__()
        self.component_name = component_name
        self.process_id = os.getpid()
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        # Add process ID
        record.process_id = self.process_id
        
        # Add component name if specified
        if self.component_name:
            record.component = self.component_name
        
        # Add timestamp for performance tracking
        record.timestamp_ms = datetime.now().timestamp() * 1000
        
        return True


class LoggingManager:
    """Centralized logging management for the cat detection system."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Log files
        self.main_log_file = self.log_dir / "cat_detection.log"
        self.error_log_file = self.log_dir / "errors.log"
        self.performance_log_file = self.log_dir / "performance.log"
        
        # Logging configuration
        self.log_level = logging.INFO
        self.max_log_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        
        # Component loggers
        self.component_loggers: Dict[str, logging.Logger] = {}
        
        # Setup root logger
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Setup the root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = StructuredFormatter(include_context=False)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Main log file handler (rotating)
        main_file_handler = logging.handlers.RotatingFileHandler(
            self.main_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        main_file_handler.setLevel(logging.DEBUG)
        main_file_formatter = StructuredFormatter(include_context=True)
        main_file_handler.setFormatter(main_file_formatter)
        root_logger.addHandler(main_file_handler)
        
        # Error log file handler (errors and critical only)
        error_file_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=self.max_log_size,
            backupCount=self.backup_count
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_formatter = StructuredFormatter(include_context=True)
        error_file_handler.setFormatter(error_file_formatter)
        root_logger.addHandler(error_file_handler)
        
        logging.info("Logging system initialized")
    
    def get_component_logger(self, component_name: str, 
                           log_level: Optional[int] = None) -> logging.Logger:
        """Get or create a logger for a specific component."""
        if component_name in self.component_loggers:
            return self.component_loggers[component_name]
        
        logger = logging.getLogger(f"cat_detection.{component_name}")
        
        if log_level:
            logger.setLevel(log_level)
        
        # Add context filter
        context_filter = ContextFilter(component_name)
        logger.addFilter(context_filter)
        
        self.component_loggers[component_name] = logger
        return logger
    
    def get_performance_logger(self) -> logging.Logger:
        """Get logger specifically for performance metrics."""
        logger_name = "cat_detection.performance"
        
        if logger_name not in self.component_loggers:
            logger = logging.getLogger(logger_name)
            
            # Performance log file handler
            perf_handler = logging.handlers.RotatingFileHandler(
                self.performance_log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count
            )
            perf_handler.setLevel(logging.INFO)
            
            # Simple format for performance logs
            perf_formatter = logging.Formatter(
                "%(asctime)s | %(message)s"
            )
            perf_handler.setFormatter(perf_formatter)
            logger.addHandler(perf_handler)
            
            self.component_loggers[logger_name] = logger
        
        return self.component_loggers[logger_name]
    
    def log_with_context(self, logger: logging.Logger, level: int, 
                        message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log message with additional context information."""
        if context:
            # Create a custom log record with context
            record = logger.makeRecord(
                logger.name, level, "", 0, message, (), None
            )
            record.context = context
            logger.handle(record)
        else:
            logger.log(level, message)
    
    def set_log_level(self, level: int) -> None:
        """Set the global log level."""
        self.log_level = level
        logging.getLogger().setLevel(level)
        
        # Update all component loggers
        for logger in self.component_loggers.values():
            logger.setLevel(level)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics."""
        stats = {
            "log_directory": str(self.log_dir),
            "log_files": {},
            "active_loggers": list(self.component_loggers.keys()),
            "log_level": logging.getLevelName(self.log_level)
        }
        
        # Get file sizes
        for log_file in [self.main_log_file, self.error_log_file, self.performance_log_file]:
            if log_file.exists():
                stats["log_files"][log_file.name] = {
                    "size_mb": log_file.stat().st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                }
        
        return stats
    
    def cleanup_old_logs(self, days_to_keep: int = 7) -> int:
        """Clean up old log files and return count of deleted files."""
        deleted_count = 0
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except OSError:
                    pass
        
        return deleted_count


# Global logging manager instance
logging_manager = LoggingManager()


def get_logger(component_name: str) -> logging.Logger:
    """Convenience function to get a component logger."""
    return logging_manager.get_component_logger(component_name)


def log_performance(message: str, metrics: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to log performance metrics."""
    perf_logger = logging_manager.get_performance_logger()
    
    if metrics:
        metric_str = " | ".join([f"{k}={v}" for k, v in metrics.items()])
        message = f"{message} | {metric_str}"
    
    perf_logger.info(message)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> LoggingManager:
    """Setup centralized logging system."""
    global logging_manager
    
    # Convert string level to int
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create new logging manager
    logging_manager = LoggingManager(log_dir)
    logging_manager.set_log_level(numeric_level)
    
    return logging_manager