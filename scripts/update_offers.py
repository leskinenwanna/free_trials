import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import date
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BRAVE_KEY = os.getenv("BRAVE_API_KEY")

# Hakulausekkeet Brave-hausta
SEARCH_QUERIES = [
    "kokeile ilmaiseksi helsinki",
    "ilmainen kokeilukerta helsinki",
    "kokeile maksutta helsinki",
    "helsinki harrastus kokeilu",
    "ilmainen treeni helsinki",
    "ilmainen tanssitunti helsinki",
    "free trial helsinki",
]

def brave_search(query):
    """Hakee Brave Search API:lla listan sivustoja."""
    headers = {"X-Subscription-Token": BRAVE_KEY}
    params = {"q": query, "count": 20, "search_lang": "fi"}
    r = requests.get("https://api.search.brave.com/res/v1/web/search",
                     headers=headers, params=params)
    try:
        results = r.json().get("web", {}).get("results", [])
        return [item["url"] for item in results]
    except Exception:
        return []


def fetch_page_text(url):
    """Lataa nettisivun ja palauttaa raakatekstin."""
    try:
        html = requests.get(url, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text(" ", strip=True)
    except Exception:
        return ""


def ai_judgement(text, url):
    """
    Pyytää OpenAI:ta arvioimaan, tarjoaako sivu
    ilmaisen kokeilukerran helsinkiläiseen harrastukseen.
    """
    prompt = f"""
Analysoi tämä sivun teksti ja URL:
URL: {url}

Vastaa täsmällisesti:
1. Onko sivulla tarjolla ilmainen kokeilukerta, ilmainen treeni, ilmainen kokeilujakso,
   maksuton tutustumiskerta TAI muu kokeilu harrastus-, hyvinvointi-, tanssi- tai liikuntapalveluun?
2. Onko se nimenomaan Helsingissä TAI verkossa koko Suomea varten (esim. FeelHobby tyyppiset sivut)?
3. Jos vastaus on kyllä, kerro lyhyesti miksi.

Vastaa muodossa:
KYLLÄ – selitys
TAI
EI – selitys

Teksti:
{text[:5000]}
"""

    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    answer = resp.output_text.strip().lower()
    return answer


def main():
    offers = []
    seen_urls = set()

    # 1) BRAVE-HAKU – löydä sivustot
    for query in SEARCH_QUERIES:
        urls = brave_search(query)
        for url in urls:
            if url not in seen_urls:
                seen_urls.add(url)

    print(f"Löytyi yhteensä {len(seen_urls)} URLia Brave-haulla.")

    # 2) ANALYSOI JOKAINEN SIVU AI:LLA
    for url in list(seen_urls)[:20]:
        text = fetch_page_text(url)
        if not text:
            continue

        answer = ai_judgement(text, url)

        # OpenAI vastaa muodossa: "kyllä – …"
        if answer.startswith("kyllä"):
            offers.append({
                "name": url.split("//")[1].split("/")[0],  # domain
                "website": url,
                "offer_type": "Ilmainen kokeilukerta (AI tunnistama)",
                "city": "Helsinki tai online",
                "ai_comment": answer,
                "last_checked": str(date.today())
            })

    # 3) KIRJOITA TIEDOSTO
    with open("data/offers.json", "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

    print(f"Tallennettu {len(offers)} ilmaista kokeilua offers.json -tiedostoon.")


if __name__ == "__main__":
    main()
