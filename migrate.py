import argparse
import sqlite3
import os
import re
import sys
import time
import pandas as pd 


# Paths

DEFAULT_CSV = os.path.join(os.path.dirname(__file__),"ChargePoint_Data_CY20Q4.csv")
DEFAULT_DB  = os.path.join(os.path.dirname(__file__), "chargepoint.db")
SCHEMA_SQL  = os.path.join(os.path.dirname(__file__),  "create_schema.sql")



# Preprocessing

def hms_to_seconds(hms):
    
    if not isinstance(hms, str): 
        return 0
    
    m = re.fullmatch(r"(\d+):(\d{2}):(\d{2})", hms.strip())
    if not m:  
        return 0
    
    h, mn, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
    
    return h * 3600 + mn * 60 + s



def parse_datetime(date_str):
    
    if not isinstance(date_str, str):
        return None
    
    try:
        dt = pd.to_datetime(date_str, dayfirst=False)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None



def clean_org_name(name):
    
    return name.strip() if isinstance(name, str) else name





# Load & clean

def load_csv(path):

    df = pd.read_csv(
        path,
        low_memory=False,
        dtype={
            "Postal Code":        str,
            "Driver Postal Code": str,
            "User ID":            str,   # read as str first coerced below
            "Port Number":        int,
            "Plug In Event Id":   int,
        },
    )




    DROP_COLS = [
        "Country",                       
        "State/Province",                
        "Currency",                       
        "GHG Savings (kg)",               
        "Gasoline Savings (gallons)",     
        "Transaction Date (Pacific Time)",
        "County",                         
        "System S/N",                     
        "Model Number",                 
    ]
    df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)

   

    # Clean org name (trailing space variant)
    df["Org Name"] = df["Org Name"].map(clean_org_name)

   

    # Fix station name typo extra space
    typo_mask = df["Station Name"].str.contains(r"#\s+\d", na=False)
    if typo_mask.any():
        df.loc[typo_mask, "Station Name"] = (
            df.loc[typo_mask, "Station Name"].str.replace(r"#\s+", "#", regex=True)
        )
        print(f"{typo_mask.sum()} station name typo(s) normalised (e.g. '# 1' → '#1')")


   
    # Coerce User ID to numeric.
    df["User ID"] = pd.to_numeric(df["User ID"], errors="coerce")
    df.loc[df["User ID"] == 0, "User ID"] = None

    v_nulled  = df["User ID"].isna().sum() - 7677  # above the original null baseline
    if v_nulled > 0:
        print(f"{v_nulled} corrupt/anonymous User ID(s) coerced to NULL ")
              

    return df





# Extract dimension tables

def extract_organizations(df) :
    orgs = (
        df["Org Name"]
        .dropna()
        .unique()
    )
    return pd.DataFrame({"org_name": sorted(orgs)})



def extract_stations(df, org_lookup) :
    
    key_cols   = ["Station Name", "Org Name", "Address 1", "City", "Postal Code"]
    coord_cols = ["Latitude", "Longitude"]


    # Mode of coordinates per station (most frequent value)
    coords = (
        df.groupby("Station Name")[coord_cols]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
    )


    meta = (
        df[key_cols]
        .drop_duplicates(subset=["Station Name"])
        .merge(coords, on="Station Name", how="left")
    )

    meta["org_id"]   = meta["Org Name"].map(org_lookup)
    meta = meta.rename(columns={
        "Station Name": "station_name",
        "Address 1":    "address",
        "City":         "city",
        "Postal Code":  "postal_code",
        "Latitude":     "latitude",
        "Longitude":    "longitude",
    })
    
    return meta[["station_name", "org_id", "address", "city",
                 "postal_code", "latitude", "longitude"]]




def extract_ports(df, station_lookup):
     
    
    port_cols = ["Station Name", "Port Number", "Port Type", "Plug Type", "EVSE ID"]

    agg = (
        df[port_cols]
        .groupby(["Station Name", "Port Number"])
        .agg(
            port_type=("Port Type",  lambda x: x.mode().iloc[0] if x.notna().any() else None),
            plug_type=("Plug Type",  lambda x: x.mode().iloc[0] if x.notna().any() else None),
            evse_id  =("EVSE ID",    lambda x: str(int(x.dropna().iloc[0]))
                                               if x.notna().any() else None),
        )
        .reset_index()
    )
    #When port_type or plug_type differ across rows for the same port we take the mode.

    agg["station_id"] = agg["Station Name"].map(station_lookup)
    agg = agg.rename(columns={"Port Number": "port_number"})
    
    return agg[["station_id", "port_number", "port_type", "plug_type", "evse_id"]]




def extract_users(df: pd.DataFrame) -> pd.DataFrame:
    
    users = (
        df[["User ID", "Driver Postal Code"]]
        .dropna(subset=["User ID"])
        .drop_duplicates(subset=["User ID"]) # exclude  anonymous sessions
        .rename(columns={
            "User ID":            "user_id",
            "Driver Postal Code": "driver_postal_code",
        })
    )
    users["user_id"] = users["user_id"].astype(float).astype(int)
    
    return users



# Build sessions

def build_sessions(df, port_lookup) :

    s = pd.DataFrame()

    s["plug_in_event_id"]   = df["Plug In Event Id"].astype(int)
    
    s["port_id"]            = df.apply(
        lambda r: port_lookup.get((r["Station Name"], int(r["Port Number"]))),
        axis=1, )
    
    s["user_id"]            = df["User ID"].apply(lambda x: int(float(x)) if pd.notna(x) else None)
    
    
    s["start_datetime"]     = df["Start Date"].map(parse_datetime)
    s["start_timezone"]     = df["Start Time Zone"]
    s["end_datetime"]       = df["End Date"].map(parse_datetime)
    s["end_timezone"]       = df["End Time Zone"]
    s["total_duration_sec"] = df["Total Duration (hh:mm:ss)"].map(hms_to_seconds)
    s["charging_time_sec"]  = df["Charging Time (hh:mm:ss)"].map(hms_to_seconds)
    s["energy_kwh"]         = df["Energy (kWh)"].fillna(0.0)
    s["fee_usd"]            = df["Fee"].fillna(0.0)
    s["ended_by"]           = df["Ended By"]

    # Drop rows where port_id could not be resolved 
    missing = s["port_id"].isna().sum()
    if missing:
        print(f"{missing} sessions have no matching port — skipped")
        s = s.dropna(subset=["port_id"])

    s["port_id"] = s["port_id"].astype(int)

    
    # Deduplication: 34 rows share  the same session recorded twice with a different End Date 
    #Strategy: keep the row with the highest energy_kwh, so the most complete measurement. 
    before = len(s)
    
    s = (
        s.sort_values("energy_kwh", ascending=False)
         .drop_duplicates(subset=["plug_in_event_id", "port_id", "start_datetime"])
         .sort_index()
    )
    
    dropped = before - len(s)
    
    if dropped:
        print(f"{dropped} duplicate sessions removed (kept highest energy_kwh)")


    return s




# Write to SQLite

def init_db(db_path, schema_path) -> sqlite3.Connection:
    
    
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database: {db_path}")


    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")


    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    print(f"Schema created: {db_path}")
    
    return conn


def insert_df(conn: sqlite3.Connection, table, df) -> None:
    df.to_sql(table, conn, if_exists="append", index=False)





# Main


def main():
    
    parser = argparse.ArgumentParser(description="Migrate CSV to SQLite.")
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--db",  default=DEFAULT_DB)
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        sys.exit(f"ERROR: CSV not found at '{args.csv}'\n")

    total_start = time.time()


    df = load_csv(args.csv)

    conn = init_db(args.db, SCHEMA_SQL)



    #  Organizations
    orgs_df = extract_organizations(df)
    insert_df(conn, "organizations", orgs_df)
    conn.commit()
    org_lookup = {row[1]: row[0]
                  for row in conn.execute("SELECT org_id, org_name FROM organizations")}
    
    print(f"{len(orgs_df)} organizations inserted")


    # Stations

    stations_df = extract_stations(df, org_lookup)
    insert_df(conn, "stations", stations_df)
    conn.commit()
    station_lookup = {row[1]: row[0]
                      for row in conn.execute("SELECT station_id, station_name FROM stations")}
    print(f" {len(stations_df)} stations inserted")



    # Ports + Users
    
    ports_df = extract_ports(df, station_lookup)
    insert_df(conn, "ports", ports_df)
    conn.commit()
    port_lookup = {(row[1], row[2]): row[0]
                   for row in conn.execute(
                       "SELECT p.port_id, s.station_name, p.port_number "
                       "FROM ports p JOIN stations s ON p.station_id = s.station_id"
                   )}


    users_df = extract_users(df)
    insert_df(conn, "users", users_df)
    conn.commit()
    
    print(f"{len(ports_df)} ports, {len(users_df)} users inserted")



    #  Sessions
    print(" Inserting sessions (this may take a few minutes <=10)")
    
    t0 = time.time()
    sessions_df = build_sessions(df, port_lookup)



    # Insert in chunks to avoid locking the process
    CHUNK = 50_000
    total = 0
    for i in range(0, len(sessions_df), CHUNK):
        chunk = sessions_df.iloc[i : i + CHUNK]
        insert_df(conn, "sessions", chunk)
        conn.commit()
        total += len(chunk)
        print(f"      … {total:,} / {len(sessions_df):,} rows", end="\r")

    print(f" {total:,} sessions inserted in {time.time()-t0:.1f}s")


    #verification
    
    for table in ("organizations", "stations", "ports", "users", "sessions"):
        (count,) = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"   {table:<15} {count:>10,} rows") 

    conn.close()


if __name__ == "__main__":
    main()
