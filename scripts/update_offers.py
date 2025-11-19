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

# -----------------------------------------------------
#  BRAVE SEARCH
# -----------------------------------------------------
def brave_search(query):
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


# -----------------------------------------------------
#  PAGE TEXT SCRAPER
# -----------------------------------------------------
def fetch_page_text(url):
    try:
        html = requests.get(url, timeout=25).text
        soup = BeautifulSoup(html, "html.parser")

        texts = soup.find_all(string=True)
        visible = []

        for t in texts:
            if t.parent.name not in ["script", "style", "meta", "noscript"]:
                stripped = t.strip()
                if stripped:
                    visible.append(stripped)

        return " ".join(visible)[:15000]

    except Exception:
        return ""


# -----------------------------------------------------
#  AI CHECK FOR FREE TRIAL
# -----------------------------------------------------
def ai_judgement(text, url):
    prompt = f"""
Analysoi sivu: {url}

Tarkoitus: päätä tarjoaako sivu ilmaisen kokeilukerran, ilmaisen treenin,
free trialin tai maksuttoman tutustumisen harrastukseen Helsingissä.

HYVÄKSY sivu, jos:
- otsikossa lukee ilmainen kokeilukerta
- tekstissä mainitaan ilmainen tutustuminen, free trial, kokeile maksutta
- ensimmäinen treeni on ilmainen
- rekisteröityminen johtaa ilmaiseen kokeiluun
- edes osa tekstistä viittaa ilmaiseen kokeiluun

ÄLÄ hylkää sivua vain, koska teksti on lyhyt.

HYLKÄÄ vain, jos:
- missään kohdassa ei mainita ilmaista kokeilua
- kyse on kauneus/hoito/laihdutuspalvelusta
- kyse on kaupungin virallisesta harrastus- tai infopalvelusta

Vastaa:
KYLLÄ – selitys
TAI
EI – selitys

Teksti:
{text}
"""

    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    return resp.output_text.strip().lower()


# -----------------------------------------------------
#  AI CATEGORY CLASSIFIER
# -----------------------------------------------------
def ai_category(text, url):
    prompt = f"""
Määrittele harrastuksen kategoria sivun {url} perusteella.

Valitse yksi:
- kuntosali
- ryhmäliikunta
- tanssi
- kamppailulajit
- palloilulaji
- taiteet
- muut

Palauta vain kategorian nimi:

Teksti:
{text[:6000]}
"""

    resp = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    return resp.output_text.strip().lower()


# -----------------------------------------------------
#  MAIN
# -----------------------------------------------------
def main():
    offers = []
    seen_urls = set()
    domain_seen = set()

    # Fetch URLs
    for q in SEARCH_QUERIES:
        for url in brave_search(q):
            seen_urls.add(url)

    print(f"Löytyi yhteensä {len(seen_urls)} URLia Brave-haulla.")

    approved_count = 0

    # Analyze URLs
    for url in sorted(seen_urls)[:100]:
        text = fetch_page_text(url)
        if not text:
            continue

        answer = ai_judgement(text, url)

        print("----")
        print(f"URL: {url}")
        print(f"AI vastaus: {answer[:400]}")

        # If accepted
        if answer.startswith("kyllä"):
            domain = urlparse(url).netloc.lower().replace("www.", "")

            if domain in domain_seen:
                print(f"⏩ Ohitetaan duplikaatti domain: {domain}")
                continue

            domain_seen.add(domain)

            # detect category
            category = ai_category(text, url)
            print(f"Kategoria: {category}")

            offers.append({
                "name": url,
                "website": url,
                "offer_type": "Ilmainen kokeilukerta (AI tunnistama)",
                "category": category,
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
