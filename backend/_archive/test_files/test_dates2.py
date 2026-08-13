from database import execute_query; import json; print(json.dumps(execute_query('SELECT id, date, month, year FROM earthquakes WHERE date LIKE ''%2026'' LIMIT 10')))
