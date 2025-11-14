import requests
from datetime import datetime

TOKEN = "MTQzODY0MDk3NTkwNjk5NjIzNA.GaD0IX.PZOk8lP1iNthW3WJholAuNGyzxoazpSgvNF0hs"
CHANNEL_ID = "885149945475248149"
DATA_MIN = datetime(2023, 5, 1)

headers = {"Authorization": f"Bot {TOKEN}"}

url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/threads/archived/public"
r = requests.get(url, headers=headers)
threads = r.json().get("threads", [])
print(threads)

resultat = []
for t in threads:
    archive_time = datetime.fromisoformat(t["archive_timestamp"].replace("Z",""))
    if archive_time.date() == DATA_MIN.date():
        resultat.append(t["name"])

print(resultat)

