import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time

db_lock = threading.RLock()

def get_connection():
    with db_lock:
        for _ in range(3):
            try:
                return psycopg2.connect(
                    host="localhost",
                    dbname="tracking",
                    user="simtec",
                    password="Golftec789+",
                    cursor_factory=RealDictCursor,
                    connect_timeout=2
                )
            except Exception:
                time.sleep(0.3)
        raise Exception("Failed to connect to database")
