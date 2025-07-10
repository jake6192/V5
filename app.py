# app.py

from flask import Flask, request, jsonify, render_template, send_file, abort
from datetime import datetime, timedelta
from flask_cors import CORS
from collections import deque
import subprocess
import traceback
import threading
import requests
import logging
import sqlite3
import time
import sys
import os

app = Flask(__name__)
CORS(app)
DB = 'tracking.db'
DOWNLOAD_DB_PASSWORD = "GolfTec3914+"
ENABLE_SYNC_LOGS = True  # Set False to suppress sync-related errors

# Forward all logging to browser console, as python console is hidden from view.
log_buffer = deque(maxlen=1000)
log_lock = threading.Lock()
def log(message):
    print(message)
    with log_lock:
        log_buffer.append(message)
def log_exception(exc_type, exc_value, exc_tb):
    error_message = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    log('[EXCEPTION]\n' + error_message)
# Hook global error handler
sys.excepthook = log_exception
@app.errorhandler(Exception)
def handle_exception(e):
    log('[FLASK ERROR] ' + str(e))
    return 'Internal server error', 500

# Auto-init the database if it's the first run
if not os.path.exists('tracking.db'):
    log("tracking.db not found. Running init_db.py...")
    subprocess.run(['python', 'init_db.py'])
    
def ensure_column_exists():
    conn = get_connection()
    c = conn.cursor()
    try:
        tables = {
            'members': 'last_updated TEXT',
            'tiers': 'last_updated TEXT',
            'perks': 'last_updated TEXT',
            'tier_perks': 'last_updated TEXT',
            'member_perks': 'last_updated TEXT'
        }
        for table, column_def in tables.items():
            c.execute(f"PRAGMA table_info({table})")
            columns = [row['name'] for row in c.fetchall()]
            if 'last_updated' not in columns:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        conn.commit()
    except Exception as e:
        log('Schema patch error:', e)
    finally:
        conn.close()

@app.route('/logs')
def get_logs():
    with log_lock:
        return jsonify(list(log_buffer)[-100:])

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

def get_connection():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def should_reset_weekly(last_claimed):
    # last_claimed comes in as "YYYY-MM-DD hh:mm:ss"
    # parse full timestamp if present, else date‐only
    try:
        last = datetime.strptime(last_claimed, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        last = datetime.strptime(last_claimed, "%Y-%m-%d")
    today = datetime.now()
    # compute this week's Monday at 00:00:00
    this_monday = (today - timedelta(days=today.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    return last < this_monday

def should_reset_monthly(last_claimed, sign_up_date):
    try:
        try:
            claimed = datetime.strptime(last_claimed, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            claimed = datetime.strptime(last_claimed, "%Y-%m-%d")
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
            claimed = datetime.strptime(last_claimed, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            claimed = datetime.strptime(last_claimed, "%Y-%m-%d")
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
        today = datetime.now().strftime("%Y-%m-%d")

        c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = ?', (member_id,))
        member = c.fetchone()
        if not member:
            return

        c.execute('''
            SELECT mp.member_id, mp.perk_id, mp.last_claimed, p.reset_period
            FROM member_perks mp
            JOIN perks p ON mp.perk_id = p.id
            WHERE mp.member_id = ?
        ''', (member_id,))
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
                c.execute('''
                    DELETE FROM member_perks
                    WHERE member_id = ? AND perk_id = ?
                ''', (member_id, row['perk_id']))

        conn.commit()
    finally:
        conn.close()

# --- calculate next reset date when claiming
def calculate_next_reset(reset_period, member):
    today = datetime.today()
    if reset_period == "Weekly":
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        return (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")
    elif reset_period == "Monthly":
        try:
            signup_day = int(member["sign_up_date"].split("-")[2])
            this_month_reset = today.replace(day=signup_day)
            if today.day < signup_day:
                next_reset = this_month_reset
            else:
                # get next month (handle year wrap)
                month = today.month + 1 if today.month < 12 else 1
                year = today.year if today.month < 12 else today.year + 1
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                day = min(signup_day, last_day)
                next_reset = today.replace(year=year, month=month, day=day)
            return next_reset.strftime("%Y-%m-%d")
        except:
            return None
    elif reset_period == "Yearly":
        try:
            dob = datetime.strptime(member["date_of_birth"], "%Y-%m-%d")
            next_reset = dob.replace(year=today.year)
            if next_reset < today:
                next_reset = next_reset.replace(year=today.year + 1)
            return next_reset.strftime("%Y-%m-%d")
        except:
            return None
    return None

@app.route('/')
def index():
    return render_template('index.html')

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
            c.execute('SELECT member_id FROM members WHERE id=?', (data['id'],))
            old = c.fetchone()
            old_member_id = old['member_id'] if old else None
            # Update the member row
            c.execute('''
                UPDATE members SET member_id=?, name=?, tier_id=?, sign_up_date=?, date_of_birth=?, location=?
                WHERE id=?
            ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location'], data['id']))
            # If member_id changed, update all member_perks rows
            if old_member_id and str(old_member_id) != str(data['member_id']):
                c.execute('''
                    UPDATE member_perks SET member_id=? WHERE member_id=?
                ''', (data['member_id'], old_member_id))
            c.execute('SELECT member_id FROM members WHERE id=?', (data['id'],))
            mid_row = c.fetchone()
            if mid_row:
                mid = mid_row['member_id']
                c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id=?', (mid,))
                member = c.fetchone()
                c.execute('''
                    SELECT mp.perk_id, p.reset_period FROM member_perks mp
                    JOIN perks p ON mp.perk_id = p.id
                    WHERE mp.member_id=?
                ''', (mid,))
                claimed_perks = c.fetchall()
                for perk in claimed_perks:
                    next_reset = calculate_next_reset(perk['reset_period'], {"sign_up_date": member["sign_up_date"], "date_of_birth": member["date_of_birth"]})
                    c.execute('UPDATE member_perks SET next_reset_date=? WHERE member_id=? AND perk_id=?',
                              (next_reset, mid, perk['perk_id']))
        else:
            c.execute('''
                INSERT INTO members (member_id, name, tier_id, sign_up_date, date_of_birth, location)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['location']))
        c.execute('''
            UPDATE members SET last_updated = CURRENT_TIMESTAMP WHERE id = ?
        ''', (data['id'],))
        conn.commit()
        log(f'[POST] 200 /api/members')
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM member_perks WHERE member_id = ?', (member_id,))
        c.execute('DELETE FROM members WHERE member_id = ?', (member_id,))
        conn.commit()
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
        c.execute('SELECT * FROM tiers WHERE id = ?', (tier_id,))
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
    conn = get_connection()
    try:
        c = conn.cursor()
        if 'id' in data and data['id']:
            c.execute('UPDATE tiers SET name=?, color=? WHERE id=?', (data['name'], data['color'], data['id']))
        else:
            c.execute('INSERT INTO tiers (name, color) VALUES (?, ?)', (data['name'], data['color']))
        conn.commit()
        log(f'[POST] 200 /api/tiers')
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/tiers/<int:tier_id>', methods=['DELETE'])
def delete_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE tier_id = ?', (tier_id,))
        c.execute('DELETE FROM tiers WHERE id = ?', (tier_id,))
        conn.commit()
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
        c.execute('SELECT * FROM perks WHERE id = ?', (perk_id,))
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
    conn = get_connection()
    try:
        c = conn.cursor()
        if 'id' in data and data['id']:
            c.execute('UPDATE perks SET name=?, reset_period=? WHERE id=?',
                      (data['name'], data['reset_period'], data['id']))
        else:
            c.execute('INSERT INTO perks (name, reset_period) VALUES (?, ?)',
                      (data['name'], data['reset_period']))
        conn.commit()
        log(f'[GET] 200 /api/perks')
        return ('OK', 200)
    finally:
        conn.close()

# TIER-PERKS ROUTES
@app.route('/api/perks/<int:perk_id>', methods=['DELETE'])
def delete_perk(perk_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE perk_id = ?', (perk_id,))
        c.execute('DELETE FROM member_perks WHERE perk_id = ?', (perk_id,))
        c.execute('DELETE FROM perks WHERE id = ?', (perk_id,))
        conn.commit()
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
            WHERE tp.tier_id = ?
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
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO tier_perks (tier_id, perk_id) VALUES (?, ?)',
                  (data['tier_id'], data['perk_id']))

        c.execute('SELECT member_id FROM members WHERE tier_id = ?', (data['tier_id'],))
        members = c.fetchall()
        for m in members:
            # No need to insert member_perks row, will be created on claim
            pass
        conn.commit()
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
        c.execute('DELETE FROM tier_perks WHERE tier_id = ? AND perk_id = ?',
                  (data['tier_id'], data['perk_id']))
        conn.commit()
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
        c.execute('SELECT tier_id FROM members WHERE member_id = ?', (member_id,))
        member = c.fetchone()
        if not member:
            log(f'[GET] 404 /api/member_perks/{member_id}  ~~  member not found')
            return jsonify([])

        c.execute('''
            SELECT 
                p.id, p.name, p.reset_period,
                mp.last_claimed, mp.next_reset_date
            FROM tier_perks tp
            JOIN perks p ON tp.perk_id = p.id
            LEFT JOIN member_perks mp
              ON mp.perk_id = p.id AND mp.member_id = ?
            WHERE tp.tier_id = ?
            ORDER BY
              CASE p.reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5
              END
        ''', (member_id, member['tier_id']))

        perks = [dict(row) for row in c.fetchall()]
        log(f'[GET] 200 /api/member_perks/{member_id}')
        return jsonify(perks)
    finally:
        conn.commit()
        conn.close()

@app.route('/api/member_perks/claim', methods=['POST'])
def claim_perk():
    data = request.json
    now_dt = datetime.now()
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT reset_period FROM perks WHERE id = ?', (data['perk_id'],))
        perk = c.fetchone()

        c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = ?', (data['member_id'],))
        member = c.fetchone()

        reset_period = perk["reset_period"] if perk else None
        member_data = {
            "sign_up_date": member["sign_up_date"],
            "date_of_birth": member["date_of_birth"]
        } if member else {}

        next_reset = calculate_next_reset(reset_period, member_data) if reset_period else None

        # INSERT new perk claim for member
        c.execute('''
                INSERT INTO member_perks (member_id, perk_id, last_claimed, next_reset_date)
                VALUES (?, ?, ?, ?)
            ''', (data['member_id'], data['perk_id'], now, next_reset))
        conn.commit()
        log(f'[POST] 200 /api/member_perks/claim')
        return ('OK', 200)
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
            WHERE member_id = ? AND perk_id = ?
        ''', (data['member_id'], data['perk_id']))
        conn.commit()
        log(f'[POST] 200 /api/member_perks/reset')
        return ('OK', 200)
    finally:
        conn.close()


# VPN SYNC ROUTES
@app.route('/sync/pull', methods=['GET'])
def sync_pull():
    conn = get_connection()
    c = conn.cursor()
    data = {}
    for table in ['members', 'tiers', 'perks', 'tier_perks', 'member_perks']:
        c.execute(f'SELECT * FROM {table}')
        data[table] = [dict(row) for row in c.fetchall()]
    conn.close()
    log(f'[GET] 200 /sync/pull')
    return jsonify(data)

@app.route('/sync/push', methods=['POST'])
def sync_push():
    payload = request.get_json()
    conn = get_connection()
    c = conn.cursor()
    try:
        for row in payload.get('members', []):
            required = ['member_id', 'name', 'location', 'tier_id', 'sign_up_date', 'date_of_birth', 'last_updated']
            if not all(field in row for field in required):
                continue
            try:
                c.execute('SELECT last_updated FROM members WHERE member_id = ?', (row['member_id'],))
                existing = c.fetchone()
                local_ts = existing['last_updated'] if existing and existing['last_updated'] else ''
                remote_ts = row.get('last_updated', '')
                if not remote_ts or remote_ts < local_ts:
                    continue
                c.execute('SELECT COUNT(*) FROM members WHERE member_id = ?', (row['member_id'],))
                exists = c.fetchone()[0] > 0
                if exists:
                    c.execute('''
                        UPDATE members SET name=?, location=?, tier_id=?, sign_up_date=?, date_of_birth=?, last_updated=?
                        WHERE member_id=?
                    ''', (row['name'], row['location'], row['tier_id'], row['sign_up_date'], row['date_of_birth'], remote_ts, row['member_id']))
                else:
                    c.execute('''
                        INSERT INTO members (member_id, name, location, tier_id, sign_up_date, date_of_birth, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (row['member_id'], row['name'], row['location'], row['tier_id'], row['sign_up_date'], row['date_of_birth'], remote_ts))
            except Exception as e:
                log(f'Member merge error: {e}')
        for table in ['tiers', 'perks']:
            for row in payload.get(table, []):
                required = ['id', 'name', 'color', 'last_updated'] if table == 'tiers' else ['id', 'name', 'reset_period', 'last_updated']
                if not all(field in row for field in required):
                    continue
                try:
                    c.execute(f'SELECT COUNT(*) FROM {table} WHERE id=?', (row['id'],))
                    exists = c.fetchone()[0] > 0
                    if exists:
                        cols = ', '.join([f"{k}=?" for k in row if k != 'id'])
                        vals = [row[k] for k in row if k != 'id'] + [row['id']]
                        c.execute(f'UPDATE {table} SET {cols} WHERE id=?', vals)
                    else:
                        keys = ', '.join(row.keys())
                        qmarks = ', '.join(['?'] * len(row))
                        c.execute(f'INSERT INTO {table} ({keys}) VALUES ({qmarks})', tuple(row.values()))
                except Exception as e:
                    log(f'{table} merge error: {e}')
        for table in ['tier_perks', 'member_perks']:
            for row in payload.get(table, []):
                required = ['tier_id', 'perk_id'] if table == 'tier_perks' else ['member_id', 'perk_id', 'perk_claimed', 'last_claimed']
                if not all(field in row for field in required):
                    continue
                try:
                    keys = list(row.keys())
                    conditions = ' AND '.join([f"{k}=?" for k in keys])
                    c.execute(f'SELECT COUNT(*) FROM {table} WHERE {conditions}', tuple(row[k] for k in keys))
                    exists = c.fetchone()[0] > 0
                    if not exists:
                        c.execute(f'INSERT INTO {table} ({", ".join(keys)}) VALUES ({", ".join(["?"]*len(keys))})', tuple(row.values()))
                except Exception as e:
                    log(f'{table} merge error: {e}')
        conn.commit()
    except Exception as e:
        log(f'SYNC_PUSH error: {e}')
    finally:
        conn.close()
    log(f'[GET] 200 /sync/push')
    return ('OK', 200)

def sync_with_peer():
    peer_ip = "10.243.4.245"  # ZeroTier IP of KL Laptop
    #peer_ip = "10.243.252.7"  # ZeroTier IP of Jake's Laptop
    while True:
        try:
            r = requests.get(f'http://{peer_ip}:5000/sync/pull', timeout=5)
            remote = r.json()
            res = requests.post('http://127.0.0.1:5000/sync/push', json=remote, timeout=5)
            if res.status_code != 200:
                log(f"Push failed with status: {res.status_code}")
        except Exception as e:
            if ENABLE_SYNC_LOGS:
                log(f'Sync failed: {e}')
                sys.excepthook(*sys.exc_info())
        time.sleep(60)

if __name__ == '__main__':
    ensure_column_exists()
    threading.Thread(target=sync_with_peer, daemon=True).start()
    app.run(debug=True, host='0.0.0.0', port=5000)
