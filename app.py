# app.py

from flask import Flask, request, jsonify, render_template, send_file, abort, g
from datetime import datetime, time, date, timedelta
from flask_cors import CORS
from collections import deque
from psycopg2.extras import RealDictCursor
import subprocess
import traceback
import threading
import datetime as dt
import requests
import psycopg2
import logging
import time
import sys
import os

app = Flask(__name__)
CORS(app)
DB = 'tracking.db'
DOWNLOAD_DB_PASSWORD = "GolfTec3914+"
db_lock = threading.RLock()

# Forward all logging to browser console, as python console is hidden from view.
log_buffer = deque(maxlen=1000)
log_lock = threading.Lock()
def log(message):
    timestamp = datetime.now().strftime("[%H:%M:%S]")
    print(f"{timestamp} {message}")
    with log_lock:
        log_buffer.append(f"{timestamp} {message}")
def log_exception(exc_type, exc_value, exc_tb):
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log('[EXCEPTION]\n' + error_message)
# Hook global error handler
sys.excepthook = log_exception
@app.errorhandler(Exception)
def handle_exception(e):
    log('[FLASK ERROR] ' + str(e))
    return 'Internal server error', 500

@app.before_request
def log_entry_latency():
    import time
    g.req_start = time.time()
    log(f"[RECV] {request.method} {request.path}")
    
@app.after_request
def after(response):
    duration = time.time() - g.get("req_start", time.time())
    if duration > 2:
        log(f"[SLOW] {request.method} {request.path} took {duration:.2f}s")
    return response

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

def get_connection():
    start = time.time()
    try:
        conn = psycopg2.connect(
            dbname='tracking',
            user='simtec',
            password='Golftec789+',
            host='localhost',
            port=5432,
            cursor_factory=RealDictCursor
        )
    except Exception as e:
        log('[DB CONNECT ERROR] ' + str(e))
        raise
    delta = time.time() - start
    if delta > 1.0:
        log(f'[DB WARNING] Connection took {delta:.2f}s')
    return conn

# Auto-init the database if it's the first run
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.members');")
    result = cur.fetchone()[0]
    if result is None:
        log("Schema not found in PostgreSQL. Running init_db.py...")
        subprocess.run(['python3', 'init_db.py'])
except Exception as e:
    log(f"[INIT CHECK ERROR] {str(e)}")
    
###################################
# Routes for loading html content #
###################################

@app.route("/")
def root_redirect():
    return render_template("hub.html")  # Loads new Hub UI

@app.route("/member-tracking")
def member_tracking():
    return render_template("index.html")  # Loads existing app with no change

@app.route("/hourlog")
def hourlog():
    return render_template("hourlog.html")  # Placeholder page

#####################
# Developer routes. #
#####################

@app.route('/logs')
def get_logs():
    with log_lock:
        return jsonify(list(log_buffer)[-100:])
@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    with log_lock:
        log_buffer.clear()
    return ('OK', 200)

@app.route('/download-db')
def download_db():
    pw = request.args.get("pw", "")
    if pw != DOWNLOAD_DB_PASSWORD:
        # Show a simple prompt if not correct
        return '''
        <form>
            <input type="password" name="pw" placeholder="Password"/>
            <button type="submit">Download DB</button>
        </form>
        <div style="color:red;margin-top:10px;">
            {}</div>
        '''.format("Incorrect password." if pw else "")
    return send_file('tracking.db', as_attachment=True)

###########################
# Staff Shift Log Routes. #
###########################

@app.route('/api/shifts')
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
        log(f"[GET /api/shifts ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/shifts", methods=["POST"])
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
    
@app.route('/api/shifts', methods=["DELETE"])
def clear_shifts():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM shifts")
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        log(f"[DELETE /api/shifts ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/shifts/<int:shift_id>", methods=["DELETE"])
def delete_shift(shift_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shifts WHERE id = %s", (shift_id,))
    conn.commit()
    return jsonify({"status": "deleted"})

@app.route('/api/shifts/cumulative')
def cumulative():
    try:
        staff = request.args.get("staff")
        start = request.args.get("start")
        end = request.args.get("end")
        venue = request.args.get("venue")
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT SUM(hours) as total
            FROM shifts
            WHERE staff = %s AND date >= %s AND date <= %s AND venue = %s
        ''', (staff, start, end, venue))
        result = cur.fetchone()
        return jsonify(result)
    except Exception as e:
        log(f"[GET /api/shifts/cumulative ERROR] {repr(e)}")
        return jsonify({"error": str(e)}), 500

####################
# Perk reset logic #
####################

def should_reset_weekly(last_claimed):
    # last_claimed comes in as "YYYY-MM-DD hh:mm:ss"
    # parse full timestamp if present, else date‐only
    try:
        last = last_claimed
    except ValueError:
        last = last_claimed
    today = datetime.now()
    # compute this week's Monday at 00:00:00
    this_monday = (today - timedelta(days=today.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    return last < this_monday

def should_reset_monthly(last_claimed, sign_up_date):
    try:
        try:
            claimed = last_claimed
        except ValueError:
            claimed = last_claimed
        signup_day = int(sign_up_date.split('-')[2])
        today = datetime.now()
        # reset cutoff at signup_day 00:00:00
        reset_cutoff = today.replace(day=signup_day, hour=0, minute=0, second=0, microsecond=0)
        return (today.day == signup_day) and (claimed < reset_cutoff)
    except:
        return False

def should_reset_yearly(last_claimed, dob):
    try:
        try:
            claimed = last_claimed
        except ValueError:
            claimed = last_claimed
        dob_month, dob_day = int(dob.split('-')[1]), int(dob.split('-')[2])
        today = datetime.now()
        # reset cutoff at birthday 00:00:00 this year
        reset_cutoff = datetime(today.year, dob_month, dob_day, 0,0,0)
        return (today.month == dob_month and today.day == dob_day) and (claimed < reset_cutoff)
    except:
        return False

def check_and_reset_member_perks(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        try:
            c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = %s', (member_id,))
        except Exception as e:
            log('[HARDENED DB ERROR] Line 151: ' + str(e))
        member = c.fetchone()
        if not member:
            return
        try:
            c.execute('''
                SELECT mp.member_id, mp.perk_id, mp.last_claimed, p.reset_period
                FROM member_perks mp
                JOIN perks p ON mp.perk_id = p.id
                WHERE mp.member_id = %s
            ''', (member_id,))
        except Exception as e:
            log('[HARDENED DB ERROR] Line 146: ' + str(e))
        rows = c.fetchall()

        for row in rows:
            if not row['last_claimed']:
                continue
            reset = False
            if row['reset_period'] == 'Weekly':
                reset = should_reset_weekly(row['last_claimed'])
            elif row['reset_period'] == 'Monthly':
                reset = should_reset_monthly(row['last_claimed'], member['sign_up_date'])
            elif row['reset_period'] == 'Yearly':
                reset = should_reset_yearly(row['last_claimed'], member['date_of_birth'])
            if reset:
                try:
                    c.execute('''
                        DELETE FROM member_perks
                        WHERE member_id = %s AND perk_id = %s
                    ''', (member_id, row['perk_id']))
                except Exception as e:
                    log('[HARDENED DB ERROR] Line 168: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[HARDENED DB ERROR] Line 172: ' + str(e))
    finally:
        conn.close()

# --- calculate next reset date when claiming
def calculate_next_reset(reset_period, member):
    today = datetime.today()
    multiplier = member.get("multiplier", 1) or 1
    if reset_period == "Weekly":
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return today + timedelta(days=days_until_monday + 7 * (multiplier - 1))
    elif reset_period == "Monthly":
        try:
            if isinstance(member["sign_up_date"], str):
                sign_up_date = datetime.strptime(member["sign_up_date"], "%Y-%m-%d")
            else:
                sign_up_date = member["sign_up_date"]
            signup_day = sign_up_date.day
            #base_reset = today.replace(day=signup_day)
            tmpMonth = today.month
            tmpYear = today.year
            if today.day > sign_up_date.day:
                for i in range(multiplier):
                    # Move to next month
                    base_month = tmpMonth + 1 if tmpMonth < 12 else 1
                    base_year = tmpYear if tmpMonth < 12 else tmpYear + 1
                    tmpMonth = tmpMonth + 1 if tmpMonth < 12 else 1
                    tmpYear = tmpYear + 1 if tmpMonth is 1 else tmpYear
            else:
                for i in range(multiplier):
                    base_month = tmpMonth
                    base_year = tmpYear
                    tmpMonth = tmpMonth + 1 if tmpMonth < 12 else 1
                    tmpYear = tmpYear + 1 if tmpMonth is 1 else tmpYear
            next_reset = datetime(year=base_year, month=base_month, day=signup_day)
            return next_reset
        except:
            log(f"[calculate_next_reset()] [Line 342] Error")
            return None
    elif reset_period == "Yearly":
        try:
            today = dt.datetime.today()
            dob = member["date_of_birth"]
            if dob:
                if isinstance(dob, str):
                    dob = datetime.strptime(dob, "%Y-%m-%d")
                try:
                    base = dob.replace(year=today.year)
                except ValueError:
                    base = dob.replace(month=2, day=28, year=today.year)
                if base < today:
                    try:
                        base = dob.replace(year=today.year + 1)
                    except ValueError:
                        base = dob.replace(month=2, day=28, year=today.year + 1)
                try:
                    return base.replace(year=base.year + (multiplier - 1))
                except ValueError:
                    return base.replace(month=2, day=28, year=base.year + (multiplier - 1))
        except:
            log(f"[calculate_next_reset()] Error")
            return None
    return None


# MEMBER ROUTES
@app.route('/api/members', methods=['GET'])
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
        log('[GET] 200 /api/members')
        return jsonify(members)
    finally:
        conn.close()

@app.route('/api/members', methods=['POST'])
def create_or_edit_member():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        if 'id' in data and data['id']:
            # Find the previous member_id for this row
            try:
                c.execute('SELECT member_id FROM members WHERE id=%s', (data['id'],))
            except Exception as e:
                log('[HARDENED DB ERROR] Line 245: ' + str(e))
            old = c.fetchone()
            old_member_id = old['member_id'] if old else None
            # Update the member row
            try:
                c.execute('''
                    UPDATE members SET member_id=%s, name=%s, tier_id=%s, sign_up_date=%s, date_of_birth=%s, location=%s
                    WHERE id=%s
                ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location'], data['id']))
            except Exception as e:
                log('[HARDENED DB ERROR] Line 255: ' + str(e))
            # If member_id changed, update all member_perks rows
            if old_member_id and str(old_member_id) != str(data['member_id']):
                try:
                    c.execute('UPDATE member_perks SET member_id=%s WHERE member_id=%s', (data['member_id'], old_member_id))
                except Exception as e:
                    log('[HARDENED DB ERROR] Line 261: ' + str(e))
            try:
                c.execute('SELECT member_id FROM members WHERE id=%s', (data['id'],))
            except Exception as e:
                log('[HARDENED DB ERROR] Line 265: ' + str(e))
            mid_row = c.fetchone()
            if mid_row:
                mid = mid_row['member_id']
                try:
                    c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id=%s', (mid,))
                except Exception as e:
                    log('[DB ERROR] Line 272: ' + str(e))
                member = c.fetchone()
                try:
                    c.execute('''
                        SELECT mp.perk_id, p.reset_period FROM member_perks mp
                        JOIN perks p ON mp.perk_id = p.id
                        WHERE mp.member_id=%s
                    ''', (mid,))
                except Exception as e:
                    log('[DB ERROR] Line 281: ' + str(e))
                claimed_perks = c.fetchall()
                for perk in claimed_perks:
                    next_reset = calculate_next_reset(perk['reset_period'], {
                        "sign_up_date": member["sign_up_date"],
                        "date_of_birth": member["date_of_birth"]
                    })
                    try:
                        c.execute('UPDATE member_perks SET next_reset_date=%s WHERE member_id=%s AND perk_id=%s',
                            (next_reset, mid, perk['perk_id']))
                    except Exception as e:
                        log('[DB ERROR] Line 291: ' + str(e))
        else:
            try:
                c.execute('INSERT INTO members (member_id, name, tier_id, sign_up_date, date_of_birth, location) VALUES (%s, %s, %s, %s, %s, %s)', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location']))
            except Exception as e:
                log('[DB ERROR] Line 297: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 301: ' + str(e))
        log(f'[POST] 200 /api/members')
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM member_perks WHERE member_id = %s', (member_id,))
        except Exception as e:
            log('[DB ERROR] Line 315: ' + str(e))
        try:
            c.execute('DELETE FROM members WHERE member_id = %s', (member_id,))
        except Exception as e:
            log('[DB ERROR] Line 319: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 323: ' + str(e))
        log(f'[DELETE] 200 /api/members/{member_id}')
        return ('OK', 200)
    finally:
        conn.close()

# TIER ROUTES
@app.route('/api/tiers', methods=['GET'])
def get_tiers():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM tiers')
        tiers = [dict(row) for row in c.fetchall()]
        log(f'[GET] 200 /api/tiers')
        return jsonify(tiers)
    finally:
        conn.close()

@app.route('/api/tiers/<int:tier_id>', methods=['GET'])
def get_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM tiers WHERE id = %s', (tier_id,))
        row = c.fetchone()
        if row:
            log(f'[GET] 200 /api/tiers/{tier_id}')
            return jsonify(dict(row))
        else:
            log(f'[GET] 404 /api/tiers/{tier_id}')
            return ('Not found', 404)
    finally:
        conn.close()

@app.route('/api/tiers', methods=['POST'])
def create_or_edit_tier():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            if 'id' in data and data['id']:
                try:
                    c.execute('UPDATE tiers SET name=%s, color=%s WHERE id=%s',
                        (data['name'], data['color'], data['id']))
                except Exception as e:
                    log('[DB ERROR] Line 369: ' + str(e))
            else:
                try:
                    c.execute('INSERT INTO tiers (name, color) VALUES (%s, %s)',
                        (data['name'], data['color']))
                except Exception as e:
                    log('[DB ERROR] Line 375: ' + str(e))
            try:
                conn.commit()
            except Exception as e:
                log('[DB ERROR] Line 380: ' + str(e))
            log(f'[POST] 200 /api/tiers')
            return ('OK', 200)
        finally:
            conn.close()

@app.route('/api/tiers/<int:tier_id>', methods=['DELETE'])
def delete_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM tier_perks WHERE tier_id = %s', (tier_id,))
        except Exception as e:
            log('[DB ERROR] Line 394: ' + str(e))
        try:
            c.execute('DELETE FROM tiers WHERE id = %s', (tier_id,))
        except Exception as e:
            log('[DB ERROR] Line 398: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 402: ' + str(e))
        log(f'[DELETE] 200 /api/tiers/{tier_id}')
        return ('OK', 200)
    finally:
        conn.close()

# PERKS ROUTES
@app.route('/api/perks', methods=['GET'])
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
        log(f'[GET] 200 /api/perks')
        return jsonify(perks)
    finally:
        conn.close()

@app.route('/api/perks/<int:perk_id>', methods=['GET'])
def get_perk(perk_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM perks WHERE id = %s', (perk_id,))
        row = c.fetchone()
        if row:
            log(f'[GET] 200 /api/perks/{perk_id}')
            return jsonify(dict(row))
        else:
            log(f'[GET] 404 /api/perks/{perk_id}')
            return ('Not found', 404)
    finally:
        conn.close()

@app.route('/api/perks', methods=['POST'])
def create_or_edit_perk():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            if 'id' in data and data['id']:
                try:
                    c.execute('UPDATE perks SET name=%s, reset_period=%s WHERE id=%s',
                        (data['name'], data['reset_period'], data['id']))
                except Exception as e:
                    log('[DB ERROR] Line 458: ' + str(e))
            else:
                try:
                    c.execute('INSERT INTO perks (name, reset_period) VALUES (%s, %s)',
                        (data['name'], data['reset_period']))
                except Exception as e:
                    log('[DB ERROR] Line 464: ' + str(e))
            try:
                conn.commit()
            except Exception as e:
                log('[DB ERROR] Line 469: ' + str(e))
            log(f'[POST] 200 /api/perks')
            return ('OK', 200)
        finally:
            conn.close()

# TIER-PERKS ROUTES
@app.route('/api/perks/<int:perk_id>', methods=['DELETE'])
def delete_perk(perk_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM tier_perks WHERE perk_id = %s', (perk_id,))
        except Exception as e:
            log('[DB ERROR] Line 484: ' + str(e))
        try:
            c.execute('DELETE FROM member_perks WHERE perk_id = %s', (perk_id,))
        except Exception as e:
            log('[DB ERROR] Line 488: ' + str(e))
        try:
            c.execute('DELETE FROM perks WHERE id = %s', (perk_id,))
        except Exception as e:
            log('[DB ERROR] Line 492: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 496: ' + str(e))
        log(f'[DELETE] 200 /api/perks/{perk_id}')
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/tier_perks/<int:tier_id>', methods=['GET'])
def get_perks_for_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
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
        ''', (tier_id,))
        perks = [dict(row) for row in c.fetchall()]
        log(f'[GET] 200 /api/tier_perks/{tier_id}')
        return jsonify(perks)
    finally:
        conn.close()

@app.route('/api/tier_perks', methods=['POST'])
def assign_perk_to_tier():
    data = request.json
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            try:
                c.execute('INSERT INTO tier_perks (tier_id, perk_id) VALUES (%s, %s)', (data['tier_id'], data['perk_id']))
            except Exception as e:
                log('[DB ERROR] Line 537: ' + str(e))
            try:
                c.execute('SELECT member_id FROM members WHERE tier_id = %s', (data['tier_id'],))
            except Exception as e:
                log('[DB ERROR] Line 541: ' + str(e))
            try:
                conn.commit()
            except Exception as e:
                log('[DB ERROR] Line 545: ' + str(e))
            log(f'[POST] 200 /api/tier_perks')
            return ('OK', 200)
        finally:
            conn.close()

# TIER-PERKS ROUTE
@app.route('/api/tier_perks', methods=['DELETE'])
def unassign_perk_from_tier():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        try:
            c.execute('DELETE FROM tier_perks WHERE tier_id = %s AND perk_id = %s', (data['tier_id'], data['perk_id']))
        except Exception as e:
            log('[DB ERROR] Line 561: ' + str(e))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 565: ' + str(e))
        log(f'[DELETE] 200 /api/tier_perks')
        return ('OK', 200)
    finally:
        conn.close()

# MEMBER-PERKS ROUTES
@app.route('/api/member_perks/<int:member_id>', methods=['GET'])
def get_member_perks(member_id):
    check_and_reset_member_perks(member_id)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT tier_id FROM members WHERE member_id = %s', (member_id,))
        member = c.fetchone()
        if not member:
            log(f'[GET] 404 /api/member_perks/{member_id}  ~~  member not found')
            return jsonify([])

        try:
            c.execute('''
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
            ''', (member_id, member['tier_id']))
        except Exception as e:
            log('[DB ERROR] Line 604: ' + str(e))
        perks = [dict(row) for row in c.fetchall()]
        log(f'[GET] 200 /api/member_perks/{member_id}')
        return jsonify(perks)
    finally:
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 612: ' + str(e))
        conn.close()

@app.route('/api/member_perks/claim', methods=['POST'])
def claim_perk():
    data = request.json
    now_dt = datetime.now()
    now = now_dt
    with db_lock:
        conn = get_connection()
        try:
            c = conn.cursor()
            try:
                c.execute('SELECT reset_period FROM perks WHERE id = %s', (data['perk_id'],))
            except Exception as e:
                log('[DB ERROR] Line 627: ' + str(e))
            perk = c.fetchone()
            reset_period = perk["reset_period"] if perk else None
            try:
                c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = %s', (data['member_id'],))
            except Exception as e:
                log('[DB ERROR] Line 631: ' + str(e))
            member = c.fetchone()
            member_data = {
                "sign_up_date": member["sign_up_date"],
                "date_of_birth": member["date_of_birth"]
            } if member else {}
            next_reset = calculate_next_reset(reset_period, member_data) if reset_period else None
            try:
                c.execute('''
                    INSERT INTO member_perks (member_id, perk_id, last_claimed, next_reset_date, multiplier)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (member_id, perk_id)
                    DO UPDATE SET
                        last_claimed = EXCLUDED.last_claimed,
                        next_reset_date = EXCLUDED.next_reset_date
                ''', (data['member_id'], data['perk_id'], now, next_reset, 1))
            except Exception as e:
                log('[DB ERROR] Line 804: ' + str(e))
            try:
                conn.commit()
            except Exception as e:
                log('[DB ERROR] Line 650: ' + str(e))
            log(f'[POST] 200 /api/member_perks/claim')
            return ('OK', 200)
        finally:
            conn.close()

@app.route('/api/member_perks/advance', methods=['POST'])
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
            log('[DB ERROR] /api/member_perks/advance: ' + str(e))
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()

@app.route('/api/member_perks/reset', methods=['POST'])
def reset_perk():
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            DELETE FROM member_perks
            WHERE member_id = %s AND perk_id = %s
        ''', (data['member_id'], data['perk_id']))
        try:
            conn.commit()
        except Exception as e:
            log('[DB ERROR] Line 669: ' + str(e))
        log(f'[POST] 200 /api/member_perks/reset')
        return ('OK', 200)
    finally:
        conn.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    app.run(debug=args.debug, host='0.0.0.0', port=5000)

