# app.py

from flask import Flask, request, jsonify, render_template, send_file, abort
from datetime import datetime, timedelta
from flask_cors import CORS
import subprocess
import sqlite3
import os
import traceback

# Auto-init the database if it's the first run
if not os.path.exists('tracking.db'):
    print("tracking.db not found. Running init_db.py...")
    subprocess.run(['python', 'init_db.py'])

app = Flask(__name__)
CORS(app)
DB = 'tracking.db'
DOWNLOAD_DB_PASSWORD = "GolfTec3914+"

@app.errorhandler(Exception)
def handle_exception(e):
    print("[FLASK ERRORHANDLER]\n", traceback.format_exc())
    return "Internal server error", 500

@app.route('/download-db')
def download_db():
    pw = request.args.get("pw", "")
    print(f"[DOWNLOAD-DB] attempt with pw={pw}")
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
    print("[DOWNLOAD-DB] password correct, sending file")
    return send_file('tracking.db', as_attachment=True)

def get_connection():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def should_reset_weekly(last_claimed):
    last = datetime.strptime(last_claimed, "%Y-%m-%d")
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday())
    return last < last_monday

def should_reset_monthly(last_claimed, sign_up_date):
    try:
        claimed = datetime.strptime(last_claimed, "%Y-%m-%d")
        signup_day = int(sign_up_date.split('-')[2])
        today = datetime.now()
        reset_date = today.replace(day=signup_day)
        return claimed < reset_date and today.day == signup_day
    except:
        return False

def should_reset_yearly(last_claimed, dob):
    try:
        claimed = datetime.strptime(last_claimed, "%Y-%m-%d")
        dob_month, dob_day = int(dob.split('-')[1]), int(dob.split('-')[2])
        today = datetime.now()
        reset_this_year = datetime(today.year, dob_month, dob_day)
        return claimed < reset_this_year and today.month == dob_month and today.day == dob_day
    except:
        return False

def check_and_reset_member_perks(member_id):
    print(f"[RESET CHECK] member_id={member_id}")
    conn = get_connection()
    try:
        c = conn.cursor()

        # Fetch member dates
        c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = ?', (member_id,))
        member = c.fetchone()
        print(f"[RESET] fetched member row: {dict(member) if member else None}")
        if not member:
            print("[RESET] No such member, skipping")
            return

        # Fetch claimed perks
        c.execute('''
            SELECT mp.member_id, mp.perk_id, mp.last_claimed, p.reset_period
            FROM member_perks mp
            JOIN perks p ON mp.perk_id = p.id
            WHERE mp.member_id = ?
        ''', (member_id,))
        rows = c.fetchall()
        print(f"[RESET] found {len(rows)} claimed perks rows")

        for row in rows:
            row_d = dict(row)
            print(f"[RESET EVAL] {row_d}")
            if not row['last_claimed']:
                continue

            reset = False
            if row['reset_period'] == 'Weekly':
                reset = should_reset_weekly(row['last_claimed'])
            elif row['reset_period'] == 'Monthly':
                reset = should_reset_monthly(row['last_claimed'], member['sign_up_date'])
            elif row['reset_period'] == 'Yearly':
                reset = should_reset_yearly(row['last_claimed'], member['date_of_birth'])

            print(f"[RESET DECISION] reset={reset} for perk_id={row['perk_id']}")
            if reset:
                c.execute('''
                    DELETE FROM member_perks
                    WHERE member_id = ? AND perk_id = ?
                ''', (member_id, row['perk_id']))
                print(f"[RESET DELETE] removed member_perks for perk_id={row['perk_id']}")

        conn.commit()
        # Final state
        c.execute('SELECT * FROM member_perks WHERE member_id = ?', (member_id,))
        final = [dict(r) for r in c.fetchall()]
        print(f"[RESET DB STATE] now has {len(final)} rows: {final}")
    except Exception as e:
        print("[RESET ERROR]\n", traceback.format_exc())
    finally:
        conn.close()

# --- calculate next reset date when claiming
def calculate_next_reset(reset_period, member):
    today = datetime.today()
    if reset_period == "Weekly":
        days_until_monday = (7 - today.weekday()) % 7 or 7
        return (today + timedelta(days=days_until_monday)).strftime("%Y-%m-%d")
    elif reset_period == "Monthly":
        try:
            signup_day = int(member["sign_up_date"].split("-")[2])
            this_month = today.replace(day=signup_day)
            if today.day < signup_day:
                next_reset = this_month
            else:
                month = today.month + 1 if today.month < 12 else 1
                year = today.year + (1 if today.month == 12 else 0)
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                day = min(signup_day, last_day)
                next_reset = datetime(year, month, day)
            return next_reset.strftime("%Y-%m-%d")
        except:
            return None
    elif reset_period == "Yearly":
        try:
            m_dob = datetime.strptime(member["date_of_birth"], "%Y-%m-%d")
            next_r = m_dob.replace(year=today.year)
            if next_r < today:
                next_r = next_r.replace(year=today.year+1)
            return next_r.strftime("%Y-%m-%d")
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
        members = [dict(r) for r in c.fetchall()]
        print(f"[API OUT] /api/members => {len(members)} rows")
        return jsonify(members)
    finally:
        conn.close()

@app.route('/api/members/<int:member_id>', methods=['GET'])
def get_member(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM members WHERE member_id = ?', (member_id,))
        row = c.fetchone()
        print(f"[API OUT] /api/members/{member_id} => {dict(row) if row else None}")
        return jsonify(dict(row)) if row else ('Not found', 404)
    finally:
        conn.close()

@app.route('/api/members', methods=['POST'])
def create_or_edit_member():
    data = request.json
    print(f"[MEMBER SAVE] payload: {data}")
    conn = get_connection()
    try:
        c = conn.cursor()
        if data.get('id'):
            # existing
            c.execute('SELECT member_id FROM members WHERE id=?', (data['id'],))
            old = c.fetchone()
            old_mid = old['member_id'] if old else None
            print(f"[MEMBER SAVE] old_member_id={old_mid}")
            c.execute('''
                UPDATE members
                SET member_id=?, name=?, tier_id=?, sign_up_date=?, date_of_birth=?
                WHERE id=?
            ''', (data['member_id'], data['name'], data['tier_id'],
                  data['sign_up_date'], data['date_of_birth'], data['id']))
            if old_mid and old_mid != data['member_id']:
                c.execute('UPDATE member_perks SET member_id=? WHERE member_id=?',
                          (data['member_id'], old_mid))
                print(f"[MEMBER SAVE] migrated member_perks from {old_mid} to {data['member_id']}")
        else:
            # new
            c.execute('''
                INSERT INTO members (member_id,name,tier_id,sign_up_date,date_of_birth)
                VALUES (?,?,?,?,?)
            ''', (data['member_id'], data['name'], data['tier_id'],
                  data['sign_up_date'], data['date_of_birth']))
            print("[MEMBER SAVE] inserted new member")
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    print(f"[MEMBER DELETE] member_id={member_id}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM member_perks WHERE member_id=?', (member_id,))
        c.execute('DELETE FROM members WHERE member_id=?', (member_id,))
        conn.commit()
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
        tiers = [dict(r) for r in c.fetchall()]
        print(f"[API OUT] /api/tiers => {len(tiers)} rows")
        return jsonify(tiers)
    finally:
        conn.close()

@app.route('/api/tiers/<int:tier_id>', methods=['GET'])
def get_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM tiers WHERE id=?', (tier_id,))
        row = c.fetchone()
        print(f"[API OUT] /api/tiers/{tier_id} => {dict(row) if row else None}")
        return jsonify(dict(row)) if row else ('Not found', 404)
    finally:
        conn.close()

@app.route('/api/tiers', methods=['POST'])
def create_or_edit_tier():
    data = request.json
    print(f"[TIER SAVE] payload: {data}")
    conn = get_connection()
    try:
        c = conn.cursor()
        if data.get('id'):
            c.execute('UPDATE tiers SET name=?,color=? WHERE id=?',
                      (data['name'], data['color'], data['id']))
            print(f"[TIER SAVE] updated tier id={data['id']}")
        else:
            c.execute('INSERT INTO tiers(name,color) VALUES (?,?)',
                      (data['name'], data['color']))
            print("[TIER SAVE] inserted new tier")
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/tiers/<int:tier_id>', methods=['DELETE'])
def delete_tier(tier_id):
    print(f"[TIER DELETE] id={tier_id}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE tier_id=?', (tier_id,))
        c.execute('DELETE FROM tiers WHERE id=?', (tier_id,))
        conn.commit()
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
            ORDER BY CASE reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5 END
        """)
        perks = [dict(r) for r in c.fetchall()]
        print(f"[API OUT] /api/perks => {len(perks)} rows")
        return jsonify(perks)
    finally:
        conn.close()

@app.route('/api/perks/<int:perk_id>', methods=['GET'])
def get_perk(perk_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT * FROM perks WHERE id=?', (perk_id,))
        row = c.fetchone()
        print(f"[API OUT] /api/perks/{perk_id} => {dict(row) if row else None}")
        return jsonify(dict(row)) if row else ('Not found', 404)
    finally:
        conn.close()

@app.route('/api/perks', methods=['POST'])
def create_or_edit_perk():
    data = request.json
    print(f"[PERK SAVE] payload: {data}")
    conn = get_connection()
    try:
        c = conn.cursor()
        if data.get('id'):
            c.execute('UPDATE perks SET name=?,reset_period=? WHERE id=?',
                      (data['name'], data['reset_period'], data['id']))
            print(f"[PERK SAVE] updated perk id={data['id']}")
        else:
            c.execute('INSERT INTO perks(name,reset_period) VALUES (?,?)',
                      (data['name'], data['reset_period']))
            print("[PERK SAVE] inserted new perk")
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/perks/<int:perk_id>', methods=['DELETE'])
def delete_perk(perk_id):
    print(f"[PERK DELETE] id={perk_id}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE perk_id=?', (perk_id,))
        c.execute('DELETE FROM member_perks WHERE perk_id=?', (perk_id,))
        c.execute('DELETE FROM perks WHERE id=?', (perk_id,))
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

# TIER-PERKS ROUTES
@app.route('/api/tier_perks/<int:tier_id>', methods=['GET'])
def get_perks_for_tier(tier_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT p.*
            FROM tier_perks tp
            JOIN perks p ON tp.perk_id = p.id
            WHERE tp.tier_id=?
            ORDER BY CASE p.reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5 END
        ''', (tier_id,))
        perks = [dict(r) for r in c.fetchall()]
        print(f"[API OUT] /api/tier_perks/{tier_id} => {len(perks)} rows")
        return jsonify(perks)
    finally:
        conn.close()

@app.route('/api/tier_perks', methods=['POST'])
def assign_perk_to_tier():
    data = request.json
    print(f"[TIER_PERKS ASSIGN] payload: {data}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO tier_perks(tier_id,perk_id) VALUES (?,?)',
                  (data['tier_id'], data['perk_id']))
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/tier_perks', methods=['DELETE'])
def unassign_perk_from_tier():
    data = request.json
    print(f"[TIER_PERKS UNASSIGN] payload: {data}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM tier_perks WHERE tier_id=? AND perk_id=?',
                  (data['tier_id'], data['perk_id']))
        conn.commit()
        return ('OK', 200)
    finally:
        conn.close()

@app.route('/api/member_perks/<int:member_id>', methods=['GET'])
def get_member_perks(member_id):
    print(f"[API IN ] GET /api/member_perks/{member_id}")
    check_and_reset_member_perks(member_id)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT tier_id FROM members WHERE member_id=?', (member_id,))
        member = c.fetchone()
        if not member:
            print("[API OUT] member has no tier => returning []")
            return jsonify([])

        c.execute('''
            SELECT p.id, p.name, p.reset_period,
                   mp.last_claimed, mp.next_reset_date
            FROM tier_perks tp
            JOIN perks p ON tp.perk_id = p.id
            LEFT JOIN member_perks mp
              ON mp.perk_id = p.id
             AND mp.member_id = ?
            WHERE tp.tier_id = ?
            ORDER BY CASE p.reset_period
                WHEN 'Weekly' THEN 1
                WHEN 'Monthly' THEN 2
                WHEN 'Yearly' THEN 3
                WHEN 'Unlimited' THEN 4
                ELSE 5 END
        ''', (member_id, member['tier_id']))
        perks = [dict(r) for r in c.fetchall()]
        print(f"[API OUT] /api/member_perks/{member_id} => {perks}")
        return jsonify(perks)
    finally:
        conn.close()

@app.route('/api/member_perks/claim', methods=['POST'])
def claim_perk():
    data = request.json
    now = datetime.now().strftime("%Y-%m-%d")
    print(f"[CLAIM IN ] payload: {data}, now={now}")
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT reset_period FROM perks WHERE id=?', (data['perk_id'],))
        perk = c.fetchone()
        print(f"[CLAIM] perk reset_period={perk['reset_period'] if perk else None}")

        c.execute('SELECT sign_up_date,date_of_birth FROM members WHERE member_id=?', (data['member_id'],))
        member = c.fetchone()
        print(f"[CLAIM] member data={dict(member) if member else None}")

        reset_period = perk["reset_period"] if perk else None
        member_data = {
            "sign_up_date": member["sign_up_date"],
            "date_of_birth": member["date_of_birth"]
        } if member else {}

        next_reset = calculate_next_reset(reset_period, member_data) if reset_period else None
        print(f"[CLAIM] next_reset computed={next_reset}")

        try:
            c.execute('''
                INSERT INTO member_perks(member_id,perk_id,last_claimed,next_reset_date)
                VALUES(?,?,?,?)
            ''', (data['member_id'], data['perk_id'], now, next_reset))
            conn.commit()
            # verify
            c.execute('SELECT * FROM member_perks WHERE member_id=? AND perk_id=?',
                      (data['member_id'], data['perk_id']))
            row = c.fetchone()
            print(f"[CLAIM VERIFY] {dict(row) if row else None}")
            print("[CLAIM SUCCESS]")
            return ('OK', 200)
        except Exception as e:
            print("[CLAIM ERROR]\n", traceback.format_exc())
            return (f"Claim failed: {str(e)}", 500)
    finally:
        conn.close()

@app.route('/api/member_perks/reset', methods=['POST'])
def reset_perk():
    print(f"[RESET IN ] payload: {request.json}")
    data = request.json
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('DELETE FROM member_perks WHERE member_id=? AND perk_id=?',
                  (data['member_id'], data['perk_id']))
        conn.commit()
        print("[RESET SUCCESS]")
        return ('OK', 200)
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
