# init_db.py

import sqlite3
conn = sqlite3.connect('tracking.db')
c = conn.cursor()

# Drop existing tables for clean start (optional)
c.executescript('''
DROP TABLE IF EXISTS member_perks;
DROP TABLE IF EXISTS tier_perks;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS tiers;
DROP TABLE IF EXISTS perks;
''')

c.execute('''
CREATE TABLE tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    color TEXT
)
''')

c.execute('''
CREATE TABLE members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER UNIQUE,
    name TEXT,
    tier_id INTEGER,
    sign_up_date TEXT,
    date_of_birth TEXT,
    FOREIGN KEY (tier_id) REFERENCES tiers(id)
)
''')

c.execute('''
CREATE TABLE perks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    reset_period TEXT
)
''')

c.execute('''
CREATE TABLE tier_perks (
    tier_id INTEGER,
    perk_id INTEGER,
    FOREIGN KEY (tier_id) REFERENCES tiers(id),
    FOREIGN KEY (perk_id) REFERENCES perks(id)
)
''')

c.execute('''
CREATE TABLE member_perks (
    member_id INTEGER,
    perk_id INTEGER,
    perk_claimed INTEGER DEFAULT 0,
    last_claimed TEXT,
    next_reset_date TEXT,
    FOREIGN KEY (member_id) REFERENCES members(member_id),
    FOREIGN KEY (perk_id) REFERENCES perks(id)
)
''')

conn.commit()
conn.close()
print("Database initialized.")
