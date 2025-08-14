import os

try:
    DB_PASSWORD = os.environ["DB_PASSWORD"]
except KeyError as exc:
    raise RuntimeError("DB_PASSWORD environment variable not set") from exc