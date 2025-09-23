"""
Category management blueprint.

Provides routes for:
- Adding new categories
- Renaming existing categories
- Deleting categories (if empty)

Integrates with:
- DataManager for database operations
- Flask-Login for user authentication
"""


from sqlalchemy.exc import SQLAlchemyError

from flask import Blueprint, flash, request, redirect, url_for
from flask_login import login_required, current_user

from data_manager import DataManager
from models import db, Category


categories_bp = Blueprint("categories", __name__)
data_manager = DataManager()


@categories_bp.route("/add", methods=["POST"])
@login_required
def add_category():
    """
    Add a new category for the current user.

    Form fields expected:
        - name (str): Name of the new category.

    Returns:
        Response: Redirects to the user's dashboard with flash messages indicating:
            - Success
            - Missing name
            - Duplicate category
            - Database errors
    """
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name required.", "error")
        return redirect(url_for("photos.dashboard"))

    # check if category with same name already exists for this user
    existing = data_manager.get_category_by_name(name, current_user.id)
    if existing:
        flash(f"Category '{name}' already exists!", "error")
        return redirect(url_for("photos.dashboard"))

    try:
        data_manager.add_category(current_user, name)
        flash(f"Category '{name}' added!", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Failed to add category: {e}", "error")

    return redirect(url_for("photos.dashboard"))


@categories_bp.route("/update/<int:category_id>", methods=["POST"])
@login_required
def update_category(category_id):
    """
    Rename an existing category.

    Form fields expected:
        - name (str): New category name.

    Args:
        category_id (int): The ID of the category to rename.

    Returns:
        Response: Redirects to the user's dashboard with flash messages indicating:
            - Success
            - Missing name
            - Duplicate name
            - Permission denied
            - Database errors
    """
    new_name = request.form.get("name")

    if not new_name:
        flash("New category name required", "error")
        return redirect(url_for("photos.dashboard"))

    # Prevent duplicate category names for the same user
    existing = data_manager.get_category_by_name(new_name, current_user.id)
    if existing and existing.id != category_id:
        flash(f"Category '{new_name}' already exists!", "error")
        return redirect(url_for("photos.dashboard"))

    category = data_manager.get_category_by_id(category_id)
    if not category or category.owner != current_user:
        flash("Category not found or permission denied.", "error")
        return redirect(url_for("photos.dashboard"))

    try:
        data_manager.update_category(category, name=new_name)
        flash(f"Category renamed to '{new_name}'", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Failed to update category: {e}", "error")

    return redirect(url_for("photos.dashboard"))


@categories_bp.route("/delete/<int:category_id>", methods=["POST"])
@login_required
def delete_category(category_id):
    """
    Delete a category if it belongs to the current user and is empty.

    Args:
        category_id (int): The ID of the category to delete.

    Returns:
        Response: Redirects to the user's dashboard with flash messages indicating:
            - Success
            - Permission denied
            - Category contains photos
            - Database errors
    """
    category = Category.query.get_or_404(category_id)
    if not category or category.owner != current_user:
        flash("Category not found or permission denied.", "error")
        return redirect(url_for("photos.dashboard"))

    # Check if any photos exist in this category in the DB
    photo_count = data_manager.count_photos_by_category(category)
    if photo_count > 0:
        flash("Cannot delete a category that contains photos.", "error")
        return redirect(url_for("photos.dashboard"))

    try:
        data_manager.delete_category(category)
        flash(f"Category '{category.name}' deleted.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Failed to delete category: {e}", "error")

    return redirect(url_for("photos.dashboard"))
