import pandas as pd
from pathlib import Path
import sqlite3
import os
from datetime import datetime
from correction import Correction
from dataclasses import asdict
import json
from messagesFromThreads import getThreadsActionsAndCorrections
from correctionHelpers import processCriteriaCorrections, processDeletions, processEditions, processInsertions, processInvalidCorrections, processMovements, processScoresheetCorrections, processTimingCorrections

"""
Estructura de cada línia del report:
Crono
Quarter --> {1, 2, 3, 4, et}
Points H                                                                          
Points V
Action nmb
BOXSC / SCORESH --> {BOXSCORE, SCORESHEET}
TEAM --> {AWAY TEAM, HOME TEAM, NO TEAM}
TYPE --> {COACH CHALLENGE, CRITERIA, FOULS, INSTANT REPLAY, JUMP BALL, 
          MISIDENTITY, MISSING, MISPLACED, NOT HAPPENED, POINTS, 
          SUBSTITUTIONS, TIME OUT, TIMING}
CATEGORY --> {ASSIST, BLOCK, DEF REBOUND, DISQUALIFYING FOUL, DSS FREE THROWS,
              FIGHTING, FOUL, FOUL DRAWN, FREE THROW IN, INSTANT REPLAY,
              JUMP BALL, MISSED FREE THROW, MISSED THREE POINTER, MISSED TWO POINTER, OFENSIVE FOUL,
              OFF REBOUND, SHOT REJECTED, STEAL, SUBSTITUTIONS, TECH FOUL BENCH,
              TECH FOUL COACH, TECHNICAL FOUL, THREE POINTER, THROW-IN-FOUL, TIME,
              TIME OUT, TIP OFF, TURNOVER, TV TIME OUT, TWO POINTER,
              UNSPORTSMANLIKE FOUL}
COMMENT

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Action Exemple --> 42    44    5    05:28    6    11    Barcelona    6    VESELY, J.    Two Pointer    0    0    0
Correction Exemple --> Insert 3P A13

Scoresheet Errors --> Jump Ball, Team Timeouts, IRS, Coach Challenge, Points (2P, 3P, FT), Fouls (Foul, Offensive Foul, Unsportsmanlike Foul, Technical Foul, Throw-in Foul),
                      Substitutions

---------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Abbreviations: 
2P: two-pointer
3P: three-pointer
AS: assist
BLK: block
CC: coachs challenge
DR: defensive rebound
DQ FOUL: disqualifying foul
FB: fast break
FD: foul drawn
FOUL: foul
FTM: free throw made
IRS: Instant Replay System
JB: jump ball
MFT: missed free throw
M3P: missed three-pointer
M2P: missed two-pointer
OF FOUL: offensive foul
OR: offensive rebound
PF: personal foul
REB: rebound
SR: shot rejected
ST: steal
SUBS: substitution
TECH: technical foul
TOUT:time-out
TO: turnover
UF: unsportsmanlike foul
"""

def getActionAbbreviationByPbpName(pbp_name): 
    conn = sqlite3.connect("dades.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.abbreviation
        FROM Action a
        WHERE a.pbp_name = ?
    """, (pbp_name,))

    action_abbreviation = cursor.fetchone()
    conn.close()

    return action_abbreviation[0] if action_abbreviation else ""

def insertCorrection(cursor, correction):
   cursor.execute("""
        INSERT INTO Correction (
            game_code, time, quarter, points_h, points_a,
            action_num, b_ss, team, type_c, category, thread_name, correction, live_game_manager
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        correction.game_code, correction.time, correction.quarter, correction.points_h, correction.points_a, correction.action_num,
        correction.b_ss, correction.team, correction.type_c, correction.category, correction.thread_name, correction.correction, correction.live_game_manager
    ))
   
def updateGame(cursor, game_code):
    cursor.execute(
        "UPDATE Game SET is_processed = 1 WHERE game_code = ?",
        (game_code,)
    )

def getLGMNameById(cursor, lgm_id):
    cursor.execute("""
        SELECT name
        FROM Lgm
        WHERE discord_id = ?
    """, (lgm_id,))

    row = cursor.fetchone()
    return row[0] if row else None

def _resolve_process_date():
    """
    Returns the date to process.

    - Default: today's local date.
    - Override with env var CORRECTIONS_DATE in YYYY-MM-DD format.
    """
    raw = (os.getenv("CORRECTIONS_DATE") or "").strip()
    if not raw:
        return datetime.now().date()

    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(
            f"Invalid CORRECTIONS_DATE='{raw}'. Expected format YYYY-MM-DD (e.g. 2026-03-13)."
        ) from e

def runCorrectionsProcessor():
    actual_date = _resolve_process_date()
    conn = sqlite3.connect("dades.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            g.game_code,
            g.year,
            g.month,
            g.day,
            is_processed,
            th.discord_channel_id,
            th.pbp_name AS home_pbp_name,
            ta.pbp_name AS away_pbp_name
        FROM Game g
        JOIN Team th ON g.code_h = th.team_code
        JOIN Team ta ON g.code_a = ta.team_code
    """)

    raw_discord_info = cursor.fetchall()

    games_info = [
        {
            "game_code": game_code,
            "discord_channel_id": discord_channel_id,
            "date": datetime(year, month, day).date(),
            "is_processed": is_processed,
            "pbp_name_h": home_pbp_name,
            "pbp_name_a": away_pbp_name
        }
        for game_code, year, month, day, is_processed, discord_channel_id, home_pbp_name, away_pbp_name in raw_discord_info
    ]

    for game_info in games_info:
        game_code = game_info["game_code"]
        date = game_info["date"]
        is_processed = game_info["is_processed"]
        discord_channel_id = game_info["discord_channel_id"]
        pbp_name_h = game_info["pbp_name_h"]
        pbp_name_a = game_info["pbp_name_a"]

        if not is_processed and actual_date == date: 
            recovery_codes_threads, threads_corrections = getThreadsActionsAndCorrections(discord_channel_id, date)
        else: continue

        if len(recovery_codes_threads) == 0:
            continue

        for thread_name, thread in threads_corrections.items():
            action = thread["Action"]
            correction = thread["Correction"]
            lgm = thread["Live_Game_Manager"]
            action_parts = action.split("    ")
            correction_parts = correction.split(" ")
            correction_instruction = correction_parts[0].lower()
            time_set = False

            action_abb = getActionAbbreviationByPbpName(action_parts[9])
            time = action_parts[3]
            points_h = action_parts[4]
            points_a = action_parts[5]
            action_num = action_parts[0]

            minute = int(action_parts[2])
            if 0 <= minute <= 10: quarter = "1"
            elif 11 <= minute <= 20: quarter = "2"
            elif 21 <= minute <= 30: quarter = "3"
            elif 31 <= minute <= 40: quarter = "4"
            else: quarter = "ET"

            live_game_manager = getLGMNameById(cursor, lgm)

            if "(CR)" in thread_name:
                correction_values = processCriteriaCorrections(action_abb, correction_instruction, pbp_name_h, pbp_name_a, action_parts, correction_parts)
            
            elif "(SS)" in thread_name:
                correction_values = processScoresheetCorrections(action_abb, correction_instruction, pbp_name_h, pbp_name_a, action_parts, correction_parts)

            elif "time" in thread_name.lower():
                correction_values = processTimingCorrections(action_abb, pbp_name_h, pbp_name_a, action_parts, correction_parts)
                time_set = True

            elif "insert" == correction_instruction:
                correction_values = processInsertions(correction_parts)

            elif "delete" == correction_instruction:
                correction_values = processDeletions(action_abb, pbp_name_h, pbp_name_a, action_parts)

            elif "edit" == correction_instruction: 
                correction_values = processEditions(action_abb, pbp_name_h, pbp_name_a, action_parts, correction_parts)

            elif "move" == correction_instruction:
                correction_values = processMovements(action_abb, pbp_name_h, pbp_name_a, action_parts)

            else:
                correction_values = processInvalidCorrections()
        
            correction_values.game_code = game_code
            correction_values.thread_name = thread_name
            correction_values.quarter = quarter
            if points_h != "":
                correction_values.points_h = points_h
            else:
                correction_values.points_h = "0"
            if points_a != "":
                correction_values.points_a = points_a
            else:
                correction_values.points_a = "0"
            correction_values.action_num = action_num
            correction_values.correction = correction
            correction_values.live_game_manager = live_game_manager

            if "JB" in correction:
                time = "09:59"
            
            if not time_set: correction_values.time = time

            insertCorrection(cursor, correction_values)

        updateGame(cursor, game_code)

    conn.commit()        
    conn.close()



   

