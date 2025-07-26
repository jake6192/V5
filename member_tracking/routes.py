from flask import Blueprint, request, jsonify
from shared.db import get_connection, db_lock
from shared.logger import log_message
from member_tracking.utils import (
    check_and_reset_member_perks,
    calculate_next_reset
)
from psycopg2.extras import RealDictCursor
from datetime import datetime

bp = Blueprint('member_tracking', __name__)

from . import bp

@bp.route("/debug-test")
def debug():
    return jsonify({"status": "working"})

@bp.route('/api/members', methods=['GET'])
def get_members():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT m.*, t.name AS tier_name, t.color
            FROM members m
            LEFT JOIN tiers t ON m.tier_id = t.id
            ORDER BY m.member_id
        ''')
        members = [dict(row) for row in c.fetchall()]
        log_message('[GET] 200 /api/members')
        return jsonify(members)
    except Exception as e:
        log_message(f"/api/members failed: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@bp.route('/api/members', methods=['POST'])
def create_or_edit_member():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        if 'id' in data and data['id']:
            c.execute('SELECT member_id FROM members WHERE id=%s', (data['id'],))
            old = c.fetchone()
            old_member_id = old['member_id'] if old else None
            c.execute('''
                UPDATE members SET member_id=%s, name=%s, tier_id=%s, sign_up_date=%s, date_of_birth=%s, location=%s
                WHERE id=%s
            ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location'], data['id']))
            if old_member_id and str(old_member_id) != str(data['member_id']):
                c.execute('UPDATE member_perks SET member_id=%s WHERE member_id=%s', (data['member_id'], old_member_id))
            c.execute('SELECT member_id FROM members WHERE id=%s', (data['id'],))
            mid_row = c.fetchone()
            if mid_row:
                mid = mid_row['member_id']
                c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id=%s', (mid,))
                member = c.fetchone()
                c.execute('''
                    SELECT mp.perk_id, p.reset_period FROM member_perks mp
                    JOIN perks p ON mp.perk_id = p.id
                    WHERE mp.member_id=%s
                ''', (mid,))
                claimed_perks = c.fetchall()
                for perk in claimed_perks:
                    next_reset = calculate_next_reset(perk['reset_period'], {
                        "sign_up_date": member["sign_up_date"],
                        "date_of_birth": member["date_of_birth"]
                    })
                    c.execute('UPDATE member_perks SET next_reset_date=%s WHERE member_id=%s AND perk_id=%s',
                              (next_reset, mid, perk['perk_id']))
        else:
            c.execute('''
                INSERT INTO members (member_id, name, tier_id, sign_up_date, date_of_birth, location)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location']))
        conn.commit()
        log_message(f'[POST] 200 /api/members')
        return ('OK', 200)
    finally:
        conn.close()

@bp.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM member_perks WHERE member_id = %s', (member_id,))
        c.execute('DELETE FROM members WHERE member_id = %s', (member_id,))
        conn.commit()
        log_message(f'[DELETE] 200 /api/members/{member_id}')
        return ('OK', 200)
    finally:
        conn.close()

# NOTE: remaining routes (tiers, perks, member_perks, claim/reset/advance) coming next.

# === TIER ROUTES ===

@bp.route('/api/tiers', methods=['GET'])
def get_tiers():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM tiers')
        tiers = [dict(row) for row in c.fetchall()]
        log_message(f'[GET] 200 /api/tiers')
        return jsonify(tiers)
    finally:
        conn.close()

@bp.route('/api/tiers', methods=['POST'])
def create_or_edit_tier():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            if 'id' in data and data['id']:
                c.execute('UPDATE tiers SET name=%s, color=%s WHERE id=%s',
                          (data['name'], data['color'], data['id']))
            else:
                c.execute('INSERT INTO tiers (name, color) VALUES (%s, %s)',
                          (data['name'], data['color']))
            conn.commit()
            log_message(f'[POST] 200 /api/tiers')
            return ('OK', 200)
        finally:
            conn.close()

@bp.route('/api/tiers/<int:tier_id>', methods=['DELETE'])
def delete_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE tier_id = %s', (tier_id,))
        c.execute('DELETE FROM tiers WHERE id = %s', (tier_id,))
        conn.commit()
        log_message(f'[DELETE] 200 /api/tiers/{tier_id}')
        return ('OK', 200)
    finally:
        conn.close()


# === PERK ROUTES ===

@bp.route('/api/perks', methods=['GET'])
def get_perks():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT * FROM perks
            ORDER BY
              CASE reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5
              END
        """)
        perks = [dict(row) for row in c.fetchall()]
        log_message(f'[GET] 200 /api/perks')
        return jsonify(perks)
    finally:
        conn.close()

@bp.route('/api/perks', methods=['POST'])
def create_or_edit_perk():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            if 'id' in data and data['id']:
                c.execute('UPDATE perks SET name=%s, reset_period=%s WHERE id=%s',
                          (data['name'], data['reset_period'], data['id']))
            else:
                c.execute('INSERT INTO perks (name, reset_period) VALUES (%s, %s)',
                          (data['name'], data['reset_period']))
            conn.commit()
            log_message(f'[POST] 200 /api/perks')
            return ('OK', 200)
        finally:
            conn.close()

@bp.route('/api/perks/<int:perk_id>', methods=['DELETE'])
def delete_perk(perk_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE perk_id = %s', (perk_id,))
        c.execute('DELETE FROM member_perks WHERE perk_id = %s', (perk_id,))
        c.execute('DELETE FROM perks WHERE id = %s', (perk_id,))
        conn.commit()
        log_message(f'[DELETE] 200 /api/perks/{perk_id}')
        return ('OK', 200)
    finally:
        conn.close()


# === TIER-PERK ROUTES ===

@bp.route('/api/tier_perks/<int:tier_id>', methods=['GET'])
def get_perks_for_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT p.*
            FROM tier_perks tp
            JOIN perks p ON tp.perk_id = p.id
            WHERE tp.tier_id = %s
            ORDER BY
              CASE p.reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5
              END
        """, (tier_id,))
        perks = [dict(row) for row in c.fetchall()]
        log_message(f'[GET] 200 /api/tier_perks/{tier_id}')
        return jsonify(perks)
    finally:
        conn.close()

@bp.route('/api/tier_perks', methods=['POST'])
def assign_perk_to_tier():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute('INSERT INTO tier_perks (tier_id, perk_id) VALUES (%s, %s)',
                      (data['tier_id'], data['perk_id']))
            conn.commit()
            log_message(f'[POST] 200 /api/tier_perks')
            return ('OK', 200)
        finally:
            conn.close()

@bp.route('/api/tier_perks', methods=['DELETE'])
def unassign_perk_from_tier():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE tier_id = %s AND perk_id = %s',
                  (data['tier_id'], data['perk_id']))
        conn.commit()
        log_message(f'[DELETE] 200 /api/tier_perks')
        return ('OK', 200)
    finally:
        conn.close()


# === MEMBER-PERKS ROUTES ===

@bp.route('/api/member_perks/<int:member_id>', methods=['GET'])
def get_member_perks(member_id):
    check_and_reset_member_perks(member_id)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT tier_id FROM members WHERE member_id = %s', (member_id,))
        member = c.fetchone()
        if not member:
            log_message(f'[GET] 404 /api/member_perks/{member_id}  ~~  member not found')
            return jsonify([])

        c.execute("""
            SELECT 
                p.id, p.name, p.reset_period,
                mp.last_claimed, mp.next_reset_date
            FROM tier_perks tp
            JOIN perks p ON tp.perk_id = p.id
            LEFT JOIN member_perks mp
              ON mp.perk_id = p.id AND mp.member_id = %s
            WHERE tp.tier_id = %s
            ORDER BY
              CASE p.reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5
              END
        """, (member_id, member['tier_id']))
        perks = [dict(row) for row in c.fetchall()]
        log_message(f'[GET] 200 /api/member_perks/{member_id}')
        return jsonify(perks)
    finally:
        conn.commit()
        conn.close()

@bp.route('/api/member_perks/claim', methods=['POST'])
def claim_perk():
    data = request.json
    now = datetime.now()
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute('SELECT reset_period FROM perks WHERE id = %s', (data['perk_id'],))
            perk = c.fetchone()
            reset_period = perk["reset_period"] if perk else None
            c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = %s', (data['member_id'],))
            member = c.fetchone()
            member_data = {
                "sign_up_date": member["sign_up_date"],
                "date_of_birth": member["date_of_birth"]
            } if member else {}
            next_reset = calculate_next_reset(reset_period, member_data) if reset_period else None
            c.execute("""
                INSERT INTO member_perks (member_id, perk_id, last_claimed, next_reset_date, multiplier)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (member_id, perk_id)
                DO UPDATE SET
                    last_claimed = EXCLUDED.last_claimed,
                    next_reset_date = EXCLUDED.next_reset_date
            """, (data['member_id'], data['perk_id'], now, next_reset, 1))
            conn.commit()
            log_message(f'[POST] 200 /api/member_perks/claim')
            return ('OK', 200)
        finally:
            conn.close()

@bp.route('/api/member_perks/advance', methods=['POST'])
def advance_perk_period():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute('''
                SELECT multiplier FROM member_perks
                WHERE member_id = %s AND perk_id = %s
            ''', (data['member_id'], data['perk_id']))
            row = c.fetchone()
            current_multiplier = row["multiplier"] if row and row["multiplier"] else 1
            new_multiplier = current_multiplier + 1

            c.execute('SELECT reset_period FROM perks WHERE id = %s', (data['perk_id'],))
            perk = c.fetchone()
            reset_period = perk["reset_period"] if perk else None
            if reset_period == "Unlimited":
                return jsonify({"error": "Unlimited perks cannot be extended"}), 400

            c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = %s', (data['member_id'],))
            member = c.fetchone()
            member_data = {
                "sign_up_date": member["sign_up_date"],
                "date_of_birth": member["date_of_birth"],
                "multiplier": new_multiplier
            } if member else {}
            next_reset = calculate_next_reset(reset_period, member_data) if reset_period else None
            c.execute('''
                UPDATE member_perks
                SET multiplier = %s, next_reset_date = %s
                WHERE member_id = %s AND perk_id = %s
            ''', (new_multiplier, next_reset, data['member_id'], data['perk_id']))
            conn.commit()
            return jsonify({"status": "advanced", "multiplier": new_multiplier, "next_reset_date": next_reset.isoformat() if next_reset else None})
        except Exception as e:
            log_message('[DB ERROR] /api/member_perks/advance: ' + str(e))
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()

@bp.route('/api/member_perks/reset', methods=['POST'])
def reset_perk():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            DELETE FROM member_perks
            WHERE member_id = %s AND perk_id = %s
        ''', (data['member_id'], data['perk_id']))
        conn.commit()
        log_message(f'[POST] 200 /api/member_perks/reset')
        return ('OK', 200)
    finally:
        conn.close()
