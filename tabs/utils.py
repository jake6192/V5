from datetime import datetime

def format_time(dt):
    return dt.strftime('%H:%M')

def tab_age_minutes(created_at, now=None):
    now = now or datetime.utcnow()
    return (now - created_at).total_seconds() / 60

def is_tab_overdue(created_at, threshold_min=60):
    return tab_age_minutes(created_at) > threshold_min

def calculate_tab_total(tab_id, db_conn):
    with db_conn.cursor() as cur:
        cur.execute("""
            SELECT SUM(ti.quantity * si.price)
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            WHERE ti.tab_id = %s
        """, (tab_id,))
        return cur.fetchone()[0] or 0.0
