"""
data_manager.py

This module provides the `DataManager` class for interacting with
the application's database. It handles all operations related to
users, categories and photos, including:

- Creating, retrieving, updating, and deleting users.
- Creating, retrieving, updating, and deleting photos.
- Creating, retrieving, updating, and deleting categories.
- Fetching all photos for a specific user.

The class abstracts away direct SQLAlchemy queries to simplify
database interactions for the rest of the application.
"""


from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from models import db, User, Photo, Category


class DataManager:
    """
    Encapsulates all database operations related to users, categories, and photos.
    """
    def __init__(self, app=None):
        """
        Initialize the DataManager with an optional Flask app.
        """
        if app:
            db.init_app(app)

    # ------------------ User operations ------------------ #

    def create_user(self, username, email, password_hash):
        """
        Create a new user in the database.

        Args:
            username (str): The name of the user to create.
            email (str): The email of the user to create.
            password_hash (str): The already hashed password of the user to create.
        """
        try:
            user = User(username=username, email=email, password_hash=password_hash)
            db.session.add(user)
            db.session.commit()
            return user
        except IntegrityError:
            db.session.rollback()
            return None  # User with same username/email exists
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def get_user_by_id(self, user_id):
        """
        Get a single user by their ID.

        Args:
            user_id (int): ID of the user.

        Returns:
            Optional[User]: The user object if found, else None.
        """
        return User.query.get(user_id)

    def get_user_by_username(self, username):
        """
        Get a single user by their username.

        Args:
            username (str): username of the user.

        Returns:
            Optional[User]: The user object if found, else None.
        """
        return User.query.filter_by(username=username).first()

    def get_user_by_email(self, email):
        """
        Get a single user by their email address.

        Args:
            email (str): email address of the user.

        Returns:
            Optional[User]: The user object if found, else None.
        """
        return User.query.filter_by(email=email).first()

    def update_user(self, user, **kwargs):
        """
        Update fields of an existing user from the database.

        Args:
            user: The user object to update.
            **kwargs: Key-value pairs of fields to update.
        """
        try:
            for key, value in kwargs.items():
                setattr(user, key, value)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def delete_user(self, user):
        """
        Delete a user.

        Args:
            user: the user to delete.
        """
        try:
            db.session.delete(user)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    # ------------------ Photo operations ------------------ #

    def add_photo(self, user, unique_filename, original_filename):
        """
        Add a new photo to the database.

        Args:
            user (User): The owner of the photo.
            unique_filename (str): Unique filename generated for storage.
            original_filename (str): Original filename of the uploaded file.
        """
        try:
            photo = Photo(
                user_id=user.id,
                unique_filename=unique_filename,
                original_filename=original_filename
            )
            db.session.add(photo)
            db.session.commit()
            return photo
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def get_photo_by_id(self, photo_id):
        """
        Get a photo by its ID.

        Args:
            photo_id (int): ID of the photo.

        Returns:
            Optional[Photo]: The photo if found, else None.
        """
        return Photo.query.get(photo_id)

    def get_photos_by_user(self, user_id):
        """
        Get all photos for a specific user.

        Args:
            user_id (int): ID of the user.

        Returns:
            List[Photo]: Photos belonging to the user.
        """
        return Photo.query.filter_by(user_id=user_id).all()

    def get_photos_all_users(self):
        """
        Get all photos for all users.

        Returns:
            List[Photo]: Photos belonging to users.
        """
        return Photo.query.all()

    def get_photos_by_category(self, category):
        """
        Get all photos linked to a category (many-to-many).

        Args:
            category (Category): The category object.

        Returns:
            list[Photo]: Photos in that category.
        """
        return category.photos.all()

    def count_photos_by_category(self, category):
        """
        Count photos linked to a category (many-to-many).

        Args:
            category (Category): The category object.

        Returns:
            int: Number of photos linked to this category.
        """
        return category.photos.count()


    def update_photo(self, photo, **kwargs):
        """
        Update fields of an existing photo.

        Args:
            photo: the photo to update.
            **kwargs: Key-value pairs of fields to update.

        Example:
            update_photo(
            photo, unique_filename="new_name.jpg",
            description="Updated description"
            )
        """
        try:
            for key, value in kwargs.items():
                setattr(photo, key, value)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def delete_photo(self, photo):
        """
        Delete a photo.

        Args:
            photo: the photo to delete.
        """
        try:
            db.session.delete(photo)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    # ------------------ Category operations ------------------ #

    def add_category(self, user, name):
        """
        Create and add a new category for a specific user.

        Args:
            user (User): The owner of the category.
            name (str): The name of the category.

        Returns:
            Category: The created category object.
        """
        try:
            category = Category(user_id=user.id, name=name)
            db.session.add(category)
            db.session.commit()
            return category
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def get_category_by_id(self, category_id):
        """
        Retrieve a category by its ID.

        Args:
            category_id (int): The ID of the category.

        Returns:
            Category | None: The category object if found, else None.
        """
        return Category.query.get(category_id)

    def get_category_by_name(self, name, user_id=None):
        """
        Retrieve a category by its name.

        Args:
            name (str): The name of the category.
            user_id (int, optional): If provided, filters by this user's categories.

        Returns:
            Category | None: The category object if found, else None.
        """
        query = Category.query.filter_by(name=name)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.first()

    def get_categories_by_user(self, user):
        """
        Retrieve all categories owned by a specific user.

        Args:
            user (User): The owner of the categories.

        Returns:
            list[Category]: A list of category objects.
        """
        return Category.query.filter_by(user_id=user.id).all()

    def update_category(self, category, **kwargs):
        """
        Update fields of an existing category from the database.

        Args:
            category (Category): The category object to update.
            **kwargs: Key-value pairs of fields to update.
        """
        try:
            for key, value in kwargs.items():
                setattr(category, key, value)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def delete_category(self, category):
        """
        Delete a given category from the database.

        Args:
            category (Category): The category object to delete.
        """
        try:
            db.session.delete(category)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    # If safe check wanted here instead of relying on flask side owner checks!

    #    def get_category_by_name(self, name, user_id=int):
    #     """
    #     Retrieve a category by its name belonging to a specific user.
    #
    #     Args:
    #         name (str): The name of the category.
    #         user_id (int): Filters by this user's categories.
    #
    #     Returns:
    #         Category | None: The category object if found, else None.
    #     """
    #     return Category.query.filter_by(name=name, user_id=user_id).first()
    #
    #       def get_categories_by_user(self, user):
    #         """
    #         Retrieve all categories owned by a specific user.
    #
    #         Args:
    #             user (User): The owner of the categories.
    #
    #         Returns:
    #             list[Category]: A list of category objects.
    #         """
    #         return Category.query.filter_by(user_id=user.id).all()
    #
    #     def update_category(self, category, **kwargs):
    #         """
    #         Update fields of an existing category from the database.
    #
    #         Args:
    #             category (Category): The category object to update.
    #             **kwargs: Key-value pairs of fields to update.
    #         """
    #         try:
    #             for key, value in kwargs.items():
    #                 setattr(category, key, value)
    #             db.session.commit()
    #         except SQLAlchemyError as e:
    #             db.session.rollback()
    #             raise e
    #
    #     def delete_category(self, category, user):
    #         """
    #         Delete a given category from the database.
    #
    #         Args:
    #             category (Category): The category object to delete.
    #             user (User): The owner of the category.
    #         """
    #         category = Category.query.filter_by(id=category.id, user_id=user.id).first()
    #         if category:
    #             try:
    #                 db.session.delete(category)
    #                 db.session.commit()
    #                 return True
    #             except SQLAlchemyError as e:
    #                 db.session.rollback()
    #                 raise e
    #         return False
    #

    # ------------------ Assign photo to category ------------------ #

    def assign_photo_to_category(self, photo, category):
        """
        Assign a photo to a single category.
        Any existing category associations are cleared first.

        Args:
            photo (Photo): The photo object.
            category (Category): The category object.
        """
        photo.categories = []  # single category per photo (remove to reinstate many-to-many)
        try:
            if category not in photo.categories:
                photo.categories.append(category)
                db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    def remove_photo_from_category(self, photo, category):
        """
        Remove the link between a photo and a category.

        Args:
            photo (Photo): The photo object.
            category (Category): The category object.
        """
        try:
            if category in photo.categories:
                photo.categories.remove(category)
                db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e
