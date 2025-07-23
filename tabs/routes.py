from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

tabs_bp = Blueprint('tabs', __name__)

DB_PARAMS = {
    'dbname': 'tracking',
    'user': 'simtec',
    'password': 'Golftec789+',
    'host': 'localhost'
}

def get_db():
    return psycopg2.connect(**DB_PARAMS)

@tabs_bp.route('/tabs')
def tabs_page():
    return render_template('tabs.html')

@tabs_bp.route('/api/tabs', methods=['POST'])
def create_tab():
    data = request.get_json()
    try:
        bay = int(data['bay_number'])
        booking = datetime.fromisoformat(data['booking_start'])
        duration = int(data['duration_minutes'])
    except (ValueError, KeyError):
        return jsonify({"error": "Invalid input"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tabs (bay_number, booking_start, duration_minutes)
                VALUES (%s, %s, %s) RETURNING id
            """, (bay, booking, duration))
            tab_id = cur.fetchone()[0]
            conn.commit()
    return jsonify({'id': tab_id})

@tabs_bp.route('/api/tabs')
def get_tabs():
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM tabs ORDER BY id DESC")
            rows = cur.fetchall()
            return jsonify([dict(row) for row in rows])

@tabs_bp.route('/api/tab_items/<int:tab_id>')
def get_tab_items(tab_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT ti.*, si.name, si.price
        FROM tab_items ti
        JOIN stock_items si ON ti.item_id = si.id
        WHERE ti.tab_id = %s
        ORDER BY ti.added_at
    """, (tab_id,))
    items = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(items)

@tabs_bp.route('/api/tabs/<int:tab_id>/items', methods=['POST'])
def add_tab_item(tab_id):
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tab_items (tab_id, item_id, quantity)
        VALUES (%s, %s, %s)
    """, (tab_id, data['item_id'], data['quantity']))
    cur.execute("""
        UPDATE stock_items SET total_inventory = total_inventory - %s
        WHERE id = %s
    """, (data['quantity'], data['item_id']))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

@tabs_bp.route('/api/tabs/<int:tab_id>/pay', methods=['POST'])
def mark_tab_paid(tab_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tabs SET paid = TRUE WHERE id = %s", (tab_id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

@tabs_bp.route('/api/tabs/<int:tab_id>', methods=['DELETE'])
def delete_tab(tab_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM tabs WHERE id = %s", (tab_id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204
