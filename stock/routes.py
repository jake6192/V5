from flask import Blueprint, request, jsonify, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import re

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
        SELECT name, SUM(qty) AS sold_qty,
               SUM(rev) AS revenue,
               SUM(cost) AS cost,
               SUM(profit) AS profit
        FROM (
            -- Active paid tabs
            SELECT si.name, ti.quantity AS qty,
                   ti.quantity * si.price AS rev,
                   ti.quantity * si.cost_price AS cost,
                   ti.quantity * (si.price - si.cost_price) AS profit
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            JOIN tabs t ON ti.tab_id = t.id
            WHERE t.paid = TRUE

            UNION ALL

            -- Archived paid tabs
            SELECT si.name, ati.quantity AS qty,
                   ati.quantity * ati.item_price AS rev,
                   ati.quantity * si.cost_price AS cost,
                   ati.quantity * (ati.item_price - si.cost_price) AS profit
            FROM archived_tab_items ati
            JOIN stock_items si ON ati.item_id = si.id
            JOIN archived_tabs at ON ati.archived_tab_id = at.id
        ) combined
        GROUP BY name
        ORDER BY profit DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@stock_bp.route("/api/fetch_image")
def fetch_image():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Missing query"}), 400

    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = "https://duckduckgo.com/"
    session = requests.Session()
    res = session.get(search_url, params={"q": query, "iax": "images", "ia": "images"}, headers=headers)
    token_match = re.search(r'vqd=([\d-]+)&', res.text)
    if not token_match:
        return jsonify({"error": "Token not found"}), 500
    vqd = token_match.group(1)

    image_res = session.get("https://duckduckgo.com/i.js", params={"q": query, "vqd": vqd}, headers=headers)
    data = image_res.json()
    if "results" in data and data["results"]:
        return jsonify({"bestImageUrl": data["results"][0]["image"]})
    return jsonify({"error": "No image found"}), 404
