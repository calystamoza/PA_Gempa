import sys
import os
sys.path.append(os.path.abspath('.'))
from database import execute_query

sql = "SELECT place, date, magnitude, depth FROM earthquakes WHERE LOWER(place) LIKE %s ORDER BY magnitude DESC LIMIT 5"
params = ['%aceh%']
result = execute_query(sql, params)
print(f"RESULTS FOR ACEH: {result}")

sql2 = "SELECT MAX(magnitude) as max_mag FROM earthquakes"
result2 = execute_query(sql2)
print(f"OVERALL MAX: {result2}")
