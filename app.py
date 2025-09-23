"""
Photo Sorting Web Application (Flask)

This application allows multiple users to manage and organize their photos.
Each user has their own account and can perform CRUD operations on their
personal photo collection.

Features:
- User Management:
    - Create new accounts (signup)
    - Login / logout
    - Delete account
- Photo Management (per user):
    - Upload photos
    - Organize photos into categories (with AI-assisted suggestions via OpenAI)
    - Update photo details
    - Delete photos
    - View all photos belonging to the user

Usage:
- Run this script directly: `python app.py`
- Access the web interface at http://localhost:5002/
- Ensure a valid SECRET_KEY and OpenAI API key are set in your `.env` file
- By default, the application uses a SQLite database stored in `data/photos.db`
"""


import logging
from pathlib import Path

from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager

from config import Config
from models import db, User
from routes.auth import auth_bp
from routes.user import user_bp
from routes.photos import photos_bp
from routes.categories import categories_bp

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # redirect if not logged in
login_manager.session_protection = "strong"


def create_app():
    """
    Application factory for the Flask app.

    This function creates and configures the Flask application instance.
    It sets up logging, initializes database and authentication extensions,
    registers blueprints, and defines global error handlers.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, app.config.get("LOG_LEVEL", "INFO")),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    # Silence verbose third-party logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    upload_path = Path(app.config["UPLOAD_FOLDER"])
    upload_path.mkdir(parents=True, exist_ok=True)  # creates static/uploads if missing

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(photos_bp, url_prefix="/photos")
    app.register_blueprint(categories_bp, url_prefix="/categories")

    @app.errorhandler(404)
    def not_found_error(_error):
        """
        Handle 404 Not Found errors.
        Flash a message and redirect the user.

        Args:
            _error (HTTPException):
                The exception that triggered the error handler.

        Returns:
            Response: Redirect to the home page with the associated HTTP status code.
        """
        flash("Resource not found.", "error")
        return redirect(url_for("auth.home")), 404

    @app.errorhandler(403)
    def forbidden_error(_error):
        """
        Handle 403 Forbidden errors.
        Flash a message and redirect the user.

        Args:
            _error (HTTPException):
                The exception that triggered the error handler.

        Returns:
            Response: Redirect to the home page with the associated HTTP status code.
        """
        flash("You do not have permission to access this resource.", "error")
        return redirect(url_for("auth.home")), 403

    @app.errorhandler(500)
    def internal_error(_error):
        """
        Handle 500 Internal Server errors.
        Flash a message and redirect the user.

        Args:
            _error (HTTPException):
                The exception that triggered the error handler.

        Returns:
            Response: Redirect to the home page with the associated HTTP status code.
        """
        flash("An unexpected error occurred.", "error")
        return redirect(url_for("auth.home")), 500

    return app


# Flask-Login: reload user from session
@login_manager.user_loader
def load_user(user_id):
    """
    Reload a user object from the session.

    Args:
        user_id (str): The ID of the user stored in the session.

    Returns:
        User | None: The user object if found, else None.
    """
    return User.query.get(int(user_id))


# WSGI entry point
app = create_app()


def main():
    """Run the Flask development server."""
    # with app.app_context():
    #     db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)


if __name__ == "__main__":
    main()
