from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Dict
import uuid

app = FastAPI()

from compositor import Compositor

# Хранилище игр
games: Dict[str, dict] = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Крестики-нолики</title>
        <style>
            body {font-family:Arial;text-align:center;padding:20px;background:#f5f5f5}
            .container {max-width:500px;margin:0 auto;background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
            input {padding:8px;margin:5px;width:150px;border:1px solid #ddd;border-radius:4px}
            button {padding:10px 20px;background:#28a745;color:#fff;border:none;border-radius:4px;cursor:pointer;margin:5px}
            button:hover {background:#218838}
            .player {background:#f8f9fa;padding:10px;margin:5px;border-radius:4px;display:flex;justify-content:space-between;align-items:center}
            .symbol {font-weight:bold;font-size:20px;margin-left:10px}
            .remove-btn {background:#dc3545;padding:5px 10px;font-size:12px}
            .remove-btn:hover {background:#c82333}
            .start-btn {background:#007bff;font-size:18px;padding:15px 40px}
            .start-btn:hover {background:#0069d9}
            .disabled {opacity:0.5;pointer-events:none}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕹️ Крестики-нолики</h1>
            <h3>Добавьте игроков</h3>
            
            <div id="players">
                <div style="color:#666;margin:10px 0">Пока нет игроков</div>
            </div>
            
            <form id="addForm" style="margin:20px 0">
                <input type="text" id="playerName" placeholder="Имя игрока" required>
                <input type="text" id="playerSymbol" placeholder="Символ (+, #, *, и т.д.)" maxlength="1" required>
                <button type="submit">➕ Добавить</button>
            </form>
            
            <button id="startBtn" class="start-btn disabled" onclick="startGame()">🚀 Играть!</button>
            <div id="gameLink" style="margin-top:15px;display:none">
                <p>Игра создана! Перейдите по ссылке:</p>
                <a id="gameUrl" href="" target="_blank"></a>
            </div>
        </div>
        
        <script>
            let players = [];
            
            document.getElementById('addForm').onsubmit = function(e) {
                e.preventDefault();
                const name = document.getElementById('playerName').value.trim();
                const symbol = document.getElementById('playerSymbol').value.trim();
                
                if (!name || !symbol) return;
                if (players.find(p => p.name === name)) {
                    alert('Игрок с таким именем уже есть!');
                    return;
                }
                if (players.find(p => p.symbol === symbol)) {
                    alert('Символ уже используется!');
                    return;
                }
                
                players.push({name, symbol});
                updatePlayers();
                document.getElementById('playerName').value = '';
                document.getElementById('playerSymbol').value = '';
            };
            
            function removePlayer(name) {
                players = players.filter(p => p.name !== name);
                updatePlayers();
            }
            
            function updatePlayers() {
                const container = document.getElementById('players');
                if (players.length === 0) {
                    container.innerHTML = '<div style="color:#666;margin:10px 0">Пока нет игроков</div>';
                } else {
                    container.innerHTML = players.map(p => 
                        `<div class="player">
                            <span><strong>${p.name}</strong> <span class="symbol">${p.symbol}</span></span>
                            <button class="remove-btn" onclick="removePlayer('${p.name}')">✕</button>
                        </div>`
                    ).join('');
                }
                
                const startBtn = document.getElementById('startBtn');
                if (players.length >= 2) {
                    startBtn.classList.remove('disabled');
                } else {
                    startBtn.classList.add('disabled');
                }
            }
            
            async function startGame() {
                if (players.length < 2) {
                    alert('Нужно минимум 2 игрока!');
                    return;
                }
                
                const response = await fetch('/create_game', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({players})
                });
                
                const data = await response.json();
                if (data.game_id) {
                    const link = document.getElementById('gameUrl');
                    link.href = `/game/${data.game_id}`;
                    link.textContent = window.location.origin + `/game/${data.game_id}`;
                    document.getElementById('gameLink').style.display = 'block';
                    document.getElementById('startBtn').disabled = true;
                }
            }
            
            updatePlayers();
        </script>
    </body>
    </html>
    """

@app.post("/create_game")
async def create_game(players: dict):
    import json
    player_list = players.get('players', [])
    if len(player_list) < 2:
        return {"error": "Need at least 2 players"}
    
    game_id = str(uuid.uuid4())[:8]
    
    # Создаем композитор
    comp = Compositor(3, 3)
    for p in player_list:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    
    games[game_id] = {
        'compositor': comp,
        'players': player_list,
        'moves': 0
    }
    
    return {"game_id": game_id}

@app.get("/game/{game_id}", response_class=HTMLResponse)
async def game(request: Request, game_id: str, x: int | None = None, y: int | None = None):
    if game_id not in games:
        return "<h1>Игра не найдена!</h1><a href='/'>Вернуться</a>"
    
    game = games[game_id]
    comp = game['compositor']
    players = game['players']
    game['moves'] = sum(1 for b in comp.get_board_list() for row in b.board for cell in row if cell)
    
    # Определяем текущего игрока
    current_player = players[game['moves'] % len(players)]
    player_name = current_player['name']
    player_symbol = current_player['symbol']
    
    msg = f"Ходит: {player_name} ({player_symbol})"
    
    # Обрабатываем ход
    if x is not None and y is not None:
        if 0 <= x < 9 and 0 <= y < 9:
            # Проверяем, не занята ли клетка
            boards = comp.get_board_list()
            board_idx = (x // 3) + (y // 3) * 3
            local_x = x % 3
            local_y = y % 3
            if boards[board_idx].board[local_y][local_x]:
                msg = f"❌ Клетка ({x},{y}) занята! Ходит: {player_name}"
            else:
                res = comp.go(x, y, player_name)
                game['moves'] += 1
                if res == "3":
                    msg = f"🏆 {player_name} ПОБЕДИЛ! 🎉"
                else:
                    # Определяем следующего игрока
                    next_player = players[game['moves'] % len(players)]
                    msg = f"✅ {player_name} походил на ({x},{y}). Ходит: {next_player['name']} ({next_player['symbol']})"
        else:
            msg = "❌ Неверные координаты"
    
    # Обновляем данные
    boards = comp.get_board_list()
    game['moves'] = sum(1 for b in boards for row in b.board for cell in row if cell)
    current_player = players[game['moves'] % len(players)]
    
    # Формируем HTML игры
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Крестики-нолики</title>
        <style>
            body{{font-family:Arial;text-align:center;padding:20px;background:#f5f5f5;margin:0}}
            .container{{max-width:650px;margin:0 auto}}
            .board{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px auto}}
            .mini{{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;background:#333;padding:2px;border-radius:4px;aspect-ratio:1}}
            .cell{{background:#fff;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:bold;cursor:pointer;border-radius:2px;transition:0.1s}}
            .cell:hover{{background:#e0e0e0;transform:scale(1.02)}}
            .cell:active{{transform:scale(0.95)}}
            .empty{{color:#ddd}}
            .msg{{background:#fff;padding:15px;border-radius:8px;margin:10px auto;box-shadow:0 2px 4px rgba(0,0,0,0.1);font-size:18px}}
            .players{{display:flex;gap:15px;justify-content:center;flex-wrap:wrap;margin:10px 0}}
            .player-tag{{padding:8px 16px;border-radius:4px;background:#e9ecef}}
            .active{{background:#ffc107!important;font-weight:bold;box-shadow:0 0 0 2px #ffc107}}
            .label{{font-size:12px;color:#666;margin-top:3px}}
            .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
            .back-btn{{padding:8px 16px;background:#6c757d;color:#fff;text-decoration:none;border-radius:4px;font-size:14px}}
            .back-btn:hover{{background:#5a6268}}
            .reset-btn{{padding:8px 16px;background:#dc3545;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px}}
            .reset-btn:hover{{background:#c82333}}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <a href="/" class="back-btn">← Назад</a>
                <button class="reset-btn" onclick="resetGame()">↺ Заново</button>
            </div>
            
            <h1>🕹️ Крестики-нолики</h1>
            <div class="players">
    """
    
    for p in players:
        active = 'active' if p['name'] == current_player['name'] else ''
        html += f'<span class="player-tag {active}">{p["name"]} ({p["symbol"]})</span>'
    
    html += f"""
            </div>
            <div class="msg" id="msg">{msg}</div>
            <div class="board">
    """
    
    for bi in range(9):
        board = boards[bi]
        html += f'<div><div class="mini">'
        for r in range(3):
            for c in range(3):
                val = board.board[r][c]
                gx = (bi % 3) * 3 + c
                gy = (bi // 3) * 3 + r
                if val:
                    color = '#28a745' if val == '+' else '#007bff' if val == '#' else '#6c757d'
                    html += f'<div class="cell" style="color:{color}" onclick="move({gx},{gy})">{val}</div>'
                else:
                    html += f'<div class="cell empty" onclick="move({gx},{gy})">·</div>'
        html += f'</div><div class="label">Поле {bi+1}</div></div>'
    
    html += f"""
            </div>
        </div>
        <script>
            function move(x,y){{
                fetch(`/game/{game_id}?x=${{x}}&y=${{y}}`)
                    .then(r=>r.text())
                    .then(html=>document.documentElement.innerHTML=html)
                    .catch(()=>alert('Ошибка'))
            }}
            function resetGame(){{
                if(confirm('Начать заново?')){{
                    fetch(`/reset_game/{game_id}`)
                        .then(()=>location.reload())
                        .catch(()=>alert('Ошибка'))
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return html

@app.get("/reset_game/{game_id}")
async def reset_game(game_id: str):
    if game_id not in games:
        return {"error": "Game not found"}
    
    game = games[game_id]
    players = game['players']
    
    # Создаем новый композитор
    comp = Compositor(3, 3)
    for p in players:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    
    game['compositor'] = comp
    game['moves'] = 0
    
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)