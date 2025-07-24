from flask import Blueprint, request, jsonify, render_template, url_for
import os, re, requests, psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.utils import secure_filename
from shared.logger import log_message

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
        # Refetch image based on new item name
        from werkzeug.utils import secure_filename
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        img_query = data.get("name", "")
        filename = secure_filename(img_query.lower()) + ".jpg"
        path = os.path.join("static/item_images", filename)
        os.makedirs("static/item_images", exist_ok=True)
        try:
            if not os.path.exists(path):
                search = session.get("https://duckduckgo.com/", params={"q": img_query, "iax": "images", "ia": "images"}, headers=headers)
                token = re.search(r'vqd=([\d-]+)&', search.text)
                if token:
                    r = session.get("https://duckduckgo.com/i.js", params={"q": img_query, "vqd": token.group(1)}, headers=headers)
                    img_url = r.json()["results"][0]["image"]
                    img_data = session.get(img_url, headers=headers, stream=True, timeout=10)
                    with open(path, "wb") as f:
                        for chunk in img_data.iter_content(1024):
                            f.write(chunk)
            image_url = url_for("static", filename=f"item_images/{filename}")
            cur.execute("UPDATE stock_items SET image_url = %s WHERE id = %s", (image_url, item_id))
            conn.commit()
        except Exception as e:
            app.logger.warning(f"Image refetch failed for {img_query}: {e}")
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
        WITH losses AS (
            SELECT item_id, SUM(quantity) AS qty_lost
            FROM unpaid_losses
            GROUP BY item_id
        )
        SELECT
            s.name,
            SUM(c.qty) AS sold_qty,
            COALESCE(l.qty_lost, 0) AS qty_lost,
            SUM(c.rev) AS revenue,
            SUM(c.cost) + COALESCE(l.qty_lost, 0) * s.cost_price AS cost,
            SUM(c.profit) AS profit,
            COALESCE(l.qty_lost, 0) * s.cost_price AS loss,
            SUM(c.profit) - COALESCE(l.qty_lost, 0) * s.cost_price AS total_pl
        FROM (
            SELECT si.id AS item_id, ti.quantity AS qty,
                   ti.quantity * si.price AS rev,
                   ti.quantity * si.cost_price AS cost,
                   ti.quantity * (si.price - si.cost_price) AS profit
            FROM tab_items ti
            JOIN stock_items si ON ti.item_id = si.id
            JOIN tabs t ON ti.tab_id = t.id
            WHERE t.paid = TRUE

            UNION ALL

            SELECT si.id AS item_id, ati.quantity AS qty,
                   ati.quantity * ati.item_price AS rev,
                   ati.quantity * si.cost_price AS cost,
                   ati.quantity * (ati.item_price - si.cost_price) AS profit
            FROM archived_tab_items ati
            JOIN stock_items si ON ati.item_id = si.id
            JOIN archived_tabs at ON ati.archived_tab_id = at.id
        ) c
        JOIN stock_items s ON c.item_id = s.id
        LEFT JOIN losses l ON c.item_id = l.item_id
        GROUP BY s.name, l.qty_lost, s.cost_price
        ORDER BY total_pl DESC
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

    os.makedirs("static/item_images", exist_ok=True)
    filename = secure_filename(query.lower()) + ".jpg"
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