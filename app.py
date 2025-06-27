# app.py

from flask import Flask, request, jsonify, render_template
from datetime import datetime, timedelta
from flask_cors import CORS
import subprocess
import sqlite3
import os

# Auto-init the database if it's the first run
if not os.path.exists('tracking.db'):
    print("tracking.db not found. Running init_db.py...")
    subprocess.run(['python', 'init_db.py'])

app = Flask(__name__)
CORS(app)

DB = 'tracking.db'

def get_connection():
    conn = sqlite3.connect(DB)
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
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = ?', (member_id,))
    member = c.fetchone()
    if not member:
        conn.close()
        return

    c.execute('''
        SELECT mp.member_id, mp.perk_id, mp.perk_claimed, mp.last_claimed, p.reset_period
        FROM member_perks mp
        JOIN perks p ON mp.perk_id = p.id
        WHERE mp.member_id = ? AND mp.perk_claimed = 1
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
                UPDATE member_perks
                SET perk_claimed = 0,
                    last_claimed = NULL,
                    next_reset_date = NULL
                WHERE member_id = ? AND perk_id = ?
            ''', (member_id, row['perk_id']))

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

# MEMBER ROUTES
@app.route('/api/members', methods=['GET'])
def get_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT m.*, t.name AS tier_name, t.color
        FROM members m
        LEFT JOIN tiers t ON m.tier_id = t.id
    ''')
    members = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(members)

@app.route('/api/members/<int:member_id>', methods=['GET'])
def get_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM members WHERE member_id = ?', (member_id,))
    row = c.fetchone()
    conn.close()
    return jsonify(dict(row)) if row else ('Not found', 404)

@app.route('/api/members', methods=['POST'])
def create_or_edit_member():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    if 'id' in data and data['id']:
        c.execute('''
            UPDATE members SET member_id=?, name=?, tier_id=?, sign_up_date=?, date_of_birth=?
            WHERE id=?
        ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth'], data['id']))
    else:
        c.execute('''
            INSERT INTO members (member_id, name, tier_id, sign_up_date, date_of_birth)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['member_id'], data['name'], data['tier_id'], data['sign_up_date'], data['date_of_birth']))
    conn.commit()
    conn.close()
    return ('OK', 200)

@app.route('/api/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM member_perks WHERE member_id = ?', (member_id,))
    c.execute('DELETE FROM members WHERE member_id = ?', (member_id,))
    conn.commit()
    conn.close()
    return ('OK', 200)

# TIER ROUTES
@app.route('/api/tiers', methods=['GET'])
def get_tiers():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tiers')
    tiers = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(tiers)

@app.route('/api/tiers/<int:tier_id>', methods=['GET'])
def get_tier(tier_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tiers WHERE id = ?', (tier_id,))
    row = c.fetchone()
    conn.close()
    return jsonify(dict(row)) if row else ('Not found', 404)

@app.route('/api/tiers', methods=['POST'])
def create_or_edit_tier():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    if 'id' in data and data['id']:
        c.execute('UPDATE tiers SET name=?, color=? WHERE id=?', (data['name'], data['color'], data['id']))
    else:
        c.execute('INSERT INTO tiers (name, color) VALUES (?, ?)', (data['name'], data['color']))
    conn.commit()
    conn.close()
    return ('OK', 200)

@app.route('/api/tiers/<int:tier_id>', methods=['DELETE'])
def delete_tier(tier_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM tier_perks WHERE tier_id = ?', (tier_id,))
    c.execute('DELETE FROM tiers WHERE id = ?', (tier_id,))
    conn.commit()
    conn.close()
    return ('OK', 200)

# PERKS ROUTES
@app.route('/api/perks', methods=['GET'])
def get_perks():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM perks')
    perks = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(perks)

@app.route('/api/perks/<int:perk_id>', methods=['GET'])
def get_perk(perk_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM perks WHERE id = ?', (perk_id,))
    row = c.fetchone()
    conn.close()
    return jsonify(dict(row)) if row else ('Not found', 404)

@app.route('/api/perks', methods=['POST'])
def create_or_edit_perk():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    if 'id' in data and data['id']:
        c.execute('UPDATE perks SET name=?, reset_period=? WHERE id=?',
                  (data['name'], data['reset_period'], data['id']))
    else:
        c.execute('INSERT INTO perks (name, reset_period) VALUES (?, ?)',
                  (data['name'], data['reset_period']))
    conn.commit()
    conn.close()
    return ('OK', 200)

@app.route('/api/perks/<int:perk_id>', methods=['DELETE'])
def delete_perk(perk_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM tier_perks WHERE perk_id = ?', (perk_id,))
    c.execute('DELETE FROM member_perks WHERE perk_id = ?', (perk_id,))
    c.execute('DELETE FROM perks WHERE id = ?', (perk_id,))
    conn.commit()
    conn.close()
    return ('OK', 200)

# TIER-PERKS ROUTES
@app.route('/api/tier_perks/<int:tier_id>', methods=['GET'])
def get_perks_for_tier(tier_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT p.*
        FROM tier_perks tp
        JOIN perks p ON tp.perk_id = p.id
        WHERE tp.tier_id = ?
    ''', (tier_id,))
    perks = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(perks)

@app.route('/api/tier_perks', methods=['POST'])
def assign_perk_to_tier():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO tier_perks (tier_id, perk_id) VALUES (?, ?)',
              (data['tier_id'], data['perk_id']))

    c.execute('SELECT member_id FROM members WHERE tier_id = ?', (data['tier_id'],))
    members = c.fetchall()
    for m in members:
        c.execute('''
            INSERT OR IGNORE INTO member_perks (member_id, perk_id)
            VALUES (?, ?)
        ''', (m['member_id'], data['perk_id']))
    conn.commit()
    conn.close()
    return ('OK', 200)

@app.route('/api/tier_perks', methods=['DELETE'])
def unassign_perk_from_tier():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM tier_perks WHERE tier_id = ? AND perk_id = ?',
              (data['tier_id'], data['perk_id']))
    conn.commit()
    conn.close()
    return ('OK', 200)

# MEMBER-PERKS ROUTES
@app.route('/api/member_perks/<int:member_id>', methods=['GET'])
def get_member_perks(member_id):
    check_and_reset_member_perks(member_id)
    conn = get_connection()
    c = conn.cursor()

    # Get member's tier
    c.execute('SELECT tier_id FROM members WHERE member_id = ?', (member_id,))
    member = c.fetchone()
    if not member:
        conn.close()
        return jsonify([])

    # Get all perks assigned to the member's tier, with LEFT JOIN to claimed status
    c.execute('''
        SELECT 
            p.id, p.name, p.reset_period,
            mp.perk_claimed, mp.last_claimed, mp.next_reset_date
        FROM tier_perks tp
        JOIN perks p ON tp.perk_id = p.id
        LEFT JOIN member_perks mp
          ON mp.perk_id = p.id AND mp.member_id = ?
        WHERE tp.tier_id = ?
    ''', (member_id, member['tier_id']))

    perks = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(perks)

@app.route('/api/member_perks/claim', methods=['POST'])
def claim_perk():
    data = request.json
    now = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE member_perks
        SET perk_claimed = 1,
            last_claimed = ?,
            next_reset_date = NULL
        WHERE member_id = ? AND perk_id = ?
    ''', (now, data['member_id'], data['perk_id']))
    conn.commit()
    conn.close()
    return ('OK', 200)

@app.route('/api/member_perks/reset', methods=['POST'])
def reset_perk():
    data = request.json
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE member_perks
        SET perk_claimed = 0,
            last_claimed = NULL,
            next_reset_date = NULL
        WHERE member_id = ? AND perk_id = ?
    ''', (data['member_id'], data['perk_id']))
    conn.commit()
    conn.close()
    return ('OK', 200)

if __name__ == '__main__':
    app.run(debug=True)
