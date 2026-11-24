from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import Message

from bot import db, engine

router = Router()


@router.message(Command("start"))
async def start(m: Message, command: CommandObject) -> None:
    sid = (command.args or await db.get_setting("default_scenario") or "").strip()
    if not sid:
        await m.answer("Бот не настроен.")
        return
    err = await engine.run(m.bot, m.chat.id, m.from_user.id, m.from_user.username, sid)
    if err:
        await m.answer(err)


@router.message(Command("cancel"), StateFilter("*"))
async def cancel(m: Message, state) -> None:
    await state.clear()
    await m.answer("Отменено.")


@router.message(StateFilter(None), F.text)
async def resume(m: Message) -> None:
    await engine.resume(m.bot, m.chat.id, m.from_user.id)
