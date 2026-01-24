import time
import logging

from config.settings import MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


def fetch_with_retry(fetch_fn, *args, max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Retry a fetch function with linear backoff. Returns None on total failure."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            result = fetch_fn(*args)
            if result is not None:
                return result
        except Exception as e:
            last_error = e
            logger.warning(f"{fetch_fn.__name__} attempt {attempt}/{max_retries} failed: {e}")
        if attempt < max_retries:
            time.sleep(delay * attempt)
    logger.error(f"{fetch_fn.__name__} failed after {max_retries} attempts. Last error: {last_error}")
    return None
