# create_tables.py

from sqlalchemy import create_engine
from models import Base  # Импортируем Base из файла models
from config import DATABASE_URL  # Строка подключения из config

# Создаем движок для подключения к базе данных
engine = create_engine(DATABASE_URL)

# Создаем все таблицы на основе моделей
Base.metadata.create_all(bind=engine)
