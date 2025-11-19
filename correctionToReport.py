import pandas as pd
from pathlib import Path
from messagesFromThreads import getThreadsActionsAndCorrections

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

def main():
    output_file = "informe_correccions.xlsx"

    # Si ja existeix, carregar-lo per continuar afegint
    if Path(output_file).exists():
        df = pd.read_excel(output_file)
        print(f"S'han carregat {len(df)} correccions existents.")
    else:
        df = pd.DataFrame(columns=[
            "Crono", "Quarter", "Points H", "Points V",
            "Action nmb", "BOXSC / SCORESH", "TEAM", "TYPE", "CATEGORY", "COMMENT"
        ])

    home_team = input("Nom equip local: ").strip()
    away_team = input("Nom equip visitant: ").strip()

    points = ['2P', 'Two Pointer', '3P', 'Three Pointer', 'FTM', 'Free Thrown In'] 
    fouls = ['OF FOUL', 'Offensive Foul', 'FOUL', 'Foul', 'UF', 'Unsportsmanlike Foul', 'TECH', 'Technical Foul', 'DQ Foul', 'Disqualifying Foul', ]
    jump_ball = ['Jump Ball']
    team_timeouts = ['TOUT', 'Time Out']
    irs = ['IRS', 'Instant Replay'] 
    coach_challenge = ['CC', 'Coach Challenge']
    substitutions = ['In', 'Out']
    missed_shots = ['M2P', 'Missed Two Pointer', 'M3P', 'Missed Three Pointer', 'MFT', 'Missed Free Throw']
    shots = missed_shots + points

    scoresheet_lists = points + fouls + jump_ball + team_timeouts + irs + coach_challenge + substitutions + shots

    category_list = ["3P", "2P", "AS", "BLK", "CC", "DR", "DQ FOUL", 
                     "FB", "FD", "FOUL", "FTM", "IRS", "JB", "MFT",
                     "M3P", "M2P", "OF FOUL", "OR", "PF", "REB", "SR",
                     "ST", "SUBS", "TECH", "TOUT", "TO", "UF"]

    threadsInfo = getThreadsActionsAndCorrections()


    for threadName, content in threadsInfo.items():
        action_line = content["Action"]
        correction_line = content["Correction"]

    # Processar acció
        parts = action_line.split("    ")
        if len(parts) < 10:
            print("Format d'acció incorrecte, torna-ho a provar.")
            continue

        action_number = parts[0]
        minute = int(parts[2])
        time = parts[3]
        home_points = parts[4]
        away_points = parts[5]
        team_name = parts[6]
        category = parts[9]

        if (0 <= minute <= 10): quarter = "1"
        elif (11 <= minute <= 20): quarter = "2"
        elif (21 <= minute <= 30): quarter = "3"
        elif (31 <= minute <= 30): quarter = "4"
        elif (minute > 40): quarter = "ET"
        else: quarter = ""

        # Determinar Home o Away
        if team_name.lower() == home_team.lower():
            team = "HOME TEAM"
        elif team_name.lower() == away_team.lower():
            team = "AWAY TEAM"
        else:
            team = ""

        # Processar correcció
        correction_parts = correction_line.split(" ")
        if len(correction_parts) == 3:
            correction_type = correction_parts[0].lower()  # Insert / Delete / Change
            stats_type = correction_parts[1]
            modification = correction_parts[2]
        elif len(correction_parts) == 1:
            correction_type[0].lower()
        elif len(correction_parts) > 3:
            correction_type = correction_parts[0].lower()
            stats_type = correction_parts[1].lower()
            modification = correction_parts[2]
            time_change = correction_parts[3]
        else:
            correction_type = ""
            stats_type = ""
            modification = ""
            time_change = ""

        type_map = {
            "insert": "MISSING",
            "delete": "NOT HAPPENED",
            "change": "MISSIDENTITY", 
            "place": "MISSPLACED"
        } 
        type = type_map.get(correction_type, "")

        if correction_type == "insert" : category = stats_type

        if correction_type in ("insert", "delete") and category in scoresheet_lists: 
            boxscore_scoresheet = "SCORESHEET"
            if category in points:
                type = "POINTS"
            elif category in fouls: 
                type = "FOULS"
            elif category in substitutions:
                type = "SUBSTITUTIONS"
            elif category in jump_ball:
                type = "JUMP BALL"
            elif category in team_timeouts:
                type = "TIME OUT"
            elif category in irs:
                type = "INSTANT REPLAY"
            elif category in coach_challenge:
                type = "COACH CHALLENGE"
        else: 
            boxscore_scoresheet = "BOXSCORE"     

        if (category in missed_shots and modification in points) or (category in points and modification in missed_shots) or (category in points and modification in points and category != modification): 
            boxscore_scoresheet = "SCORESHEET"
            type = "POINTS"   

        if modification in category_list and category not in points:
            type = "NOT HAPPENED"  
        elif modification not in category_list:
            type = "MISSIDENTITY"

        if correction_type in ("insert", "delete") and (stats_type == "AS" or "AST"):
            type = "CRITERIA"
            category = "AS"

        if "place" in correction_type:
            type = "MISSPLACED"
        
        if "time" in stats_type and correction_type == "change":
            type = "TIMING"
            time = time_change

        # Crear nova fila
        new_row = {
            "Crono": time,
            "Quarter": quarter,
            "Points H": home_points,
            "Points V": away_points,
            "Action nmb": action_number,
            "BOXSC / SCORESH": boxscore_scoresheet,
            "TEAM": team,
            "TYPE": type,
            "CATEGORY": category,
            "COMMENT": ""
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(output_file, index=False)
        print(f"Correcció afegida i guardada a {output_file}")

    print(f"Informe final generat amb {len(df)} correccions!")

if __name__ == "__main__":
    main()