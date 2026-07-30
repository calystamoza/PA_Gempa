from database import execute_query; import json; print(json.dumps(execute_query('SELECT date FROM earthquakes ORDER BY to_date(date, ''DD/MM/YYYY'') DESC LIMIT 5')))
