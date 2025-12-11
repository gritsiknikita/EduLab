from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from .db import engine, Base, get_db
from .models import User, Workstation, Command
from .schemas import RegisterIn, LoginIn, TokenOut, WorkstationOut, CommandIn
from .security import hash_password, verify_password, create_access_token
from typing import Dict, List
agents: Dict[str, WebSocket] = {}
agent_apps: Dict[str, List[str]] = {}
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="EduLab API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    # создаём таблицы (для MVP)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/health")
async def health():
    return {"ok": True}

# --- AUTH ---
@app.post("/auth/register")
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == data.email))
    if q.scalar_one_or_none():
        raise HTTPException(400, "Email already exists")

    u = User(email=data.email, password_hash=hash_password(data.password), role=data.role)
    db.add(u)
    await db.commit()
    return {"ok": True}

@app.post("/auth/login", response_model=TokenOut)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).where(User.email == data.email))
    u = q.scalar_one_or_none()
    if not u or not verify_password(data.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(sub=u.email, role=u.role)
    return TokenOut(access_token=token)

# --- WORKSTATIONS ---
@app.get("/workstations", response_model=list[WorkstationOut])
async def list_workstations(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Workstation).order_by(Workstation.id))
    items = q.scalars().all()
    return [
        WorkstationOut(
            id=w.id, pc_id=w.pc_id, name=w.name, room=w.room, online=w.online, locked=w.locked
        )
        for w in items
    ]

# --- COMMANDS (пока просто пишем в БД) ---
@app.post("/workstations/{ws_id}/commands")
async def create_command(ws_id: int, data: CommandIn, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Workstation).where(Workstation.id == ws_id))
    ws_obj = q.scalar_one_or_none()
    if not ws_obj:
        raise HTTPException(404, "Workstation not found")

    cmd = Command(workstation_id=ws_obj.id, type=data.type, payload=data.payload, status="queued")
    db.add(cmd)
    await db.commit()
    await db.refresh(cmd)

    # если агент онлайн — шлём команду сразу
    agent_ws = agents.get(ws_obj.pc_id)
    if agent_ws:
        try:
            await agent_ws.send_text(json.dumps({
                "id": cmd.id,
                "type": cmd.type,
                "payload": cmd.payload
            }))
            cmd.status = "sent"
            await db.commit()
        except Exception as e:
            cmd.status = "error"
            cmd.error = str(e)
            cmd.finished_at = datetime.now(timezone.utc)
            await db.commit()

    return {"command_id": cmd.id, "status": cmd.status}

@app.get("/workstations/{ws_id}/apps")
async def get_ws_apps(ws_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Workstation).where(Workstation.id == ws_id))
    w = q.scalar_one_or_none()
    if not w:
        raise HTTPException(404, "Workstation not found")
    return {"apps": agent_apps.get(w.pc_id, [])}

@app.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    await ws.accept()
    pc_id = None

    try:
        # ждём HELLO
        msg = await ws.receive_text()
        data = json.loads(msg)
        if data.get("type") != "HELLO":
            await ws.close(code=1008)
            return

        pc_id = data["pc_id"]
        name = data.get("name", pc_id)
        room = data.get("room", "")

        agents[pc_id] = ws

        # upsert workstation
        async for db in get_db():
            q = await db.execute(select(Workstation).where(Workstation.pc_id == pc_id))
            w = q.scalar_one_or_none()
            if not w:
                w = Workstation(pc_id=pc_id, name=name, room=room, online=True, locked=False)
                db.add(w)
            else:
                w.name = name
                w.room = room
                w.online = True
            w.last_seen = datetime.now(timezone.utc)
            await db.commit()

        # основной цикл
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)

            if data.get("type") == "HEARTBEAT":
                locked = bool(data.get("locked", False))
                apps = data.get("apps") or []
                agent_apps[pc_id] = apps
                async for db in get_db():
                    q = await db.execute(select(Workstation).where(Workstation.pc_id == pc_id))
                    w = q.scalar_one()
                    w.online = True
                    w.locked = locked
                    w.last_seen = datetime.now(timezone.utc)
                    await db.commit()

            elif data.get("type") == "RESULT":
                cmd_id = data.get("id")
                ok = bool(data.get("ok"))
                err = data.get("error")

                async for db in get_db():
                    q = await db.execute(select(Command).where(Command.id == cmd_id))
                    cmd = q.scalar_one_or_none()
                    if cmd:
                        cmd.status = "done" if ok else "error"
                        cmd.error = None if ok else (err or "unknown error")
                        cmd.finished_at = datetime.now(timezone.utc)
                        await db.commit()


    except WebSocketDisconnect:
        pass
    finally:
        if pc_id:
            agents.pop(pc_id, None)
            agent_apps.pop(pc_id, None)
            async for db in get_db():
                q = await db.execute(select(Workstation).where(Workstation.pc_id == pc_id))
                w = q.scalar_one_or_none()
                if w:
                    w.online = False
                    await db.commit()
