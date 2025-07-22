from flask import Blueprint, request, jsonify
from shared.db import get_connection
from shared.logger import log_message
from psycopg2.extras import RealDictCursor

bp = Blueprint('hourlog', __name__)

from . import bp

@bp.route('/api/shifts', methods=['GET'])
def get_shifts():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT id, staff, date, start, "end", venue, notes, hours FROM shifts ORDER BY date DESC, start DESC, "end" DESC')
        rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "staff": r["staff"],
                "date": r["date"].isoformat() if r["date"] else "",
                "start": str(r["start"]) if r["start"] else "",
                "end": str(r["end"]) if r["end"] else "",
                "venue": str(r["venue"]) if r["venue"] else "",
                "notes": r["notes"] or "",
                "hours": float(r["hours"]) if r["hours"] is not None else 0.0
            })
        return jsonify(result)
    except Exception as e:
        log_message(f"[GET /api/shifts ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/api/shifts", methods=["POST"])
def add_shift():
    data = request.json
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO shifts (staff, date, start, "end", venue, notes, hours)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (data["staff"], data["date"], data["start"], data["end"], data["venue"], data.get("notes", ""), data["hours"]))
    conn.commit()
    return jsonify({"status": "ok"})

@bp.route('/api/shifts', methods=["DELETE"])
def clear_shifts():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM shifts")
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        log_message(f"[DELETE /api/shifts ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route("/api/shifts/<int:shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shifts WHERE id = %s", (shift_id,))
    conn.commit()
    return jsonify({"status": "deleted"})

@bp.route('/api/shifts/cumulative')
def cumulative():
    try:
        staff = request.args.get("staff")
        start = request.args.get("start")
        end = request.args.get("end")
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT SUM(hours) as total
            FROM shifts
            WHERE staff = %s AND date >= %s AND date <= %s
        ''', (staff, start, end))
        result = cur.fetchone()
        return jsonify(result)
    except Exception as e:
        log_message(f"[GET /api/shifts/cumulative ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500
