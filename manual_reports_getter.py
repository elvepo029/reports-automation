import pandas as pd
import json
import os
from datetime import datetime
from correction import Correction
from dataclasses import asdict
import sqlite3
from datetime import time, datetime

DB = "dades_staging.db" #PROVES
#DB = "dades_prod.db" #PRODUCCIó

def update_game(conn, game_code, game_data):
    cursor = conn.cursor()

    # eliminar claus buides si has marcat report buit
    if not game_data:
        return

    fields = ", ".join([f"{key} = ?" for key in game_data.keys()])
    values = list(game_data.values())

    query = f"""
        UPDATE GAME
        SET {fields}
        WHERE game_code = ?
    """

    cursor.execute(query, values + [game_code])

def insert_corrections(conn, corrections_data):
    cursor = conn.cursor()

    if not corrections_data:
        return

    keys = corrections_data[0].keys()
    fields = ", ".join(keys)
    placeholders = ", ".join(["?"] * len(keys))

    query = f"""
        INSERT INTO Correction ({fields})
        VALUES ({placeholders})
    """

    values = [tuple(c.values()) for c in corrections_data]

    cursor.executemany(query, values)

def serialize(obj):
    if isinstance(obj, (datetime, time)):
        return obj.isoformat()
    if pd.isna(obj):
        return None
    return obj

type_map = {
    "MISSIDENTITY": "MISIDENTITY",
    "MISSPLACED": "MISPLACED"
}

category_map = {
    "ASSIST": "AS",
    "BLOCK": "BLK",
    "COACH CHALLENGE": "CC", 
    "DEF REBOUND": "DR",
    "DISQUALIFYING FOUL": "DQ_FOUL",
    "FOUL DRAWN": "FD",
    "FREE THROW IN": "FT",
    "INSTANT REPLAY": "IRS",
    "JUMP BALL": "JB",
    "MISSED FREE THROW": "MFT",
    "MISSED THREE POINTER": "M3P",
    "MISSED TWO POINTER": "M2P",
    "OFENSIVE FOUL": "OF_FOUL",
    "OFF REBOUND": "OR",
    "SHOT REJECTED": "SR",
    "STEAL": "ST",
    "SUBSTITUTIONS": "IN",
    "TECH FOUL BENCH": "TECH_BENCH",
    "TECH FOUL COACH": "TECH_COACH",
    "TECHNICAL FOUL": "TECH",
    "THREE POINTER": "3P",
    "THROW-IN-FOUL": "TI_FOUL",
    "TIME OUT": "TOUT",
    "TURNOVER": "TO",
    "TV TIME OUT": "TV_TOUT",
    "TWO POINTER": "2P",
    "UNSPORTSMANLIKE FOUL": "UF"
}

def load_team_mapping():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("SELECT team_name, team_code FROM Team")
    
    mapping = {name: code for name, code in cursor.fetchall()}
    
    conn.close()
    return mapping

def get_game_codes_to_import_manual_report():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
                    SELECT game_code
                    FROM GAME
                    WHERE 
                        (
                        (year = 2025)
                        OR
                        (year = 2026 AND month < 3)
                        OR
                        (year = 2026 AND month = 3 AND day <= 20)
                        )
                        AND is_processed = 0;
    """)
    
    codes = {row[0] for row in  cursor.fetchall()}
    
    conn.close()
    return codes

def process_excel(conn, file_path, game_code, empty_reports_list):
    # Llegir Excel sense header
    df = pd.read_excel(file_path, header=None, engine="openpyxl")

    def cell(row, col):
        value = df.iloc[row, col]

        if pd.isna(value):
            return None
        
        if isinstance(value, (datetime, time)):
            return value.isoformat()
        
        return value

    # --- GAME CODE ---
    game_code = f"{cell(1,1)}_{cell(1,2)}"  # B2_C2

    game_data = {
        "data_entry": cell(5, 3),  # D6
        "caller_1": cell(6, 3),  # D7
        "caller_2": cell(7, 3),  # D8
        "timer": cell(8, 3),  # D9
        "shot_clock_operator": cell(9, 3),  # D10
        "irs_operator": cell(10, 3),  # D11
        "is_processed": True,
        "arrival_time": cell(11, 8),  # I12
        "checklist_on_time": cell(11, 9),  # J12
        "communication": cell(11, 10),  # K12
        "corrections_speed": cell(11, 11),  # L12
        "rescouted": cell(11, 12),  # M12
        "total_actions": int(cell(2, 3)),  # D3
        "total_corrections": int(cell(2, 5)),  # F3
        "lgm_comment": cell(3, 12),  # M4
        "result": round(cell(6, 12), 1),  # M7
    }

    #columnes (dreta): 3 -> 12
    #files (esquerra): 16 -> (16 + num_correccions - 1) - 1
    game_corrections_data = []

    actual_correction_row = 16
    last_correction_row = actual_correction_row + int(cell(2, 5)) - 1

    while (actual_correction_row <= last_correction_row):
        correction = Correction (
            game_code = game_code,
            time = cell(actual_correction_row, 3), #crono
            quarter = cell(actual_correction_row, 4), #quarter
            points_h = cell(actual_correction_row, 5), #points_h
            points_a = cell(actual_correction_row, 6), #points_a
            action_num = cell(actual_correction_row, 8), #action_number
            b_ss = cell(actual_correction_row, 9), #boxscore/scoresheet
            team = cell(actual_correction_row, 10), #team
            type_c = type_map.get(cell(actual_correction_row, 11), cell(actual_correction_row, 11)), #type
            category = category_map.get(cell(actual_correction_row, 12), cell(actual_correction_row, 12)), #category
            thread_name = "Correcció Manual",
            correction = "Correcció Manual",
            live_game_manager = cell(13, 3)
        )
        
        game_corrections_data.append(asdict(correction))

        actual_correction_row += 1

    # Pots adaptar això si vols més camps de corrections

    if (game_data["data_entry"] == "Data entry Name" or game_data["data_entry"] is None) and len(game_corrections_data) == 0:
        game_data = {}
        empty_reports_list.append(game_code)
    else:
        update_game(conn, game_code, game_data)
        insert_corrections(conn, game_corrections_data)


def process_folder():
    conn = sqlite3.connect(DB)
    empty_reports_list = []

    folder_path = "./excels"

    game_codes_to_import = get_game_codes_to_import_manual_report(DB)

    for file in os.listdir(folder_path):
        if file.endswith(".xlsx") or file.endswith(".xlsm"):

            game_code = file.split("_")[-1].split(".")[0] + "_" + str(int(file.split("_")[2]))
        
            if game_code not in game_codes_to_import:
                continue

            file_path = os.path.join(folder_path, file)

            process_excel(conn, file_path, game_code, empty_reports_list)

            game_codes_to_import.remove(game_code)

    conn.commit()
    conn.close()

    print(empty_reports_list)
    print(len(empty_reports_list))

process_folder()