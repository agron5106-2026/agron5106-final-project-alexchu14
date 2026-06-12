# REPORT.md


**Option B:** Real Data Migration: Flat to Relational  
**Author:** Alexandre Chu · A14922123  
**Dataset:** Electric Vehicle Charging Station Usage, Palo Alto CA (2011–2020)

---

## 1. Project overview

The dataset represents electric vehicle charging station usage in Palo Alto, California from 2011 to 2020.
It comes as a single flat CSV file: 259,415 charging sessions, 33 columns, ~85 MB. The CSV file can be downloaded at this adress: https://data.paloalto.gov/dataviews/257812/ELECT-VEHIC-CHARG-STATI-83602/ .

Every row repeats the same station name, address, organisation, and port type : there is no separation between "what happened during a session" and "facts about the station/port/user".
This makes the file inefficient to query and easy to corrupt
This project migrates the flat file into a normalised SQLite database with 5 tables (`organizations`, `stations`, `ports`, `users`, `sessions`),
connected through foreign keys. 

---

## 2. Repository structure and file descriptions

```
.
├── data/                         # Raw source data 
│   └── ChargePoint_Data_CY20Q4.csv
├── sql/
│   ├── create_schema.sql         # DDL: all CREATE TABLE, indexes, constraints
│   └── queries.sql               # Query demonstrations 
├              
├── migrate.py                    # Migration pipeline: CSV → SQLite
├── chargepoint.db                # Output 
├── README.md                     # Public-facing documentation
└── REPORT.md                     # This file
```

---


## 3. How to reproduce the project


### Steps


```bash
# 1. Clone the repository
git clone <repo-url>
cd <repo-folder>


# 2. Install dependencies
pip install pandas


# 3. Download the CSV and place it in the current working directory (i did everything from downloads):
# Source: https://data.paloalto.gov/dataviews/257812/ELECT-VEHIC-CHARG-STATI-83602/

# 4. Run the migration (creates chargepoint.db)
python migrate.py

# 5. Open chargepoint.db in DB Browser for SQLite to run queries
```


> The migration script is idempotent: running it multiple times always produces the same database from scratch. If `chargepoint.db` already exists, it is deleted and recreated.



---



## 4. Schema design and justification

The project decomposes the flat file into **5 tables**:

```
organizations ──→ stations ──→ ports ──→ sessions ←── users
```

### Table-by-table justification




#### `organizations`

`Org Name` has only 2 distinct values in the flat file ("City of Palo Alto"
and "City of Palo Alto " with a trailing space), but it is repeated on all
259,415 rows. Storing it once and referencing it by `org_id` removes this
redundancy and fixes an update anomaly. The trailing-space variant is stripped during migration.



#### `stations`
Station metadata (address, city, postal code, latitude, longitude) describes
the physical charging location, not the individual session. Two sessions at
the same station always share the same address, so there are repetitions in the CSV file. 
`Station Name` is used as the stable identifier rather than `MAC Address`,
because MAC addresses are tied to hardware, not to the station.

Latitude/longitude required a similar decision, some stations have
more than one recorded coordinate pair with differences of only a few tens
of metres (GPS measurement noise). For each station, the most frequently recorded coordinate
pair is stored as the canonical location.




#### `ports`

Each station has up to two physical charging ports, and `port_type` /
`plug_type` are properties of the port itself, not of a session ; the same
port always has the same connector type. Splitting `ports` into its own
table expresses this one-to-many relationship explicitly, with a foreign key `station_id` and a `UNIQUE (station_id,
port_number)` constraint to prevent duplicate port records.




#### `users`

Not every session has an associated user: 7,677 rows have no `User ID` at
all in the source file. Rather than discard these sessions, `user_id` in
`sessions` is nullable, and joins to `users` use `LEFT JOIN` so anonymous
sessions remain in query results with `user_id = NULL`.


Two further cases are treated the same way:

-`User ID = 0`  is the value ChargePoint assigns to unregistered/guest sessions,it does not
identify a real user so it is mapped to NULL. 

-Likewise, 41 rows have alphanumeric IDs with a trailing "V"  across  distinct
values; these do not correspond to valid numeric user IDs and are coerced to
NULL. 

In all three cases the session itself is kept, only the user link is removed.





#### `sessions`

`sessions` is the fact table: every other table describes an entity
(organisation, station, port, user) that exists independently of any single
charging event, while `sessions` records what actually happened, when, on
which port, by whom, for how long, and how much energy was delivered.

Durations (`Total Duration`, `Charging Time`) are stored as `INTEGER` seconds
rather than as `HH:MM:SS` strings. This makes aggregation easier.


`plug_in_event_id`, the natural identifier provided by the dataset, turned
out not to be globally unique: the counter resets per port, so the same ID
appears for different sessions at different ports. It therefore cannot serve as a primary key. Instead,
`session_id` is an `AUTOINCREMENT` surrogate key and the closest available
natural key is the combination `(plug_in_event_id, port_id, start_datetime)`.



###  Constraints and integrity



All foreign keys use `ON DELETE RESTRICT` . In this
schema, deleting a station or a port should not silently delete years of
session history.


Two `UNIQUE` constraints enforce the structure described above.
`UNIQUE (station_name, org_id)` on `stations` prevents the same station
being inserted twice, and `UNIQUE (station_id, port_number)` on `ports`
ensures a station cannot have two ports with the same number.



`CHECK` constraints encode domain knowledge directly in the schema.
`port_type` is restricted to `'Level 1'` or `'Level 2'` and `plug_type` to
`'J1772'` or `'NEMA 5-20R'`, the only values present in the dataset.
`energy_kwh`, `fee_usd`, and the duration columns are constrained to be
non-negative (`>= 0`), since negative energy or negative charging time would indicate a data error rather than a valid session.

---

























