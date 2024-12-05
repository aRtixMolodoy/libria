# config.py

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Загрузка переменных окружения из .env
load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')

# Список Telegram Chat IDs администраторов
ADMIN_CHAT_IDS = [
    int(os.getenv('ADMIN_TELEGRAM_ID')),
    # Добавьте дополнительные Chat ID при необходимости, без дублирования
]

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
OAUTH_TOKEN = os.getenv('OAUTH_TOKEN')

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Добавление Base для декларативных моделей
Base = declarative_base()
