import os
import logging
import asyncio
from bots.gpt import get_assistant_response
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from bots.handlers import router
from bots.prompt import CONTINUES_DATA
from bots.state import StateGpt
from bots.db import create_table
from dotenv import load_dotenv
load_dotenv()

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state != StateGpt.greeted.state:
        greeting_message = "Представляйся как Ева, виртуальный ассистент менеджера. Один раз! Сообщи, что рада, что пользователь обратился к нам в компанию! Сообщи, что ты здесь, чтобы помочь вам спланировать идеальную поездку. И поинтересуйся у пользователя - хочет ли он подобрать тур? Не повторяй этот пример, он предназначен только для твоего обучения. Используй его как руководство, но не копируй в ответах."
        response_text = await get_assistant_response(user_id=message.from_user.id, user_message=greeting_message)
        await message.reply(response_text)
        await state.set_state(StateGpt.greeted)  
    else:
        await message.reply(CONTINUES_DATA)
    await state.set_state(StateGpt.waiting_for_query)

async def main():  
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    create_table()
    asyncio.run(main())



