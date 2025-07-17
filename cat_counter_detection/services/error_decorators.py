"""Error handling decorators for the cat detection system."""

import functools
import time
import logging
from typing import Optional, List, Type, Callable, Any

from cat_counter_detection.services.error_handler import (
    ErrorHandler, ErrorSeverity, global_error_handler
)
from cat_counter_detection.logging_config import get_logger

logger = get_logger("error_decorators")


def with_error_handling(component: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                       error_handler: Optional[ErrorHandler] = None):
    """Decorator to add error handling to functions.
    
    Args:
        component: The component name for error tracking
        severity: The severity level of errors
        error_handler: Optional custom error handler
        
    Returns:
        Decorated function with error handling
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Use global error handler if none provided
            handler = error_handler or global_error_handler
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                recovery_success = handler.handle_error(component, e, severity)
                
                # Re-raise critical errors
                if severity == ErrorSeverity.CRITICAL:
                    raise
                
                # Return None for non-critical errors
                return None
        return wrapper
    return decorator


def retry_on_error(max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 1.0,
                  exceptions: Optional[List[Type[Exception]]] = None):
    """Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        exceptions: List of exception types to catch and retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            exceptions_to_catch = exceptions or (Exception,)
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions_to_catch as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}")
                    
                    # Don't sleep on the last attempt
                    if attempt < max_attempts:
                        sleep_time = delay * (backoff_factor ** (attempt - 1))
                        logger.debug(f"Retrying in {sleep_time:.2f} seconds")
                        time.sleep(sleep_time)
            
            # If we get here, all attempts failed
            logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


def log_execution_time(logger_name: Optional[str] = None, level: int = logging.DEBUG):
    """Decorator to log function execution time.
    
    Args:
        logger_name: Optional logger name to use
        level: Logging level for the message
        
    Returns:
        Decorated function that logs execution time
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger
            log = get_logger(logger_name or func.__module__)
            
            # Record start time
            start_time = time.time()
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log execution time
            log.log(level, f"Function {func.__name__} executed in {execution_time:.4f} seconds")
            
            return result
        return wrapper
    return decorator


def safe_operation(default_return: Any = None, log_exception: bool = True):
    """Decorator to make a function safe by catching all exceptions.
    
    Args:
        default_return: Value to return if an exception occurs
        log_exception: Whether to log the exception
        
    Returns:
        Decorated function that never raises exceptions
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_exception:
                    logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
                return default_return
        return wrapper
    return decorator