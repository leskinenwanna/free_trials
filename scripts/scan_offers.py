import json
from datetime import date

with open("data/offers.json", "r", encoding="utf-8") as f:
    offers = json.load(f)

# Päivitä päivämäärä jokaiseen riviin (simuloi tekoälyn päivitystä)
for o in offers:
    o["last_checked"] = str(date.today())

with open("data/offers.json", "w", encoding="utf-8") as f:
    json.dump(offers, f, ensure_ascii=False, indent=2)

print("Offers updated!")
