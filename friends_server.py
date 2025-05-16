from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime, timedelta
import sqlite3
import os

app = FastAPI()
DB_FILE = "friends.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            name TEXT PRIMARY KEY,
            token TEXT,
            last_seen TEXT,
            last_ip TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS friends (
            user TEXT,
            friend TEXT,
            PRIMARY KEY (user, friend)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS friend_requests (
            from_user TEXT,
            to_user TEXT,
            status TEXT,
            timestamp TEXT,
            PRIMARY KEY (from_user, to_user)
        )''')

init_db()

class RegisterRequest(BaseModel):
    name: str

class StatusUpdate(BaseModel):
    ip: str

class FriendRequest(BaseModel):
    friend: str

class RemoveFriendRequest(BaseModel):
    friend: str

def get_user_by_token(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token header")
    token = authorization.split(" ", 1)[1]
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE token = ?", (token,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid token")
        return row[0]

@app.post("/register")
def register(req: RegisterRequest):
    token = str(uuid4())
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE name = ?", (req.name,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="User already exists")
        c.execute("INSERT INTO users (name, token) VALUES (?, ?)", (req.name, token))
    return {"token": token}

@app.post("/status")
def update_status(data: StatusUpdate, user: str = Depends(get_user_by_token)):
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET last_seen = ?, last_ip = ? WHERE name = ?", (now, data.ip, user))
    return {"status": "ok"}

@app.post("/friends/request")
def request_friend(data: FriendRequest, user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE name = ?", (data.friend,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="Friend not found")
        c.execute("INSERT OR REPLACE INTO friend_requests (from_user, to_user, status, timestamp) VALUES (?, ?, ?, ?)",
                  (user, data.friend, "pending", datetime.utcnow().isoformat()))
    return {"status": "friend request sent"}

# Die Freundschaftsanfrage wird trotzdem in der Tabelle friend_requests gespeichert,
# auch wenn der Empfänger offline ist. Beim nächsten Login oder Abruf sieht der User die Anfrage.

# Das ist das Standardverhalten:
# - POST /friends/request legt immer einen Eintrag in friend_requests an (Status "pending").
# - Der Empfänger muss nicht online sein.
# - Beim nächsten GET /friends/requests sieht der Empfänger alle offenen Anfragen.

# Es ist keine Änderung am Servercode nötig, das ist bereits so implementiert.

@app.get("/friends/requests")
def get_friend_requests(user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT from_user FROM friend_requests WHERE to_user = ? AND status = 'pending'", (user,))
        requests = [row[0] for row in c.fetchall()]
    return {"incoming_requests": requests}

@app.post("/friends/accept")
def accept_friend(data: FriendRequest, user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE friend_requests SET status = 'accepted' WHERE from_user = ? AND to_user = ?", (data.friend, user))
        c.execute("INSERT OR IGNORE INTO friends (user, friend) VALUES (?, ?)", (user, data.friend))
        c.execute("INSERT OR IGNORE INTO friends (user, friend) VALUES (?, ?)", (data.friend, user))
    return {"status": "friend request accepted"}

@app.post("/friends/reject")
def reject_friend(data: FriendRequest, user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("UPDATE friend_requests SET status = 'rejected' WHERE from_user = ? AND to_user = ?", (data.friend, user))
    return {"status": "friend request rejected"}

@app.post("/friends/remove")
def remove_friend(data: RemoveFriendRequest, user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        # Entferne Freundschaft in beide Richtungen
        c.execute("DELETE FROM friends WHERE (user = ? AND friend = ?) OR (user = ? AND friend = ?)", (user, data.friend, data.friend, user))
        # Optional: Entferne offene Anfragen zwischen den beiden
        c.execute("DELETE FROM friend_requests WHERE (from_user = ? AND to_user = ?) OR (from_user = ? AND to_user = ?)", (user, data.friend, data.friend, user))
    return {"status": "friend removed"}

@app.get("/friends/online")
def online_friends(user: str = Depends(get_user_by_token)):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT friend FROM friends WHERE user = ?", (user,))
        friends = [row[0] for row in c.fetchall()]

        result = []
        threshold = datetime.utcnow() - timedelta(seconds=60)
        for friend in friends:
            c.execute("SELECT last_seen, last_ip FROM users WHERE name = ?", (friend,))
            row = c.fetchone()
            if row:
                last_seen = datetime.fromisoformat(row[0]) if row[0] else None
                if last_seen and last_seen > threshold:
                    result.append({"name": friend, "ip": row[1], "last_seen": row[0]})

    return {"online_friends": result}

if __name__ == "__main__":
    import uvicorn
    # Hier kannst du host und port anpassen:
    uvicorn.run("friends_server:app", host="0.0.0.0", port=8000, reload=True)
