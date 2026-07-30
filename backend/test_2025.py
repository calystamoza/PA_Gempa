from database import execute_query; import json; print(json.dumps(execute_query('''SELECT id, date, year FROM earthquakes WHERE year = 2025 LIMIT 10''')))
