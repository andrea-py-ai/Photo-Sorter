"""
User profile management blueprint.

Provides routes for viewing, updating, and deleting the currently
logged-in user's profile. Integrates with DataManager for database
operations and Flask-Login for authentication.

Routes:
- GET /profile: Display the profile editing form.
- POST /update: Update username, email, and/or password.
- POST /delete: Delete the user account and associated photos.
"""


from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.security import generate_password_hash

from flask import Blueprint, flash, render_template, request, redirect, url_for
from flask_login import login_required, logout_user, current_user

from data_manager import DataManager
from models import db

user_bp = Blueprint("user", __name__)
data_manager = DataManager()


@user_bp.route("/profile")
@login_required
def profile():
    """
    Render the profile editing page for the current user.

    Returns:
        Response: Rendered HTML template for profile editing.
    """
    return render_template("edit_profile.html", user=current_user)


@user_bp.route("/update", methods=["POST"])
@login_required
def update_user():
    """
    Update the currently logged-in user's profile.

    Allows updating:
    - username
    - email
    - password (minimum 6 characters)

    Validates uniqueness for username and email. Updates only fields
    that have changed. Flash messages indicate success, info, or errors.

    Form fields expected in request:
        - username (str)
        - email (str)
        - password (str, optional)

    Returns:
        Response: Redirects to the user's dashboard or back to the profile
        page with appropriate flash messages.
    """
    new_username = request.form.get("username")
    new_email = request.form.get("email")
    new_password = request.form.get("password")

    updates = {}

    if new_username and new_username != current_user.username:
        if data_manager.get_user_by_username(new_username):
            flash("Username already taken.", "error")
            return redirect(url_for("user.profile"))
        updates["username"] = new_username

    if new_email and new_email != current_user.email:
        if data_manager.get_user_by_email(new_email):
            flash("Email already in use.", "error")
            return redirect(url_for("user.profile"))
        updates["email"] = new_email

    if new_password:
        if len(new_password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("user.profile"))
        updates["password_hash"] = generate_password_hash(new_password)

    if not updates:
        flash("No changes detected.", "info")
        return redirect(url_for("user.profile"))

    try:
        data_manager.update_user(current_user, **updates)
        flash("Profile updated successfully!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Database error: {str(e)}", "error")

    return redirect(url_for("photos.dashboard"))


@user_bp.route("/delete", methods=["POST"])
@login_required
def delete_user():
    """
    Delete the currently logged-in user and their photos.

    Performs the following:
    - Deletes the user record from the database
    - Deletes all associated photos via cascading
    - Logs out the user
    - Flashes success or error messages

    Returns:
        Response: Redirects to the home page.
    """
    try:
        data_manager.delete_user(current_user)
        logout_user()
        flash("Your account has been deleted.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Failed to delete user: {e}", "error")

    return redirect(url_for("auth.home"))
