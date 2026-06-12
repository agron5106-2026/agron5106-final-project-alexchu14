-- ChargePoint EV Charging Data — Relational Schema
-- Source: ChargePoint_Data_CY20Q4.csv (259,415 sessions, 2011–2020)


PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;


-- 1. organizations
--    2 unique values in the flat file 


CREATE TABLE IF NOT EXISTS organizations (
    org_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    org_name    TEXT    NOT NULL UNIQUE
);


-- 2. stations
--    47 unique Station Names in the flat file.
--   A single station can have multiple MAC addresses over its lifetime (hardware replacements?). 
--    The stable identifier is therefore (station_name, org_id), not MAC address.


CREATE TABLE IF NOT EXISTS stations (
    station_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    station_name TEXT    NOT NULL,
    org_id       INTEGER NOT NULL REFERENCES organizations(org_id)
                         ON DELETE RESTRICT,
    address      TEXT    NOT NULL,
    city         TEXT    NOT NULL,
    postal_code  TEXT    NOT NULL,
    latitude     REAL    NOT NULL,
    longitude    REAL    NOT NULL,
    UNIQUE (station_name, org_id)
);

CREATE INDEX IF NOT EXISTS idx_stations_org ON stations(org_id);


-- 3. ports
--    80 unique (station_name, port_number) combinations.
--    Each physical port has a fixed type and plug connector.

CREATE TABLE IF NOT EXISTS ports (
    port_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id  INTEGER NOT NULL REFERENCES stations(station_id)
                        ON DELETE RESTRICT,
    port_number INTEGER NOT NULL,
    port_type   TEXT    CHECK (port_type IN ('Level 1', 'Level 2')),
    plug_type   TEXT    CHECK (plug_type IN ('J1772', 'NEMA 5-20R')),
    evse_id     TEXT,  -- nullable: missing for ~30% rows
    UNIQUE (station_id, port_number)
);

CREATE INDEX IF NOT EXISTS idx_ports_station ON ports(station_id);


-- 4. users

CREATE TABLE IF NOT EXISTS users (
    user_id            INTEGER PRIMARY KEY,  -- natural key from source data
    driver_postal_code TEXT  -- nullable: 3.2% missing
);


-- 5. sessions  (fact table)
--    One row per charging event (plug-in to plug-out).
--    IMPORTANT: plug_in_event_id is NOT globally unique in the source data.
--    ChargePoint resets the counter per port, and even per (port, year).
--   The narrowest available natural key is (plug_in_event_id, port_id, start_datetime). 

CREATE TABLE IF NOT EXISTS sessions (
    session_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plug_in_event_id    INTEGER NOT NULL,
    port_id             INTEGER NOT NULL REFERENCES ports(port_id)
                                ON DELETE RESTRICT,
    user_id             INTEGER REFERENCES users(user_id)
                                ON DELETE SET NULL,
    start_datetime      TEXT    NOT NULL,           
    start_timezone      TEXT    CHECK (start_timezone IN ('PDT','PST','UTC')),
    end_datetime        TEXT,                       
    end_timezone        TEXT    CHECK (end_timezone IN ('PDT','PST','UTC')),
    total_duration_sec  INTEGER NOT NULL CHECK (total_duration_sec >= 0),
    charging_time_sec   INTEGER NOT NULL CHECK (charging_time_sec >= 0),
    energy_kwh          REAL    NOT NULL CHECK (energy_kwh >= 0),
    fee_usd             REAL    NOT NULL CHECK (fee_usd >= 0),
    ended_by            TEXT  -- nullable: 248 missing
    -- No UNIQUE constraint on plug_in_event_id: ChargePoint resets counters per port. 
);

CREATE INDEX IF NOT EXISTS idx_sessions_port    ON sessions(port_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start   ON sessions(start_datetime);
CREATE INDEX IF NOT EXISTS idx_sessions_energy  ON sessions(energy_kwh);
