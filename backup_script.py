# backup_script.py

import os
import subprocess
from datetime import datetime, timedelta
import logging
import telebot
from config import (
    API_TOKEN,
    ADMIN_CHAT_IDS,
    DB_USER,
    DB_NAME,
    DB_PASSWORD,
    GOOGLE_DRIVE_FOLDER_ID
)
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

def send_telegram_message(message_text):
    for admin_id in ADMIN_CHAT_IDS:
        try:
            bot.send_message(admin_id, message_text)
            logging.info(f"Уведомление отправлено администратору с ID {admin_id}.")
        except Exception as e:
            logging.error(f"Ошибка отправки уведомления администратору с ID {admin_id}: {e}")

# Настройка логирования
current_directory = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(current_directory, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(BACKUP_DIR, "backup.log"),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_dump():
    """Создать дамп базы данных."""
    # Формирование уникального имени файла
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.sql")

    try:
        env = os.environ.copy()
        env["PGPASSWORD"] = DB_PASSWORD  # Устанавливаем пароль напрямую

        logging.info("Запуск pg_dump...")

        result = subprocess.run(
            [
                r"D:/progi/postgres/bin/pg_dump.exe",  # Предполагается, что pg_dump доступен в PATH
                "-U", DB_USER,
                "-F", "c",  # Формат custom
                "-b",       # Инклюзия больших объектов
                "-v",       # Подробный вывод
                "-f", backup_file,
                DB_NAME,
            ],
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logging.info(f"Дамп {backup_file} успешно создан!\n{result.stdout}")
        send_telegram_message(f"Дамп {backup_file} успешно создан!")
        return backup_file
    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при создании дампа: {e.stderr}")
        send_telegram_message(f"Ошибка при создании дампа: {e.stderr}")
        raise
    except Exception as e:
        logging.error(f"Неизвестная ошибка при создании дампа: {e}")
        send_telegram_message(f"Неизвестная ошибка при создании дампа: {e}")
        raise

def upload_to_google_drive(file_path, file_name):
    """Загрузить файл на Google Диск в указанную папку."""
    try:
        logging.info(f"Начало загрузки файла {file_name} на Google Диск.")

        # Путь к JSON ключу служебного аккаунта
        service_account_file = os.path.join(current_directory, "service_account.json")

        if not os.path.exists(service_account_file):
            logging.error(f"Файл учетных данных служебного аккаунта не найден: {service_account_file}")
            send_telegram_message(f"Файл учетных данных служебного аккаунта не найден: {service_account_file}")
            return

        # Создание учетных данных
        creds = Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/drive"]
        )

        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': file_name,
            'parents': [GOOGLE_DRIVE_FOLDER_ID]  # ID папки на Google Диске
        }

        media = MediaFileUpload(file_path, resumable=True)

        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        logging.info(f"Файл {file_name} успешно загружен на Google Диск. ID файла: {file.get('id')}")
        send_telegram_message(f"Файл {file_name} успешно загружен на Google Диск.")
    except Exception as e:
        logging.error(f"Ошибка при загрузке файла на Google Диск: {e}")
        send_telegram_message(f"Ошибка при загрузке файла на Google Диск: {e}")
        raise

def cleanup_old_backups(days=30):
    """Удалить резервные копии старше указанного количества дней."""
    cutoff_date = datetime.now() - timedelta(days=days)
    for filename in os.listdir(BACKUP_DIR):
        if filename.startswith("backup_") and filename.endswith(".sql"):
            file_path = os.path.join(BACKUP_DIR, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime < cutoff_date:
                os.remove(file_path)
                logging.info(f"Удален старый файл резервной копии: {file_path}")
                send_telegram_message(f"Удален старый файл резервной копии: {file_path}")

if __name__ == "__main__":
    try:
        # Создание дампа
        backup_file = create_dump()

        # Загрузка дампа на Google Диск
        upload_to_google_drive(backup_file, os.path.basename(backup_file))

        # Очистка старых резервных копий
        cleanup_old_backups(days=30)

    except Exception as e:
        send_telegram_message(f"Произошла ошибка при резервном копировании: {e}")
    finally:
        # Удаление локального файла после загрузки
        if 'backup_file' in locals() and os.path.exists(backup_file):
            try:
                os.remove(backup_file)
                logging.info(f"Локальный файл {backup_file} успешно удален.")
                send_telegram_message(f"Локальный файл {backup_file} успешно удален.")
            except Exception as e:
                logging.error(f"Ошибка при удалении локального файла {backup_file}: {e}")
                send_telegram_message(f"Ошибка при удалении локального файла {backup_file}: {e}")
