import json
import re

text = """Namun, karena pertanyaan user sebelumnya adalah "Tampilkan 10 gempa terbaru yang tercatat dalam data kita", maka kita harus menghapus filter lokasi (place) agar pencarian dilakukan secara global. Berikut adalah JSON yang dapat dikembalikan:

```json
{
  "intent": "average",
  "metric": "magnitude",
  "filters": {
    "place": null,
    "year": 2023
  },
  "group_by": null,
  "order_by": null,
  "order_dir": null,
  "limit": null
}
```
"""

print("Original:")
print(repr(text))

match = re.search(r'\{.*\}', text, re.DOTALL)
if match:
    extracted = match.group(0)
    print("\nExtracted:")
    print(repr(extracted))
    try:
        parsed = json.loads(extracted)
        print("\nParsed successfully:", parsed)
    except Exception as e:
        print("\nJSON parse error:", e)
else:
    print("No match found")
