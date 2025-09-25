import logging
import os
import time
from functools import wraps

class DetailedLogger:
    def __init__(self, logs_dir='logs', session_id=None):
        if not session_id:
            session_id = time.strftime("%Y%m%d-%H%M%S")

        self.session_id = session_id
        self.logs_dir = logs_dir
        self._setup_logging()

    def _setup_logging(self):
        os.makedirs(self.logs_dir, exist_ok=True)

        self.log_file = os.path.join(self.logs_dir, f'app_session_{self.session_id}.log')

        # Root logger setup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )

        # Performance logger
        self.perf_log_file = os.path.join(self.logs_dir, f'performance_{self.session_id}.log')
        self.perf_logger = logging.getLogger('performance')
        self.perf_logger.setLevel(logging.INFO)
        perf_handler = logging.FileHandler(self.perf_log_file)
        perf_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        self.perf_logger.addHandler(perf_handler)

    def get_logger(self, name):
        return logging.getLogger(name)

    def _log_perf(self, func_name, duration):
        self.perf_logger.info(f'{func_name},{duration:.4f}')

# Singleton instance
detailed_logger = None

def _get_logger_instance():
    global detailed_logger
    if detailed_logger is None:
        detailed_logger = DetailedLogger()
    return detailed_logger

def get_logger(name='app'):
    return _get_logger_instance().get_logger(name)

def log_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        _get_logger_instance()._log_perf(func.__name__, duration)
        return result
    return wrapper

if __name__ == '__main__':
    # Example Usage
    main_logger = get_logger('main_module')
    main_logger.info("Application starting up.")

    @log_performance
    def example_function():
        # Simulate some work
        time.sleep(0.5)

    example_function()

    main_logger.info("Application shutting down.")