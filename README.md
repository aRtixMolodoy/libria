# Libria
Файлы кода в master
## Table of Contents

- [Описание](#описание)
- [Особенности](#особенности)
- [Требования](#требования)
- [Установка](#установка)
- [Настройка](#настройка)
- [Запуск](#запуск)
- [Использование](#использование)
  - [Пользовательские команды](#пользовательские-команды)
  - [Административные команды](#административные-команды)
- [Структура проекта](#структура-проекта)
- [Логирование](#логирование)
- [Отладка](#отладка)
- [Выполнил](#выполнил)

## Описание

Telegram Book Store Bot — это бот для Telegram, предназначенный для управления интернет-магазином книг. Бот позволяет пользователям просматривать доступные книги, добавлять их в корзину, оформлять заказы, а администраторам — управлять пользователями, экспортировать данные и выполнять скрапинг книг из внешних источников.

## Особенности

- **Регистрация пользователей**: Новые пользователи могут зарегистрироваться, указав свои данные. Администраторы автоматически назначаются на основе Telegram ID.
- **Просмотр книг**: Пользователи могут просматривать доступные книги с поддержкой пагинации.
- **Поиск по категориям**: Возможность поиска книг по выбранным категориям (каталогам) с поддержкой пагинации.
- **Корзина**: Добавление книг в корзину и управление содержимым корзины.
- **Оформление заказов**: Оформление текущего заказа с расчетом общей суммы.
- **Административные функции**:
  - Добавление новых пользователей.
  - Повышение пользователей до администраторов.
  - Экспорт данных в форматы Excel и CSV.
  - Принудительное резервное копирование базы данных.
  - Скрапинг книг из внешних источников.
- **Логирование**: Все действия бота логируются для мониторинга и отладки.
- **Безопасность**: Только пользователи с административными правами имеют доступ к административным функциям.

## Требования

- Python 3.7+
- PostgreSQL (или другая поддерживаемая СУБД)
- Google API Credentials (для резервного копирования на Google Drive)
- Зависимости, указанные в `requirements.txt`

## Установка

1. **Клонируйте репозиторий:**

   ```bash
   git clone 
   cd https://github.com/aRtixMolodoy/libria.git
2.
```bash python -m venv venv```
```bash source venv/bin/activate```  # Для Unix/Linux
```bash venv\Scripts\activate```     # Для Windows

## Настройка
Переименуйте example.env в .env и заполните:
API_TOKEN=your_telegram_bot_api_token
ADMIN_CHAT_IDS=admin_telegram_id1,admin_telegram_id2
DB_USER=your_db_username
DB_PASSWORD=your_db_password
DB_NAME=your_db_name
DB_HOST=your_db_host
DB_PORT=your_db_port
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
OAUTH_TOKEN=your_google_oauth_token

## Запуск
1. Запустите create_tables.py для создание таблиц в бд.
```bash
python create_tables.py
```
2. Далее запускаем бота
```bash
python bot.pu
```

## Использование
# Пользовательские команды
/start: Начало взаимодействия с ботом. Если пользователь не зарегистрирован, начнётся процесс регистрации.
📚 Просмотр книг: Просмотр доступных книг с поддержкой пагинации.
🔍 Поиск по категории: Поиск книг по выбранным категориям.
🛒 Корзина: Просмотр и управление корзиной.
✅ Оформить заказ: Оформление текущего заказа.
ℹ️ Помощь: Показать доступные команды.
# Административные команды
Доступны только пользователям с ролью admin.

➕ Добавить пользователя: Добавление нового пользователя в систему.
⬆️ Повысить пользователя: Повышение пользователя до администратора.
📤 Экспорт в Excel: Экспорт данных в файл Excel.
📤 Экспорт в CSV: Экспорт данных в файл CSV.
🔄 Принудительный бэкап: Инициирование резервного копирования базы данных.
🔄 Парсить книги: Начало процесса скрапинга книг.
🔍 Поиск по категории: Поиск книг по выбранным категориям.
🔙 Назад: Возврат в главное или административное меню.
## Структура проекта
libria/
├── bot.py
├── scraper.py
├── crud.py
├── models.py
├── config.py
├── decorators.py
├── export_data.py
├── backup_script.py
├── requirements.txt
├── .env
├── README.md
└── bot.log
## Логирование

Все действия бота логируются в файл bot.log для мониторинга и отладки. Логи включают информацию о командах, ошибках и других важных событиях.

## Отладка
Если при использовании бота возникают ошибки, рекомендуется:

  1.Проверить лог-файл bot.log: В нем содержатся подробные сообщения об ошибках и действиях бота.
  2.Убедиться в корректности данных в базе данных: Проверьте, существуют ли категории, книги и пользователи.
  3.Проверить правильность настроек в .env файле: Убедитесь, что все переменные окружения установлены правильно.
  4.Проверить права доступа: Убедитесь, что только администраторы имеют доступ к административным командам.

## Выполнил
Жердев Даниил КБ-221 ИИТУС