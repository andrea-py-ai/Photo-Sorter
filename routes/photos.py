"""
Photo management blueprint.

Provides routes for:
- Viewing the dashboard with photos organized by category.
- Uploading multiple photos.
- Sorting photos automatically via AI.
- Updating photo details (original filename, category).
- Deleting photos.
- Searching photos by description or filename.

Integrates with:
- DataManager for database operations
- PhotoService for AI categorization
- Flask-Login for user authentication
"""


import logging
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from werkzeug.utils import secure_filename

from flask import Blueprint, current_app, flash, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from data_manager import DataManager
from models import db
from services.photo_service import PhotoService


photos_bp = Blueprint("photos", __name__)
data_manager = DataManager()
logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    """
    Check if the file has an allowed image extension.

    Args:
        filename (str): Name of the file to check.

    Returns:
        bool: True if file is allowed, False otherwise.
    """
    return (
            "." in filename and
            filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@photos_bp.route("/dashboard")
@login_required
def dashboard():
    """
    Render the user's photo dashboard, grouping photos by category.

    - Builds a dictionary of categories containing photos.
    - Adds an "Uncategorized" section for photos without a category.

    Returns:
        Response: Rendered 'dashboard.html' template with the user,
        their categories, and photos organized by category.
    """
    categories = data_manager.get_categories_by_user(current_user)
    photos = data_manager.get_photos_by_user(current_user.id)

    # Build dict only for categories that actually have photos
    photos_by_category = {}
    for cat in categories:
        cat_photos = [p for p in photos if cat in p.categories]
        if cat_photos:
            photos_by_category[cat.name] = cat_photos

    # Add Uncategorized if there are photos without a category
    uncategorized_photos = [p for p in photos if not p.categories]
    if uncategorized_photos:
        photos_by_category["Uncategorized"] = uncategorized_photos

    return render_template(
        "dashboard.html",
        user=current_user,
        categories=categories,
        photos_by_category=photos_by_category,
        photos=photos
    )


def get_upload_folder() -> Path:
    """
    Get the absolute path to the upload folder.
    Creates it if it does not exist.

    Returns:
        Path: Upload folder path.
    """
    folder = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def get_photo_service():
    """
    Initialize a PhotoService instance using the current upload folder.

    Returns:
        PhotoService: Initialized service object.
    """
    return PhotoService(str(get_upload_folder()))


@photos_bp.route("/upload", methods=["POST"])
@login_required
def upload_photos():
    """
    Upload one or more photos for the current user.

    - Ensures unique filenames by prepending a UUID.
    - Validates allowed file types: png, jpg, jpeg, gif.
    - Stores files in the configured UPLOAD_FOLDER.
    - Creates Photo records in the database.
    - Automatically categorizes photos using AI if possible.

    Form fields expected:
        - photos: List of uploaded files (input type="file")

    Returns:
        Response: Redirects to dashboard with flash messages indicating:
            - Upload success
            - AI categorization success or failures
            - Validation errors
    """
    if "photos" not in request.files:
        flash("No files selected", "error")
        return redirect(url_for("photos.dashboard"))

    files = request.files.getlist("photos")
    if not files or all(file.filename == "" for file in files):
        flash("No selected files.", "error")
        return redirect(url_for("photos.dashboard"))

    upload_folder = get_upload_folder()

    uploaded_photos = []
    for file in files:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid4().hex}_{original_filename}"
            file_path = upload_folder / unique_filename

            try:
                file.save(file_path)
                photo = data_manager.add_photo(current_user, unique_filename, original_filename)
                uploaded_photos.append(photo)
            except SQLAlchemyError as e:
                db.session.rollback()
                flash(f"Database error for {original_filename}: {e}", "error")
        else:
            flash(f"Invalid file type: {file.filename}", "error")

    if uploaded_photos:
        photo_service = get_photo_service()
        categorized_count, uncategorized_photos = photo_service.sort_all_photos_for_user_ai(
            uploaded_photos, current_user
        )
        flash(f"{len(uploaded_photos)} photo(s) uploaded.", "success")
        if categorized_count:
            flash(f"{categorized_count} photo(s) categorized successfully!", "success")
        if uncategorized_photos:
            flash(f"Could not categorize: {', '.join(uncategorized_photos)}", "warning")

    return redirect(url_for("photos.dashboard"))


@photos_bp.route("/sort", methods=["POST"])
@login_required
def sort_photos():
    """
    Re-run AI categorization for all photos of the current user into existing categories.

    Returns:
        Response: Redirects to dashboard with flash messages indicating results.
    """
    photo_service = get_photo_service()

    photos = data_manager.get_photos_by_user(current_user.id)
    categorized_count, uncategorized_photos = photo_service.sort_all_photos_for_user_ai(photos, current_user)

    flash(f"{categorized_count} photo(s) categorized successfully!", "success")
    if uncategorized_photos:
        flash(f"Could not match categories for: {', '.join(uncategorized_photos)}", "warning")

    return redirect(url_for("photos.dashboard"))


@photos_bp.route("/sort_photo/<int:photo_id>", methods=["POST"])
@login_required
def sort_single_photo(photo_id):
    """
    Categorize a single photo using AI or a user-selected category.

    - If 'category_id' is provided in the form, assigns that category.
      Updates the photo description via AI only.
    - Otherwise, runs AI categorization including both category and description.

    Args:
        photo_id (int): The ID of the photo to categorize.

    Returns:
        Response: Redirects to dashboard with flash messages indicating
        the result of categorization.
    """
    photo_service = get_photo_service()
    photo = data_manager.get_photo_by_id(photo_id)

    if not photo:
        flash("Photo not found.", "error")
        return redirect(url_for("photos.dashboard"))

    # Check if user submitted a category override
    category_id = request.form.get("category_id")

    if category_id:
        try:
            category = data_manager.get_category_by_id(int(category_id))
            if category:
                # Assign the category
                photo_service.data_manager.assign_photo_to_category(photo, category)

                # Run AI for description only
                result = photo_service.openai.analyze_image(
                    photo_service.upload_folder / photo.unique_filename,
                    existing_categories=None
                )
                description = result.get("description")
                if description:
                    data_manager.update_photo(photo, description=description)

                flash(f"Photo assigned to '{category.name}' with new description!", "success")
            else:
                flash("Invalid category selected.", "error")
        except ValueError:
            flash("Invalid category ID.", "error")

    else:
        # Use AI-suggested category
        assigned_category = photo_service.auto_categorize_photo_ai(photo, current_user)
        if assigned_category:
            flash(f"Photo categorized as '{assigned_category}' successfully!", "success")
        else:
            flash("Could not categorize this photo.", "warning")

    return redirect(url_for("photos.dashboard"))


@photos_bp.route("/update/<int:photo_id>", methods=["POST"])
@login_required
def update_photo(photo_id):
    """
    Update photo details:
    - Rename original/friendly filename.
    - Reassign to a different category.
    Does not modify unique_filename.

    Form fields expected:
        - original_filename (str, optional)
        - category_id (int, optional)

    Args:
        photo_id (int): The ID of the photo to update.

    Returns:
        Response: Redirects to dashboard with flash messages indicating result.
    """
    photo = data_manager.get_photo_by_id(photo_id)
    if not photo or photo.owner != current_user:
        flash("Photo not found or permission denied.", "error")
        return redirect(url_for("photos.dashboard"))

    updates = {}

    # Allow renaming the display/original filename
    new_original_filename = request.form.get("original_filename")
    if new_original_filename and new_original_filename != photo.original_filename:
        updates["original_filename"] = new_original_filename

    # Allow changing the category
    new_category_id = request.form.get("category_id")
    if new_category_id:
        category = data_manager.get_category_by_id(int(new_category_id))
        if category:
            updates["categories"] = [category]

    if updates:
        try:
            data_manager.update_photo(photo, **updates)
            flash("Photo successfully updated!", "success")
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f"Database error: {e}", "error")
    else:
        flash("No changes detected.", "info")

    return redirect(url_for("photos.dashboard"))


@photos_bp.route("/delete/<int:photo_id>", methods=["POST"])
@login_required
def delete_photo(photo_id):
    """
    Delete a photo by ID (only if it belongs to the current user).

    Args:
        photo_id (int): The ID of the photo to delete.

    Returns:
        Redirects to the user's dashboard with flash messages.
    """
    photo = data_manager.get_photo_by_id(photo_id)
    if not photo:
        flash(f"Photo with id ({photo_id}) not found!", "error")
        return redirect(url_for("photos.dashboard"))

    if photo.owner != current_user:
        flash("You do not have permission to delete this photo.", "error")
        return redirect(url_for("photos.dashboard"))

    try:
        data_manager.delete_photo(photo)
        flash(f"Photo '{photo.unique_filename}' deleted successfully.", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"Failed to delete photo: {e}", "error")

    return redirect(url_for("photos.dashboard"))


@photos_bp.route("/search")
@login_required
def search_photos():
    """
    Search the current user's photos by description or original filename.

    Query parameters:
        - q (str): Search term

    Returns:
        Response: Rendered dashboard showing matching photos under
        'Search results'. Flash message if the query is empty.
    """
    query = request.args.get("q", "").strip()
    if not query:
        flash("Please enter a search term.", "warning")
        return redirect(url_for("photos.dashboard"))

    # Get all photos for this user
    photos = data_manager.get_photos_by_user(current_user.id)

    # Filter photos (case-insensitive match in description or filename)
    results = [
        photo for photo in photos
        if (photo.description and query.lower() in photo.description.lower())
        or (photo.original_filename and query.lower() in photo.original_filename.lower())
    ]

    return render_template(
        "dashboard.html",
        user=current_user,
        categories=data_manager.get_categories_by_user(current_user),
        photos_by_category={"Search results": results},
        search_query=query
    )
