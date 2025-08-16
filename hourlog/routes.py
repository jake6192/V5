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

        limit = request.args.get('limit', default=25, type=int)
        offset = request.args.get('offset', default=0, type=int)

        staff = request.args.get('staff')
        venue = request.args.get('venue')
        start = request.args.get('start')
        end = request.args.get('end')
        sort = request.args.get('sort', 'date')
        order = request.args.get('order', 'desc').upper()

        where_clauses = []
        params = []
        if staff:
            where_clauses.append('staff = %s')
            params.append(staff)
        if venue:
            where_clauses.append('venue = %s')
            params.append(venue)
        if start:
            where_clauses.append('date >= %s')
            params.append(start)
        if end:
            where_clauses.append('date <= %s')
            params.append(end)
        where_sql = ' WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''

        count_q = f'SELECT COUNT(*) AS total, COALESCE(SUM(hours),0) AS total_hours FROM shifts{where_sql}'
        cur.execute(count_q, params)
        stats = cur.fetchone()
        total = stats['total']
        total_hours = float(stats['total_hours']) if stats['total_hours'] is not None else 0.0

        valid_sort = {'staff', 'venue', 'hours', 'date'}
        if sort not in valid_sort:
            sort = 'date'
        order = 'ASC' if order == 'ASC' else 'DESC'
        if sort == 'date':
            sort_clause = f'ORDER BY date {order}, start {order}, "end" {order}'
        else:
            sort_clause = f'ORDER BY {sort} {order}, date DESC, start DESC, "end" DESC'

        data_q = f'SELECT id, staff, date, start, "end", venue, notes, hours FROM shifts{where_sql} {sort_clause} LIMIT %s OFFSET %s'
        cur.execute(data_q, params + [limit, offset])
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

        cur.execute('SELECT DISTINCT staff FROM shifts ORDER BY staff')
        staff_options = [row['staff'] for row in cur.fetchall()]
        cur.execute('SELECT DISTINCT venue FROM shifts ORDER BY venue')
        venue_options = [row['venue'] for row in cur.fetchall()]

        return jsonify({
            "results": result,
            "total": total,
            "total_hours": total_hours,
            "limit": limit,
            "offset": offset,
            "staff_options": staff_options,
            "venue_options": venue_options
        })
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
