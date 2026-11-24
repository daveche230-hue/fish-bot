import json
from pathlib import Path
import aiosqlite

from bot.config import DB_PATH, DEFAULTS

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS leads(
        tg_id INTEGER PRIMARY KEY, chat_id INTEGER, username TEXT,
        scenario TEXT, step INTEGER DEFAULT 0, waiting INTEGER DEFAULT 0,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)""",
    """CREATE TABLE IF NOT EXISTS events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, kind TEXT,
        payload TEXT, ts TEXT DEFAULT CURRENT_TIMESTAMP)""",
]


async def init() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        for q in SCHEMA:
            await db.execute(q)
        await db.commit()
    for k, v in DEFAULTS.items():
        if await get_setting(k, None) is None:
            await set_setting(k, v)


async def _q(sql: str, args: tuple = ()) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(sql, args)
        rows = await cur.fetchall()
        await db.commit()
        return rows


async def get_setting(key: str, default: str | None = "") -> str | None:
    rows = await _q("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0][0] if rows else default


async def set_setting(key: str, value: str) -> None:
    await _q("INSERT INTO settings(key,value) VALUES(?,?) "
             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


async def get_json(key: str) -> list:
    return json.loads(await get_setting(key, "[]") or "[]")


async def set_json(key: str, value: list) -> None:
    await set_setting(key, json.dumps(value, ensure_ascii=False))


async def start_lead(tg_id: int, chat_id: int, username: str, scenario: str) -> None:
    await _q("INSERT INTO leads(tg_id,chat_id,username,scenario,step,waiting) "
             "VALUES(?,?,?,?,0,0) ON CONFLICT(tg_id) DO UPDATE SET chat_id=excluded.chat_id,"
             "scenario=excluded.
scenario,step=0,waiting=0",
             (tg_id, chat_id, username or "", scenario))


async def get_lead(tg_id: int):
    rows = await _q("SELECT tg_id,chat_id,username,scenario,step,waiting "
                    "FROM leads WHERE tg_id=?", (tg_id,))
    return rows[0] if rows else None


async def set_step(tg_id: int, step: int) -> None:
    await _q("UPDATE leads SET step=? WHERE tg_id=?", (step, tg_id))


async def set_waiting(tg_id: int, flag: int) -> None:
    await _q("UPDATE leads SET waiting=? WHERE tg_id=?", (flag, tg_id))


async def add_event(tg_id: int, kind: str, payload: str = "") -> None:
    await _q("INSERT INTO events(tg_id,kind,payload) VALUES(?,?,?)", (tg_id, kind, payload))


async def stats() -> tuple[int, int]:
    return ((await _q("SELECT COUNT(*) FROM leads"))[0][0],
            (await _q("SELECT COUNT(*) FROM events WHERE kind='start'"))[0][0])
