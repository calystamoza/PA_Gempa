import re

def extract_numbers_from_text(text: str) -> list[float]:
    pattern = r"(?<!\d)\d+(?:[.,]\d+)*(?!\d)"
    matches = re.findall(pattern, text)
    results = []
    for m in matches:
        # 1. Asumsi semuanya bukan desimal (ribuan) -> "2.202" -> 2202.0
        digits_only = re.sub(r"[^\d]", "", m)
        if digits_only:
            results.append(float(digits_only))
            
        # 2. Asumsi koma adalah desimal, titik adalah ribuan -> "2.202,50" -> 2202.50
        try:
            val_koma = float(m.replace(".", "").replace(",", "."))
            results.append(val_koma)
        except ValueError:
            pass
            
        # 3. Asumsi titik adalah desimal, koma adalah ribuan -> "2,202.50" -> 2202.50
        try:
            val_titik = float(m.replace(",", ""))
            results.append(val_titik)
        except ValueError:
            pass
            
    return list(set(results))

print("Text: 2.202")
print(extract_numbers_from_text("Rata-rata 3,852 dari total 2.202 kejadian M9.0."))
