import logging 
import sqlite3
import time

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import Message

from config import TOKEN
from config import ADMIN
from messages import MESSAGES
import keyboards as kb
from keyboards import kbs
from keyboards import krg
from filter_admin import IsAdminFilter

logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)
banned_users = set()

# Создаем базу данных для панели админестратора
conn = sqlite3.connect('db')
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users(user_id INTEGER, block INTEGER);""")
conn.commit()

# Создаем базу данных для регистрации пользователей
db = sqlite3.connect('server.db')
sql = db.cursor()
sql.execute("""CREATE TABLE IF NOT EXISTS pols(
    login TEXT,
    password TEXT
)""")

db.commit()


class dialog(StatesGroup):
    spam = State()
    blacklist = State()
    whitelist = State()


dp.filters_factory.bind(IsAdminFilter)

dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def start(message: Message):
    curs = conn.cursor()
    curs.execute(f"SELECT block FROM users WHERE user_id = {message.chat.id}")
    result = curs.fetchone()
    if message.from_user.id == ADMIN:
        await message.answer('Добро пожаловать White prince', reply_markup=kbs)
    else:
        if result is None:
            text = f"Здравствуйте {message.from_user.full_name}👋\n"
            await message.answer(text=text)
            await message.reply(MESSAGES['start'], reply_markup=kb.grt_kb2, reply=False)
            curs = conn.cursor()
            curs.execute(f'''SELECT * FROM users WHERE (user_id="{message.from_user.id}")''')
            entry = curs.fetchone()
            if entry is None:
                curs.execute(f'''INSERT INTO users VALUES ('{message.from_user.id}', '0')''')
                conn.commit()
            else:
                await message.answer('Вы были заблокированы!')
 

@dp.message_handler(commands=['help'])
# Команда помощь
async def process_help_command(message: types.Message):
    await message.reply(MESSAGES['help'], reply=False)


@dp.message_handler(commands="sys")
# Регистрация в аккаунт
async def reg_command(message: types.Message):
    await message.answer('Выберите ваше действие', reply_markup=krg)


@dp.message_handler(commands=['fm'])
# Функция вызова быстрого сообщения, позволяет пользователю быстро выдовать стандартные фразы
async def process_fm_command(message: types.Message):
    await message.answer('Функция быстрых фраз', reply_markup=kb.markup3)


@dp.message_handler(content_types=['text'], text='Рассылка')
async def spam(message: Message):
    if message.from_user.id == ADMIN:
        await dialog.spam.set()
        await message.answer('Что нужно разослать?')


@dp.message_handler(state=dialog.spam)  # Функция рассылки
async def start_spam(message: Message, state: FSMContext):
    if message.text == 'Отмена':
        await message.answer('Главное меню', reply_markup=kbs)
        await state.finish()
    else:
        curs = conn.cursor()
        curs.execute(f'''SELECT user_id FROM users''')
        spam_base = curs.fetchall()
        for z in range(len(spam_base)):
            await bot.send_message(spam_base[z][0], message.text)
            await message.answer('Рассылка завершена', reply_markup=kbs)
            await state.finish()


@dp.message_handler(content_types=['text'], text='Добавить в Blacklist')
async def handler(message: types.Message, state: FSMContext):
    if message.chat.id == ADMIN:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.InlineKeyboardButton(text="Назад"))
        await message.answer('Введите id пользователя, которого нужно заблокировать.\n'
                             'Для отмены нажмите кнопку ниже', reply_markup=keyboard)
        await dialog.blacklist.set()


@dp.message_handler(state=dialog.blacklist)
async def proces(message: types.Message, state: FSMContext):
    if message.text == 'Назад':
        await message.answer('Отмена! Возвращаю назад.', reply_markup=kbs)
        await state.finish()
    else:
        if message.text.isdigit():
            curs = conn.cursor()
            curs.execute(f"SELECT block FROM users WHERE user_id = {message.text}")
            result = curs.fetchall()
            if len(result) == 0:
                await message.answer('Такой пользователь не найден в базе данных.', reply_markup=kbs)
                await state.finish()
            else:
                a = result[0]
                idt = a[0]
                if idt == 0:
                    curs.execute(f"UPDATE users SET block = 1 WHERE user_id = {message.text}")
                    conn.commit()
                    await message.answer('Пользователь успешно добавлен в ЧС.', reply_markup=kbs)
                    await state.finish()
                    await bot.send_message(message.text, 'Ты был забанен Администрацией')
                else:
                    await message.answer('Данный пользователь уже получил бан', reply_markup=kbs)
                    await state.finish()
        else:
            await message.answer('Ты вводишь буквы...\n\nВведи ID')


@dp.message_handler(content_types=['text'], text='Убрать из Blacklist')
async def hfandler(message: types.Message, state: FSMContext):
    curs = conn.cursor()
    curs.execute(f"SELECT block FROM users WHERE user_id = {message.chat.id}")
    result = curs.fetchone()
    if result is None:
        if message.chat.id == ADMIN:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(types.InlineKeyboardButton(text="Назад"))
            await message.answer('Введите id пользователя, которого нужно разблокировать.\n'
                                 'Для отмены нажмите кнопку ниже', reply_markup=keyboard)
            await dialog.whitelist.set()


@dp.message_handler(state=dialog.whitelist)
async def proc(message: types.Message, state: FSMContext):
    if message.text == 'Отмена':
        await message.answer('Отмена! Возвращаю назад.', reply_markup=kbs)
        await state.finish()
    else:
        if message.text.isdigit():
            curs = conn.cursor()
            curs.execute(f"SELECT block FROM users WHERE user_id = {message.text}")
            result = curs.fetchall()
            conn.commit()
            if len(result) == 0:
                await message.answer('Такой пользователь не найден в базе данных.', reply_markup=kbs)
                await state.finish()
            else:
                a = result[0]
                idt = a[0]
                if idt == 1:
                    curs = conn.cursor()
                    curs.execute(f"UPDATE users SET block = 0 WHERE user_id = {message.text}")
                    conn.commit()
                    await message.answer('Пользователь успешно разбанен.', reply_markup=kbs)
                    await state.finish()
                    await bot.send_message(message.text, 'Вы были разблокированы администрацией.')
                else:
                    await message.answer('Данный пользователь не получал бан.', reply_markup=kbs)
                    await state.finish()
        else:
            await message.answer('Вы вводите текст\nВведи ID')


@dp.message_handler(content_types=['text'], text='Статистика')  # Статистика по участникам бота
async def handler(message: types.Message, state: FSMContext):
    curs = conn.cursor()
    curs.execute('''select * from users''')
    results = curs.fetchall()
    await message.answer(f'Людей которые когда либо заходили в бота: {len(results)}')


@dp.message_handler(content_types=['text'], text='Sing up')
async def sing_up(message: types.Message, state: FSMContext):
    await message.answer('Для возвращения напишите: Отмена')
    if message.text == 'Отмена':
        await message.answer('Отмена! Возвращаю назад.', reply_markup=krg)
        await state.finish()
    if message.text != 'Отмена':
        await message.answer('Введите Login: ')
        time.sleep(15)
        sql.execute(f"SELECT login FROM pols WHERE login = '{message.text}'")
        await message.answer('Такой логин уже зарегестрирован')
    else:
        sql.execute(f"SELECT login FROM pols WHERE login = '{message.text}'")
        login = message.text
        password = 0000
        sql.execute(f"INSERT INTO pols VALUES (?, ?)", (login, password))
        db.commit()
        await message.answer('Готово')
        if password == 0000:
            await message.answer('Введите Password: ')
            time.sleep(15)
            password = message.text
            sql.execute(f"SELECT login FROM pols WHERE password = '{message.text}'")
            sql.execute(f"INSERT INTO pols VALUES (?, ?)", (login, password))
            db.commit()
            await message.answer('Вы зарегестрированны')


@dp.message_handler(content_types=['text'], text='Log in')
async def log_in(message: types.Message, state: FSMContext):
    await message.answer('Для возвращения напишите: Отмена')
    if message.text == 'Отмена':
        await message.answer('Отмена! Возвращаю назад.', reply_markup=krg)
        await state.finish()
    elif message.text != 'Отмена':
        await message.answer('Введите Логин')
        time.sleep(15)
        sql.execute(f"SELECT login FROM pols WHERE login = '{message.text}'")
        await message.answer('Введите пароль')
        sql.execute(f"SELECT password FROM pols WHERE password = '{message.text}'")
        time.sleep(15)
        await message.answer('Вы вошли в систему')
    else:
        await message.answer('Такого пользователя не существует')


@dp.message_handler(commands=["boom"])  # Взрывное сообщение
async def boom(message: types.Message):
    time.sleep(3)
    await message.delete()

    
@dp.message_handler()  # Фильтор плохих слова
async def filter_msg(message: types.Message):
    if message.text in MESSAGES['badwords']:
        await message.delete()


async def shutdown(dispatcher: Dispatcher):
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()

# полинг
if __name__ == '__main__':
    executor.start_polling(dp, on_shutdown=shutdown)
