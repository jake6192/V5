from datetime import datetime, timedelta
import datetime as dt
from shared.db import get_connection
from shared.logger import log_message

def should_reset_weekly(last_claimed):
    try:
        last = last_claimed
    except ValueError:
        last = last_claimed
    today = datetime.now()
    this_monday = (today - timedelta(days=today.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    return last < this_monday

def should_reset_monthly(last_claimed, sign_up_date):
    try:
        claimed = last_claimed
        signup_day = int(sign_up_date.split('-')[2])
        today = datetime.now()
        reset_cutoff = today.replace(day=signup_day, hour=0, minute=0, second=0, microsecond=0)
        return (today.day == signup_day) and (claimed < reset_cutoff)
    except:
        return False

def should_reset_yearly(last_claimed, dob):
    try:
        claimed = last_claimed
        dob_month, dob_day = int(dob.split('-')[1]), int(dob.split('-')[2])
        today = datetime.now()
        reset_cutoff = datetime(today.year, dob_month, dob_day, 0,0,0)
        return (today.month == dob_month and today.day == dob_day) and (claimed < reset_cutoff)
    except:
        return False

def check_and_reset_member_perks(member_id):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT sign_up_date, date_of_birth FROM members WHERE member_id = %s', (member_id,))
        member = c.fetchone()
        if not member:
            return
        c.execute('''
            SELECT mp.member_id, mp.perk_id, mp.last_claimed, p.reset_period
            FROM member_perks mp
            JOIN perks p ON mp.perk_id = p.id
            WHERE mp.member_id = %s
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
                    WHERE member_id = %s AND perk_id = %s
                ''', (member_id, row['perk_id']))
        conn.commit()
    finally:
        conn.close()

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
            tmpMonth = today.month
            tmpYear = today.year
            if today.day > signup_day:
                for _ in range(multiplier):
                    base_month = tmpMonth + 1 if tmpMonth < 12 else 1
                    base_year = tmpYear if tmpMonth < 12 else tmpYear + 1
                    tmpMonth = base_month
                    tmpYear = base_year
            else:
                for _ in range(multiplier):
                    base_month = tmpMonth
                    base_year = tmpYear
                    tmpMonth = tmpMonth + 1 if tmpMonth < 12 else 1
                    tmpYear = tmpYear + 1 if tmpMonth == 1 else tmpYear
            next_reset = datetime(year=base_year, month=base_month, day=signup_day)
            return next_reset
        except:
            log_message(f"[calculate_next_reset()] Monthly error")
            return None
    elif reset_period == "Yearly":
        try:
            dob = member["date_of_birth"]
            if dob:
                if isinstance(dob, str):
                    dob = datetime.strptime(dob, "%Y-%m-%d")
                base = dob.replace(year=today.year)
                if base < today:
                    base = dob.replace(year=today.year + 1)
                return base.replace(year=base.year + (multiplier - 1))
        except:
            log_message(f"[calculate_next_reset()] Yearly error")
            return None
    return None
