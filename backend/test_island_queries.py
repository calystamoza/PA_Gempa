from rag_engine import process_query
import json

# Testing "Jawa" query
print("Testing 'Jawa' (Island level query)")
res_jawa = process_query("berapa total gempa di jawa tahun 2023?")
print(f"Intent Place: {res_jawa.get('fetched_data')[0] if res_jawa.get('fetched_data') else 'No Data'}")
print(f"SQL: {res_jawa.get('sql_query')}")
print(f"Answer: {res_jawa.get('answer')}")
print("-" * 30)

# Testing "Sumatera" query
print("Testing 'Sumatera' (Island level query)")
res_sumatera = process_query("rata rata magnitudo di sumatera")
print(f"SQL: {res_sumatera.get('sql_query')}")
print(f"Answer: {res_sumatera.get('answer')}")
