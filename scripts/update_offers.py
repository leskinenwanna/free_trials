import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import date
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BRAVE_KEY = os.getenv("BRAVE_API_KEY")


SEARCH_QUERIES = [
    "ilmainen kokeilukerta helsinki",
    "ilmainen treeni helsinki",
    "tutustumiskerta ilmaiseksi helsinki",
    "helsinki ilmainen harrastus kokeilu",
    "kokeile tanssia maksutta helsinki",
    "free trial gym helsinki",
]


def brave_search(query):
    headers = {"X-Subscription-Token": BRAVE_KEY}
    params = {"q": query, "count": 20, "search_lang": "fi"}
    r = requests.get("https://api.search.brave.com/res/v1/web/search",
                     headers=headers,
                     params=params)
    try:
        results = r.json().get("web", {}).get("results", [])
        return [item["url"] for item in results]
    except Exception:
        return []


def fetch_page_text(url):
    """Return much more page text than before."""
    try:
        html = requests.get(url, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")

        # Try to keep text readable
        texts = soup.find_all(text=True)
        visible_texts = []
        for t in texts:
            if t.parent.name not in ["script", "style", "meta", "noscript"]:
                visible_texts.append(t.strip())

        full_text = " ".join(visible_texts)
        return full_text[:15000]  # increase to 15000 chars
    except Exception:
        return ""


def ai_judgement(text, url):
    """
    Ask AI again, but with a more forgiving prompt.
    """
    prompt = f"""
Analysoi tämä sivun teksti ja URL: {url}

Etsi nimenomaan:
- ilmainen kokeilukerta
- ilmainen treeni
- kokeile maksutta
- free trial
- tutustuminen ilmaiseksi
- ensimmäinen treeni maksutta
- free class for new members
- kokeile ilmaiseksi

Jos sivu tarjoaa ilmaisen kokeilukerran harrastukseen, hyvinvointiin,
liikuntaan, tanssiin, joogaan, salille, koripalloon tai muuhun aktiviteettiin Helsingissä:

Vastaa:
KYLLÄ – selitys

Muuten:
EI – selitys

Tässä sivun teksti:
{text}
"""

    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    return resp.output_text.strip().lower()


def main():
    offers = []
    seen = set()

    # Gather URLs
    for q in SEARCH_QUERIES:
        for url in brave_search(q):
            if url not in seen:
                seen.add(url)

    print(f"Löytyi yhteensä {len(seen)} URLia Brave-haulla.")

    # AI only for the first 75 URLs to save money
    for url in list(seen)[:75]:
        text = fetch_page_text(url)
        if not text:
            continue

        answer = ai_judgement(text, url)

        if answer.startswith("kyllä"):
            offers.append({
                "name": url.split("//")[1].split("/")[0],
                "website": url,
                "offer_type": "Ilmainen kokeilukerta (AI tunnistama)",
                "ai_comment": answer,
                "last_checked": str(date.today())
            })

    with open("data/offers.json", "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

    print(f"Tallennettu {len(offers)} ilmaista kokeilua offers.json -tiedostoon.")


if __name__ == "__main__":
    main()

