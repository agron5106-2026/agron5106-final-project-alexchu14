# REPORT.md


**Option B:** Real Data Migration: Flat to Relational  
**Author:** Alexandre Chu · A14922123  
**Dataset:** Electric Vehicle Charging Station Usage, Palo Alto CA (2011–2020)

---

## 1. Project overview

The dataset represents electric vehicle charging station usage in Palo Alto, California from 2011 to 2020.
It comes as a single flat CSV file: 259,415 charging sessions, 33 columns, ~85 MB. The CSV file can be downloaded at this adress: https://www.kaggle.com/datasets/venkatsairo4899/ev-charging-station-usage-of-california-city/data

Every row repeats the same station name, address, organisation, and port type : there is no separation between "what happened during a session" and "facts about the station/port/user".
This makes the file inefficient to query and easy to corrupt
This project migrates the flat file into a normalised SQLite database with 5 tables (`organizations`, `stations`, `ports`, `users`, `sessions`),
connected through foreign keys. 
