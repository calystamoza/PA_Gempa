from database import execute_query; import json; print(json.dumps(execute_query('''
SELECT id, date, year, month, 
  CASE 
    WHEN year >= 2026 THEN split_part(date, '/', 1)::integer
    ELSE split_part(date, '/', 2)::integer
  END as day
FROM earthquakes 
ORDER BY year DESC, month DESC, day DESC
LIMIT 5
''')))
