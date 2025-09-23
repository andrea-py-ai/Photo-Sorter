"""
Photo service module.

Provides business logic for handling photo categorization and metadata.
Integrates with OpenAI to analyze images, suggest categories, and update
photo descriptions. Falls back to existing categories when possible.
"""


import difflib
import time
import logging
from pathlib import Path
import re

import openai

from data_manager import DataManager
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "at", "in", "on", "for", "with", "to", "by", "from"
}


def match_category(suggested_category: str, description: str, existing_categories: list):
    """
    Match an AI-suggested category to a user's existing categories.

    Attempts to find a close match using fuzzy string similarity.
    If no direct match, tries to match keywords from the photo description.
    Falls back to the original suggestion if no match is found.

    Args:
        suggested_category (str): Category name suggested by the AI.
        description (str): Description of the photo from AI analysis.
        existing_categories (list[Category]): List of existing Category objects.

    Returns:
        Category | None: A matching Category object if found, else None.
    """
    if not existing_categories and not suggested_category and not description:
        return None

    # Check suggested category against existing
    if suggested_category:
        suggested_lower = suggested_category.strip().lower()
        for cat in existing_categories:
            if difflib.SequenceMatcher(None, suggested_lower, cat.name.strip().lower()).ratio() > 0.7:
                return cat

    # Check description words against existing categories
    if description:
        words = [w for w in re.findall(r'\w+', description.lower()) if w not in STOPWORDS]
        for word in words:
            for cat in existing_categories:
                if difflib.SequenceMatcher(None, word, cat.name.strip().lower()).ratio() > 0.7:
                    return cat
    return None


class PhotoService:
    """
    Service layer for photo operations.

    Handles photo categorization, description updates, and integration with
    OpenAI for AI-powered photo analysis. Uses a DataManager to persist
    categories and assignments.
    """
    def __init__(self, upload_folder: str):
        self.openai = OpenAIService()
        self.data_manager = DataManager()
        self.upload_folder = Path(upload_folder)

    def sort_all_photos_for_user_ai(self, photos, user):
        """
        Categorize all photos for a given user using AI suggestions.

        Iterates over the user's photos, analyzes each with OpenAI, and
        assigns them to categories if possible. Skips missing files.

        Args:
            photos (list[Photo]): List of Photo objects belonging to the user.
            user (User): The user who owns the photos.

        Returns:
            tuple[int, list[str]]:
                - Number of successfully categorized photos.
                - List of filenames that could not be categorized.
        """
        categorized_count = 0
        uncategorized_photos = []

        for photo in photos:
            result = self.auto_categorize_photo_ai(photo, user)
            if result:
                categorized_count += 1
            else:
                uncategorized_photos.append(photo.original_filename)

        return categorized_count, uncategorized_photos

    def auto_categorize_photo_ai(self, photo, user, match_existing=True, max_retries=3):
        """
        Analyze a photo with OpenAI and assign it to a category.

        - Uses AI to suggest a category and description.
        - Matches against existing categories (if enabled).
        - Creates a new category if no match is found.
        - Updates the photo's description in the database.
        - Retries on rate limits with exponential backoff.

        Args:
            photo (Photo): The photo object to categorize.
            user (User): The owner of the photo.
            match_existing (bool, optional): Whether to try matching existing
                categories first. Defaults to True.
            max_retries (int, optional): Number of retries on API errors.
                Defaults to 3.

        Returns:
            str | None: The name of the matched or created category,
            or None if categorization failed.
        """
        photo_path = self.upload_folder / photo.unique_filename
        if not photo_path.exists():
            logger.warning(f"[PhotoService] Skipping missing file: {photo_path}")
            return None

        retries = 0
        existing_categories = self.data_manager.get_categories_by_user(user)

        while retries < max_retries:
            try:
                # Pass existing categories if desired
                categories_for_prompt = existing_categories if match_existing else None
                result: dict = self.openai.analyze_image(photo_path, existing_categories=categories_for_prompt)

                suggested_category = result.get("category")
                description = result.get("description")

                # Match category using your match_category helper (can include description words)
                matched_category = match_category(suggested_category, description, existing_categories)

                # If no existing match, create a new category (capitalized)
                if not matched_category and suggested_category:
                    # Capitalize the first letter
                    formatted_category = suggested_category.strip().capitalize()
                    # Create new category for the user
                    matched_category = self.data_manager.add_category(user, formatted_category)
                    existing_categories.append(matched_category)

                # Assign photo to category
                if matched_category:
                    self.data_manager.assign_photo_to_category(photo, matched_category)
                # Update description
                if description:
                    self.data_manager.update_photo(photo, description=description)

                return matched_category.name if matched_category else None

            except openai.RateLimitError as e:
                retries += 1
                wait_time = 2 ** retries
                logger.warning(f"Rate limit hit (retry {retries}/{max_retries}) in {wait_time}s: {e}")
                time.sleep(wait_time)

            except (openai.APIError, openai.APIConnectionError, openai.APIStatusError) as e:
                logger.error(f"OpenAI API error while categorizing {photo.original_filename}: {e}")
                return None
            except Exception as e:
                logger.exception(f"Unexpected error for {photo.original_filename}: {e}")
                return None

        logger.error(f"Failed to categorize {photo.original_filename} after {max_retries} retries")
        return None
