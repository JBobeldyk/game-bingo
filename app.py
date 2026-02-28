import random
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from collections import Counter

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
socketio = SocketIO(app, cors_allowed_origins="*")

BOARD_SIZE = 5
ADMIN_PASSWORD = "admin123"

phrases = [
    "Space Pirates",
    "Critical Hit",
    "Side Quest",
    "Plot Twist",
    "Final Boss",
    "Dice Roll",
    "Unexpected Betrayal",
    "Mysterious Stranger",
    "Hidden Treasure",
    "Secret Passage",
    "Ancient Artifact",
    "Stormy Seas",
    "Cursed Ship",
    "Legendary Weapon",
    "Magic Compass",
    "Lost Map",
    "Ghost Crew",
    "Treasure Chest",
    "Kraken Attack",
    "Smuggler's Cove",
    "Mutiny",
    "Siren Song",
    "Captain's Log",
    "Golden Idol",
    "Dark Prophecy",
    "Abandoned Island",
    "Revenge Plot",
    "Royal Navy"
]

players = {}  # sid -> {name, color, is_admin}
board = []    # list of dicts: {text, claimed_by}
winner = None
tiebreaker = None


def generate_board():
    global board, winner, tiebreaker
    winner = None
    tiebreaker = None
    selected = random.sample(phrases, BOARD_SIZE * BOARD_SIZE)
    board = [{"text": p, "claimed_by": None} for p in selected]


def check_bingo(player_name):
    grid = [board[i:i+BOARD_SIZE] for i in range(0, BOARD_SIZE * BOARD_SIZE, BOARD_SIZE)]

    # Rows
    for row in grid:
        if all(cell["claimed_by"] == player_name for cell in row):
            return True

    # Columns
    for col in range(BOARD_SIZE):
        if all(grid[row][col]["claimed_by"] == player_name for row in range(BOARD_SIZE)):
            return True

    # Diagonals
    if all(grid[i][i]["claimed_by"] == player_name for i in range(BOARD_SIZE)):
        return True

    if all(grid[i][BOARD_SIZE - i - 1]["claimed_by"] == player_name for i in range(BOARD_SIZE)):
        return True

    return False


def check_bingo_possible():
    grid = [board[i:i+BOARD_SIZE] for i in range(0, BOARD_SIZE * BOARD_SIZE, BOARD_SIZE)]

    players = set(
        cell["claimed_by"]
        for cell in board
        if cell["claimed_by"] != tiebreaker
    )

    def line_is_open_for(player, line):
        return all(
            cell["claimed_by"] in (None, player)
            for cell in line
        )

    # Check each player for at least one open line
    for player in players:
        # rows
        for row in grid:
            if line_is_open_for(player, row):
                return True

        # columns
        for col in range(BOARD_SIZE):
            column = [grid[r][col] for r in range(BOARD_SIZE)]
            if line_is_open_for(player, column):
                return True

        # diagonals
        diag1 = [grid[i][i] for i in range(BOARD_SIZE)]
        diag2 = [grid[i][BOARD_SIZE - i - 1] for i in range(BOARD_SIZE)]

        if line_is_open_for(player, diag1) or line_is_open_for(player, diag2):
            return True
        
    return False


def check_majority():
    count = Counter(cell["claimed_by"] for cell in board)
    leader_score = count.pop(tiebreaker, 0)
    unclaimed_score = count.pop(None, 0)
    next_highest_score = max(count.values(), default=0)
    return tiebreaker if leader_score >= next_highest_score + unclaimed_score else None


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("join")
def handle_join(data):
    name = data["name"]
    password = data.get("password", "")

    is_admin = password == ADMIN_PASSWORD
    color = f"hsl({random.randint(0,360)}, 70%, 70%)"

    players[request.sid] = {
        "name": name,
        "color": color,
        "is_admin": is_admin
    }

    emit("board_update", {
        "board": board,
        "players": players,
        "winner": winner,
        "size": BOARD_SIZE,
        "phrases": phrases,
        "tiebreaker": tiebreaker
    }, broadcast=True)


@socketio.on("claim")
def handle_claim(index):
    global winner, tiebreaker

    if index < 0 or index >= len(board):
        return

    if board[index]["claimed_by"] is not None:
        return

    player = players.get(request.sid)
    if not player:
        return

    board[index]["claimed_by"] = player["name"]

    count = Counter(cell["claimed_by"] for cell in board)
    if not tiebreaker or count.get(player["name"]) > count.get(tiebreaker):
        tiebreaker = player["name"]

    if not winner:
        if check_bingo(player["name"]):
            winner = player["name"]
        elif not check_bingo_possible():
            winner = check_majority()
        

    socketio.emit("board_update", {
        "board": board,
        "players": players,
        "winner": winner,
        "size": BOARD_SIZE,
        "phrases": phrases,
        "tiebreaker": tiebreaker
    })


@socketio.on("reset")
def handle_reset(data):
    global BOARD_SIZE, phrases

    player = players.get(request.sid)
    if not player or not player["is_admin"]:
        return
    
    size = data.get("size", 5)
    new_phrases = data.get("phrases", [])
    
    if size*size > len(new_phrases):
        return
    
    
    BOARD_SIZE = max(3, min(5, size))  # clamp between 3 and 5

    
    if new_phrases:
        phrases = new_phrases

    generate_board()

    socketio.emit("board_update", {
        "board": board,
        "players": players,
        "winner": winner,
        "size": BOARD_SIZE,
        "phrases": phrases,
        "tiebreaker": tiebreaker
    })


@socketio.on("disconnect")
def handle_disconnect():
    players.pop(request.sid, None)


if __name__ == "__main__":
    generate_board()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)