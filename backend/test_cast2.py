from database import execute_query; rows = execute_query('''
SELECT id, date, year FROM earthquakes
''');
errors = 0
for row in rows:
    try:
        if row['year'] >= 2026:
            d = row['date'].split('/')
            if len(d) == 3: pass
        else:
            d = row['date'].split('/')
            if len(d) == 3: pass
    except:
        errors += 1
print(f'Done checking, errors: {errors}')

