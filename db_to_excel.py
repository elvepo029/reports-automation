import pandas as pd
import sqlite3

EXCEL = "reports_automation_database.xlsx"
DB = "dades.db"

# Connexió a SQLite
conn = sqlite3.connect(DB)

# Llegir la taula Game de la base de dades
df_game = pd.read_sql_query("SELECT * FROM Game", conn)

conn.close()

print(f"S'han carregat {len(df_game)} files de la taula Game")

df_game["is_processed"] = df_game["is_processed"].astype(bool)

# Escriure al full Game de l'Excel (sense tocar els altres fulls)
with pd.ExcelWriter(
    EXCEL,
    engine="openpyxl",
    mode="a",              # append
    if_sheet_exists="replace"  # reemplaça només el full Game
) as writer:
    df_game.to_excel(writer, sheet_name="Game", index=False)

print("Full 'Game' de l'Excel actualitzat correctament")
