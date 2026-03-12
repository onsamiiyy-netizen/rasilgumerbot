import asyncio
import os
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, UserIsBlockedError, InputUserDeactivatedError, PeerFloodError, UsernameNotOccupiedError, UsernameInvalidError
import time

BOT_TOKEN = os.environ["BOT_TOKEN"]
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
ADMIN_IDS = [int(x) for x in os.environ["ADMIN_IDS"].split(",")]
SESSION = os.path.splitext(os.path.basename(__file__))[0]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
main_loop = None


class S(StatesGroup):
    users = State()
    msg = State()
    ok = State()


def yn():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="да"), KeyboardButton(text="нет")]],
        resize_keyboard=True
    )


def do_blast(users, text, chat_id, message_id):
    with TelegramClient(SESSION, API_ID, API_HASH) as tg:
        ok = skip = fail = 0
        for i, u in enumerate(users, 1):
            try:
                tg.send_message(u, text)
                ok += 1
            except FloodWaitError as e:
                time.sleep(e.seconds + 3)
                try:
                    tg.send_message(u, text)
                    ok += 1
                except:
                    fail += 1
            except (UserPrivacyRestrictedError, UserIsBlockedError, InputUserDeactivatedError, UsernameNotOccupiedError, UsernameInvalidError):
                skip += 1
            except PeerFloodError:
                fail += 1
                time.sleep(60)
            except:
                fail += 1

            time.sleep(5)

        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id, f"готово\n\nок: {ok}\nскип: {skip}\nerr: {fail}"),
            main_loop
        )


@dp.message(F.text == "/start")
async def cmd_start(m: Message, state: FSMContext):
    if m.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await m.answer("юзеры (через пробел):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(S.users)


@dp.message(S.users)
async def step_users(m: Message, state: FSMContext):
    users = [u.lstrip("@") for u in m.text.replace(",", " ").split() if u.strip()]
    if not users:
        await m.answer("не понял, ещё раз")
        return
    await state.update_data(users=users)
    await m.answer("текст:")
    await state.set_state(S.msg)


@dp.message(S.msg)
async def step_msg(m: Message, state: FSMContext):
    await state.update_data(text=m.text)
    d = await state.get_data()
    await m.answer(f"{len(d['users'])} юзеров\n\n{d['text']}\n\nотправить?", reply_markup=yn())
    await state.set_state(S.ok)


@dp.message(S.ok, F.text == "да")
async def step_blast(m: Message, state: FSMContext):
    d = await state.get_data()
    users = d["users"]
    text = d["text"]
    await state.clear()
    await m.answer("пошло...", reply_markup=ReplyKeyboardRemove())
    t = threading.Thread(target=do_blast, args=(users, text, m.chat.id, m.message_id), daemon=True)
    t.start()


@dp.message(S.ok, F.text == "нет")
async def step_cancel(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("отмена", reply_markup=ReplyKeyboardRemove())


async def main():
    global main_loop
    main_loop = asyncio.get_event_loop()
    await dp.start_polling(bot)

asyncio.run(main())
