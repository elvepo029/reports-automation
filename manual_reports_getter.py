import pandas as pd
import json
import os
from datetime import datetime
from correction import Correction
from dataclasses import asdict
import sqlite3

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

team_map = {

}

def load_team_mapping(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT team_name, team_code FROM Team")
    
    mapping = {name: code for name, code in cursor.fetchall()}
    
    conn.close()
    return mapping


def parse_date(value):
    """Converteix la cel·la B3 a year, month, day"""
    if isinstance(value, datetime):
        return value.year, value.month, value.day
    try:
        dt = pd.to_datetime(value)
        return dt.year, dt.month, dt.day
    except:
        return None, None, None

def process_excel(file_path):
    # Llegir Excel sense header
    df = pd.read_excel(file_path, header=None, engine="openpyxl")

    def cell(row, col):
        return df.iloc[row, col]
    
    year, month, day = parse_date(cell(2, 1))  # B3

    # --- GAME CODE ---
    game_code = f"{cell(1,1)}_{cell(1,2)}"  # B2_C2

    team_mapping = load_team_mapping("dades.db")

    game_data = {
        "game_code": game_code,
        "code_h": team_mapping.get(cell(3, 3)),  # D4
        "code_a": team_mapping.get(cell(4, 3)),  # D5
        "year": year,
        "month": month,
        "day": day,
        "round": int(cell(0, 2)),  # C1
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
        "total_actions": cell(2, 3),  # D3
        "total_corrections": cell(2, 5),  # F3
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

    return game_data, game_corrections_data


def process_folder():
    game_data_list = []
    corrections_data_list = []

    folder_path = "./excels"

    for file in os.listdir(folder_path):
        if file.endswith(".xlsx") or file.endswith(".xlsm"):
            file_path = os.path.join(folder_path, file)
            print(f"Processing: {file}")

            game_data, corrections_data = process_excel(file_path)

            game_data_list.append(game_data)
            corrections_data_list.append(corrections_data)

    # Guardar JSONs
    with open("game_data.json", "w", encoding="utf-8") as f:
        json.dump(game_data_list, f, indent=4, ensure_ascii=False)

    with open("corrections_data.json", "w", encoding="utf-8") as f:
        json.dump(corrections_data_list, f, indent=4, ensure_ascii=False)

process_folder()