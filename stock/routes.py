from flask import Blueprint, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor

stock_bp = Blueprint('stock', __name__)

DB_PARAMS = {
    'dbname': 'tracking',
    'user': 'simtec',
    'password': 'Golftec789+',
    'host': 'localhost'
}

def get_db():
    return psycopg2.connect(**DB_PARAMS)

@stock_bp.route('/stock')
def stock_page():
    return render_template('stock.html')

@stock_bp.route('/api/stock')
def get_stock():
    conn = get_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM stock_items ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@stock_bp.route('/api/stock', methods=['POST'])
def create_stock():
    data = request.json
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO stock_items (name, venue, price, cost_price, total_inventory, description, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        data['name'], data['venue'], data['price'],
        data.get('cost_price'), data.get('total_inventory', 0),
        data.get('description'), data.get('image_url')
    ))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

@stock_bp.route('/api/stock/<int:item_id>', methods=['PUT'])
def update_stock_item(item_id):
    data = request.json
    fields = [
        ('name', data.get('name')),
        ('venue', data.get('venue')),
        ('price', data.get('price')),
        ('cost_price', data.get('cost_price')),
        ('description', data.get('description')),
        ('image_url', data.get('image_url')),
        ('total_inventory', data.get('total_inventory'))
    ]
    updates = [f"{k} = %s" for k, v in fields if v is not None]
    values = [v for _, v in fields if v is not None]

    if updates:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(f"UPDATE stock_items SET {', '.join(updates)} WHERE id = %s", (*values, item_id))
        conn.commit()
        cur.close()
        conn.close()
    return '', 204

@stock_bp.route('/api/stock/<int:item_id>', methods=['DELETE'])
def delete_stock_item(item_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM stock_items WHERE id = %s", (item_id,))
    conn.commit()
    cur.close()
    conn.close()
    return '', 204

@stock_bp.route('/api/reports/profit')
def report_profit():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT si.name, SUM(ti.quantity) AS sold_qty,
               SUM(ti.quantity * si.price) AS revenue,
               SUM(ti.quantity * si.cost_price) AS cost,
               SUM(ti.quantity * (si.price - si.cost_price)) AS profit
        FROM tab_items ti
        JOIN stock_items si ON ti.item_id = si.id
        GROUP BY si.name
        ORDER BY profit DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)
