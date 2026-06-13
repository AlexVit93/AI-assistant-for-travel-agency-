import logging
import os
import re
import json
from aiogram import Router, F
from aiogram.types import Message
from bots.state import StateGpt
from aiogram.fsm.context import FSMContext
from bots.gpt import get_assistant_response, dialogues
from bots.db import insert_data
from bots.prompt import HEAD_PROMPT, CONTINUES_DATA_CONTACT
from bots.google_sheets import write_to_google_sheets

logging.basicConfig(level=logging.INFO)
DIALOG_JSON_PATH = 'bots/dialog_data.json'
router = Router()

def add_to_json(user_id, user_message, bot_response):
    logging.info("Вызвана функция add_to_json для пользователя %s", user_id)
    if os.path.exists(DIALOG_JSON_PATH):
        try:
            with open(DIALOG_JSON_PATH, 'r') as file:
                data = json.load(file)
            logging.info("Загружен JSON: %s", data)
        except Exception as e:
            logging.error("Ошибка при чтении JSON файла: %s", str(e))
            data = {}
    else:
        logging.info("JSON файл не существует, создаю новый")
        data = {}

    if str(user_id) not in data:
        logging.info("Создан новый ключ для пользователя %s", user_id)
        data[str(user_id)] = []

    data[str(user_id)].append({
        "user_message": user_message,
        "bot_response": bot_response
    })

    try:
        with open(DIALOG_JSON_PATH, 'w') as file:
            json.dump(data, file, indent=4)
        logging.info("Записан обновленный JSON: %s", data)
    except Exception as e:
        logging.error("Ошибка при записи в JSON файл: %s", str(e))

def extract_contact_details(message_text):
    phone_pattern = re.compile(r'(\+?\d[\d\s\-]{7,}\d)')
    name_pattern = re.compile(r'([A-Za-zА-Яа-яёЁ]+(?:\s+[A-Za-zА-Яа-яёЁ]+)*)')
    
    phone_match = phone_pattern.search(message_text)
    name_match = name_pattern.search(message_text)
    
    if phone_match and name_match:
        if phone_match.start() < name_match.start():
            phone_number = phone_match.group(1).strip()
            name = name_match.group(1).strip()
        else:
            name = name_match.group(1).strip()
            phone_number = phone_match.group(1).strip()

        logging.info(f"Извлечены контактные данные: телефон - {phone_number}, имя - {name}")
        return {
            "phone_number": phone_number,
            "name": name
        }
    else:
        logging.info("Не удалось извлечь контактные данные из сообщения.")
        return None

async def extract_trip_details_with_gpt(user_id):
    dialogue_history = dialogues.get(user_id, [])
    messages = [
        {"role": "system", "content": HEAD_PROMPT},
        {"role": "system", "content": "Пожалуйста, извлеки детали поездки из следующего диалога. Верни результат в формате JSON без оборачивания в тройные обратные кавычки со следующими ключами: trip_direction, people_number, travel_dates, budget, customer_wishes, phone_number, name. Пример: { \"trip_direction\": \"Грузия\", \"people_number\": \"2 взрослых\", \"travel_dates\": \"Следующий месяц\", \"budget\": \"до 1000$\", \"customer_wishes\": \"все включено\", \"phone_number\": \"80295901539\", \"name\": \"Джордани\" }"}
    ]
    messages.extend(dialogue_history)
    response_text = await get_assistant_response(user_id=user_id, user_message="", custom_messages=messages)

    response_text = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
    response_text = re.sub(r'```$', '', response_text.strip())

    logging.info("Ответ GPT для извлечения деталей поездки: %s", response_text)

    try:
        trip_details = json.loads(response_text)
    except json.JSONDecodeError as e:
        logging.error("Не удалось распарсить trip_details из ответа GPT: %s", str(e))
        trip_details = None
    return trip_details


@router.message(StateGpt.text)
async def state_answer(message: Message):
    await message.reply("Пожалуйста, дождитесь ответа!")

@router.message(F.text & ~F.text.startswith('/'))
async def gpt_work(message: Message, state: FSMContext):
    await state.set_state(StateGpt.text)
    answer = await message.reply("Пишем ответ...")
    user_id = message.from_user.id
    user_message = message.text
    response = await get_assistant_response(user_id=user_id, user_message=user_message)
    add_to_json(user_id, user_message, response)
    await answer.edit_text(response)

    contact_details = extract_contact_details(user_message)
    if contact_details:
        logging.info("Данные контакта получены: %s", contact_details)
        trip_details = await extract_trip_details_with_gpt(user_id)
        if trip_details:
            await extract_data_from_json_and_save(user_id, contact_details, trip_details)
            await state.clear()
            await message.reply("Разговор завершен. Если у вас остались вопросы, не стесняйтесь обращаться!")
            logging.info("Разговор завершен и состояние очищено")
            return
        else:
            await message.reply("Не удалось извлечь детали поездки. Пожалуйста, предоставьте информацию заново.")
            return

    await state.clear()

@router.message(StateGpt.waiting_for_query)
async def process_query(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_input = message.text.split(',')

    trip_direction = user_input[0].strip() if len(user_input) > 0 else None
    people_number = user_input[1].strip() if len(user_input) > 1 else None
    travel_dates = user_input[2].strip() if len(user_input) > 2 else None
    budget = user_input[3].strip() if len(user_input) > 3 else None
    customer_wishes = user_input[4].strip() if len(user_input) > 4 else None

    trip_details = {
        "trip_direction": trip_direction,
        "people_number": people_number,
        "travel_dates": travel_dates,
        "budget": budget,
        "customer_wishes": customer_wishes
    }

    await state.update_data(trip_details=trip_details)

    add_to_json(user_id, message.text, "Основная информация о поездке получена")

    await message.reply(CONTINUES_DATA_CONTACT)
    await state.set_state(StateGpt.getting_contact)

@router.message(StateGpt.getting_contact)
async def get_contact_info(message: Message, state: FSMContext):
    user_message = message.text.strip()
    
    logging.info("Вызвана функция get_contact_info")
    
    if "," in user_message and any(char.isdigit() for char in user_message):
        contact_parts = user_message.split(',')
        if len(contact_parts) == 2:
            contact_details = {
                "phone_number": contact_parts[0].strip(),
                "name": contact_parts[1].strip()
            }

            logging.info("Данные контакта получены: %s", contact_details)

            state_data = await state.get_data()
            trip_details = state_data.get('trip_details')
            logging.info("Полученные данные о поездке: %s", trip_details)

            await extract_data_from_json_and_save(message.from_user.id, contact_details, trip_details)

            await state.finish()
            await message.answer("Разговор завершен. Если у вас остались вопросы, не стесняйтесь обращаться!")
        else:
            logging.info("Введены некорректные данные контакта")
            await message.reply("Пожалуйста, введите корректный номер телефона и имя.")
    else:
        logging.info("Пользователь не ввел номер телефона и имя корректно")
        await message.reply("Пожалуйста, введите корректный номер телефона и имя.")

async def extract_data_from_json_and_save(user_id, contact_details, trip_details):
    if os.path.exists(DIALOG_JSON_PATH):
        try:
            with open(DIALOG_JSON_PATH, 'r') as file:
                data = json.load(file)
        except Exception as e:
            logging.error("Ошибка при чтении JSON файла: %s", str(e))
            data = {}
    else:
        data = {}

    user_data = data.get(str(user_id), [])

    if trip_details and contact_details:
        user_data.append({
            "trip_details": trip_details,
            "contact_details": contact_details
        })
        data[str(user_id)] = user_data

        try:
            with open(DIALOG_JSON_PATH, 'w') as file:
                json.dump(data, file, indent=4)
            logging.info("Данные успешно сохранены в JSON и БД")
        except Exception as e:
            logging.error("Ошибка при записи данных в JSON файл: %s", str(e))
        
        insert_data(trip_details, contact_details)
        write_to_google_sheets(contact_details["phone_number"], contact_details["name"], trip_details)
    else:
        logging.error("Недостаточно данных для сохранения")

