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
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tabs (bay_number, booking_start, duration_minutes)
        VALUES (%s, %s, %s) RETURNING id
    """, (data['bay_number'], data['booking_start'], data.get('duration_minutes', 60)))
    tab_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'tab_id': tab_id})

@tabs_bp.route('/api/tabs')
def get_tabs():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM tabs ORDER BY created_at DESC")
    tabs = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(tabs)

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
