import pandas as pd
from pathlib import Path

def main():
    output_file = "informe_correccions.xlsx"

    # Si ja existeix, carregar-lo per continuar afegint
    if Path(output_file).exists():
        df = pd.read_excel(output_file)
        print(f"📂 S'han carregat {len(df)} correccions existents.")
    else:
        df = pd.DataFrame(columns=[
            "Time", "Quarter", "Home Points", "Away Points",
            "Action Number", "Type", "Team", "Type 2", "Type 3"
        ])

    home_team = input("🏠 Nom equip local: ").strip()
    away_team = input("🚶‍♂️ Nom equip visitant: ").strip()

    while True:
        print("\n👉 Enganxa la línia de l'acció (o escriu 'sortir' per acabar):")
        action_line = input().strip()
        if action_line.lower() == "sortir":
            break

        print("🟡 Enganxa la línia de la correcció:")
        correction_line = input().strip()

        # Processar acció
        parts = action_line.split("\t")
        if len(parts) < 10:
            print("⚠️ Format d'acció incorrecte, torna-ho a provar.")
            continue

        action_number = parts[0]
        time = parts[3]
        home_points = parts[4]
        away_points = parts[5]
        team_name = parts[6]

        # Determinar Home o Away
        if team_name.lower() == home_team.lower():
            team = "Home"
        elif team_name.lower() == away_team.lower():
            team = "Away"
        else:
            team = ""

        # Processar correcció
        correction_parts = correction_line.split()
        if len(correction_parts) >= 2:
            correction_type = correction_parts[0].lower()  # Insert / Delete / Change
            action_type3 = correction_parts[-1].lower()
        else:
            correction_type = ""
            action_type3 = ""

        type2_map = {
            "insert": "missing",
            "delete": "wrong",
            "change": "missidentity"
        }
        type2 = type2_map.get(correction_type, "")

        # Crear nova fila
        new_row = {
            "Time": time,
            "Quarter": "",
            "Home Points": home_points,
            "Away Points": away_points,
            "Action Number": action_number,
            "Type": "BOXSCORE",
            "Team": team,
            "Type 2": type2,
            "Type 3": action_type3
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_excel(output_file, index=False)
        print(f"✅ Correcció afegida i guardada a {output_file}")

    print(f"\n🎯 Informe final generat amb {len(df)} correccions!")

if __name__ == "__main__":
    main()