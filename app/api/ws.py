from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChannelMessage
import json
from datetime import datetime

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}  # channel_id -> [ws]

    async def connect(self, websocket: WebSocket, channel_id: int):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: int):
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]

    async def broadcast(self, channel_id: int, message: dict):
        if channel_id in self.active_connections:
            for conn in self.active_connections[channel_id]:
                try:
                    await conn.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.websocket("/ws/channel/{channel_id}")
async def channel_websocket(websocket: WebSocket, channel_id: int):
    # Auth via query param token
    token = websocket.query_params.get("token", "")
    user_id = None
    username = "anonymous"
    if token:
        try:
            from jose import jwt
            from app.config import SECRET_KEY, ALGORITHM
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = int(payload.get("sub", 0))
            username = payload.get("username", "anonymous")
        except:
            await websocket.close(code=4001)
            return

    await manager.connect(websocket, channel_id)
    try:
        db = SessionLocal()
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            content = msg_data.get("content", "").strip()
            if not content:
                continue

            # Save to DB
            msg = ChannelMessage(channel_id=channel_id, author_id=user_id or 0, content=content)
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # Broadcast
            await manager.broadcast(channel_id, {
                "id": msg.id,
                "channel_id": channel_id,
                "author_id": user_id,
                "author_username": username,
                "content": content,
                "created_at": msg.created_at.isoformat(),
                "type": "message",
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)
    finally:
        db.close()
