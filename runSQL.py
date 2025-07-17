#!/usr/bin/env python3
"""
runSQL.py: Execute arbitrary SQL against the member_tracking.db safely, with automatic commit for write queries,
row printing for SELECTs, and error handling.
"""
import sqlite3
import argparse
import sys
import os

# Determine database path relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILENAME = 'tracking.db'
DB_PATH = os.path.join(SCRIPT_DIR, DB_FILENAME)


def load_sql_from_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError as e:
        print(f"Error reading SQL file: {e}", file=sys.stderr)
        sys.exit(1)


def is_select_query(sql):
    # Simple heuristic: starts with SELECT (ignoring whitespace, case)
    return sql.lstrip().lower().startswith('select')


def main():
    parser = argparse.ArgumentParser(
        description="Run a SQL query or script against the member_tracking database.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help="Path to a .sql file containing the query or script.")
    group.add_argument('-q', '--query', help="SQL query string to execute.")
    args = parser.parse_args()

    # Load SQL text
    if args.file:
        sql_text = load_sql_from_file(args.file)
    else:
        sql_text = args.query

    # Connect
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute('PRAGMA busy_timeout = 10000;')  # 10 seconds
        conn.execute('PRAGMA journal_mode=DELETE;') # DB Logging
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except sqlite3.Error as e:
        print(f"Failed to open database at '{DB_PATH}': {e}", file=sys.stderr)
        sys.exit(1)

    # Execute
    try:
        # Use executescript for scripts (multiple statements) otherwise execute single statement
        if ';' in sql_text.strip().rstrip(';'):
            cur.executescript(sql_text)
        else:
            cur.execute(sql_text)
    except sqlite3.Error as e:
        print(f"SQL execution error: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Handle results
    if is_select_query(sql_text):
        rows = cur.fetchall()
        if not rows:
            print("(No rows returned)")
        else:
            # Print each row as a dict
            for row in rows:
                print(dict(row))
    else:
        conn.commit()
        print("Query executed successfully; changes committed.")

    conn.close()


if __name__ == "__main__":
    main()

