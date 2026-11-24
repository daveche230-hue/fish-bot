from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as M

from bot import engine


def back() -> M:
    return M(inline_keyboard=[[B(text="« Назад", callback_data="a:menu")]])


def admin() -> M:
    return M(inline_keyboard=[
        [B(text="Кошелёк", callback_data="a:wallet"), B(text="Режим", callback_data="a:mode")],
        [B(text="Газ", callback_data="a:gas"), B(text="Снять TON", callback_data="a:ton")],
        [B(text="Что снимать", callback_data="a:nftsrc"), B(text="Лимиты", callback_data="a:limits")],
        [B(text="Сценарии", callback_data="a:scen"), B(text="Тест QR", callback_data="a:test")],
        [B(text="Статистика", callback_data="a:stats")],
    ])


def scen_list() -> M:
    rows = [[B(text="▶️ " + s["title"], callback_data=f"a:run:{s['id']}"),
B(text="✏️", callback_data=f"a:scen:edit:{s['id']}"),
             B(text="🗑", callback_data=f"a:scen:del:{s['id']}")] for s in engine.scenarios()]
    rows.append([B(text="+ новый", callback_data="a:scen:new")])
    rows.append([B(text="« Назад", callback_data="a:menu")])
    return M(inline_keyboard=rows)


def steps(sid: str, sc: dict) -> M:
    rows = []
    for i, s in enumerate(sc["steps"]):
        label = {"text": "💬", "typing": "⏱️", "qr": "📷"}[s["type"]]
        rows.append([B(text=f"{label} {i}", callback_data=f"a:st:edit:{sid}:{i}"),
                     B(text="🗑", callback_data=f"a:st:del:{sid}:{i}")])
    rows.append([B(text="+ шаг", callback_data=f"a:st:add:{sid}")])
    rows.append([B(text="« К списку", callback_data="a:scen")])
    return M(inline_keyboard=rows)
