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





