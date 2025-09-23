"""
models.py

This module defines the database models for the photo sorting application.

Models:
- User: Represents an application user with authentication credentials.
- Photo: Represents an uploaded photo owned by a user.
- Category: Represents a user-defined category for sorting photos.
- PhotoCategory: many-to-many relation between photos and categories

Relationships:
- Each User can own multiple Photos (one-to-many).
- Each Photo belongs to a single User (many-to-one).
- Each Category is created by a single User (many-to-one).
- Photos can belong to multiple Categories,
and Categories can contain multiple Photos (many-to-many).
"""


from datetime import date

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# Association table for many-to-many relationship between Photo and Category
photo_category = db.Table(
    'photo_category',
    db.Column('photo_id', db.Integer, db.ForeignKey('photos.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)


class User(db.Model, UserMixin):
    """
    Represents a user in the application.

    Attributes:
        id (int): Unique identifier for the user.
        username (str): Unique username of the user.
        email (str): Unique email address of the user.
        password_hash (str): Hashed password for authentication.
        photos (list[Photo]): Photos uploaded by the user
            (one-to-many relationship).
        categories (list[Category]): Categories created by the user
            (one-to-many relationship).
    """
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    photos = db.relationship(
        'Photo',
        backref='owner',
        lazy=True,
        cascade="all, delete-orphan"
    )
    categories = db.relationship(
        'Category',
        back_populates='owner',
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Photo(db.Model):
    """
    Represents a user's photo.

    Attributes:
        id (int): Unique identifier for the photo.
        user_id (int): Foreign key linking the photo to its owner (User).
        unique_filename (str): Unique filename used for storage.
        original_filename (str): Original filename of the uploaded photo.
        uploaded_at (datetime): Date the photo was uploaded.
        description (str, optional): AI-generated description of the photo.
        categories (list[Category]): Categories associated with the photo
            (many-to-many relationship).
    """
    __tablename__ = 'photos'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    unique_filename = db.Column(db.String(200), unique=True, nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    uploaded_at = db.Column(db.Date, default=date.today, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    categories = db.relationship(
        'Category',
        secondary=photo_category,
        backref=db.backref('photos', lazy='dynamic')
    )

    def __repr__(self):
        return f"<Photo {self.unique_filename}>"


class Category(db.Model):
    """
    Represents a user-defined category for organizing photos.

    Attributes:
        id (int): Unique identifier for the category.
        user_id (int): Foreign key linking the category to its creator (User).
        name (str): Name of the category.
        owner (User): The user who created the category (many-to-one relationship).
    """
    __tablename__ = 'categories'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    owner = db.relationship(
        'User',
        back_populates='categories'
    )

    def __repr__(self):
        return f"<Category {self.name}>"
