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
                INSERT INTO tabs (bay_number, booking_start, duration_minutes, paid)
                VALUES (%s, %s, %s, FALSE) RETURNING id
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
    cur.execute("UPDATE tabs SET paid = TRUE, paid_at = NOW() WHERE paid = FALSE AND id = %s", (tab_id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

@tabs_bp.route('/api/tabs/<int:tab_id>', methods=['DELETE'])
def delete_tab(tab_id):
    force_paid = request.args.get('force_paid') == 'true'
    conn = get_db()
    cur = conn.cursor()

    # 1. Fetch tab metadata
    cur.execute("SELECT * FROM tabs WHERE id = %s", (tab_id,))
    tab = cur.fetchone()
    if not tab:
        return jsonify({"error": "Tab not found"}), 404

    # tab[] indices: [id, bay_number, booking_start, duration_minutes, paid, paid_at, created_at, archived]
    tab_id_val = tab[0]
    is_paid = tab[4]
    paid_at = tab[5]

    # 2. Calculate total cost (used for archive or loss)
    cur.execute("""
        SELECT COALESCE(SUM(si.price * ti.quantity), 0),
               COALESCE(SUM(si.cost_price * ti.quantity), 0)
        FROM tab_items ti
        JOIN stock_items si ON ti.item_id = si.id
        WHERE ti.tab_id = %s
    """, (tab_id_val,))
    result = cur.fetchone()
    total_price, total_cost = result[0], result[1]

    # 3. Archive paid tabs
    if is_paid:
        cur.execute("""
            INSERT INTO archived_tabs (original_tab_id, bay_number, booking_start, duration_minutes, paid, total, paid_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (tab[0], tab[1], tab[2], tab[3], tab[4], total_price, paid_at))
        archive_id = cur.fetchone()[0]

        # Copy tab items into archive
        cur.execute("""
            SELECT ti.item_id, si.name, si.price, ti.quantity
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            WHERE ti.tab_id = %s
        """, (tab_id_val,))
        for item in cur.fetchall():
            cur.execute("""
                INSERT INTO archived_tab_items (archived_tab_id, item_id, item_name, item_price, quantity)
                VALUES (%s, %s, %s, %s, %s)
            """, (archive_id, *item))

    # 4. Log loss if unpaid and not force_paid
    if not is_paid and not force_paid:
        print(f"⚠️ Unpaid tab deleted. Loss recorded: £{total_cost:.2f}")
        # Optional: insert loss record into audit table

    # 5. Delete tab and items
    cur.execute("DELETE FROM tab_items WHERE tab_id = %s", (tab_id_val,))
    cur.execute("DELETE FROM tabs WHERE id = %s", (tab_id_val,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204


@tabs_bp.route('/api/tabs/<int:tab_id>/undo', methods=['POST'])
def undo_tab_paid(tab_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE tabs SET paid = FALSE, paid_at = NULL WHERE paid = TRUE AND id = %s", (tab_id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204
