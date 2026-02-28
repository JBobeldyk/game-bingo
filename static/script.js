const socket = io();
let playerName = null;
let players = {};

function join() {
    playerName = document.getElementById("name").value;
    const password = document.getElementById("password").value;

    socket.emit("join", { name: playerName, password });

    document.getElementById("login").style.display = "none";
}

socket.on("board_update", data => {
    players = data.players;
    const size = data.size;
    document.documentElement.style.setProperty('--grid-size', size);
    renderBoard(data.board);
    renderWinner(data.winner);

    const me = Object.values(players).find(p => p.name === playerName);
    if (me && me.is_admin) {
        document.getElementById("resetSection").style.display = "block";

        // Prepopulate phrases
        const textarea = document.getElementById("phraseList");
        textarea.value = data.phrases.join("\n");
    }
});

function renderBoard(board) {
    const boardDiv = document.getElementById("board");
    boardDiv.innerHTML = "";

    board.forEach((cell, index) => {
        const div = document.createElement("div");
        div.className = "cell";
        div.innerText = cell.text;

        if (cell.claimed_by) {
            const player = Object.values(players).find(p => p.name === cell.claimed_by);
            div.style.backgroundColor = player ? player.color : "gray";
            div.innerText += "\n(" + cell.claimed_by + ")";
        } else {
            div.onclick = () => socket.emit("claim", index);
        }

        boardDiv.appendChild(div);
    });
}

function renderWinner(winner) {
    const winnerEl = document.getElementById("winner");
    if (winner) {
        winnerEl.innerText = winner + " WINS!";
    } else {
        winnerEl.innerText = "";
    }
}

function resetGame() {
    const size = parseInt(document.getElementById("newSize").value);
    const raw = document.getElementById("phraseList").value;
    const phrases = raw.split("\n").map(p => p.trim()).filter(p => p);

    socket.emit("reset", {
        size,
        phrases
    });
}