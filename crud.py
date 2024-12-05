# crud

from sqlalchemy.orm import Session
from models import User, Author, Genre, Catalog, Book, Order, OrderItem

def create_user(db: Session, first_name: str, last_name: str, email: str, phone: str, role: str, telegram_id: int = None):
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        role=role,
        idTelegram=telegram_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def promote_to_admin(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = 'admin'
        db.commit()
        db.refresh(user)
    return user

def get_or_create_author(db: Session, author_name: str):
    author = db.query(Author).filter(Author.name.ilike(author_name)).first()
    if not author:
        author = Author(name=author_name)
        db.add(author)
        db.commit()
        db.refresh(author)
    return author

def get_or_create_genre(db: Session, genre_name: str):
    genre = db.query(Genre).filter(Genre.name.ilike(genre_name)).first()
    if not genre:
        genre = Genre(name=genre_name)
        db.add(genre)
        db.commit()
        db.refresh(genre)
    return genre

def get_or_create_catalog(db: Session, catalog_name: str = "Без категории"):
    catalog = db.query(Catalog).filter(Catalog.catalog_name.ilike(catalog_name)).first()
    if not catalog:
        catalog = Catalog(catalog_name=catalog_name, description=f"Каталог для {catalog_name}")
        db.add(catalog)
        db.commit()
        db.refresh(catalog)
    return catalog

def create_or_update_order(db: Session, user_id: int, book_id: int, quantity: int, price_at_time_of_order: float):
    order = db.query(Order).filter(Order.user_id == user_id, Order.status == 'active').first()
    if not order:
        order = Order(user_id=user_id, status='active', order_date=None, total_price=0.0)
        db.add(order)
        db.commit()
        db.refresh(order)

    order_item = db.query(OrderItem).filter(OrderItem.order_id == order.id, OrderItem.book_id == book_id).first()
    if order_item:
        order_item.quantity += quantity
    else:
        order_item = OrderItem(order_id=order.id, book_id=book_id, quantity=quantity, price_at_time_of_order=price_at_time_of_order)
        db.add(order_item)
    db.commit()
    db.refresh(order)
    return order

def get_book_by_id(db: Session, book_id: int):
    return db.query(Book).filter(Book.id == book_id).first()
