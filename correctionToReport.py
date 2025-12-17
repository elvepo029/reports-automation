import pandas as pd
from pathlib import Path
import sqlite3
from datetime import datetime
from messagesFromThreads import getThreadsActionsAndCorrections
#from correctionHelpers import processCriteriaCorrections, processDeletions, processEditions, processInsertions, processInvalidCorrections, processMovements, processScoresheetCorrections

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
          MISSIDENTITY, MISSING, MISSPLACED, NOT HAPPENED, POINTS, 
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

conn = sqlite3.connect("dades.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT
        g.year,
        g.month,
        g.day,
        t.discord_channel_id
    FROM Game g
    JOIN Team t WHERE g.code_h = t.team_code
""")

raw_discord_info = cursor.fetchall()
conn.close()

games_discord_info = [
    {
        "discord_channel_id": discord_channel_id,
        "date": datetime(year, month, day).date()
    }
    for year, month, day, discord_channel_id in raw_discord_info
]

for game_discord_info in games_discord_info:
    date = game_discord_info["date"]
    discord_channel_id = game_discord_info["discord_channel_id"]

    threads_corrections = getThreadsActionsAndCorrections(discord_channel_id, date)






   

