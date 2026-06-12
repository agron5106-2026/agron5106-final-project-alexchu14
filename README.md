# Electric Vehicle Charging Station Usage in Palo Alto, California — Flat to Relational

A data migration project that converts a real-world EV charging dataset from a flat CSV file into a normalised SQLite relational database, enabling efficient querying and eliminating data redundancy.

**Dataset:** [Electric Vehicle Charging Station Usage — City of Palo Alto] (https://data.paloalto.gov/dataviews/257812/ELECT-VEHIC-CHARG-STATI-83602/)  
**Period:** July 2011 – December 2020  
**Source format:** CSV flat file · 259,415 rows · 33 columns · ~85 MB

---

## What this project does

The City of Palo Alto publishes usage data for its public EV charging
network as a single flat CSV file: 259,415 charging sessions recorded
between 2011 and 2020, with every row repeating the same station name,
address, organisation, and port details. This makes the file large,
redundant, and awkward to query ; answering a question like "which stations
deliver the most energy?" means scanning and grouping 259k rows by hand every time.



This project migrates that flat file into a normalised **SQLite database**
with 5 related tables (organisations, stations, ports, users, sessions),
connected by foreign keys. Along the way, the migration script also cleans
up several real data quality issues found in the source file : inconsistent
station names, duplicate sessions, anonymous/corrupted user IDs, and drifting
GPS coordinates. The result is a ~45 MB database where the same questions can be answered with a few lines of SQL.



---


## Repository structure


```
.
├── data/                         # Raw source data 
│   └── ChargePoint_Data_CY20Q4.csv
├── sql/
│   ├── create_schema.sql         # DDL: all CREATE TABLE, indexes, constraints
│   └── queries.sql               # Query demonstrations 
├              
├── migrate.py                    # Migration pipeline: CSV → SQLite
├── README.md                     # This file
└── REPORT.md                     # Technical report for reproducibility
```

---




## Quickstart



### 1. Get the data

Download the CSV from https://data.paloalto.gov/dataviews/257812/ELECT-VEHIC-CHARG-STATI-83602/ 




### 2. Run the migration


```bash
python migrate.py
```


This will create `chargepoint.db` in the project root. The script is **idempotent**, running it twice drops and recreates the database from scratch.


Custom paths are supported:

```bash
python migrate.py --csv path/to/your.csv --db path/to/output.db
```

Expected output:

```
Loading CSV

Schema created: chargepoint.db

Inserting organizations …

Inserting stations …
     
Inserting ports and users …
     
Inserting sessions (this may take ~10mn) …

✅  Migration complete→ chargepoint.db


```

### 3. Query the database

Open `chargepoint.db` in [DB Browser for SQLite](https://sqlitebrowser.org/) and run queries from `sql/queries.sql`, or use any SQLite client.

---



## Schema overview


```
organizations ──→ stations ──→ ports ──→ sessions ←── users
```


Each charging session links back to the port it occurred on, which links to
its station, which links to the organisation that operates it. Sessions also
optionally link to the user who charged — `NULL` when the session was
anonymous.

| Table | Rows | Description |
|---|---|---|
| `organizations` | 1 | The operator (City of Palo Alto) |
| `stations` | 46 | Physical charging locations |
| `ports` | 80 | Individual connectors per station |
| `users` | 21,419 | Registered drivers (anonymous sessions excluded) |
| `sessions` | 259,398 | One row per charging event |

For full design explanation, see [REPORT.md](REPORT.md).


---



## Why not just use the CSV?


In the flat file, the organisation name is repeated on all 259,415 rows for
only 2 distinct values, and station addresses are repeated roughly 13,000
times each.  Beyond the storage savings, normalisation removes update anomalies: fixing a station's address
in the CSV means editing thousands of rows by hand, while in the database
it's a single `UPDATE` statement. Queries that group or filter by station,
port type, or user (the kind of analysis this dataset is actually useful
for),  also become a few lines of SQL instead of manual spreadsheet manipulation.




