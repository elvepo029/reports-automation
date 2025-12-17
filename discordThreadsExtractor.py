import requests
from datetime import datetime

TOKEN = "MTQzODg5NzE5MjU3NTE3Njg1MQ.G6uaFm.ayKgV1iEhLGKbNI5yJUMhAcep3tmi8HzKdO2_0"
headers = {"Authorization": f"Bot {TOKEN}"}

def get(url):
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print("Error:", r.text)
        return {}
    return r.json()

def getDateThreads(channel_id, target_date):
    base = f"https://discord.com/api/v10/channels/{channel_id}/threads"
    # --- 1. Agafar només fils arxivats públics (els que veus que funcionen)
    archived_public = get(base + "/archived/public").get("threads", [])

    filtered_threads = []

    # --- 2. Per cada fil, demanem la informació completa
    for t in archived_public:
        thread_id = t["id"]
        detail = get(f"https://discord.com/api/v10/channels/{thread_id}")

        # Obtenim la data real de creació
        ts = detail["thread_metadata"]["create_timestamp"]

        if ts:
            date = datetime.fromisoformat(ts.replace("Z", "")).date()
            if date == target_date:
                filtered_threads.append(detail)

    return filtered_threads



