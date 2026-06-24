from fastapi import FastAPI, Request, Response, Cookie, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from urllib.parse import quote, unquote
import uuid
import json
import asyncio
from typing import Dict, Set
import time

app = FastAPI()

from compositor import Compositor, End

# Хранилище игр
games: Dict[str, dict] = {}
# Хранилище WebSocket соединений для каждой игры
websockets: Dict[str, Set[WebSocket]] = {}

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Крестики-нолики</title>
    <style>
        body {font-family:Arial;text-align:center;padding:20px;background:#f5f5f5}
        .container {max-width:500px;margin:0 auto;background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}
        input, select {padding:8px;margin:5px;width:150px;border:1px solid #ddd;border-radius:4px}
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
        <h3>Создайте игру</h3>
        <div class="field-size">
            <label>Размер поля:</label>
            <select id="fieldSize">
                <option value="2">2x2 (4 поля)</option>
                <option value="3" selected>3x3 (9 полей)</option>
                <option value="4">4x4 (16 полей)</option>
                <option value="5">5x5 (25 полей)</option>
            </select>
        </div>
        <div id="players"><div style="color:#666;margin:10px 0">Пока нет игроков</div></div>
        <form id="addForm" style="margin:20px 0">
            <input type="text" id="playerName" placeholder="Имя игрока" required>
            <input type="text" id="playerSymbol" placeholder="Символ (+, #, *...)" maxlength="1" required>
            <button type="submit">➕ Добавить</button>
        </form>
        <button id="startBtn" class="start-btn disabled" onclick="startGame()">🚀 Играть!</button>
        <div id="gameLink" style="margin-top:15px;display:none">
            <p>Игра создана! Отправьте ссылку игрокам:</p>
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
            if (players.find(p => p.name === name)) { alert('Имя уже есть!'); return; }
            if (players.find(p => p.symbol === symbol)) { alert('Символ уже используется!'); return; }
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
                    `<div class="player"><span><strong>${p.name}</strong> <span class="symbol">${p.symbol}</span></span>
                    <button class="remove-btn" onclick="removePlayer('${p.name}')">✕</button></div>`
                ).join('');
            }
            document.getElementById('startBtn').classList.toggle('disabled', players.length < 2);
        }
        async function startGame() {
            if (players.length < 2) { alert('Нужно минимум 2 игрока!'); return; }
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
    comp = Compositor(field_size, field_size)
    for p in player_list:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    scores = {p['name']: 0 for p in player_list}
    games[game_id] = {
        'compositor': comp,
        'players': player_list,
        'scores': scores,
        'completed_boards': set(),
        'field_size': field_size,
        'total_boards': field_size * field_size,
        'moves': 0,
        'game_over': False,
        'winner': None
    }
    websockets[game_id] = set()
    return {"game_id": game_id}

# WebSocket эндпоинт
@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    if game_id not in websockets:
        websockets[game_id] = set()
    websockets[game_id].add(websocket)
    
    # Отправляем текущее состояние при подключении
    state = await get_state(game_id)
    await websocket.send_text(json.dumps(state))
    
    try:
        while True:
            # Ждем сообщения от клиента (для поддержки соединения)
            await websocket.receive_text()
    except WebSocketDisconnect:
        websockets[game_id].discard(websocket)

# Функция оповещения всех подписчиков
async def notify_game(game_id: str, event: dict):
    if game_id in websockets:
        message = json.dumps(event)
        for ws in websockets[game_id].copy():
            try:
                await ws.send_text(message)
            except:
                websockets[game_id].discard(ws)

@app.get("/game/{game_id}", response_class=HTMLResponse)
async def game_page(request: Request, game_id: str, player_name: str | None = None):
    if game_id not in games:
        return "<h1>Игра не найдена!</h1><a href='/'>Вернуться</a>"
    game = games[game_id]
    players = game['players']
    
    if not player_name:
        options = ''.join(f'<option value="{p["name"]}">{p["name"]} ({p["symbol"]})</option>' for p in players)
        return f"""
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>Вход в игру</title>
        <style>body{{font-family:Arial;text-align:center;padding:50px;background:#f5f5f5}}
        .container{{max-width:400px;margin:0 auto;background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}}
        select,button{{padding:10px;margin:10px;width:80%;font-size:16px}}
        button{{background:#007bff;color:#fff;border:none;border-radius:4px;cursor:pointer}}
        button:hover{{background:#0069d9}}
        </style></head>
        <body>
        <div class="container">
            <h1>🕹️ Крестики-нолики</h1>
            <p>Выберите своё имя:</p>
            <form action="/game/{game_id}" method="get">
                <select name="player_name" required>
                    <option value="">-- Выберите --</option>
                    {options}
                </select>
                <button type="submit">Войти</button>
            </form>
        </div>
        </body></html>
        """
    
    if player_name not in [p['name'] for p in players]:
        return "<h1>Игрок не найден!</h1><a href='/'>Вернуться</a>"
    
    html = generate_game_html(game_id, player_name)
    response = Response(content=html, media_type="text/html")
    encoded_name = quote(player_name, safe='')
    response.set_cookie(key="player_name", value=encoded_name, httponly=True)
    return response

def generate_game_html(game_id: str, player_name: str):
    field_size = games[game_id]['field_size']
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Крестики-нолики</title>
        <style>
            body{{font-family:Arial;text-align:center;padding:20px;background:#f5f5f5;margin:0}}
            .container{{max-width:1000px;margin:0 auto;display:flex;gap:20px;align-items:flex-start}}
            .game-area{{flex:1}}
            .sidebar{{width:200px;background:#fff;padding:20px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);position:sticky;top:20px}}
            .board{{display:grid;grid-template-columns:repeat({field_size},1fr);gap:10px;margin:20px auto}}
            .mini{{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;background:#333;padding:2px;border-radius:4px;aspect-ratio:1;position:relative}}
            .mini.completed{{opacity:0.6;pointer-events:none}}
            .mini.completed::after{{
                content:'✓';
                position:absolute;top:50%;left:50%;
                transform:translate(-50%,-50%);
                font-size:40px;color:#28a745;font-weight:bold;
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
            @media (max-width:768px){{ .container{{flex-direction:column}} .sidebar{{width:100%;position:static}} .cell{{font-size:20px}} }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="game-area">
                <div class="header">
                    <span>Вы: <strong>{player_name}</strong></span>
                    <a href="/" class="back-btn">← Выйти</a>
                    <button class="reset-btn" onclick="resetGame()">↺ Заново</button>
                </div>
                <h1>🕹️ Крестики-нолики</h1>
                <div class="players" id="playersList"></div>
                <div class="msg" id="message">Подключение...</div>
                <div class="board" id="boardContainer"></div>
            </div>
            <div class="sidebar" id="sidebar">
                <h3>🏆 Счет</h3>
                <div class="scoreboard" id="scoreboard"></div>
                <div style="margin-top:15px;font-size:12px;color:#666" id="progress"></div>
                <div style="margin-top:5px;font-size:12px;color:#666" id="movesInfo"></div>
            </div>
        </div>
        <script>
            const gameId = '{game_id}';
            let ws = null;
            
            function connectWebSocket() {{
                ws = new WebSocket(`ws://${{window.location.host}}/ws/${{gameId}}`);
                
                ws.onopen = function() {{
                    console.log('WebSocket connected');
                }};
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    updateUI(data);
                }};
                
                ws.onerror = function(error) {{
                    console.error('WebSocket error:', error);
                    setTimeout(connectWebSocket, 3000);
                }};
                
                ws.onclose = function() {{
                    console.log('WebSocket closed, reconnecting...');
                    setTimeout(connectWebSocket, 3000);
                }};
            }}
            
            function updateUI(data) {{
                const playersList = document.getElementById('playersList');
                playersList.innerHTML = data.players.map(p => 
                    `<span class="player-tag ${{p.active ? 'active' : ''}}">${{p.name}} (${{p.symbol}})</span>`
                ).join('');
                
                document.getElementById('message').innerHTML = data.message;
                
                const container = document.getElementById('boardContainer');
                container.innerHTML = data.boards_html;
                
                const scoreboard = document.getElementById('scoreboard');
                scoreboard.innerHTML = data.scores_html;
                
                document.getElementById('progress').textContent = data.progress;
                document.getElementById('movesInfo').textContent = data.moves_info;
            }}
            
            function makeMove(x, y) {{
                fetch(`/move/${{gameId}}?x=${{x}}&y=${{y}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}}
                }})
                .then(r => r.json())
                .then(data => {{
                    if (data.error) {{
                        alert(data.error);
                    }}
                    // WebSocket сам обновит состояние
                }})
                .catch(err => alert('Ошибка: ' + err));
            }}
            
            function resetGame() {{
                if (confirm('Начать заново?')) {{
                    fetch(`/reset_game/${{gameId}}`, {{method: 'POST'}})
                        .then(() => {{ }})
                        .catch(err => alert('Ошибка: ' + err));
                }}
            }}
            
            // Подключаем WebSocket
            connectWebSocket();
        </script>
    </body>
    </html>
    """

@app.get("/state/{game_id}")
async def get_state(game_id: str):
    if game_id not in games:
        raise HTTPException(404, "Game not found")
    game = games[game_id]
    comp = game['compositor']
    players = game['players']
    scores = game['scores']
    completed_boards = game['completed_boards']
    field_size = game['field_size']
    total_boards = game['total_boards']
    moves = game['moves']
    current_player = players[moves % len(players)]
    
    boards_html = build_boards_html(comp, field_size, completed_boards)
    scores_html = build_scores_html(scores)
    players_list = [{'name': p['name'], 'symbol': p['symbol'], 'active': p['name'] == current_player['name']} for p in players]
    
    if game.get('game_over'):
        msg = f"🎉 Игра завершена! Победитель: {game['winner']}" if game['winner'] else "🤝 Ничья!"
    else:
        msg = f"Ходит: {current_player['name']} ({current_player['symbol']})"
    
    return {
        'players': players_list,
        'message': msg,
        'boards_html': boards_html,
        'scores_html': scores_html,
        'progress': f"Завершено полей: {len(completed_boards)}/{total_boards}",
        'moves_info': f"Ходов: {moves}"
    }

def build_boards_html(comp, field_size, completed_boards):
    boards = comp.get_board_list()
    total = field_size * field_size
    html = ''
    for bi in range(total):
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
                    html += f'<div class="cell" style="color:{color}" onclick="makeMove({gx},{gy})">{val}</div>'
                else:
                    html += f'<div class="cell empty" onclick="makeMove({gx},{gy})">·</div>'
        html += f'</div><div class="label">Поле {bi+1}</div></div>'
    return html

def build_scores_html(scores):
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    max_score = max(scores.values()) if scores else 0
    html = ''
    for name, score in sorted_scores:
        is_winner = score == max_score and max_score > 0
        winner_class = "winner" if is_winner else ""
        html += f'<div class="score-item {winner_class}"><span class="name">{name}</span><span class="score">{score}</span></div>'
    return html

@app.post("/move/{game_id}")
async def make_move(request: Request, game_id: str, x: int, y: int, player_name: str = Cookie(None)):
    if game_id not in games:
        return {"error": "Game not found"}
    game = games[game_id]
    if game.get('game_over'):
        return {"error": "Игра уже завершена"}
    
    if not player_name:
        return {"error": "Вы не авторизованы"}
    try:
        player_name = unquote(player_name)
    except:
        return {"error": "Ошибка авторизации"}
    
    moves = game['moves']
    players = game['players']
    current_player = players[moves % len(players)]
    
    if current_player['name'] != player_name:
        return {"error": f"Сейчас ходит {current_player['name']}, а не вы!"}
    
    field_size = game['field_size']
    if not (0 <= x < field_size * 3 and 0 <= y < field_size * 3):
        return {"error": "Неверные координаты"}
    
    comp = game['compositor']
    board_idx = (x // 3) + (y // 3) * field_size
    if board_idx in game['completed_boards']:
        return {"error": "Это поле уже завершено"}
    
    boards = comp.get_board_list()
    local_x = x % 3
    local_y = y % 3
    if boards[board_idx].board[local_y][local_x]:
        return {"error": "Клетка занята"}
    
    res = comp.go(x, y, player_name)
    game['moves'] += 1
    
    if res == End.finished:
        if board_idx not in game['completed_boards']:
            game['scores'][player_name] += 1
            game['completed_boards'].add(board_idx)
            if len(game['completed_boards']) == game['total_boards']:
                game['game_over'] = True
                max_score = max(game['scores'].values())
                winners = [name for name, score in game['scores'].items() if score == max_score]
                game['winner'] = winners[0] if len(winners) == 1 else None
    
    state = await get_state(game_id)
    await notify_game(game_id, state)
    return {"status": "ok"}

@app.post("/reset_game/{game_id}")
async def reset_game(game_id: str):
    if game_id not in games:
        return {"error": "Game not found"}
    game = games[game_id]
    players = game['players']
    field_size = game['field_size']
    comp = Compositor(field_size, field_size)
    for p in players:
        comp.add_player(p['name'], p['symbol'])
    comp.init()
    game['compositor'] = comp
    game['scores'] = {p['name']: 0 for p in players}
    game['completed_boards'] = set()
    game['moves'] = 0
    game['game_over'] = False
    game['winner'] = None
    state = await get_state(game_id)
    await notify_game(game_id, state)
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)