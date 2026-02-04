from discordThreadsExtractor import getDateThreads
import requests
from datetime import datetime
import json

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

#Users ids order --> Pablo, Oriol, Mario, Marc, Hector, Xavi, Eloi, Oscar

live_game_managers_ids = [
    "885505850821718037", "893148312843210833", 
    "893141967033229344", "851947426192556062", 
    "900034318833967154", "1204776291140636764", 
    "1344308238752944208", "697495204168728586"
]

TOKEN = "MTQzODg5NzE5MjU3NTE3Njg1MQ.GhMX43.-74alpoimk9L4Pkyob-_d55VMaBN515CYIqsUQ"
headers = {"Authorization": f"Bot {TOKEN}"}

def getThreadsActionsAndCorrections(channel_id, target_date):
    threads_list = getDateThreads(channel_id, target_date)
    lgm_id = ""
    is_recovery_code_thread = False

    thread_messages = {}
    recovery_code_messages = {}
    for thread in threads_list:
        thread_id = thread['id']
        thread_name = thread['name']

        if thread_name not in thread_messages and thread_name not in recovery_code_messages:
            thread_messages[thread_name] = []
            recovery_code_messages[thread_name] = []

        url = f"https://discord.com/api/v10/channels/{thread_id}/messages?limit=100"
        thread_content = requests.get(url, headers=headers).json()
    
        for msgs in thread_content:
            message = msgs.get("content", "")
            author_id = msgs.get("author", "").get("id", "")

            # DETECCIÓ: és ACTION si conté 3 espais seguits en mínim 12 vegades
            if message.count("   ") >= 12:   
                entry = {"Action": message}
            else:
                entry = {"Correction": message}

            if "recovery" in thread_name.lower():
                is_recovery_code_thread = True
                entry1 = {"Action": message}
                entry2 = {"Correction": message}
        
            if message != "" and author_id in live_game_managers_ids: 
                thread_messages[thread_name].append(entry)
                if is_recovery_code_thread:
                    recovery_code_messages[thread_name].append(entry1)
                    recovery_code_messages[thread_name].append(entry2)
                lgm_id = author_id

        thread_messages[thread_name].reverse()

    # FILTRAR: només threads amb Action + Correction
    filtered_threads = {}
    filtered_recovery_code_threads = {}

    for thread_name, msgs in recovery_code_messages.items():
        first_action = None
        first_correction = None

        for m in msgs:
            if first_action is None and "Action" in m:
                first_action = m["Action"]
            if first_correction is None and "Correction" in m:
                first_correction = m["Correction"]

            if first_action is not None and first_correction is not None:
                break

        if first_action and first_correction:
            filtered_recovery_code_threads[thread_name] = {
                "Action": first_action,
                "Correction": first_correction,
                "Live_Game_Manager": lgm_id
            }

    for thread_name, msgs in thread_messages.items():
        first_action = None
        first_correction = None

        for m in msgs:
            if first_action is None and "Action" in m:
                first_action = m["Action"]
            if first_correction is None and "Correction" in m:
                first_correction = m["Correction"]

            # Si ja tenim les dues, podem parar abans
            if first_action is not None and first_correction is not None:
                break

        if first_action and first_correction:
            filtered_threads[thread_name] = {
                "Action": first_action,
                "Correction": first_correction, 
                "Live_Game_Manager": lgm_id
            }

    #with open("filteredThreads.json", "w", encoding="utf-8") as f:
        #json.dump(filtered_threads, f, indent=4, ensure_ascii=False)

    #with open("filtered_recovery.json", "w", encoding="utf-8") as f:
        #json.dump(filtered_recovery_code_threads, f, indent=4, ensure_ascii=False)
        
    return filtered_recovery_code_threads, filtered_threads