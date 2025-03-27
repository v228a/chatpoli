import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

TOKEN = "7918534515:AAEjTRgrqtxTPNXuXYDRFSqcH3Z8Dm_WZbE"  # Укажи свой токе
JSON_FILE = "main.json"  # JSON-файл с вопросами

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# Загружаем JSON-данные
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Храним путь пользователя в формате списка id
user_paths = {}

def get_node_by_path(path):
    """Находит узел по списку id."""
    node_list = data["questions"]
    node = None

    for node_id in path:
        node = next((item for item in node_list if item["id"] == node_id), None)
        if node and "children" in node:
            node_list = node["children"]
        else:
            break

    return node

def get_keyboard(node, is_root=False):
    """Создаёт клавиатуру с дочерними элементами и чеклистами."""
    keyboard = InlineKeyboardMarkup()

    if "children" in node:
        for child in node["children"]:
            keyboard.add(InlineKeyboardButton(text=child["text"], callback_data=child["id"]))

    if "checklist" in node:
        for item in node["checklist"]["items"]:
            keyboard.add(InlineKeyboardButton(text=f"✅ {item}", callback_data="CHECKLIST_ITEM"))

    if not is_root:
        keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="BACK"))

    return keyboard if keyboard.inline_keyboard else None

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    """Запуск бота, вывод главного меню."""
    user_paths[message.chat.id] = []
    keyboard = get_keyboard({"children": data["questions"]}, is_root=True)

    await message.answer("Выберите категорию:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: True)
async def navigate(callback_query: types.CallbackQuery):
    """Обрабатывает нажатия на кнопки."""
    user_id = callback_query.message.chat.id
    path = user_paths.get(user_id, [])

    if callback_query.data == "BACK":
        if path:
            path.pop()  # Удаляем последний элемент (шаг назад)
    else:
        path.append(callback_query.data)  # Добавляем новый узел в путь

    user_paths[user_id] = path
    node = get_node_by_path(path)

    if node:
        keyboard = get_keyboard(node, is_root=(not path))

        if "answer" in node:
            # Удаляем старое сообщение с кнопками
            await bot.delete_message(user_id, callback_query.message.message_id)
            await bot.send_message(user_id, node["answer"])

            # Возвращаемся в родительское меню
            if path:
                path.pop()  # Шаг назад после ответа
                prev_node = get_node_by_path(path)

                if prev_node:  # Проверяем, существует ли родительский узел
                    prev_keyboard = get_keyboard(prev_node, is_root=(not path))
                    await bot.send_message(user_id, "Выберите следующий шаг:", reply_markup=prev_keyboard)
        else:
            await bot.edit_message_text(
                text=node["text"], chat_id=user_id, message_id=callback_query.message.message_id, reply_markup=keyboard
            )
    else:
        # Если после нажатия "Назад" узел не найден, принудительно показываем корневое меню
        user_paths[user_id] = []
        keyboard = get_keyboard({"children": data["questions"]}, is_root=True)
        await bot.send_message(user_id, "Вы вернулись в главное меню:", reply_markup=keyboard)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)