# init_db.py

import psycopg2

DB = {
    "dbname": "tracking",
    "user": "simtec",
    "password": "Golftec789+",
    "host": "localhost",
    "port": 5432
}

conn = psycopg2.connect(**DB)
conn.autocommit = True
c = conn.cursor()

# Drop existing tables
c.execute("""
    DROP TABLE IF EXISTS member_perks CASCADE;
    DROP TABLE IF EXISTS tier_perks CASCADE;
    DROP TABLE IF EXISTS members CASCADE;
    DROP TABLE IF EXISTS perks CASCADE;
    DROP TABLE IF EXISTS tiers CASCADE;
""")

# Rebuild schema
c.execute("""
CREATE TABLE tiers (
    id SERIAL PRIMARY KEY,
    name TEXT,
    color TEXT
)
""")

c.execute("""
CREATE TABLE perks (
    id SERIAL PRIMARY KEY,
    name TEXT,
    reset_period TEXT
)
""")

c.execute("""
CREATE TABLE members (
    id SERIAL PRIMARY KEY,
    member_id INTEGER UNIQUE GENERATED BY DEFAULT AS IDENTITY,
    name TEXT,
    tier_id INTEGER REFERENCES tiers(id),
    sign_up_date TEXT,
    date_of_birth TEXT
)
""")

c.execute("""
CREATE TABLE tier_perks (
    tier_id INTEGER REFERENCES tiers(id),
    perk_id INTEGER REFERENCES perks(id),
    PRIMARY KEY (tier_id, perk_id)
)
""")

c.execute("""
CREATE TABLE member_perks (
    member_id INTEGER REFERENCES members(id),
    perk_id INTEGER REFERENCES perks(id),
    claimed INTEGER,
    last_claimed TEXT,
    next_reset_date TEXT,
    PRIMARY KEY (member_id, perk_id)
)
""")

# Index for faster lookup in tier_perks
c.execute("""
CREATE INDEX IF NOT EXISTS idx_tierperk_pair ON tier_perks(tier_id, perk_id)
""")

print("✅ PostgreSQL schema initialized successfully.")
conn.close()
