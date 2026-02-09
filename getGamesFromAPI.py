import requests
import sqlite3
from game import Game

DB = "dades.db"
conn = sqlite3.connect(DB)
cursor = conn.cursor()

def getGameCodesList():
    cursor.execute("SELECT game_code FROM Game")
    return [row[0] for row in cursor.fetchall()]

def insertGame(game: Game):
   cursor.execute("""
        INSERT INTO Game (
            game_code, code_h, code_a, year, month,
            day, round, data_entry, caller_1, caller_2, timer, shot_clock_operator, irs_operator, is_processed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game.game_code, game.code_h, game.code_a, game.year, game.month, game.day, game.round, game.data_entry,
        game.caller_1, game.caller_2, game.timer, game.shot_clock_operator, game.irs_operator, game.is_processed
    ))

el_competition_code = "E"
ec_competition_code = "U"

el_season_code = "E2025"
ec_season_code = "U2025"

url_euroleague = f"https://api-live.euroleague.net/v2/competitions/{el_competition_code}/seasons/{el_season_code}/games"
url_eurocup = f"https://api-live.euroleague.net/v2/competitions/{ec_competition_code}/seasons/{ec_season_code}/games"

euroleague_games_info = requests.get(url_euroleague).json()
eurocup_games_info = requests.get(url_eurocup).json()

euroleague_games_data = euroleague_games_info["data"]
eurocup_games_data = eurocup_games_info["data"]

games_data = euroleague_games_data + eurocup_games_data #agrupació de partits d'eurolliga i eurocup (no distinció)

games_data.sort(
    key = lambda g: (
        #ordenació per data --> any, mes i dia (en aquest ordre)
        int(g["date"].split("T")[0].split("-")[0]),
        int(g["date"].split("T")[0].split("-")[1]),
        int(g["date"].split("T")[0].split("-")[2]),
        #ordenació per hora --> hores i minuts (en aquest ordre)
        int(g["date"].split("T")[1].split(":")[0]),
        int(g["date"].split("T")[1].split(":")[1]),
    )
)

games_in_db = getGameCodesList()

for game_data in games_data:
    game_identifier = game_data["identifier"] #el que a la meva base de dades és el game code, ex: E2025_234

    if game_identifier in games_in_db: #si el partit ja està a la base de dades, passa al següent
        continue

    game_date_time = game_data["date"]
    game_date = game_date_time.split("T")[0]

    date_parts = game_date.split("-")
    game_year = int(date_parts[0])
    game_month = int(date_parts[1])
    game_day = int(date_parts[2])

    #resta de dades necessàries per a fer l'insert a la meva base de dades
    code_h = game_data["local"]["club"]["code"]
    code_a = game_data["road"]["club"]["code"]
    round = game_data["round"]

    if game_month == 2 and game_day > 9: #partits que falten de febrer
        game = Game(
            game_code = game_identifier,
            code_h = code_h,
            code_a = code_a,
            year = game_year,
            month = game_month,
            day = game_day,
            round = round,
            data_entry = "",
            caller_1 = "",
            caller_2 = "",
            timer = "",
            shot_clock_operator = "",
            irs_operator = "",
            is_processed = False
        )

        insertGame(game)

    elif game_year == 2026 and game_month >= 3: #tots els altres partits a partir del primer dia de març
        game = Game(
            game_code = game_identifier,
            code_h = code_h,
            code_a = code_a,
            year = game_year,
            month = game_month,
            day = game_day,
            round = round,
            data_entry = "",
            caller_1 = "",
            caller_2 = "",
            timer = "",
            shot_clock_operator = "",
            irs_operator = "",
            is_processed = False
        )

        insertGame(game)

    else:
        continue

conn.commit()        
conn.close()