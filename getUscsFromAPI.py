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

url_el_uscs = f"https://api-live.euroleague.net/v2/competitions/{el_competition_code}/seasons/{el_season_code}/people?personType=Z&active=true"
url_ec_uscs = f"https://api-live.euroleague.net/v2/competitions/{ec_competition_code}/seasons/{ec_season_code}/people?personType=Z&active=true"

euroleague_games_info = requests.get(url_euroleague).json()
eurocup_games_info = requests.get(url_eurocup).json()

euroleague_games_data = euroleague_games_info["data"]
eurocup_games_data = eurocup_games_info["data"]

games_data = euroleague_games_data + eurocup_games_data #agrupació de partits d'eurolliga i eurocup (no distinció)