from database import execute_query; import json; print(json.dumps(execute_query('SELECT id, date, month, year FROM earthquakes LIMIT 10')))
