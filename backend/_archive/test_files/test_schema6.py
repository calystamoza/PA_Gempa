import datetime; from database import execute_query; import json; 
def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))
print(json.dumps(execute_query("SELECT id, date, time FROM earthquakes LIMIT 5"), default=json_serial))
