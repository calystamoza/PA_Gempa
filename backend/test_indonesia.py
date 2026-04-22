from rag_engine import process_query
import json

# Kasus 1: "rata rata gempa indonesia"
res1 = process_query("rata rata gempa indonesia")
print("Query: rata rata gempa indonesia")
print(f"SQL: {res1['sql_query']}")
print(f"Answer: {res1['answer']}")
print("-" * 20)

# Kasus 2: "total gempa di indonesia tahun 2020"
res2 = process_query("total gempa di indonesia tahun 2020")
print("Query: total gempa di indonesia tahun 2020")
print(f"SQL: {res2['sql_query']}")
print(f"Answer: {res2['answer']}")
