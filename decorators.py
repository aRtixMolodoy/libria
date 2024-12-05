# decorators

from functools import wraps
from telebot import types
from config import SessionLocal
from models import User
import logging

def admin_only(bot):
    def decorator(func):
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.idTelegram == message.from_user.id).first()
                if user and user.role == 'admin':
                    return func(message, *args, **kwargs)
                else:
                    bot.reply_to(message, "У вас нет прав для выполнения этой команды.", reply_markup=types.ReplyKeyboardRemove())
                    logging.warning(f"Пользователь {message.from_user.id} попытался выполнить административную команду без прав.")
            except Exception as e:
                bot.reply_to(message, "Произошла ошибка при проверке прав доступа.")
                logging.error(f"Ошибка в декораторе admin_only: {e}")
            finally:
                db.close()
        return wrapper
    return decorator
