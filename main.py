from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from typing import Dict
import uuid

app = FastAPI()

from compositor import Compositor, End

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
            select {padding:8px;margin:5px;border:1px solid #ddd;border-radius:4px}
            button {padding:10px 20px;background:#28a745;color:#fff;border:none;border-radius:4px;cursor:pointer;margin:5px}
            button:hover {background:#218838}
            .player {background:#f8f9fa;padding:10px;margin:5px;border-radius:4px;display:flex;justify-content:space-between;align-items:center}
            .symbol {font-weight:bold;font-size:20px;margin-left:10px}
            .remove-btn {background:#dc3545;padding:5px 10px;font-size:12px}
            .remove-btn:hover {background:#c82333}
            .start-btn {background:#007bff;font-size:18px;padding:15px 40px}
            .start-btn:hover {background:#0069d9}
            .disabled {opacity:0.5;pointer-events:none}
            .field-size {display:flex;gap:10px;justify-content:center;align-items:center;margin:10px 0}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕹️ Крестики-нолики</h1>
            <h3>Добавьте игроков</h3>
            
            <div class="field-size">
                <label>Размер поля:</label>
                <select id="fieldSize">
                    <option value="2">2x2 (4 поля)</option>
                    <option value="3" selected>3x3 (9 полей)</option>
                    <option value="4">4x4 (16 полей)</option>
                    <option value="5">5x5 (25 полей)</option>
                </select>
            </div>
            
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
                
                const fieldSize = parseInt(document.getElementById('fieldSize').value);
                
                const response = await fetch('/create_game', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({players, field_size: fieldSize})
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
async def create_game(data: dict):
    player_list = data.get('players', [])
    field_size = data.get('field_size', 3)
    
    if len(player_list) < 2:
        return {"error": "Need at least 2 players"}
    
    game_id = str(uuid.uuid4())[:8]
    
    # Создаем композитор с заданным размером
    comp = Compositor(field_size, field_size)
    for p in player_list:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    
    # Инициализируем счетчики очков
    scores = {p['name']: 0 for p in player_list}
    completed_boards = set()  # номера завершенных полей
    
    games[game_id] = {
        'compositor': comp,
        'players': player_list,
        'scores': scores,
        'completed_boards': completed_boards,
        'field_size': field_size,
        'total_boards': field_size * field_size,
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
    field_size = game['field_size']
    total_boards = game['total_boards']
    scores = game['scores']
    completed_boards = game['completed_boards']
    
    # Считаем ходы
    game['moves'] = sum(1 for b in comp.get_board_list() for row in b.board for cell in row if cell)
    
    # Определяем текущего игрока
    current_player = players[game['moves'] % len(players)]
    player_name = current_player['name']
    player_symbol = current_player['symbol']
    
    msg = f"Ходит: {player_name} ({player_symbol})"
    winner_msg = ""
    
    # Обрабатываем ход
    if x is not None and y is not None:
        if 0 <= x < field_size * 3 and 0 <= y < field_size * 3:
            # Определяем индекс доски
            board_idx = (x // 3) + (y // 3) * field_size
            
            # Проверяем, не завершено ли поле
            if board_idx in completed_boards:
                msg = f"❌ Это поле уже завершено! Ходит: {player_name}"
            else:
                boards = comp.get_board_list()
                local_x = x % 3
                local_y = y % 3
                
                # Проверяем, не занята ли клетка
                if boards[board_idx].board[local_y][local_x]:
                    msg = f"❌ Клетка ({x},{y}) занята! Ходит: {player_name}"
                else:
                    # Делаем ход
                    res = comp.go(x, y, player_name)
                    game['moves'] += 1
                    
                    if res == End.finished:
                        # Проверяем, не завершено ли это поле уже
                        if board_idx not in completed_boards:
                            scores[player_name] += 1
                            completed_boards.add(board_idx)
                            winner_msg = f"🏆 {player_name} выиграл поле {board_idx+1}! (+1 очко)"
                            
                            # Проверяем, не завершена ли вся игра
                            if len(completed_boards) == total_boards:
                                # Находим победителя
                                max_score = max(scores.values())
                                winners = [name for name, score in scores.items() if score == max_score]
                                if len(winners) == 1:
                                    winner_msg = f"🎉🎉🎉 {winners[0]} ПОБЕДИЛ В ИГРЕ с {max_score} очками! 🎉🎉🎉"
                                else:
                                    winner_msg = f"🤝 Ничья! {', '.join(winners)} набрали по {max_score} очков"
                    
                    # Определяем следующего игрока
                    next_player = players[game['moves'] % len(players)]
                    msg = f"✅ {player_name} походил на ({x},{y}). {winner_msg} Ходит: {next_player['name']} ({next_player['symbol']})"
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
            .container{{max-width:900px;margin:0 auto;display:flex;gap:20px;align-items:flex-start}}
            .game-area{{flex:1}}
            .sidebar{{width:200px;background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);position:sticky;top:20px}}
            .board{{display:grid;grid-template-columns:repeat({field_size},1fr);gap:10px;margin:20px auto}}
            .mini{{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;background:#333;padding:2px;border-radius:4px;aspect-ratio:1;position:relative}}
            .mini.completed{{opacity:0.6;pointer-events:none}}
            .mini.completed::after{{
                content:'✓';
                position:absolute;
                top:50%;left:50%;
                transform:translate(-50%,-50%);
                font-size:40px;
                color:#28a745;
                font-weight:bold;
                text-shadow:0 0 10px rgba(40,167,69,0.5);
            }}
            .cell{{background:#fff;aspect-ratio:1;display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:bold;cursor:pointer;border-radius:2px;transition:0.1s}}
            .cell:hover{{background:#e0e0e0;transform:scale(1.02)}}
            .cell:active{{transform:scale(0.95)}}
            .empty{{color:#ddd}}
            .msg{{background:#fff;padding:15px;border-radius:8px;margin:10px auto;box-shadow:0 2px 4px rgba(0,0,0,0.1);font-size:16px}}
            .players{{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin:10px 0}}
            .player-tag{{padding:6px 12px;border-radius:4px;background:#e9ecef;font-size:14px}}
            .active{{background:#ffc107!important;font-weight:bold;box-shadow:0 0 0 2px #ffc107}}
            .label{{font-size:11px;color:#666;margin-top:2px}}
            .header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:10px}}
            .back-btn{{padding:8px 16px;background:#6c757d;color:#fff;text-decoration:none;border-radius:4px;font-size:14px}}
            .back-btn:hover{{background:#5a6268}}
            .reset-btn{{padding:8px 16px;background:#dc3545;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px}}
            .reset-btn:hover{{background:#c82333}}
            .scoreboard{{text-align:left}}
            .score-item{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee}}
            .score-item:last-child{{border-bottom:none}}
            .score-item .name{{font-weight:bold}}
            .score-item .score{{font-size:18px;color:#007bff}}
            .score-item.winner{{background:#fff3cd;padding:8px;border-radius:4px}}
            .completed-label{{font-size:12px;color:#28a745;font-weight:bold}}
            @media (max-width:768px){{
                .container{{flex-direction:column}}
                .sidebar{{width:100%;position:static}}
                .cell{{font-size:20px}}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="game-area">
                <div class="header">
                    <a href="/" class="back-btn">← Назад</a>
                    <button class="reset-btn" onclick="resetGame()">↺ Заново</button>
                </div>
                
                <h1>🕹️ Крестики-нолики {field_size}x{field_size}</h1>
                <div class="players">
    """
    
    for p in players:
        active = 'active' if p['name'] == current_player['name'] else ''
        html += f'<span class="player-tag {active}">{p["name"]} ({p["symbol"]})</span>'
    
    html += f"""
                </div>
                <div class="msg">{msg}</div>
                <div class="board">
    """
    
    for bi in range(total_boards):
        board = boards[bi]
        is_completed = bi in completed_boards
        completed_class = "completed" if is_completed else ""
        html += f'<div><div class="mini {completed_class}">'
        for r in range(3):
            for c in range(3):
                val = board.board[r][c]
                gx = (bi % field_size) * 3 + c
                gy = (bi // field_size) * 3 + r
                if val:
                    color = '#28a745' if val == '+' else '#007bff' if val == '#' else '#6c757d'
                    html += f'<div class="cell" style="color:{color}" onclick="move({gx},{gy})">{val}</div>'
                else:
                    html += f'<div class="cell empty" onclick="move({gx},{gy})">·</div>'
        html += f'</div><div class="label">Поле {bi+1}</div></div>'
    
    html += f"""
                </div>
            </div>
            
            <div class="sidebar">
                <h3>🏆 Счет</h3>
                <div class="scoreboard">
    """
    
    # Сортируем по очкам
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    max_score = max(scores.values()) if scores else 0
    
    for name, score in sorted_scores:
        is_winner = score == max_score and max_score > 0
        winner_class = "winner" if is_winner else ""
        html += f'<div class="score-item {winner_class}">'
        html += f'<span class="name">{name}</span>'
        html += f'<span class="score">{score}</span>'
        html += f'</div>'
    
    html += f"""
                </div>
                <div style="margin-top:15px;font-size:12px;color:#666">
                    Завершено полей: {len(completed_boards)}/{total_boards}
                </div>
                <div style="margin-top:5px;font-size:12px;color:#666">
                    Ходов: {game['moves']}
                </div>
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
    field_size = game['field_size']
    
    # Создаем новый композитор
    comp = Compositor(field_size, field_size)
    for p in players:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    
    game['compositor'] = comp
    game['scores'] = {p['name']: 0 for p in players}
    game['completed_boards'] = set()
    game['moves'] = 0
    
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)