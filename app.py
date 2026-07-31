import sqlite3, os
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "records.db"
JST = timedelta(hours=9)
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "yangyangCheckOnMe")
BARK_KEY = os.environ.get("BARK_API_KEY", "TV7ecrvu53F9NHi9VN2bjk")

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

class BarkBody(BaseModel):
    title: str = "凌止"
    content: str

def verify_auth(req: Request):
    auth = req.headers.get("Authorization", "")
    token = req.query_params.get("token", "")
    return auth == f"Bearer {AUTH_TOKEN}" or token == AUTH_TOKEN

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

@app.post("/bark/push")
async def bark_push(body: BarkBody, req: Request):
    if not verify_auth(req):
        raise HTTPException(401, "Unauthorized")
    if not BARK_KEY:
        raise HTTPException(500, "BARK_API_KEY 未配置")
    url = f"https://api.day.app/{BARK_KEY}/{body.title}/{body.content}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return {"status": "ok", "message": "推送成功"}
        return {"status": "error", "message": "推送失败"}
    except Exception as e:
        raise HTTPException(500, f"推送异常：{e}")

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
    # 只统计今天（JST时区）的记录，每天零点自动清零翻篇
    now_jst = datetime.utcnow() + JST
    day_start_jst = now_jst.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_utc = day_start_jst - JST
    sessions, opens = {}, {}
    for r in rows:
        app, ev, ts = r
        t = datetime.fromisoformat(ts)
        if t < day_start_utc:  # 昨天的记录直接跳过，只算今天的
            continue
        if ev == "open":
            opens[app] = t
        elif ev == "close" and app in opens:
            gap = int((t - opens[app]).total_seconds())
            sessions[app] = sessions.get(app, 0) + gap
            del opens[app]
    return {
        "recent_apps": [r[0] for r in recent],
        "sessions": sessions,
        "period": "today"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
