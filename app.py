from flask import Flask, request, jsonify, render_template, send_file, abort, g
from shared.db import get_connection, db_lock
from shared.logger import log_message, log_buffer, log_exception
from flask_cors import CORS
import subprocess, sys, time

app = Flask(__name__)
CORS(app)

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    import sys
    log_exception(*sys.exc_info())
    return "Internal Server Error", 500


@app.before_request
def log_entry_latency():
    g.req_start = time.time()
    log_message(f"[RECV] {request.method} {request.path}")

@app.after_request
def after(response):
    duration = time.time() - g.get("req_start", time.time())
    if duration > 2:
        log_message(f"[SLOW] {request.method} {request.path} took {duration:.2f}s")
    return response

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Initial DB check
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.members');")
    result = cur.fetchone()[0]
    if result is None:
        log_message("Schema not found in PostgreSQL. Running init_db.py...")
        subprocess.run(['python3', 'init_db.py'])
except Exception as e:
    log_message(f"[INIT CHECK ERROR] {str(e)}")

# HTML routes
@app.route('/')
def root(): return render_template('hub.html')
@app.route('/hourlog')
def hourlog(): return render_template('hourlog.html')
@app.route('/member-tracking')
def member_tracking(): return render_template('members.html')

# Logs and DB download
@app.route('/logs')
def get_logs():
    from shared.logger import log_buffer, log_lock
    with log_lock:
        return jsonify(list(log_buffer)[-100:])

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    from shared.logger import log_buffer, log_lock
    with log_lock:
        log_buffer.clear()
    return ('OK', 200)

@app.route('/download-db')
def download_db():
    pw = request.args.get("pw", "")
    if pw != "GolfTec3914+":
        return '''<form><input type="password" name="pw" placeholder="Password"/><button type="submit">Download DB</button></form><div style="color:red;margin-top:10px;">{}</div>'''.format("Incorrect password." if pw else "")
    return send_file('tracking.db', as_attachment=True)

# Register blueprints
from member_tracking import bp as member_bp
from hourlog import bp as hourlog_bp
app.register_blueprint(member_bp)
app.register_blueprint(hourlog_bp)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    app.run(debug=args.debug, host='0.0.0.0', port=5000)