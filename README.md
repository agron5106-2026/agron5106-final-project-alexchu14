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
