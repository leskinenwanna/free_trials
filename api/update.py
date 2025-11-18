import subprocess
from pathlib import Path

def handler(request, response):
    # Aja update_offers.py skripti
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "update_offers.py"

    try:
        subprocess.run(["python3", str(script_path)], check=True)
        return response.status(200).send("Offers updated successfully.")
    except Exception as e:
        return response.status(500).send(f"Error: {e}")
