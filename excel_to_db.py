import pandas as pd
import sqlite3

EXCEL = "reports_automation_database.xlsx"
DB = "dades.db"

# Connexió a SQLite
conn = sqlite3.connect(DB)

# Llegeix tots els fulls de l'Excel
fulls = pd.read_excel(EXCEL, sheet_name=None)

for nom_taula, df in fulls.items():
    print(f"Important taula: {nom_taula}")
    print(len(df))

    df.to_sql(
        nom_taula,
        conn,
        if_exists="replace",  # crea o sobreescriu
        index=False
    )