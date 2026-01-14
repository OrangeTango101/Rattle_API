from fastapi import FastAPI, HTTPException, status, Path
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from pydantic import BaseModel
from game import Game
import uuid
import time

games = {}
timeout = 20 #seconds 

async def timeout_worker():
    while True:
        now = time.time()
        to_remove = []
        for game_id, game in games.items():
            for user_id, player in game.users.items():
                if now - player.last_connection > timeout:
                    game.user_disconnect(user_id)
            
            if all([user.disconnected for user in game.users.values()]):
                to_remove.append(game_id)
        
        for game_id in to_remove:
            games.pop(game_id)              

        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout_task = asyncio.create_task(timeout_worker())
    yield
    timeout_task.cancel()
    await timeout_task

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Server is running!"}

class CreateGameResponse(BaseModel):
    game_id: str
    user_id: str
    players: list
    full: bool

class State(BaseModel):
    game_id: str 
    full: bool
    game: dict

class MoveRequest(BaseModel):
    game_id: str
    user_id: str
    move: str 

@app.post("/create_game/{game_type}", response_model=CreateGameResponse)
def create_game(game_type):
    if game_type not in Game.game_types:
        raise HTTPException(status_code=404, detail="Game type not found") 

    game_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    players = [0, 1] if game_type == "local" else [0]
    games[game_id] = Game(user_id, game_type, players)

    return {
        "game_id": game_id,
        "user_id": user_id,
        "players": players,
        "full": games[game_id].game_full()
    }

@app.get("/join_game/{game_id}", response_model=CreateGameResponse)
def join_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found") 
    if games[game_id].game_full():
        raise HTTPException(status_code=400, detail="Game is already full") 
    user_id = str(uuid.uuid4())
    games[game_id].add_user(user_id, [1])

    return {
        "game_id": game_id,
        "user_id": user_id,
        "players": [1],
        "full": True
    }

@app.post("/make_move", response_model=State)
def make_move(req: MoveRequest):
    if req.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found") 
    if req.user_id not in games[req.game_id].users:
        raise HTTPException(status_code=404, detail="User not found") 
    user = games[req.game_id].users[req.user_id]
    if not games[req.game_id].game_full():
        raise HTTPException(status_code=400, detail="Game is not full yet") 
    if games[req.game_id].player_turn not in user.players:
        raise HTTPException(status_code=400, detail="It is not your turn") 
    if not games[req.game_id].winner is None:
        raise HTTPException(status_code=400, detail="Game is over") 
    if req.move not in games[req.game_id].game_state.get_actions_ls(games[req.game_id].player_turn):
        raise HTTPException(status_code=400, detail="Not a legal action") 
    games[req.game_id].run_action(req.move)
    
    return {
        "game_id": req.game_id,
        "full": True,
        "game": games[req.game_id].to_dict()
    }

@app.get("/get_state/{game_id}/{user_id}", response_model=State)
def get_state(game_id: str, user_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found") 
    if user_id not in games[game_id].users:
        raise HTTPException(status_code=404, detail="User not found") 
    games[game_id].users[user_id].last_connection = time.time()
    
    return {
        "game_id": game_id,
        "full": games[game_id].game_full(),
        "game": games[game_id].to_dict()
    }

@app.delete("/end_game/{game_id}")
def end_game(game_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found") 
    games.pop(game_id)
    return {"message": "Game successfully ended"}

@app.post("/find_game", response_model=CreateGameResponse)
def find_game():
    user_id = str(uuid.uuid4())
    for game_id, game in games.items():
        if not game.game_full():
            games[game_id].add_user(user_id, [1])
            return {
                "game_id": game_id,
                "user_id": user_id,
                "players": [1],
                "full": True
            }
    
    game_id = str(uuid.uuid4())
    games[game_id] = Game(user_id, "online", [0])
    return {
        "game_id": game_id,
        "user_id": user_id,
        "players": [0],
        "full": False
    }

@app.delete("/leave_game/{game_id}/{user_id}")
def leave_game(game_id: str, user_id: str):
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found") 
    if user_id not in games[game_id].users:
        raise HTTPException(status_code=404, detail="User not found") 
    games[game_id].user_disconnect(user_id)
    return {"message": "Successfully left the game"}


