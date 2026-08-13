from database import execute_query; import json; print(json.dumps(execute_query('''
SELECT id, date, year, 
  CASE 
    WHEN year >= 2026 THEN to_date(date, 'DD/MM/YYYY') 
    ELSE to_date(date, 'MM/DD/YYYY') 
  END as parsed_date
FROM earthquakes 
LIMIT 5
''')))
