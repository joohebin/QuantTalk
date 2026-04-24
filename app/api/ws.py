from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app.models import ChannelMessage, User
from sqlalchemy import desc
import json
from datetime import datetime
import asyncio
from typing import Optional

router = APIRouter()


class ConnectionManager:
    """频道消息连接管理器"""
    def __init__(self):
        self.active_connections: dict[int, list[tuple[WebSocket, int, str]]] = {}  # channel_id -> [(ws, user_id, username)]

    async def connect(self, websocket: WebSocket, channel_id: int, user_id: int, username: str):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = []
        self.active_connections[channel_id].append((websocket, user_id, username))
        # 广播用户加入
        await self.broadcast(channel_id, {
            "type": "user_joined",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now().isoformat()
        })

    def disconnect(self, websocket: WebSocket, channel_id: int, user_id: int, username: str):
        if channel_id in self.active_connections:
            self.active_connections[channel_id] = [
                (ws, uid, name) for ws, uid, name in self.active_connections[channel_id]
                if ws != websocket
            ]
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]

    async def broadcast(self, channel_id: int, message: dict):
        if channel_id in self.active_connections:
            disconnected = []
            for ws, user_id, username in self.active_connections[channel_id]:
                try:
                    await ws.send_json(message)
                except:
                    disconnected.append(ws)
            # 清理断开的连接
            for ws in disconnected:
                self.disconnect(ws, channel_id, 0, "")

    def get_channel_users(self, channel_id: int) -> list[dict]:
        """获取频道在线用户列表"""
        if channel_id not in self.active_connections:
            return []
        return [
            {"user_id": uid, "username": name}
            for ws, uid, name in self.active_connections[channel_id]
            if uid > 0
        ]


class PresenceManager:
    """用户在线状态管理器"""
    def __init__(self):
        self.online_users: dict[int, dict] = {}  # user_id -> {username, status, last_heartbeat}
        self.statuses = ["online", "away", "busy", "dnd"]  # 在线、离开、忙碌、勿扰

    def set_online(self, user_id: int, username: str, status: str = "online"):
        self.online_users[user_id] = {
            "username": username,
            "status": status,
            "last_heartbeat": datetime.now()
        }

    def set_offline(self, user_id: int):
        if user_id in self.online_users:
            del self.online_users[user_id]

    def set_status(self, user_id: int, status: str):
        if user_id in self.online_users:
            self.online_users[user_id]["status"] = status
            self.online_users[user_id]["last_heartbeat"] = datetime.now()

    def heartbeat(self, user_id: int):
        if user_id in self.online_users:
            self.online_users[user_id]["last_heartbeat"] = datetime.now()
            # 如果状态是离开，恢复在线
            if self.online_users[user_id]["status"] == "away":
                self.online_users[user_id]["status"] = "online"

    def is_online(self, user_id: int) -> bool:
        if user_id not in self.online_users:
            return False
        # 超过5分钟无心跳视为离线
        last = self.online_users[user_id]["last_heartbeat"]
        if (datetime.now() - last).total_seconds() > 300:
            self.set_offline(user_id)
            return False
        return True

    def get_user_status(self, user_id: int) -> Optional[dict]:
        if not self.is_online(user_id):
            return None
        return self.online_users.get(user_id)

    def get_all_online(self) -> list[dict]:
        """获取所有在线用户"""
        # 清理超时用户
        now = datetime.now()
        to_remove = []
        for uid, data in self.online_users.items():
            if (now - data["last_heartbeat"]).total_seconds() > 300:
                to_remove.append(uid)
        for uid in to_remove:
            self.set_offline(uid)

        return [
            {"user_id": uid, **data, "is_online": True}
            for uid, data in self.online_users.items()
            if uid not in to_remove
        ]

    def get_online_count(self) -> int:
        return len([u for u in self.online_users.keys() if self.is_online(u)])


# 全局实例
manager = ConnectionManager()
presence = PresenceManager()

# 心跳检查任务
async def check_presence():
    """定期检查并清理离线用户"""
    while True:
        await asyncio.sleep(60)  # 每分钟检查一次
        try:
            db = SessionLocal()
            # 获取所有活跃的user_id
            active_ids = set()
            for users in manager.active_connections.values():
                for ws, uid, name in users:
                    active_ids.add(uid)

            # 更新数据库中用户的在线状态
            if active_ids:
                db.query(User).filter(User.id.in_(active_ids)).update(
                    {"is_online": True}, synchronize_session=False
                )
                db.commit()

            # 标记离线用户
            offline_ids = [uid for uid in presence.online_users.keys() if uid not in active_ids]
            if offline_ids:
                db.query(User).filter(User.id.in_(offline_ids)).update(
                    {"is_online": False}, synchronize_session=False
                )
                db.commit()

            db.close()
        except Exception as e:
            print(f"Presence check error: {e}")


@router.websocket("/ws/channel/{channel_id}")
async def channel_websocket(websocket: WebSocket, channel_id: int):
    """频道消息 WebSocket"""
    token = websocket.query_params.get("token", "")
    user_id = 0
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

    await manager.connect(websocket, channel_id, user_id, username)

    # 标记用户在线
    if user_id > 0:
        presence.set_online(user_id, username)
        # 更新数据库
        try:
            db = SessionLocal()
            db.query(User).filter(User.id == user_id).update({"is_online": True})
            db.commit()
            db.close()
        except:
            pass

    try:
        db = SessionLocal()
        heartbeat_count = 0

        while True:
            try:
                # 设置超时，每30秒等待数据或心跳
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                msg_data = json.loads(raw)
                msg_type = msg_data.get("type", "message")

                if msg_type == "heartbeat":
                    # 心跳包
                    heartbeat_count += 1
                    if user_id > 0:
                        presence.heartbeat(user_id)
                    # 回复心跳确认
                    await websocket.send_json({"type": "heartbeat_ack", "timestamp": datetime.now().isoformat()})

                elif msg_type == "status_change":
                    # 状态变更
                    new_status = msg_data.get("status", "online")
                    if user_id > 0 and new_status in ["online", "away", "busy", "dnd"]:
                        presence.set_status(user_id, new_status)
                        # 广播状态变更
                        await manager.broadcast(channel_id, {
                            "type": "status_changed",
                            "user_id": user_id,
                            "username": username,
                            "status": new_status
                        })

                elif msg_type == "message":
                    # 聊天消息
                    content = msg_data.get("content", "").strip()
                    if content:
                        msg = ChannelMessage(channel_id=channel_id, author_id=user_id, content=content)
                        db.add(msg)
                        db.commit()
                        db.refresh(msg)
                        await manager.broadcast(channel_id, {
                            "id": msg.id,
                            "channel_id": channel_id,
                            "author_id": user_id,
                            "author_username": username,
                            "content": content,
                            "created_at": msg.created_at.isoformat(),
                            "type": "message",
                        })

            except asyncio.TimeoutError:
                # 超时，发送ping保持连接
                await websocket.send_json({"type": "ping"})
                heartbeat_count += 1
                # 如果连续3次超时（90秒），用户标记为离开
                if heartbeat_count >= 3 and user_id > 0:
                    presence.set_status(user_id, "away")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket, channel_id, user_id, username)

        # 标记用户离线
        if user_id > 0:
            presence.set_offline(user_id)
            # 如果用户在其他频道还有连接，不标记离线
            still_online = any(user_id in [u[1] for u in users] for users in manager.active_connections.values())
            if not still_online:
                try:
                    db = SessionLocal()
                    db.query(User).filter(User.id == user_id).update({"is_online": False})
                    db.commit()
                    db.close()
                except:
                    pass
            else:
                # 广播用户离开当前频道
                await manager.broadcast(channel_id, {
                    "type": "user_left",
                    "user_id": user_id,
                    "username": username,
                    "timestamp": datetime.now().isoformat()
                })


@router.websocket("/ws/presence")
async def presence_websocket(websocket: WebSocket):
    """全局在线状态 WebSocket（用于实时更新好友/社区成员状态）"""
    token = websocket.query_params.get("token", "")
    user_id = 0

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

    await websocket.accept()

    # 标记在线
    if user_id > 0:
        presence.set_online(user_id, username)

    try:
        # 发送当前在线用户列表
        online_users = presence.get_all_online()
        await websocket.send_json({
            "type": "presence_init",
            "users": online_users,
            "count": len(online_users)
        })

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                msg_data = json.loads(raw)

                if msg_data.get("type") == "heartbeat":
                    presence.heartbeat(user_id)
                    await websocket.send_json({"type": "heartbeat_ack"})

                elif msg_data.get("type") == "status_change":
                    new_status = msg_data.get("status", "online")
                    if new_status in ["online", "away", "busy", "dnd"]:
                        presence.set_status(user_id, new_status)
                        await websocket.send_json({
                            "type": "status_updated",
                            "user_id": user_id,
                            "status": new_status
                        })

                elif msg_data.get("type") == "get_online_users":
                    users = presence.get_all_online()
                    await websocket.send_json({
                        "type": "online_users",
                        "users": users,
                        "count": len(users)
                    })

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        if user_id > 0:
            presence.set_offline(user_id)
    except Exception as e:
        print(f"Presence WS error: {e}")
        if user_id > 0:
            presence.set_offline(user_id)


@router.get("/online-users")
async def get_online_users():
    """获取所有在线用户列表（REST API）"""
    users = presence.get_all_online()
    return {
        "users": users,
        "count": len(users)
    }


@router.get("/channel/{channel_id}/online-members")
async def get_channel_online_members(channel_id: int):
    """获取频道在线成员"""
    users = manager.get_channel_users(channel_id)
    # 补充在线状态
    result = []
    for u in users:
        status = presence.get_user_status(u["user_id"])
        result.append({
            **u,
            "status": status["status"] if status else "offline"
        })
    return {"members": result, "count": len(result)}
