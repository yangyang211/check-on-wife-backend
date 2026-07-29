import sqlite3, os
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "records.db"
JST = timedelta(hours=9)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "yangyangCheckOnMe")

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT NOT NULL,
        event TEXT NOT NULL,
        timestamp TEXT NOT NULL)""")
    conn.commit(); conn.close()

init_db()

app = FastAPI(title="查岗系统")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ReportBody(BaseModel):
    app_name: str
    event: str

def verify_auth(req: Request):
    """支持Header和query参数两种鉴权方式"""
    auth = req.headers.get("Authorization", "")
    token = req.query_params.get("token", "")
    if auth == f"Bearer {AUTH_TOKEN}" or token == AUTH_TOKEN:
        return True
    return False

@app.post("/report")
async def report(body: ReportBody, req: Request):
    if not verify_auth(req):
        raise HTTPException(401, "Unauthorized")
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("INSERT INTO records (app_name, event, timestamp) VALUES (?, ?, ?)",
                 (body.app_name, body.event, now))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.get("/api/screentime/toggle/{app_name}")
async def toggle(app_name: str, req: Request):
    """toggle接口：自动判断该记open还是close"""
    if not verify_auth(req):
        raise HTTPException(401, "Unauthorized")
    
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT event FROM records WHERE app_name=? ORDER BY id DESC LIMIT 1", (app_name,))
    last = cur.fetchone()
    
    new_event = "close" if last and last[0] == "open" else "open"
    now = datetime.utcnow().isoformat()
    conn.execute("INSERT INTO records (app_name, event, timestamp) VALUES (?, ?, ?)",
                 (app_name, new_event, now))
    conn.commit(); conn.close()
    return {"app": app_name, "event": new_event, "time": now}

@app.get("/ping")
async def ping():
    return "pong"

@app.get("/activity/summary")
async def summary():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute("SELECT app_name, event, timestamp FROM records ORDER BY id DESC LIMIT 5")
    recent = cur.fetchall()
    cur.execute("SELECT app_name, event, timestamp FROM records ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    sessions, opens = {}, {}
    for r in rows:
        app, ev, ts = r
        if ev == "open":
            opens[app] = datetime.fromisoformat(ts)
        elif ev == "close" and app in opens:
            gap = int((datetime.fromisoformat(ts) - opens[app]).total_seconds())
            sessions[app] = sessions.get(app, 0) + gap
            del opens[app]
    return {
        "recent_apps": [r[0] for r in recent],
        "sessions": sessions
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)