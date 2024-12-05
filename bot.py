# bot.py

import os
import subprocess
import sys
import math
import telebot
from telebot import types
import logging
from datetime import datetime
from crud import (
    create_user,
    promote_to_admin,
    get_or_create_author,
    get_or_create_genre,
    get_or_create_catalog,
    create_or_update_order,
    get_book_by_id
)
from models import *
from config import SessionLocal, API_TOKEN, ADMIN_CHAT_IDS, GOOGLE_DRIVE_FOLDER_ID, OAUTH_TOKEN
from decorators import admin_only
from export_data import export_data  # Импортируем функцию export_data
from scraper import scrape_books
import threading

# Очистка лог-файла при запуске
with open('bot.log', 'w') as log_file:
    pass

bot = telebot.TeleBot(API_TOKEN)

# Настроим логирование
logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# Валидация email
def is_valid_email(email):
    import re
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email)


# Валидация телефона
def is_valid_phone(phone):
    # Простая проверка: телефон должен состоять из 10 цифр
    return phone.isdigit() and len(phone) == 10


# Функция для создания главного меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_view_books = types.KeyboardButton("📚 Просмотр книг")
    btn_view_cart = types.KeyboardButton("🛒 Корзина")
    btn_checkout = types.KeyboardButton("✅ Оформить заказ")
    btn_search_category = types.KeyboardButton("🔍 Поиск по категории")
    btn_help = types.KeyboardButton("ℹ️ Помощь")
    markup.add(btn_view_books, btn_view_cart)
    markup.add(btn_checkout)
    markup.add(btn_search_category)
    markup.add(btn_help)
    return markup


# Функция для создания административного меню
def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add_user = types.KeyboardButton("➕ Добавить пользователя")
    btn_promote_user = types.KeyboardButton("⬆️ Повысить пользователя")
    btn_view_books = types.KeyboardButton("📚 Просмотр книг")
    btn_view_cart = types.KeyboardButton("🛒 Корзина")
    btn_export_excel = types.KeyboardButton("📤 Экспорт в Excel")
    btn_export_csv = types.KeyboardButton("📤 Экспорт в CSV")
    btn_force_backup = types.KeyboardButton("🔄 Принудительный бэкап")
    btn_scrape = types.KeyboardButton("🔄 Парсить книги")
    btn_search_category = types.KeyboardButton("🔍 Поиск по категории")
    btn_help = types.KeyboardButton("ℹ️ Помощь")
    markup.add(btn_add_user, btn_promote_user)
    markup.add(btn_view_books, btn_view_cart)
    markup.add(btn_export_excel, btn_export_csv)
    markup.add(btn_force_backup, btn_scrape)
    markup.add(btn_search_category)
    markup.add(btn_help)
    return markup


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def cmd_start(message):
    logging.info(f"Получена команда /start от пользователя {message.from_user.id}")
    db = SessionLocal()
    user = db.query(User).filter(User.idTelegram == message.from_user.id).first()

    if not user:
        bot.reply_to(message, "Привет! Похоже, ты новый пользователь. Давай зарегистрируемся.")
        msg = bot.send_message(message.chat.id, "Введите ваше имя:")
        bot.register_next_step_handler(msg, process_first_name)
    else:
        greeting = f"Привет, {user.first_name}! Добро пожаловать обратно."
        if user.role == 'admin':
            bot.reply_to(message, greeting, reply_markup=admin_menu())
            logging.info(f"Пользователь {user.idTelegram} идентифицирован как администратор.")
        else:
            bot.reply_to(message, greeting, reply_markup=main_menu())
            logging.info(f"Пользователь {user.idTelegram} идентифицирован как обычный пользователь.")
    db.close()


# Обработчики для регистрации нового пользователя
def process_first_name(message):
    user_id = message.from_user.id
    first_name = message.text.strip()
    logging.info(f"Получено имя: {first_name} от пользователя {user_id}")
    if not first_name:
        bot.send_message(message.chat.id, "Имя не может быть пустым. Пожалуйста, введите ваше имя:")
        bot.register_next_step_handler(message, process_first_name)
        return
    msg = bot.send_message(message.chat.id, "Введите вашу фамилию:")
    bot.register_next_step_handler(msg, lambda m: process_last_name(m, user_id, first_name))


def process_last_name(message, user_id, first_name):
    last_name = message.text.strip()
    logging.info(f"Получена фамилия: {last_name} от пользователя {user_id}")
    if not last_name:
        bot.send_message(message.chat.id, "Фамилия не может быть пустой. Пожалуйста, введите вашу фамилию:")
        bot.register_next_step_handler(message, lambda m: process_last_name(m, user_id, first_name))
        return
    msg = bot.send_message(message.chat.id, "Введите вашу почту:")
    bot.register_next_step_handler(msg, lambda m: process_email(m, user_id, first_name, last_name))


def process_email(message, user_id, first_name, last_name):
    email = message.text.strip()
    logging.info(f"Получен email: {email} от пользователя {user_id}")
    if not is_valid_email(email):
        bot.send_message(message.chat.id, "Неверный формат email. Пожалуйста, введите корректный email:")
        bot.register_next_step_handler(message, lambda m: process_email(m, user_id, first_name, last_name))
        return
    msg = bot.send_message(message.chat.id, "Введите ваш телефон (10 цифр):")
    bot.register_next_step_handler(msg, lambda m: process_phone(m, user_id, first_name, last_name, email))


def process_phone(message, user_id, first_name, last_name, email):
    phone = message.text.strip()
    logging.info(f"Получен телефон: {phone} от пользователя {user_id}")
    if not is_valid_phone(phone):
        bot.send_message(message.chat.id, "Неверный формат телефона. Пожалуйста, введите корректный телефон (10 цифр):")
        bot.register_next_step_handler(message, lambda m: process_phone(m, user_id, first_name, last_name, email))
        return
    db = SessionLocal()
    try:
        # Определение роли на основе ADMIN_CHAT_IDS
        role = 'admin' if user_id in ADMIN_CHAT_IDS else 'user'

        # Создаём пользователя с Telegram ID
        new_user = create_user(db, first_name, last_name, email, phone, role=role, telegram_id=user_id)
        if role == 'admin':
            welcome_message = f"Регистрация завершена! Добро пожаловать, {first_name} {last_name}! Вы теперь администратор."
        else:
            welcome_message = f"Регистрация завершена! Добро пожаловать, {first_name} {last_name}!"
        bot.reply_to(message, welcome_message, reply_markup=admin_menu() if role == 'admin' else main_menu())
        logging.info(f"Пользователь {first_name} {last_name} зарегистрирован с Telegram ID {user_id} и ролью {role}")
    except Exception as e:
        # Ограничиваем длину сообщения до 200 символов
        error_message = f"Произошла ошибка при регистрации: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message)
        logging.error(f"Error during user registration: {e}")
    finally:
        db.close()


def initiate_backup(message):
    admin_user = message.from_user
    admin_id = admin_user.id
    admin_name = f"{admin_user.first_name} {admin_user.last_name}" if admin_user.last_name else admin_user.first_name
    logging.info(f"Получена команда принудительного бэкапа от администратора {admin_id} ({admin_name})")

    # Отправляем уведомление инициатору о начале резервного копирования
    bot.send_message(message.chat.id, "Начинаю резервное копирование базы данных. Пожалуйста, подождите...")

    try:
        # Полный путь к вашему скрипту резервного копирования
        backup_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backup_script.py")

        if not os.path.exists(backup_script_path):
            bot.send_message(message.chat.id, f"Скрипт резервного копирования не найден по пути: {backup_script_path}")
            logging.error(f"Backup script not found at: {backup_script_path}")
            return

        # Используем текущий исполняемый файл Python
        python_executable = sys.executable  # Это гарантирует использование того же интерпретатора

        # Запуск скрипта резервного копирования с передачей chat_id
        logging.info(f"Запуск скрипта резервного копирования: {backup_script_path}")
        result = subprocess.run(
            [python_executable, backup_script_path, str(message.chat.id)],
            capture_output=True,
            text=True,
            check=True
        )

        # Обработка вывода скрипта, если необходимо
        output = result.stdout.strip() if result.stdout else "Нет вывода."
        logging.info(f"Backup initiated by admin {admin_id} ({admin_name}) succeeded with output: {output}")

    except subprocess.CalledProcessError as e:
        error_message = f"Ошибка при резервном копировании: {e.stderr if e.stderr else 'Нет ошибки.'}"
        bot.send_message(message.chat.id, error_message)
        logging.error(f"Backup initiated by admin {admin_id} ({admin_name}) failed: {e.stderr}")
    except Exception as e:
        error_message = f"Произошла непредвиденная ошибка: {str(e)}"
        bot.send_message(message.chat.id, error_message)
        logging.error(f"Backup initiated by admin {admin_id} ({admin_name}) encountered an unexpected error: {str(e)}")


# Обработчик команды /goto
@bot.message_handler(commands=['goto'])
def cmd_goto(message):
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Пожалуйста, используйте формат: /goto <номер_страницы>")
        return
    try:
        page = int(args[1])
        if page < 1:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректный номер страницы (целое число, большее 0).")
        return

    logging.info(f"Пользователь {message.from_user.id} запрашивает переход на страницу {page}")
    show_books(message, page)


# Обработчик выбора категории
@bot.message_handler(func=lambda message: is_catalog_exists(message.text))
def handle_category_selection(message):
    category_name = message.text
    logging.info(f"Выбор категории: '{category_name}' пользователем {message.from_user.id}")

    if category_name == "🔙 Назад":
        bot.send_message(message.chat.id, "Возвращаюсь в главное меню.", reply_markup=main_menu())
        return

    db = SessionLocal()
    catalog = db.query(Catalog).filter(Catalog.catalog_name.ilike(category_name.strip())).first()
    db.close()

    if not catalog:
        bot.send_message(message.chat.id, "Категория не найдена. Пожалуйста, выберите другую.",
                         reply_markup=main_menu())
        logging.warning(f"Категория '{category_name}' не найдена в базе данных.")
        return

    logging.info(f"Категория найдена: '{catalog.catalog_name}' (ID: {catalog.id})")
    show_books(message, page=1, catalog_id=catalog.id)
    logging.info(f"Пользователь {message.from_user.id} выбрал категорию '{catalog.catalog_name}' для поиска.")


# Обработчик кнопок
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    db = SessionLocal()
    user = db.query(User).filter(User.idTelegram == message.from_user.id).first()
    db.close()

    if message.text == "📚 Просмотр книг":
        show_books(message, page=1)
    elif message.text == "🔍 Поиск по категории":
        show_categories(message)
    elif message.text == "🛒 Корзина":
        show_cart(message)
    elif message.text == "✅ Оформить заказ":
        checkout(message)
    elif message.text == "ℹ️ Помощь":
        show_help(message)
    elif message.text == "➕ Добавить пользователя" and user and user.role == 'admin':
        # Начинаем процесс добавления пользователя
        bot.send_message(message.chat.id, "Введите имя нового пользователя:")
        bot.register_next_step_handler(message, process_new_user_first_name)
    elif message.text == "⬆️ Повысить пользователя" and user and user.role == 'admin':
        # Начинаем процесс повышения пользователя
        bot.send_message(message.chat.id, "Введите ID пользователя для повышения:")
        bot.register_next_step_handler(message, process_promote_user)
    elif message.text == "📤 Экспорт в Excel" and user and user.role == 'admin':
        export_data(bot, message, export_format='excel', initiated_by=user)
    elif message.text == "📤 Экспорт в CSV" and user and user.role == 'admin':
        export_data(bot, message, export_format='csv', initiated_by=user)
    elif message.text == "🔄 Принудительный бэкап" and user and user.role == 'admin':
        # Инициируем резервное копирование
        initiate_backup(message)
    elif message.text == "🔄 Парсить книги" and user and user.role == 'admin':
        # Отправляем команду /scrape
        bot.send_message(message.chat.id, "Начинаю парсинг книг...", reply_markup=admin_menu())
        cmd_scrape(message)
    elif message.text == "🔙 Назад":
        # Обработка кнопки "Назад"
        if user and user.role == 'admin':
            bot.send_message(message.chat.id, "Вы вернулись в административное меню.", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu())
    else:
        bot.reply_to(message, "Неизвестная команда. Пожалуйста, используйте кнопки меню.", reply_markup=main_menu())


def show_categories(message):
    db = SessionLocal()
    catalogs = db.query(Catalog).order_by(Catalog.catalog_name).all()
    db.close()

    if not catalogs:
        bot.send_message(message.chat.id, "Категории не найдены.", reply_markup=main_menu())
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for catalog in catalogs:
        markup.add(catalog.catalog_name)
    markup.add("🔙 Назад")

    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)
    logging.info(f"Пользователь {message.from_user.id} начал поиск по категории.")


def is_catalog_exists(name: str) -> bool:
    db = SessionLocal()
    name_clean = name.strip()
    catalog = db.query(Catalog).filter(Catalog.catalog_name.ilike(name_clean)).first()
    db.close()
    exists = bool(catalog)
    logging.info(f"Проверка существования категории '{name_clean}': {'найдена' if exists else 'не найдена'}")
    return exists


def show_books(message, page=1, catalog_id=None, user_id=None):
    try:
        BOOKS_PER_PAGE = 6
        db = SessionLocal()
        if user_id is None:
            user_id = message.from_user.id
        logging.info(f"show_books called for user ID: {user_id}, page: {page}, catalog_id: {catalog_id}")

        user = db.query(User).filter(User.idTelegram == user_id).first()
        if not user:
            logging.warning(f"User with Telegram ID {user_id} not found.")
            bot.send_message(message.chat.id, "Пользователь не найден. Пожалуйста, зарегистрируйтесь.",
                             reply_markup=main_menu())
            db.close()
            return
        else:
            logging.info(f"User found: {user.first_name} {user.last_name}")

        query = db.query(Book).order_by(Book.id)

        if catalog_id:
            query = query.filter(Book.catalog_id == catalog_id)
            logging.info(f"Фильтрация книг по catalog_id: {catalog_id}")

        total_books = query.count()
        logging.info(f"Total books: {total_books}, requested page: {page}")

        if total_books == 0:
            if catalog_id:
                bot.send_message(message.chat.id, "В этой категории книг не найдено.",
                                 reply_markup=main_menu())
            else:
                bot.send_message(message.chat.id, "Книги не найдены.",
                                 reply_markup=admin_menu() if user.role == 'admin' else main_menu())
            logging.info("No books found.")
            db.close()
            return

        total_pages = math.ceil(total_books / BOOKS_PER_PAGE)

        # Корректировка номера страницы
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages

        offset_value = (page - 1) * BOOKS_PER_PAGE

        books_on_page = query.offset(offset_value).limit(BOOKS_PER_PAGE).all()

        if books_on_page:
            for book in books_on_page:
                books_text = (
                    f"📖 *{book.title}*\n"
                    f"👤 Автор: {book.author.name}\n"
                    f"📚 Жанр: {book.genre.name}\n"
                    f"📂 Каталог: {book.catalog.catalog_name}\n"
                    f"💲 Цена: {book.price} руб.\n\n"
                )
                markup = book_inline_buttons(book.id)
                bot.send_message(
                    message.chat.id,
                    books_text,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
                logging.info(f"Sent info for book '{book.title}' with add-to-cart button.")

            # Отправляем пагинацию
            pagination_text = f"Страница {page} из {total_pages}."
            pagination_markup = create_pagination_keyboard(page, total_pages, catalog_id)
            bot.send_message(
                message.chat.id,
                pagination_text,
                parse_mode='Markdown',
                reply_markup=pagination_markup
            )
            logging.info(f"Sent pagination for page {page}")
        else:
            if catalog_id:
                bot.send_message(message.chat.id, "В этой категории книг не найдено.",
                                 reply_markup=main_menu())
            else:
                bot.send_message(message.chat.id, "Книги не найдены.",
                                 reply_markup=admin_menu() if user.role == 'admin' else main_menu())
            logging.info(f"No books found on page {page}")

    except Exception as e:
        error_message = f"Произошла ошибка при отображении книг: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message)
        logging.error(f"Error in show_books: {e}")
    finally:
        db.close()


def create_pagination_keyboard(current_page, total_pages, catalog_id=None):
    markup = types.InlineKeyboardMarkup()
    buttons = []

    # Кнопка "Предыдущая"
    if current_page > 1:
        if catalog_id:
            buttons.append(types.InlineKeyboardButton("⬅️ Предыдущая",
                                                      callback_data=f"page:{current_page - 1}:catalog:{catalog_id}"))
        else:
            buttons.append(types.InlineKeyboardButton("⬅️ Предыдущая", callback_data=f"page:{current_page - 1}"))

    # Кнопки номеров страниц (максимум 5 рядом)
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, current_page + 2)

    for page in range(start_page, end_page + 1):
        if page == current_page:
            buttons.append(types.InlineKeyboardButton(f"📄 {page}", callback_data="current"))
        else:
            if catalog_id:
                buttons.append(types.InlineKeyboardButton(str(page), callback_data=f"page:{page}:catalog:{catalog_id}"))
            else:
                buttons.append(types.InlineKeyboardButton(str(page), callback_data=f"page:{page}"))

    # Кнопка "Следующая"
    if current_page < total_pages:
        if catalog_id:
            buttons.append(types.InlineKeyboardButton("Следующая ➡️",
                                                      callback_data=f"page:{current_page + 1}:catalog:{catalog_id}"))
        else:
            buttons.append(types.InlineKeyboardButton("Следующая ➡️", callback_data=f"page:{current_page + 1}"))

    markup.add(*buttons)

    # Добавление кнопки для перехода к конкретной странице для всех пользователей
    btn_jump = types.InlineKeyboardButton("🔢 Перейти к странице", callback_data="jump_page")
    markup.add(btn_jump)

    # Добавление кнопки "Назад" для всех
    btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data="back_main")
    markup.add(btn_back)

    return markup


def book_inline_buttons(book_id):
    markup = types.InlineKeyboardMarkup()
    btn_add_to_cart = types.InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_to_cart:{book_id}")
    markup.add(btn_add_to_cart)
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data.startswith("page:") or call.data == "current":
        handle_pagination(call)
    elif call.data == "jump_page":
        handle_jump_page(call)
    elif call.data.startswith("add_to_cart:"):
        handle_add_to_cart(call)
    elif call.data == "back_main":
        handle_back_main(call)
    else:
        bot.answer_callback_query(call.id, "Неизвестная команда.")
        logging.warning(f"Неизвестный callback_data: {call.data}")


def handle_pagination(call):
    if call.data == "current":
        # Ничего не делаем, пользователь уже на этой странице
        bot.answer_callback_query(call.id, "Вы уже на этой странице.")
        return

    try:
        parts = call.data.split(":")
        if len(parts) == 2:
            _, page_str = parts
            catalog_id = None
        elif len(parts) == 4 and parts[2] == "catalog":
            _, page_str, _, catalog_id_str = parts
            catalog_id = int(catalog_id_str)
        else:
            raise ValueError("Некорректный формат callback_data.")

        page = int(page_str)
        logging.info(f"Пользователь {call.from_user.id} перешёл на страницу {page} категории {catalog_id}")

    except (IndexError, ValueError) as e:
        bot.answer_callback_query(call.id, "Некорректный номер страницы.")
        logging.error(f"Некорректный номер страницы: {call.data}, ошибка: {e}")
        return

    # Отправляем книги на выбранной странице с передачей catalog_id
    show_books(call.message, page, catalog_id=catalog_id, user_id=call.from_user.id)

    bot.answer_callback_query(call.id)


def handle_jump_page(call):
    user_id = call.from_user.id
    msg = bot.send_message(call.message.chat.id, "Введите номер страницы для перехода:")
    bot.register_next_step_handler(msg, lambda m: process_jump_page(m, user_id))
    bot.answer_callback_query(call.id)


def process_jump_page(message, user_id):
    try:
        page = int(message.text.strip())
        if page < 1:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер страницы (целое число, большее 0).")
        return

    logging.info(f"Пользователь {user_id} запрашивает переход на страницу {page}")
    show_books(message, page, user_id=user_id)


def handle_add_to_cart(call):
    try:
        book_id = int(call.data.split(":")[1])
        db = SessionLocal()
        book = db.query(Book).filter(Book.id == book_id).first()
        user = db.query(User).filter(User.idTelegram == call.from_user.id).first()
        if not user:
            bot.answer_callback_query(call.id, "Пользователь не найден. Пожалуйста, зарегистрируйтесь.")
            logging.warning(f"Пользователь с Telegram ID {call.from_user.id} не найден при добавлении в корзину.")
            db.close()
            return
        if not book:
            bot.answer_callback_query(call.id, "Книга не найдена.")
            logging.warning(f"Книга с ID {book_id} не найдена при добавлении в корзину.")
            db.close()
            return
        # Добавляем книгу в заказ (корзину) с использованием User.id
        create_or_update_order(db, user_id=user.id, book_id=book.id, quantity=1, price_at_time_of_order=book.price)
        bot.answer_callback_query(call.id, f"Книга '{book.title}' добавлена в корзину.")
        logging.info(f"Пользователь {user.idTelegram} добавил книгу '{book.title}' в корзину.")
        db.close()
    except Exception as e:
        # Ограничиваем длину сообщения до 200 символов
        error_message = f"Произошла ошибка: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.answer_callback_query(call.id, error_message)
        logging.error(f"Error adding to cart: {e}")


def handle_back_main(call):
    db = SessionLocal()
    user = db.query(User).filter(User.idTelegram == call.from_user.id).first()
    db.close()
    if user:
        if user.role == 'admin':
            bot.send_message(call.message.chat.id, "Вы вернулись в административное меню.", reply_markup=admin_menu())
        else:
            bot.send_message(call.message.chat.id, "Вы вернулись в главное меню.", reply_markup=main_menu())
    else:
        bot.send_message(call.message.chat.id, "Пользователь не найден.", reply_markup=main_menu())
    bot.answer_callback_query(call.id)


def show_cart(message):
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.idTelegram == message.from_user.id).first()
        if not user:
            bot.send_message(message.chat.id, "Пользователь не найден.", reply_markup=main_menu())
            db.close()
            return

        order = db.query(Order).filter(Order.user_id == user.id, Order.status == 'active').first()
        if not order or not order.order_items:
            bot.send_message(message.chat.id, "Ваша корзина пуста.", reply_markup=main_menu())
            db.close()
            return

        messages = []
        total = 0.0
        for item in order.order_items:
            book = db.query(Book).filter(Book.id == item.book_id).first()
            if book:
                message_text = (
                    f"📖 *{book.title}*\n"
                    f"👤 Автор: {book.author.name}\n"
                    f"📚 Жанр: {book.genre.name}\n"
                    f"📂 Каталог: {book.catalog.catalog_name}\n"
                    f"🛒 Количество: {item.quantity}\n\n"
                )
                messages.append(message_text)
                total += item.price_at_time_of_order * item.quantity  # Оставляем сумму для общего итога

        if messages:
            for msg_text in messages:
                bot.send_message(
                    message.chat.id,
                    msg_text,
                    parse_mode='Markdown'
                )
            cart_summary = f"💰 *Итого:* {total} руб."
            markup = create_cart_keyboard()
            bot.send_message(
                message.chat.id,
                cart_summary,
                parse_mode='Markdown',
                reply_markup=markup
            )
            logging.info(f"Пользователь {user.idTelegram} просмотрел корзину, сумма заказа: {total} руб.")
        else:
            bot.send_message(message.chat.id, "Ваша корзина пуста.", reply_markup=main_menu())
            logging.info(f"Книги не найдены в корзине пользователя {user.idTelegram}")
        db.close()
    except Exception as e:
        error_message = f"Произошла ошибка при отображении корзины: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message)
        logging.error(f"Error in show_cart: {e}")


def create_cart_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_checkout = types.KeyboardButton("✅ Оформить заказ")
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn_checkout)
    markup.add(btn_back)
    return markup


def checkout(message):
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.idTelegram == message.from_user.id).first()

        if not user:
            bot.send_message(message.chat.id, "Пользователь не найден. Пожалуйста, зарегистрируйтесь.",
                             reply_markup=main_menu())
            db.close()
            return

        # Ищем активный заказ пользователя
        order = db.query(Order).filter(Order.user_id == user.id, Order.status == 'active').first()

        if not order or not order.order_items:
            bot.send_message(message.chat.id, "Ваша корзина пуста. Добавьте товары перед оформлением заказа.",
                             reply_markup=main_menu())
            db.close()
            return

        # Рассчитываем общую сумму заказа
        total_price = sum(item.price_at_time_of_order * item.quantity for item in order.order_items)
        order.total_price = total_price

        # Обновляем статус заказа на 'completed'
        order.status = 'completed'
        order.order_date = datetime.utcnow()

        db.commit()

        # Отправляем подтверждение пользователю
        bot.send_message(message.chat.id,
                         f"Спасибо за ваш заказ!\nОбщая сумма: {total_price} руб.\nМы свяжемся с вами для уточнения деталей.",
                         reply_markup=main_menu())
        logging.info(f"Пользователь {user.idTelegram} оформил заказ на сумму {total_price} руб.")

    except Exception as e:
        error_message = f"Произошла ошибка при оформлении заказа: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message)
        logging.error(f"Error in checkout: {e}")
    finally:
        db.close()


def show_help(message):
    help_text = """
*Доступные команды:*
📚 *Просмотр книг* - Просмотреть каталог доступных книг
🔍 *Поиск по категории* - Найти книги по выбранной категории
🛒 *Корзина* - Просмотреть и управлять корзиной
✅ *Оформить заказ* - Оформить текущий заказ
ℹ️ *Помощь* - Показать это сообщение

*Административные команды:*
➕ *Добавить пользователя* - Добавить нового пользователя в систему
⬆️ *Повысить пользователя* - Повысить пользователя до администратора
📤 *Экспорт в Excel* - Экспортировать данные в файл Excel
📤 *Экспорт в CSV* - Экспортировать данные в файл CSV
🔄 *Принудительный бэкап* - Инициировать резервное копирование
🔄 *Парсить книги* - Начать парсинг книг
🔙 *Назад* - Вернуться в главное меню
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown', reply_markup=main_menu())
    logging.info(f"Пользователь {message.from_user.id} запросил помощь.")


# Административные обработчики
def process_new_user_first_name(message):
    new_first_name = message.text.strip()
    logging.info(f"Получено имя нового пользователя: {new_first_name}")
    if not new_first_name:
        bot.send_message(message.chat.id, "Имя не может быть пустым. Пожалуйста, введите имя нового пользователя:")
        bot.register_next_step_handler(message, process_new_user_first_name)
        return
    msg = bot.send_message(message.chat.id, "Введите фамилию нового пользователя:")
    bot.register_next_step_handler(msg, lambda m: process_new_user_last_name(m, new_first_name))


def process_new_user_last_name(message, first_name):
    new_last_name = message.text.strip()
    logging.info(f"Получена фамилия нового пользователя: {new_last_name}")
    if not new_last_name:
        bot.send_message(message.chat.id,
                         "Фамилия не может быть пустой. Пожалуйста, введите фамилию нового пользователя:")
        bot.register_next_step_handler(message, lambda m: process_new_user_last_name(m, first_name))
        return
    msg = bot.send_message(message.chat.id, "Введите email нового пользователя:")
    bot.register_next_step_handler(msg, lambda m: process_new_user_email(m, first_name, new_last_name))


def process_new_user_email(message, first_name, last_name):
    email = message.text.strip()
    logging.info(f"Получен email нового пользователя: {email}")
    if not is_valid_email(email):
        bot.send_message(message.chat.id, "Неверный формат email. Пожалуйста, введите корректный email:")
        bot.register_next_step_handler(message, lambda m: process_new_user_email(m, first_name, last_name))
        return
    msg = bot.send_message(message.chat.id, "Введите телефон нового пользователя (10 цифр):")
    bot.register_next_step_handler(msg, lambda m: process_new_user_phone(m, first_name, last_name, email))


def process_new_user_phone(message, first_name, last_name, email):
    phone = message.text.strip()
    logging.info(f"Получен телефон нового пользователя: {phone}")
    if not is_valid_phone(phone):
        bot.send_message(message.chat.id, "Неверный формат телефона. Пожалуйста, введите корректный телефон (10 цифр):")
        bot.register_next_step_handler(message, lambda m: process_new_user_phone(m, first_name, last_name, email))
        return
    msg = bot.send_message(message.chat.id,
                           "Введите Telegram ID нового пользователя (если известен), или оставьте пустым:")
    bot.register_next_step_handler(msg, lambda m: process_new_user_telegram_id(m, first_name, last_name, email, phone))


def process_new_user_telegram_id(message, first_name, last_name, email, phone):
    telegram_id_text = message.text.strip()
    telegram_id = int(telegram_id_text) if telegram_id_text.isdigit() else None
    logging.info(f"Получен Telegram ID нового пользователя: {telegram_id_text}")

    if telegram_id_text and not telegram_id:
        bot.send_message(message.chat.id,
                         "Неверный формат Telegram ID. Пользователь будет создан без привязки Telegram ID.")
        logging.warning(f"Неверный Telegram ID: {telegram_id_text}")

    if telegram_id:
        msg = bot.send_message(message.chat.id, "Введите роль нового пользователя (user/admin):")
        bot.register_next_step_handler(msg, lambda m: process_new_user_role(m, first_name, last_name, email, phone,
                                                                            telegram_id))
    else:
        # Создаём пользователя с Telegram ID=None и ролью 'user'
        db = SessionLocal()
        try:
            new_user = create_user(db, first_name, last_name, email, phone, role="user", telegram_id=None)
            bot.reply_to(message, f"Пользователь {first_name} {last_name} добавлен с ролью 'user'.",
                         reply_markup=admin_menu())
            logging.info(f"Добавлен пользователь {first_name} {last_name} с ролью 'user' без Telegram ID.")
        except Exception as e:
            error_message = f"Произошла ошибка при добавлении пользователя: {str(e)}"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            bot.reply_to(message, error_message, reply_markup=admin_menu())
            logging.error(f"Error adding user: {e}")
        finally:
            db.close()


def process_new_user_role(message, first_name, last_name, email, phone, telegram_id):
    role = message.text.lower()
    logging.info(f"Получена роль нового пользователя: {role}")
    if role not in ['user', 'admin']:
        bot.send_message(message.chat.id, "Неверная роль. Пользователь будет создан с ролью 'user'.")
        role = 'user'
        logging.warning(f"Неверная роль: {role}. Установлена роль 'user'.")
    db = SessionLocal()
    try:
        # Создаём нового пользователя с указанной ролью
        new_user = create_user(db, first_name, last_name, email, phone, role=role, telegram_id=telegram_id)
        bot.reply_to(message, f"Пользователь {first_name} {last_name} добавлен с ролью '{role}'.",
                     reply_markup=admin_menu())
        logging.info(f"Добавлен пользователь {first_name} {last_name} с ролью '{role}' и Telegram ID {telegram_id}.")
    except Exception as e:
        error_message = f"Произошла ошибка при добавлении пользователя: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message, reply_markup=admin_menu())
        logging.error(f"Error adding user: {e}")
    finally:
        db.close()


def process_promote_user(message):
    try:
        user_id = int(message.text.strip())
        logging.info(f"Попытка повысить пользователя с ID {user_id}")
        db = SessionLocal()
        user = promote_to_admin(db, user_id)
        db.close()
        if user:
            bot.reply_to(message, f"Пользователь {user.first_name} {user.last_name} теперь администратор.",
                         reply_markup=admin_menu())
            logging.info(f"Пользователь {user.first_name} {user.last_name} повышен до администратора.")
        else:
            bot.reply_to(message, "Пользователь не найден.", reply_markup=admin_menu())
            logging.warning(f"Пользователь с ID {user_id} не найден при попытке повышения.")
    except ValueError:
        bot.reply_to(message, "Неверный формат user_id. Введите числовой ID пользователя.", reply_markup=admin_menu())
        logging.error(f"Неверный формат user_id: {message.text.strip()}")
    except Exception as e:
        error_message = f"Произошла ошибка при повышении пользователя: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message, reply_markup=admin_menu())
        logging.error(f"Error promoting user: {e}")


@bot.message_handler(commands=['scrape'])
@admin_only(bot)
def cmd_scrape(message):
    admin_user = message.from_user
    admin_id = admin_user.id
    admin_name = f"{admin_user.first_name} {admin_user.last_name}" if admin_user.last_name else admin_user.first_name
    logging.info(f"Получена команда /scrape от администратора {admin_id} ({admin_name})")

    def run_scrape():
        try:
            logging.info("Запуск функции scrape_books()")
            scrape_books()
            scrape_success_message = (
                f"Скрапинг книг завершён.\n"
                f"Выполнил: {admin_name} (ID: {admin_id})\n"
                f"Время: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
            for admin_chat_id in ADMIN_CHAT_IDS:
                bot.send_message(admin_chat_id, scrape_success_message)
            logging.info(f"Скрапинг книг завершён по команде админа {admin_id} ({admin_name}).")
        except Exception as e:
            error_message = f"Произошла ошибка при скрапинге книг: {str(e)}"
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            for admin_chat_id in ADMIN_CHAT_IDS:
                bot.send_message(admin_chat_id, error_message)
            logging.error(f"Error during scraping: {e}")

    threading.Thread(target=run_scrape).start()
    bot.send_message(message.chat.id, "Начинаю скрапинг книг. Пожалуйста, подождите...")
    logging.info(f"Инициирован процесс скрапинга книг по команде админа {admin_id} ({admin_name})")


def handle_pagination(call):
    if call.data == "current":
        # Ничего не делаем, пользователь уже на этой странице
        bot.answer_callback_query(call.id, "Вы уже на этой странице.")
        return

    try:
        parts = call.data.split(":")
        if len(parts) == 2:
            _, page_str = parts
            catalog_id = None
        elif len(parts) == 4 and parts[2] == "catalog":
            _, page_str, _, catalog_id_str = parts
            catalog_id = int(catalog_id_str)
        else:
            raise ValueError("Некорректный формат callback_data.")

        page = int(page_str)
        logging.info(f"Пользователь {call.from_user.id} перешёл на страницу {page} категории {catalog_id}")

    except (IndexError, ValueError) as e:
        bot.answer_callback_query(call.id, "Некорректный номер страницы.")
        logging.error(f"Некорректный номер страницы: {call.data}, ошибка: {e}")
        return

    # Отправляем книги на выбранной странице с передачей catalog_id
    show_books(call.message, page, catalog_id=catalog_id, user_id=call.from_user.id)

    bot.answer_callback_query(call.id)


def process_jump_page(message, user_id):
    try:
        page = int(message.text.strip())
        if page < 1:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректный номер страницы (целое число, большее 0).")
        return

    logging.info(f"Пользователь {user_id} запрашивает переход на страницу {page}")
    show_books(message, page, user_id=user_id)


# Запуск бота
if __name__ == "__main__":
    logging.info("Запуск бота.")
    bot.polling(none_stop=True)
