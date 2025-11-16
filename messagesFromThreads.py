from discordThreadsExtractor import getDateThreads
import requests
import json

#Users ids order --> Pablo, Oriol, Mario, Marc, Hector, Xavi, Eloi, Oscar

liveGameManagersIds = [
    "885505850821718037", "893148312843210833", 
    "893141967033229344", "851947426192556062", 
    "900034318833967154", "1204776291140636764", 
    "1344308238752944208", "697495204168728586"
]

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
        authorId = msgs.get("author", "").get("id", "")

        # DETECCIÓ: és ACTION si conté 3 espais seguits en mínim 9 vegades
        if message.count("   ") >= 12:   
            entry = {"Action": message}
        else:
            entry = {"Correction": message}
        
        if message != "" and authorId in liveGameManagersIds: 
            threadMessages[threadName].append(entry)

    threadMessages[threadName].reverse()

# FILTRAR: només threads amb Action + Correction
filteredThreads = {}

for threadName, msgs in threadMessages.items():
    hasAction = any("Action" in m for m in msgs)
    hasCorrection = any("Correction" in m for m in msgs)

    if hasAction and hasCorrection:
        filteredThreads[threadName] = msgs

filename = "threadMessages.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(filteredThreads, f, indent=4, ensure_ascii=False)



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