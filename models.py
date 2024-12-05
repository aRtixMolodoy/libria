# models.py

from sqlalchemy import Column, BigInteger, Integer, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from config import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    idTelegram = Column(BigInteger, unique=True, nullable=True)  # Изменено с Integer на BigInteger
    role = Column(String, nullable=False, default='user')  # 'user' или 'admin'
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)

    orders = relationship("Order", back_populates="user")

class Author(Base):
    __tablename__ = 'authors'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    books = relationship("Book", back_populates="author")

class Genre(Base):
    __tablename__ = 'genres'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    books = relationship("Book", back_populates="genre")

class Catalog(Base):
    __tablename__ = 'catalogs'

    id = Column(Integer, primary_key=True, index=True)
    catalog_name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)

    books = relationship("Book", back_populates="catalog")

class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey('authors.id'), nullable=False)
    genre_id = Column(Integer, ForeignKey('genres.id'), nullable=False)
    description = Column(Text, nullable=True)
    catalog_id = Column(Integer, ForeignKey('catalogs.id'), nullable=False)
    price = Column(Float, nullable=False)

    author = relationship("Author", back_populates="books")
    genre = relationship("Genre", back_populates="books")
    catalog = relationship("Catalog", back_populates="books")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String, nullable=False, default='active')  # 'active' или 'completed'
    order_date = Column(DateTime, nullable=True)
    total_price = Column(Float, nullable=False, default=0.0)

    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    price_at_time_of_order = Column(Float, nullable=False)

    order = relationship("Order", back_populates="order_items")
    book = relationship("Book")
