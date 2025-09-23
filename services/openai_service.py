"""
OpenAI service wrapper for photo analysis.

Provides a thin abstraction over the OpenAI Chat Completions API
to analyze images, generate short descriptions, and suggest
categories. Ensures JSON-only output and retries safely on errors.
"""

import base64
import io
import json
import logging
import os
from PIL import Image
import random
import re
import time

from openai import (APIConnectionError,
                    APIError,
                    InternalServerError,
                    RateLimitError,
                    OpenAI
                    )
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionContentPartImageParam
)

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Wrapper around the OpenAI client for photo categorization.

    This service:
    - Resizes and encodes photos as base64 before sending.
    - Prompts OpenAI with instructions to return a strict JSON object
      containing a short description and category name.
    - Optionally biases categorization toward the user's existing categories.
    - Retries failed requests with exponential backoff on rate limits
      and transient API errors.
    """
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def analyze_image(self, image_path, existing_categories=None, max_categories=6) -> dict:
        """
        Analyze a photo using OpenAI and return a suggested description and category.

        - Resizes the image to 512x512 max to reduce payload.
        - Encodes the image as base64 for API transmission.
        - Instructs the model to output a strict JSON object.
        - Optionally includes existing categories to bias classification.
        - Retries on rate limit or API errors with exponential backoff.

        Args:
            image_path (Path | str): Path to the image file.
            existing_categories (list[Category], optional):
                List of user-defined categories to bias classification.
                Defaults to None.
            max_categories (int, optional):
                Maximum number of categories to include in the prompt
                if existing categories are provided. Defaults to 6.

        Returns:
            dict: A dictionary with keys:
                - "description" (str): Short description of the photo.
                - "category" (str | None): Suggested category name, or None if unavailable.

        Raises:
            RuntimeError: If the request fails after maximum retries.
        """
        # Resize image to reduce payload
        with Image.open(image_path) as img:
            img.thumbnail((512, 512))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # System message: enforces JSON output
        system_content = (
            "You are a photo categorization assistant. "
            "Your ONLY output must be a valid JSON object with exactly two keys:\n"
            "{\n"
            '  "description": "short human-friendly description of the photo (max 12 words)",\n'
            '  "category": "one category name (1-2 words, lowercase)"\n'
            "}\n"
            "Do NOT include explanations, markdown, or backticks.\n"
            "Example:\n"
            '{"description": "small boat on a lake", "category": "landscape"}'
        )
        # User message: task + optional categories
        prompt = "Analyze this photo."

        if existing_categories:
            categories_str = ", ".join([cat.name for cat in existing_categories[:max_categories]])
            prompt += (
                f"The user already has categories: [{categories_str}].\n"
                "If the photo clearly matches one of these, use it as 'category'.\n"
                "Only suggest a new category if none apply.\n"
            )

        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_content),
            ChatCompletionUserMessageParam(
                role="user",
                content=[
                    ChatCompletionContentPartTextParam(type="text", text=prompt),
                    ChatCompletionContentPartImageParam(
                        type="image_url",
                        image_url={"url": f"data:image/jpeg;base64,{img_base64}"}
                    ),
                ]
            )
        ]

        # Retry with exponential backoff
        max_retries = 3
        backoff = 2  # seconds

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                )
                content = response.choices[0].message.content.strip()
                if not content:
                    return {"category": None, "description": "No response from model"}

                # Parse JSON safely
                try:
                    # Remove markdown fences like ```json ... ``` or just ```
                    cleaned = re.sub(
                        r"^```(?:json)?|```$", "", content, flags=re.IGNORECASE
                    ).strip()

                    data = json.loads(cleaned)
                    return {
                        "category": data.get("category"),
                        "description": data.get("description")
                    }
                except json.JSONDecodeError:
                    # fallback: clean up any leftover formatting
                    clean_text = (
                        content.replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )
                    return {"category": None, "description": clean_text}

            except RateLimitError as e:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Rate limit hit. "
                    f"Waiting {wait_time:.1f}s before retry ({attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(wait_time)
            except (APIConnectionError, APIError, InternalServerError) as e:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Temporary API error. "
                    f"Waiting {wait_time:.1f}s before retry ({attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error type {type(e)}: {e}")
                return {"category": None, "description": f"Error: {e}"}

        raise RuntimeError("OpenAI request failed after maximum retries (rate limit).")
