"""
Feature Flag & Remote Config Engine — Backend Server

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Interactive API docs (auto-generated) will be at:
    http://localhost:8000/docs
"""

import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import database
from evaluation import is_flag_enabled
from models import AppState, ConfigValue, FeatureFlag, RolloutRule

app = FastAPI(title="Feature Flag & Remote Config Engine")

# Allow any origin to call this API. This is a local/dev tool, and the
# Flutter app, web dashboards, etc. may run on different ports/devices.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    database.init_db()


def get_state() -> AppState:
    return AppState(flags=database.get_all_flags(), configs=database.get_all_configs())


# ---------------------------------------------------------------------------
# WebSocket connection manager — keeps every connected client in sync
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_state(self) -> None:
        """Send the full current state to every connected client."""
        message = json.dumps(get_state().model_dump())
        still_connected: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                still_connected.append(connection)
            except Exception:
                # The client disconnected without a clean close — drop it.
                pass
        self.active_connections = still_connected


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# REST API — read state
# ---------------------------------------------------------------------------
@app.get("/api/state", response_model=AppState)
def read_state() -> AppState:
    """Everything a client needs: all flags + all configs."""
    return get_state()


@app.get("/api/flags", response_model=List[FeatureFlag])
def list_flags() -> List[FeatureFlag]:
    return database.get_all_flags()


@app.get("/api/configs", response_model=List[ConfigValue])
def list_configs() -> List[ConfigValue]:
    return database.get_all_configs()


@app.get("/api/evaluate/{flag_name}")
def evaluate(flag_name: str, user_id: Optional[str] = None) -> dict:
    """Convenience endpoint: ask the server directly 'is this flag ON for this user?'"""
    flag = database.get_flag(flag_name)
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"flag": flag_name, "user_id": user_id, "enabled": is_flag_enabled(flag, user_id)}


# ---------------------------------------------------------------------------
# REST API — manage flags
# ---------------------------------------------------------------------------
@app.post("/api/flags", response_model=FeatureFlag)
async def create_flag(flag: FeatureFlag) -> FeatureFlag:
    created = database.create_flag(flag)
    await manager.broadcast_state()
    return created


@app.patch("/api/flags/{name}/toggle", response_model=FeatureFlag)
async def toggle_flag(name: str) -> FeatureFlag:
    flag = database.toggle_flag(name)
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    await manager.broadcast_state()
    return flag


@app.put("/api/flags/{name}/rollout", response_model=FeatureFlag)
async def set_rollout(name: str, rollout: RolloutRule) -> FeatureFlag:
    flag = database.update_flag_rollout(name, rollout)
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    await manager.broadcast_state()
    return flag


@app.delete("/api/flags/{name}")
async def remove_flag(name: str) -> dict:
    database.delete_flag(name)
    await manager.broadcast_state()
    return {"ok": True}


# ---------------------------------------------------------------------------
# REST API — manage configs
# ---------------------------------------------------------------------------
@app.post("/api/configs", response_model=ConfigValue)
async def create_config(config: ConfigValue) -> ConfigValue:
    created = database.create_config(config)
    await manager.broadcast_state()
    return created


@app.put("/api/configs/{key}", response_model=ConfigValue)
async def set_config(key: str, config: ConfigValue) -> ConfigValue:
    updated = database.update_config(key, config.value, config.value_type)
    if updated is None:
        raise HTTPException(status_code=404, detail="Config not found")
    await manager.broadcast_state()
    return updated


@app.delete("/api/configs/{key}")
async def remove_config(key: str) -> dict:
    database.delete_config(key)
    await manager.broadcast_state()
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket — real-time push to dashboards and apps
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        # Send the current state immediately so the client doesn't have to wait.
        await websocket.send_text(json.dumps(get_state().model_dump()))
        while True:
            # We don't expect messages FROM clients, but this keeps the
            # connection open and lets us detect a disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
