--Number of sessions per station
SELECT s.station_name,
       COUNT(se.session_id) AS nb_sessions
FROM sessions se
JOIN ports    p ON se.port_id    = p.port_id
JOIN stations s ON p.station_id  = s.station_id
GROUP BY s.station_id
ORDER BY nb_sessions DESC;


-- The 10 users with the most sessions
SELECT u.user_id,
       COUNT(se.session_id)          AS nb_sessions,
       ROUND(SUM(se.energy_kwh), 1)  AS total_kwh,
       COUNT(DISTINCT p.station_id)  AS nb_visited_stations
FROM sessions se
JOIN users u ON se.user_id = u.user_id
JOIN ports p ON se.port_id = p.port_id
GROUP BY u.user_id
ORDER BY nb_sessions DESC
LIMIT 10;


-- Rank areas by benefits 
SELECT 
    s.postal_code AS code_postal,
    COUNT(se.session_id) AS total_recharges,
    ROUND(SUM(se.energy_kwh), 0) AS total_energy_kwh,
    ROUND(SUM(se.fee_usd), 0) AS total_benefits_usd
FROM sessions se
JOIN ports p ON se.port_id = p.port_id
JOIN stations s ON p.station_id = s.station_id
GROUP BY s.postal_code
ORDER BY total_benefits_usd DESC;


--Loyal users
SELECT u.user_id,
       COUNT(se.session_id)           AS nb_sessions,
       COUNT(DISTINCT p.station_id)   AS nb_stations,
       MIN(s.station_name)            AS station_unique
FROM sessions se
JOIN users    u ON se.user_id    = u.user_id
JOIN ports    p ON se.port_id    = p.port_id
JOIN stations s ON p.station_id  = s.station_id
GROUP BY u.user_id
HAVING nb_stations = 1
   AND nb_sessions >= 20
ORDER BY nb_sessions DESC
LIMIT 10;

