import pandas as pd
from pathlib import Path
from messagesFromThreads import getThreadsActionsAndCorrections
from correctionHelpers import processCriteriaCorrections, processDeletions, processEditions, processInsertions, processInvalidCorrections, processMovements, processScoresheetCorrections

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

    threadsInfo = getThreadsActionsAndCorrections()

    for threadName, content in threadsInfo.items():
        action_line = content["Action"]
        correction_line = content["Correction"]

        action_parts = action_line.split("    ")
        if len(action_parts) < 10:
            continue

        action_number = action_parts[0]
        minute = int(action_parts[2])
        time = action_parts[3]
        home_points = action_parts[4]
        away_points = action_parts[5]
        #team_name = action_parts[6]
        #stat = action_parts[9]

        match minute: 
            case minute if 0 <= minute <= 10: quarter = "1"
            case minute if 11 <= minute <= 20: quarter = "2"
            case minute if 21 <= minute <= 30: quarter = "3"
            case minute if 31 <= minute <= 40: quarter = "4"
            case minute if minute < 40: quarter = "ET"
            case _: quarter = ""    

        # Determinar Home o Away
        if team_name.lower() == home_team.lower():
            team = "HOME TEAM"
        elif team_name.lower() == away_team.lower():
            team = "AWAY TEAM"
        else:
            team = ""

        # Processar correcció
        correction_parts = correction_line.split(" ")
        correction_type = correction_parts[0].lower

        if "cr" in threadName.lower():
            correction_type = "criteria"

        if "ss" in threadName.lower():
            correction_type = "scoresheet"

        match correction_type:
            case correction if correction == "criteria": processCriteriaCorrections(correction_parts)
            case correction if correction == "insert": processInsertions()
            case correction if correction == "delete": processDeletions()
            case correction if correction == "edit": processEditions()
            case correction if correction == "move": processMovements()
            case correction if correction == "scoresheet": processScoresheetCorrections()
            case _: processInvalidCorrections()
        
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