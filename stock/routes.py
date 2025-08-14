from flask import Blueprint, request, jsonify, render_template, url_for
import os, re, requests
from stock.utils import has_cached_image, delete_cached_image
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from shared.logger import log_message
from shared.db import get_connection as get_db

stock_bp = Blueprint('stock', __name__)

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
    items = rows
    return jsonify(items)

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
    conn = get_db()
    cur = conn.cursor()

    image_url = (data.get('image_url') or '').strip()
    name = data.get('name', '')
    if not image_url:
        static_path = f'static/item_images/{item_id}.jpg'
        if os.path.exists(static_path):
            image_url = '/' + static_path
        else:
            fetch_image(name, item_id)
            image_url = f'/static/item_images/{item_id}.jpg'
    cur.execute("""
        UPDATE stock_items SET name=%s, venue=%s, price=%s, cost_price=%s, total_inventory=%s, description=%s, image_url=%s
        WHERE id=%s
    """, (
        name,
        data.get('venue'),
        data.get('price'),
        data.get('cost_price'),
        data.get('total_inventory'),
        data.get('description'),
        image_url,
        item_id
    ))
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

@stock_bp.route('/api/reports/profit', methods=['POST'])
def report_profit():
    data = request.get_json()
    date_range = data.get('dateRange', '')
    conn = get_db()
    cur = conn.cursor()
    clauses = []
    params = []

    if isinstance(date_range, dict):
        start = str(date_range.get('start'))
        end = str(date_range.get('end'))
        if start and end and start != 'None' and end != 'None':
            start += " 00:00:00"
            end += " 23:59:59.999999"
            clauses.append("t.paid_at BETWEEN %s AND %s")
            clauses.append("at.paid_at BETWEEN %s AND %s")
            clauses.append("ul.deleted_at BETWEEN %s AND %s")
            params += [start, end, start, end, start, end]

    cur.execute(f"""
        WITH sold AS (
            SELECT si.id AS item_id, ti.quantity AS qty, 
                   ti.quantity * si.price AS rev,
                   ti.quantity * si.cost_price AS cost,
                   ti.quantity * (si.price - si.cost_price) AS profit
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            JOIN tabs t ON ti.tab_id = t.id
            WHERE t.paid = TRUE
            {'AND ' + clauses[0] if clauses else ''}
            UNION ALL
            SELECT si.id AS item_id, ati.quantity AS qty,
                   ati.quantity * ati.item_price AS rev,
                   ati.quantity * si.cost_price AS cost,
                   ati.quantity * (ati.item_price - si.cost_price) AS profit
            FROM archived_tab_items ati
            JOIN stock_items si ON ati.item_id = si.id
            JOIN archived_tabs at ON ati.archived_tab_id = at.id
            {'WHERE ' + clauses[1] if clauses else ''}
        ),
        lost AS (
            SELECT ul.item_id, SUM(ul.quantity) AS qty_lost
            FROM unpaid_losses ul
            {'WHERE ' + clauses[2] if clauses else ''}
            GROUP BY ul.item_id
        ),
        all_items AS (
            SELECT item_id FROM sold
            UNION
            SELECT item_id FROM lost
        )
        SELECT
            s.name,
            COALESCE(SUM(sold.qty), 0) AS sold_qty,
            COALESCE(lost.qty_lost, 0) AS qty_lost,
            COALESCE(SUM(sold.rev), 0) AS revenue,
            COALESCE(SUM(sold.cost), 0) + COALESCE(lost.qty_lost, 0) * s.cost_price AS cost,
            COALESCE(SUM(sold.profit), 0) AS profit,
            COALESCE(lost.qty_lost, 0) * s.cost_price AS loss,
            COALESCE(SUM(sold.profit), 0) - COALESCE(lost.qty_lost, 0) * s.cost_price AS total_pl
        FROM all_items ai
        JOIN stock_items s ON ai.item_id = s.id
        LEFT JOIN sold ON ai.item_id = sold.item_id
        LEFT JOIN lost ON ai.item_id = lost.item_id
        GROUP BY s.name, lost.qty_lost, s.cost_price
        ORDER BY total_pl DESC
    """, params)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(rows)

@stock_bp.route("/api/fetch_image")
def fetch_image(r_name=None, r_item_id=0):
    if not r_name:
        query = request.args.get("q", "")
        item_id = request.args.get("id", "")
    else:
        query = r_name
        item_id = r_item_id
    if not query:
        return jsonify({"error": "Missing query"}), 400

    os.makedirs("static/item_images", exist_ok=True)
    filename = secure_filename(f"{item_id}") + ".jpg"
    path = os.path.join("static/item_images", filename)
    if os.path.exists(path):
        return jsonify({"bestImageUrl": url_for("static", filename=f"item_images/{filename}")})
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    res = session.get("https://duckduckgo.com/", params={"q": query, "iax": "images", "ia": "images"}, headers=headers)
    token = re.search(r'vqd=([\d-]+)&', res.text)
    if not token:
        return jsonify({"error": "Token not found"}), 500

    image_res = session.get("https://duckduckgo.com/i.js", params={"q": query, "vqd": token.group(1)}, headers=headers)
    results = image_res.json().get("results", [])
    if not results:
        return jsonify({"error": "No image found"}), 404
    img_url = results[0]["image"]
    r = session.get(img_url, headers=headers, stream=True, timeout=10)
    try:
        with open(path, "wb") as f:
            for chunk in r.iter_content(1024):
                f.write(chunk)
    except Exception as e:
        app.logger.exception(f"Failed to write image for {query}")
        return jsonify({"error": "Failed to cache image"}), 500
    # After saving image to disk:
    conn = get_db()
    cur = conn.cursor()
    url = (url_for("static", filename=f"item_images/{filename}"))
    cur.execute("UPDATE stock_items SET image_url = %s WHERE name = %s", (url, query))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"bestImageUrl": url_for("static", filename=f"item_images/{filename}")})

@stock_bp.route('/api/check_for_cached_image/<int:item_id>')
def check_for_cached_image_api(item_id):
    if has_cached_image(item_id):
      return jsonify(True)
    return jsonify(False), 404

@stock_bp.route('/api/delete_cached_image/<int:item_id>', methods=['DELETE'])
def delete_cached_image_api(item_id):
    if has_cached_image(item_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE stock_items SET image_url = %s WHERE id = %s", ('', item_id))
        conn.commit()
        cur.close()
        conn.close()
        delete_cached_image(item_id)
        return jsonify({'success': True})
    return jsonify({'error': 'No cached image'}), 404
