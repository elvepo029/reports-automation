from discordThreadsExtractor import getDateThreads
import requests
import json

TOKEN = "MTQzODg5NzE5MjU3NTE3Njg1MQ.G6uaFm.ayKgV1iEhLGKbNI5yJUMhAcep3tmi8HzKdO2_0"
headers = {"Authorization": f"Bot {TOKEN}"}

threadsList = getDateThreads()

threadMessages = {}
for thread in threadsList:
    threadId = thread['id']
    threadName = thread['name']

    if threadName not in threadMessages:
        threadMessages[threadName] = []

    url = f"https://discord.com/api/v10/channels/{threadId}/messages?limit=100"
    threadContent = requests.get(url, headers=headers).json()
    
    for msgs in threadContent:
        message = msgs.get("content", "")
        if message != "": 
            threadMessages[threadName].append(message)

    threadMessages[threadName].reverse()

filename = "threadMessages.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(threadMessages, f, indent=4, ensure_ascii=False)



#{'id': '1435340576940621825', 
#'type': 11, 
#'last_message_id': '1435340612701392938',
#'flags': 0,
#'guild_id': '851948216022597653',
#'name': 'Action 128 Def REB',
#'parent_id': '885149945475248149',
#'rate_limit_per_user': 0,
#'bitrate': 64000,
#'user_limit': 0,
#'rtc_region': None,
#'owner_id': '1344308238752944208',
#'thread_metadata': {'archived': True,
#                    'archive_timestamp': '2025-11-04T18:54:22.564000+00:00',
#                    'auto_archive_duration': 4320,
#                    'locked': False,
#                    'create_timestamp': '2025-11-04T18:51:05.608000+00:00'},
#'message_count': 2,
#'member_count': 1,
#'total_message_sent': 2}