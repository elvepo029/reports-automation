import requests
import sqlite3
from game import Game
import json
from usc import USC
from dataclasses import asdict

DB = "dades.db"
conn = sqlite3.connect(DB)
cursor = conn.cursor()

def insertUsc(usc: USC):
    cursor.execute("""
        INSERT OR IGNORE INTO Usc (
            code, name, team_code, season
        ) VALUES (?, ?, ?, ?)
    """, (usc.code, usc.name, usc.club_code, usc.season))

el_competition_code = "E"
ec_competition_code = "U"

el_season_code = "E2025"
ec_season_code = "U2025"

url_el_uscs = f"https://api-live.euroleague.net/v2/competitions/{el_competition_code}/seasons/{el_season_code}/people?personType=Z&active=true"
url_ec_uscs = f"https://api-live.euroleague.net/v2/competitions/{ec_competition_code}/seasons/{ec_season_code}/people?personType=Z&active=true"

euroleague_uscs_info = requests.get(url_el_uscs).json()
eurocup_uscs_info = requests.get(url_ec_uscs).json()

euroleague_uscs_data = euroleague_uscs_info["data"]
eurocup_uscs_data = eurocup_uscs_info["data"]

uscs_data = euroleague_uscs_data + eurocup_uscs_data #agrupació de uscs d'eurolliga i eurocup (no distinció)

#with open("uscs_data.json", "w", encoding="utf-8") as f:
    #json.dump(uscs_data, f, indent=4, ensure_ascii=False)

for usc_data in uscs_data:
    #dades necessàries per omplir taula de Usc de base de dades pròpia:
    usc_code = usc_data["person"]["code"]
    usc_name = usc_data["person"]["name"].split(", ")[1]
    usc_surnames = usc_data["person"]["name"].split(", ")[0]
    usc_reordered_name = usc_name + " " + usc_surnames #reordenació de components del nom tal com es vol al report (nom cognom)
    usc_club_code = usc_data["club"]["code"]
    usc_season = usc_data["season"]["code"]
    
    usc = USC(
        code = usc_code,
        name = usc_reordered_name,
        club_code = usc_club_code,
        season = usc_season
    )

    insertUsc(usc)

conn.commit()
conn.close()