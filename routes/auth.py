"""
Authentication blueprint.

Provides routes for:
- Home page (login/signup)
- User login
- User logout
- User signup
"""


from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash


from flask import Blueprint, flash, render_template, request, redirect, url_for
from flask_login import login_required, login_user, logout_user

from data_manager import DataManager
from models import db


auth_bp = Blueprint("auth", __name__)
data_manager = DataManager()


@auth_bp.route("/")
def home():
    """
    Render the home page with login and signup forms.

    Returns:
        Response: Rendered 'index.html' template.
    """
    return render_template("index.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate an existing user.

    Form fields expected:
        - username (str): Username of the user.
        - password (str): Plain-text password to verify.

    Returns:
        Response: Redirect to user's dashboard if successful,
        otherwise back to home with flash messages.
    """
    username = request.form.get("username")
    password = request.form.get("password")

    user = data_manager.get_user_by_username(username)
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        flash(f"Welcome back, {user.username}!", "success")
        return redirect(url_for("photos.dashboard"))  # or photos page
    else:
        flash("Invalid username or password.", "error")
        return redirect(url_for("auth.home"))


@auth_bp.route("/logout")
@login_required
def logout():
    """
    Log out the currently logged-in user.

    Returns:
        Response: Redirect to home page with flash message.
    """
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.home"))


@auth_bp.route("/signup", methods=["POST"])
def add_user():
    """
    Sign up a new user.

    Form fields expected:
        - username (str)
        - email (str)
        - password (str)

    Password is hashed before storing.

    Returns:
        Response: Redirect to home page with flash messages for:
            - Success
            - Missing fields
            - Password too short
            - Duplicate email or username
            - Database errors
    """
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if not username or not email or not password:
        flash("All fields are required!", "error")
        return redirect(url_for("auth.home"))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "error")
        return redirect(url_for("auth.home"))

    if data_manager.get_user_by_email(email):
        flash(f"Email '{email}' already registered.", "error")
        return redirect(url_for("auth.home"))

    if data_manager.get_user_by_username(username):
        flash(f"Username '{username}' already exists.", "error")
        return redirect(url_for("auth.home"))

    try:
        password_hash = generate_password_hash(password)
        data_manager.create_user(username, email, password_hash)
        flash(f"New user '{username}' successfully created!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Database error: {str(e)}", "error")

    return redirect(url_for("auth.home"))
