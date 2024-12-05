# export_data.py

import pandas as pd
import logging
from sqlalchemy.orm import Session
from models import User, Book, Order, OrderItem
from config import SessionLocal, ADMIN_CHAT_IDS
from datetime import datetime

def export_data(bot, message, export_format='excel', initiated_by=None):
    try:
        db = SessionLocal()
        users = db.query(User).all()
        books = db.query(Book).all()
        orders = db.query(Order).all()
        order_items = db.query(OrderItem).all()

        # Преобразование данных в DataFrame
        users_df = pd.DataFrame([{
            'ID': user.id,
            'Telegram ID': user.idTelegram,
            'Роль': user.role,
            'Имя': user.first_name,
            'Фамилия': user.last_name,
            'Email': user.email,
            'Телефон': user.phone
        } for user in users])

        books_df = pd.DataFrame([{
            'ID': book.id,
            'Название': book.title,
            'Автор': book.author.name,
            'Жанр': book.genre.name,
            'Описание': book.description,
            'Каталог': book.catalog.catalog_name,
            'Цена': book.price
        } for book in books])

        orders_df = pd.DataFrame([{
            'ID': order.id,
            'Пользователь ID': order.user_id,
            'Статус': order.status,
            'Дата заказа': order.order_date,
            'Общая цена': order.total_price
        } for order in orders])

        order_items_df = pd.DataFrame([{
            'ID': item.id,
            'Заказ ID': item.order_id,
            'Книга ID': item.book_id,
            'Количество': item.quantity,
            'Цена на момент заказа': item.price_at_time_of_order
        } for item in order_items])

        # Экспорт данных
        if export_format == 'excel':
            with pd.ExcelWriter('exported_data.xlsx') as writer:
                users_df.to_excel(writer, sheet_name='Пользователи', index=False)
                books_df.to_excel(writer, sheet_name='Книги', index=False)
                orders_df.to_excel(writer, sheet_name='Заказы', index=False)
                order_items_df.to_excel(writer, sheet_name='Элементы заказа', index=False)
            with open('exported_data.xlsx', 'rb') as file:
                bot.send_document(message.chat.id, file)
            logging.info("Данные экспортированы в Excel.")
            # Уведомление администраторов
            initiated_by_text = f"Пользователь: {initiated_by.first_name} {initiated_by.last_name} (ID: {initiated_by.idTelegram})" if initiated_by else "Неизвестный пользователь"
            admin_info = f"Экспорт данных выполнен.\nФормат: Excel\nИнициатор: {initiated_by_text}\nВремя: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            for admin_id in ADMIN_CHAT_IDS:
                bot.send_message(admin_id, admin_info)
        elif export_format == 'csv':
            users_df.to_csv('users.csv', index=False)
            books_df.to_csv('books.csv', index=False)
            orders_df.to_csv('orders.csv', index=False)
            order_items_df.to_csv('order_items.csv', index=False)
            with open('users.csv', 'rb') as file:
                bot.send_document(message.chat.id, file)
            with open('books.csv', 'rb') as file:
                bot.send_document(message.chat.id, file)
            with open('orders.csv', 'rb') as file:
                bot.send_document(message.chat.id, file)
            with open('order_items.csv', 'rb') as file:
                bot.send_document(message.chat.id, file)
            logging.info("Данные экспортированы в CSV.")
            # Уведомление администраторов
            initiated_by_text = f"Пользователь: {initiated_by.first_name} {initiated_by.last_name} (ID: {initiated_by.idTelegram})" if initiated_by else "Неизвестный пользователь"
            admin_info = f"Экспорт данных выполнен.\nФормат: CSV\nИнициатор: {initiated_by_text}\nВремя: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            for admin_id in ADMIN_CHAT_IDS:
                bot.send_message(admin_id, admin_info)
        else:
            bot.reply_to(message, "Неподдерживаемый формат экспорта.")
            logging.warning(f"Попытка экспорта в неподдерживаемый формат: {export_format}")
    except Exception as e:
        error_message = f"Произошла ошибка при экспорте данных: {str(e)}"
        if len(error_message) > 200:
            error_message = error_message[:200] + "..."
        bot.reply_to(message, error_message)
        logging.error(f"Error exporting data: {e}")
    finally:
        db.close()
