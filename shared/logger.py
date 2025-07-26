import logging
import time
import traceback

log_buffer = []

# Set up real logging
logger = logging.getLogger("simtec")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_message(message, origin=None):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{timestamp}] {origin or ''} {message}"
    log_buffer.append(entry)
    if len(log_buffer) > 200:
        log_buffer.pop(0)
    logger.info(entry)

def log_exception(exc_type, exc_value, exc_tb):
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log_message(error_message, origin="EXCEPTION")
