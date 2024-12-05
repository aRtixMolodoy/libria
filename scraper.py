# scraper.py

import requests
import logging
import random
from sqlalchemy.orm import Session
from crud import get_or_create_author, get_or_create_genre, get_or_create_catalog
from models import Book
from config import SessionLocal

def scrape_books():
    logging.info("Начало процесса скрапинга книг.")
    base_url = "https://openlibrary.org/subjects/love.json"
    limit = 100  # Количество книг за запрос
    offset = 0
    total_books = 250  # Общее количество книг

    db = SessionLocal()
    try:
        catalog = get_or_create_catalog(db, catalog_name="Love")  # Пример: все книги с темой "Love" в каталоге "Love"
        logging.info(f"Используется каталог ID: {catalog.id} - {catalog.catalog_name}")

        while True:
            params = {
                'limit': limit,
                'offset': offset
            }
            logging.info(f"Отправка запроса к {base_url} с параметрами {params}")
            response = requests.get(base_url, params=params)
            if response.status_code != 200:
                logging.error(f"Ошибка при запросе данных: {response.status_code}")
                break

            data = response.json()
            books_data = data.get('works', [])
            if not books_data:
                logging.info("Больше книг для парсинга нет.")
                break

            if total_books is None:
                total_books = data.get('work_count', 0)
                logging.info(f"Найдено {total_books} книг.")

            for book in books_data:
                try:
                    title = book.get('title', 'Без названия')
                    authors = book.get('authors', [])
                    author_name = authors[0].get('name', 'Неизвестный автор') if authors else 'Неизвестный автор'
                    description_data = book.get('description', "Описание отсутствует")
                    if isinstance(description_data, dict):
                        description = description_data.get('value', "Описание отсутствует")
                    else:
                        description = description_data

                    # Получаем или создаём автора и жанр
                    author = get_or_create_author(db, author_name)
                    genres = book.get('subject', ['Неизвестный жанр'])
                    genre_name = genres[0] if isinstance(genres, list) and genres else 'Неизвестный жанр'
                    genre = get_or_create_genre(db, genre_name)

                    # Определяем каталог на основе первого предмета
                    subjects = book.get('subject', [])
                    catalog_name = subjects[0] if subjects else "Без категории"
                    catalog = get_or_create_catalog(db, catalog_name=catalog_name)

                    # Проверка на существование книги с таким названием и каталогом
                    existing_book = db.query(Book).filter(
                        Book.title.ilike(f"%{title}%"),
                        Book.catalog_id == catalog.id
                    ).first()

                    if not existing_book:
                        # Устанавливаем случайную цену для книги
                        price = round(random.uniform(100.0, 1000.0), 2)  # Цена в рублях

                        new_book = Book(
                            title=title,
                            author_id=author.id,
                            genre_id=genre.id,
                            description=description,
                            catalog_id=catalog.id,
                            price=price  # Устанавливаем цену
                        )
                        db.add(new_book)
                        db.commit()
                        db.refresh(new_book)
                        logging.info(f"Книга '{title}' добавлена в каталог '{catalog_name}' с ценой {price} руб.")
                    else:
                        logging.info(f"Книга '{title}' уже существует в каталоге '{catalog_name}'.")

                except Exception as e:
                    logging.error(f"Ошибка при обработке книги '{book.get('title', 'Без названия')}': {e}")
                    db.rollback()  # Откат транзакции для текущей книги
                    continue  # Переходим к следующей книге

            offset += limit  # Переходим к следующей странице
            logging.info(f"Переход к следующей странице: offset={offset}")

    except Exception as e:
        logging.error(f"Произошла ошибка в функции scrape_books: {e}")
    finally:
        db.close()
        logging.info("Парсинг книг завершён.")
