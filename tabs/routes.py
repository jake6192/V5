from flask import Blueprint, request, jsonify, render_template
from shared.logger import log_message
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
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM tabs")
    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]  # 💥 capture before second query

    tabs = []
    for row in rows:
        tab = dict(zip(column_names, row))  # ✅ safe now

        # New sub-cursor to avoid overwriting cur.description
        cur2 = conn.cursor()
        cur2.execute("""
            SELECT COALESCE(SUM(si.price * ti.quantity), 0)
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            WHERE ti.tab_id = %s
        """, (tab['id'],))
        tab['total'] = cur2.fetchone()[0]
        cur2.close()

        tabs.append(tab)

    return jsonify(tabs)

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

@tabs_bp.route('/api/tab_items/<int:tab_id>/<int:item_id>', methods=['DELETE'])
def delete_tab_item(tab_id, item_id):
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tab_items WHERE tab_id = %s AND item_id = %s", (tab_id, item_id))
                conn.commit()
        return '', 204
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@tabs_bp.route('/api/tab_item_qty', methods=['POST'])
def update_tab_item_qty():
    try:
        data = request.get_json()
        if data is None:
            print("❌ No JSON received")
            return jsonify({'error': 'No JSON received'}), 400

        tab_id = data.get('tab_id')
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        
        if not all([tab_id, item_id, quantity]):
            print(f"❌ Missing data: {data}")
            return jsonify({'error': 'Missing one or more fields'}), 400

        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE tab_items SET quantity = %s
            WHERE tab_id = %s AND item_id = %s
        """, (quantity, tab_id, item_id))
        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ Exception in update_tab_item_qty: {e}")
        return jsonify({'error': str(e)}), 500

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
