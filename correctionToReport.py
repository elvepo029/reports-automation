import pandas as pd
from pathlib import Path

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

    while True:
        print("Enganxa la línia de l'acció (o escriu 'sortir' per acabar):")
        action_line = input().strip()
        if action_line.lower() == "sortir":
            break

        print("Enganxa la línia de la correcció:")
        correction_line = input().strip()

        # Processar acció
        parts = action_line.split("    ")
        if len(parts) < 10:
            print("Format d'acció incorrecte, torna-ho a provar.")
            continue

        action_number = parts[0]
        time = parts[3]
        home_points = parts[4]
        away_points = parts[5]
        team_name = parts[6]
        category = parts[9]

        # Determinar Home o Away
        if team_name.lower() == home_team.lower():
            team = "Home"
        elif team_name.lower() == away_team.lower():
            team = "Away"
        else:
            team = ""

        # Processar correcció
        correction_parts = correction_line.split(" ")
        if len(correction_parts) > 0:
            correction_type = correction_parts[0].lower()  # Insert / Delete / Change
            stats_type = correction_parts[1]
        else:
            correction_type = ""
            stats_type = ""

        type_map = {
            "insert": "MISSING",
            "delete": "NOT HAPPENED",
            "change": "MISSIDENTITY"
        }
        type = type_map.get(correction_type, "")

        stats_map = {
            "AST": "ASSIST",
            "BLK": "BLOCK",
            "Def REB": "DEF REBOUND",
            "FT In": "FREE THROW IN",
            "IRS": "INSTANT REPLAY",
            "Missed FT": "MISSED FREE THROW",
            "Missed 3P": "MISSED THREE POINTER",
            "Missed 2P": "MISSED TWO POINTER",
            "Off Foul": "OFENSIVE FOUL",
            "Off REB": "OFF REBOUND",
            "STL": "STEAL",
            "3P": "THREE POINTER",
            "TOV": "TURNOVER",
            "2P": "TWO POINTER",
        }

        if correction_type == "insert" : category = stats_map.get(stats_type, "")

        # Crear nova fila
        new_row = {
            "Crono": time,
            "Quarter": "",
            "Points H": home_points,
            "Points V": away_points,
            "Action nmb": action_number,
            "BOXSC / SCORESH": "BOXSCORE",
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