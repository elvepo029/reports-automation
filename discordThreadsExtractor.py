import requests
from datetime import datetime

TOKEN = "MTQzODg5NzE5MjU3NTE3Njg1MQ.GhMX43.-74alpoimk9L4Pkyob-_d55VMaBN515CYIqsUQ"
headers = {"Authorization": f"Bot {TOKEN}"}

def get(url, params=None):
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        print("Error:", r.status_code, r.text)
        return {}
    return r.json()

def getDateThreads(channel_id, target_date):
    base = f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public"

    result = []
    before = None

    while True:
        params = {"limit": 100}
        if before:
            params["before"] = before

        data = get(base, params)
        threads = data.get("threads", [])

        if not threads:
            break

        for t in threads:
            ts = t["thread_metadata"].get("create_timestamp")
            if not ts:
                continue

            thread_date = datetime.fromisoformat(ts.replace("Z", "")).date()

            if thread_date == target_date:
                result.append(t)

            # venen del més nou al més vell → podem parar
            elif thread_date < target_date:
                return result

        before = threads[-1]["thread_metadata"]["archive_timestamp"]

    return result



