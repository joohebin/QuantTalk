"""
WebRTC 视频通话信令服务器
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal, get_db
from app.models import User
from app.auth import get_current_user
from datetime import datetime
import json
from typing import Optional

router = APIRouter()


# WebRTC 信令管理器
class RoomManager:
    """视频通话房间管理器"""
    def __init__(self):
        # room_id -> {host_id, participants: {user_id: {ws, username, muted, video_on}}}
        self.rooms: dict[str, dict] = {}
        # user_id -> room_id
        self.user_rooms: dict[int, str] = {}
        # WebSocket connections for signaling
        self.signaling_connections: dict[int, WebSocket] = {}

    def create_room(self, room_id: str, host_id: int, host_username: str) -> dict:
        """创建房间"""
        self.rooms[room_id] = {
            "id": room_id,
            "host_id": host_id,
            "participants": {},
            "created_at": datetime.now().isoformat(),
            "max_participants": 10
        }
        return self.rooms[room_id]

    def join_room(self, room_id: str, user_id: int, username: str, ws: WebSocket) -> bool:
        """加入房间"""
        if room_id not in self.rooms:
            return False
        
        room = self.rooms[room_id]
        if len(room["participants"]) >= room["max_participants"]:
            return False
        
        room["participants"][user_id] = {
            "user_id": user_id,
            "username": username,
            "muted": False,
            "video_on": True,
            "joined_at": datetime.now().isoformat()
        }
        self.user_rooms[user_id] = room_id
        self.signaling_connections[user_id] = ws
        return True

    def leave_room(self, user_id: int) -> tuple[str | None, dict | None]:
        """离开房间"""
        room_id = self.user_rooms.get(user_id)
        if not room_id or room_id not in self.rooms:
            return None, None
        
        room = self.rooms[room_id]
        if user_id in room["participants"]:
            del room["participants"][user_id]
        
        del self.user_rooms[user_id]
        if user_id in self.signaling_connections:
            del self.signaling_connections[user_id]
        
        # 如果房间空了，删除房间
        if not room["participants"]:
            del self.rooms[room_id]
        
        return room_id, room if room_id in self.rooms else None

    def get_room(self, room_id: str) -> dict | None:
        """获取房间信息"""
        return self.rooms.get(room_id)

    def get_user_room(self, user_id: int) -> str | None:
        """获取用户所在房间"""
        return self.user_rooms.get(user_id)

    def is_host(self, room_id: str, user_id: int) -> bool:
        """检查是否是房主"""
        room = self.rooms.get(room_id)
        return room and room["host_id"] == user_id

    def toggle_mute(self, user_id: int, muted: bool):
        """切换静音状态"""
        room_id = self.user_rooms.get(user_id)
        if room_id and room_id in self.rooms:
            if user_id in self.rooms[room_id]["participants"]:
                self.rooms[room_id]["participants"][user_id]["muted"] = muted

    def toggle_video(self, user_id: int, video_on: bool):
        """切换视频状态"""
        room_id = self.user_rooms.get(user_id)
        if room_id and room_id in self.rooms:
            if user_id in self.rooms[room_id]["participants"]:
                self.rooms[room_id]["participants"][user_id]["video_on"] = video_on

    async def send_to_user(self, user_id: int, message: dict):
        """向指定用户发送消息"""
        if user_id in self.signaling_connections:
            try:
                await self.signaling_connections[user_id].send_json(message)
            except Exception as e:
                print(f"Error sending to user {user_id}: {e}")

    async def broadcast_to_room(self, room_id: str, message: dict, exclude_user: int | None = None):
        """向房间内所有用户广播消息"""
        if room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        for pid in room["participants"]:
            if pid != exclude_user:
                await self.send_to_user(pid, message)

    async def notify_user_joined(self, room_id: str, user_id: int, username: str):
        """通知用户加入"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        # 通知其他人
        for pid in room["participants"]:
            if pid != user_id:
                await self.send_to_user(pid, {
                    "type": "user_joined",
                    "room_id": room_id,
                    "user_id": user_id,
                    "username": username,
                    "participants": list(room["participants"].keys())
                })
        
        # 告诉新用户当前房间的所有参与者
        await self.send_to_user(user_id, {
            "type": "room_joined",
            "room_id": room_id,
            "host_id": room["host_id"],
            "participants": [
                {"user_id": pid, "username": p["username"], "muted": p["muted"], "video_on": p["video_on"]}
                for pid, p in room["participants"].items()
                if pid != user_id
            ]
        })

    async def notify_user_left(self, room_id: str, user_id: int, username: str):
        """通知用户离开"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        await self.broadcast_to_room(room_id, {
            "type": "user_left",
            "room_id": room_id,
            "user_id": user_id,
            "username": username,
            "is_host": room["host_id"] == user_id,
            "participants": list(room["participants"].keys())
        }, exclude_user=user_id)


# 全局实例
room_manager = RoomManager()


# REST API 端点
@router.get("/rooms")
async def list_rooms(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有活跃房间"""
    active_rooms = []
    for room_id, room in room_manager.rooms.items():
        participants = [
            {"user_id": pid, "username": p["username"], "muted": p["muted"], "video_on": p["video_on"]}
            for pid, p in room["participants"].items()
        ]
        active_rooms.append({
            "id": room_id,
            "host_id": room["host_id"],
            "participant_count": len(participants),
            "participants": participants,
            "created_at": room["created_at"]
        })
    return {"rooms": active_rooms, "count": len(active_rooms)}


@router.post("/rooms")
async def create_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建视频通话房间"""
    if room_id in room_manager.rooms:
        return {"error": "Room already exists", "room_id": room_id}
    
    room = room_manager.create_room(room_id, current_user.id, current_user.username)
    
    # 记录房间创建到数据库
    from app.models import VideoRoom
    db_room = db.query(VideoRoom).filter(VideoRoom.room_id == room_id).first()
    if not db_room:
        db_room = VideoRoom(room_id=room_id, host_id=current_user.id, host_username=current_user.username)
        db.add(db_room)
        db.commit()
    
    return {
        "room_id": room_id,
        "host_id": current_user.id,
        "host_username": current_user.username,
        "created_at": room["created_at"]
    }


@router.get("/rooms/{room_id}")
async def get_room_info(room_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取房间信息"""
    room = room_manager.get_room(room_id)
    if not room:
        return {"error": "Room not found", "room_id": room_id}
    
    participants = [
        {"user_id": pid, "username": p["username"], "muted": p["muted"], "video_on": p["video_on"]}
        for pid, p in room["participants"].items()
    ]
    
    return {
        "room_id": room_id,
        "host_id": room["host_id"],
        "participant_count": len(participants),
        "participants": participants,
        "created_at": room["created_at"]
    }


@router.delete("/rooms/{room_id}")
async def close_room(room_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """关闭房间（仅房主）"""
    room = room_manager.get_room(room_id)
    if not room:
        return {"error": "Room not found"}
    
    if room["host_id"] != current_user.id:
        return {"error": "Only host can close the room"}
    
    # 通知所有用户房间已关闭
    for pid in list(room["participants"].keys()):
        room_manager.leave_room(pid)
    
    # 删除数据库记录
    from app.models import VideoRoom
    db.query(VideoRoom).filter(VideoRoom.room_id == room_id).delete()
    db.commit()
    
    return {"message": "Room closed"}


# WebSocket 信令端点
@router.websocket("/ws/room/{room_id}")
async def room_signaling_websocket(websocket: WebSocket, room_id: str):
    """视频通话房间信令 WebSocket"""
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

    await websocket.accept()

    # 检查是否已在其他房间
    current_room = room_manager.get_user_room(user_id)
    if current_room:
        await room_manager.leave_room(user_id)

    # 加入房间
    if not room_manager.join_room(room_id, user_id, username, websocket):
        await websocket.send_json({"type": "error", "message": "Cannot join room"})
        await websocket.close()
        return

    # 通知其他用户并获取当前参与者
    await room_manager.notify_user_joined(room_id, user_id, username)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "offer":
                # WebRTC Offer
                target_user = data.get("to")
                if target_user:
                    await room_manager.send_to_user(target_user, {
                        "type": "offer",
                        "from": user_id,
                        "from_username": username,
                        "sdp": data.get("sdp"),
                        "room_id": room_id
                    })

            elif msg_type == "answer":
                # WebRTC Answer
                target_user = data.get("to")
                if target_user:
                    await room_manager.send_to_user(target_user, {
                        "type": "answer",
                        "from": user_id,
                        "from_username": username,
                        "sdp": data.get("sdp"),
                        "room_id": room_id
                    })

            elif msg_type == "ice_candidate":
                # ICE Candidate
                target_user = data.get("to")
                if target_user:
                    await room_manager.send_to_user(target_user, {
                        "type": "ice_candidate",
                        "from": user_id,
                        "candidate": data.get("candidate"),
                        "room_id": room_id
                    })

            elif msg_type == "mute":
                # 静音状态变更
                muted = data.get("muted", True)
                room_manager.toggle_mute(user_id, muted)
                await room_manager.broadcast_to_room(room_id, {
                    "type": "participant_updated",
                    "user_id": user_id,
                    "muted": muted
                }, exclude_user=user_id)

            elif msg_type == "video_toggle":
                # 视频开关
                video_on = data.get("video_on", False)
                room_manager.toggle_video(user_id, video_on)
                await room_manager.broadcast_to_room(room_id, {
                    "type": "participant_updated",
                    "user_id": user_id,
                    "video_on": video_on
                }, exclude_user=user_id)

            elif msg_type == "chat":
                # 通话中文字聊天
                content = data.get("content", "").strip()
                if content:
                    await room_manager.broadcast_to_room(room_id, {
                        "type": "chat",
                        "from": user_id,
                        "from_username": username,
                        "content": content,
                        "timestamp": datetime.now().isoformat()
                    })

            elif msg_type == "heartbeat":
                await websocket.send_json({"type": "heartbeat_ack"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Room signaling error: {e}")
    finally:
        # 离开房间
        _, room = await room_manager.leave_room(user_id)
        if room is not None or room_id in room_manager.rooms:
            await room_manager.notify_user_left(room_id, user_id, username)
        elif room_id in room_manager.rooms:
            # 房间已空但还没删除
            del room_manager.rooms[room_id]
