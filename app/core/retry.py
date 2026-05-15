import time
import functools
import logging

logger = logging.getLogger(__name__)


def retry(max_retries=3, base_delay=1.0, backoff=2.0, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        logger.warning(f"[RETRY] {func.__name__} attempt {attempt+1}/{max_retries} failed: {e}, retrying in {delay:.1f}s")
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(f"[RETRY] {func.__name__} failed after {max_retries} attempts: {e}")
            raise last_error
        return wrapper
    return decorator
