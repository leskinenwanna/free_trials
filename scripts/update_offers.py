import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import date
from urllib.parse import urlparse
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
BRAVE_KEY = os.getenv("BRAVE_API_KEY")

SEARCH_QUERIES = [
    "ilmainen kokeilukerta helsinki",
    "ilmainen treeni helsinki",
    "tutustumiskerta ilmaiseksi helsinki",
    "helsinki ilmainen harrastus kokeilu",
    "free trial gym helsinki",
    "kokeile maksutta helsinki",
    "ilmainen tanssitunti helsinki",
]

def brave_search(query):
    """Fetch URLs from Brave Search."""
    headers = {"X-Subscription-Token": BRAVE_KEY}
    params = {"q": query, "count": 20, "search_lang": "fi"}
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params=params,
            timeout=20
        )
        results = r.json().get("web", {}).get("results", [])
        return [item["url"] for item in results]
    except Exception:
        return []

def fetch_page_text(url):
    """Extract visible text from a webpage."""
    try:
        html = requests.get(url, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")

        texts = soup.find_all(string=True)
        visible_texts = []
        for t in texts:
            if t.parent.name not in ["script", "style", "meta", "noscript"]:
                stripped = t.strip()
                if stripped:
                    visible_texts.append(stripped)

        full_text = " ".join(visible_texts)
        return full_text[:15000]
    except Exception:
        return ""

def ai_judgement(text, url):
    """
    Improved AI prompt for detecting free trials.
    More permissive and real-world friendly.
    """
    prompt = f"""
Analysoi tämä sivun teksti ja URL: {url}

Tunnista, tarjoaako sivu ilmaisen kokeilukerran, ilmaisen treenin, free trialin
tai maksuttoman tutustumiskerran harrastukseen, liikuntaan, tanssiin, joogaan,
kuntosaliin tai muuhun harrastus aktiviteettiin Helsingissä.

HYVÄKSY SIVU, JOS:
- otsikossa tai tekstissä lukee “ilmainen kokeilukerta”
- sivulla lukee “kokeile ilmaiseksi”, “kokeile maksutta”, “tutustuminen ilmaiseksi”
- ensimmäinen treeni on ilmainen uusille asiakkaille
- rekisteröityminen johtaa ilmaiseen kokeiluun
- teksti antaa edes osittain ymmärtää ilmaisen kokeilun mahdollisuutta

ÄLÄ HYLKÄÄ
vain siksi että sivun teksti on lyhyt tai vajaa.

HYLKÄÄ SIVU
vain jos missään kohdassa ei viitata ilmaiseen kokeiluun tai kyseessä oleva kokeilu esim. tarjoaa laihdutus- tai kauneuspalveluita.

Vastaa muodossa:
KYLLÄ – selitys
TAI
EI – selitys

Sivun teksti:
{text}
"""

    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )
    return resp.output_text.strip().lower()

def main():
    offers = []
    seen_urls = set()
    domain_seen = set()  # for domain-level dedupe

    # Collect URLs from Brave
    for q in SEARCH_QUERIES:
        for url in brave_search(q):
            if url not in seen_urls:
                seen_urls.add(url)

    print(f"Löytyi yhteensä {len(seen_urls)} URLia Brave-haulla.")

    approved_count = 0

    # Analyze first 100 URLs
    for url in sorted(seen_urls)[:100]:
        text = fetch_page_text(url)
        if not text:
            continue

        answer = ai_judgement(text, url)

        print("----")
        print(f"URL: {url}")
        print(f"AI vastaus: {answer[:500]}")

        if answer.startswith("kyllä"):
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")

            # skip duplicate domains
            if domain in domain_seen:
                print(f"⏩ Ohitetaan duplikaatti domain: {domain}")
                continue

            domain_seen.add(domain)

            offers.append({
                "name": url,  # unique by URL
                "website": url,
                "offer_type": "Ilmainen kokeilukerta (AI tunnistama)",
                "ai_comment": answer,
                "last_checked": str(date.today())
            })

            approved_count += 1

    # Save results
    os.makedirs("data", exist_ok=True)
    with open("data/offers.json", "w", encoding="utf-8") as f:
        json.dump(offers, f, ensure_ascii=False, indent=2)

    print(f"Tallennettu {approved_count} ilmaista kokeilua offers.json -tiedostoon.")

if __name__ == "__main__":
    main()
