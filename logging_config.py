#!/usr/bin/env python3
"""
Comprehensive logging configuration for the Blackjack Tracker system.
Provides detailed logging for debugging, performance monitoring, and testing.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

class DetailedLogger:
    """Configures detailed logging for the entire application."""
    
    def __init__(self, name="BlackjackTracker", log_level=logging.DEBUG):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup file and console handlers with detailed formatting."""
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # File handler with rotation (10MB files, keep 5 files)
        file_handler = RotatingFileHandler(
            f"logs/blackjack_tracker_{datetime.now().strftime('%Y%m%d')}.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Detailed formatter for file logging
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
        )
        file_handler.setFormatter(detailed_formatter)
        
        # Simple formatter for console
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self, name=None):
        """Get a logger with the specified name."""
        if name:
            return logging.getLogger(f"BlackjackTracker.{name}")
        return self.logger

# Global logger instance
detailed_logger = DetailedLogger()

def get_logger(name=None):
    """Get a configured logger instance."""
    return detailed_logger.get_logger(name)

# Performance monitoring decorator
def log_performance(func):
    """Decorator to log function performance."""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger("Performance")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.debug(f"Function {func.__name__} executed in {execution_time:.4f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.4f}s: {e}")
            raise
    
    return wrapper

# Memory monitoring
def log_memory_usage(logger_name="Memory"):
    """Log current memory usage."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    logger = get_logger(logger_name)
    logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    return memory_info.rss / 1024 / 1024  # Return MB


