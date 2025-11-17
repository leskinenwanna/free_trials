import json
from datetime import date
import requests
from bs4 import BeautifulSoup

# Esimerkkisivut
urls = [
    "https://www.esport.fi/",
    "https://www.elixia.fi/",
    "https://www.flamingo.fi/",
]

offers = []

for url in urls:
    try:
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text().lower()

        # Jos sivulla esiintyy "ilmainen kokeilu" tai "free trial"
        if "ilmainen kokeilu" in text or "free trial" in text:
            offers.append({
                "name": url.split("//")[1].split("/")[0],
                "category": "Kuntosali",
                "offer_type": "Ilmainen kokeilukerta",
                "website": url,
                "city_district": "Helsinki",
                "last_checked": str(date.today()),
                "status": "aktiivinen"
            })
    except Exception as e:
        print(f"Virhe haettaessa {url}: {e}")

# Kirjoitetaan tulokset korvaten koko tiedosto
with open("data/offers.json", "w", encoding="utf-8") as f:
    json.dump(offers, f, ensure_ascii=False, indent=2)

print(f"Luotu uusi offers.json {len(offers)} kohteella ({date.today()})")
