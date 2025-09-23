"""
config.py

This module defines configuration settings for the photo sorting application.

It loads environment variables from a `.env` file (if present) and provides
a `Config` class with centralized settings for Flask and SQLAlchemy.

Attributes:
    basedir (Path): Absolute path to the project directory containing this file.
    DATA_DIR (Path): Path to the `data` directory for database storage.
"""


import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()  # load .env

basedir = Path(__file__).resolve().parent
DATA_DIR = basedir / "data"


class Config:
    """
    Configuration class for Flask and SQLAlchemy.

    Attributes:
        SECRET_KEY (str): Secret key for session management and CSRF protection.
                          Loaded from the `SECRET_KEY` environment variable,
                          defaults to `"dev_secret"` for development.
        SQLALCHEMY_DATABASE_URI (str): Database URI for SQLAlchemy.
                                       Defaults to a SQLite database in `DATA_DIR`.
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): Disable modification tracking
                                               to save resources (default: False).
        UPLOAD_FOLDER (str): Path to the folder where uploaded files are stored.
        LOG_LEVEL (str): Logging verbosity level (default: "DEBUG").
                         Can be overridden with the `LOG_LEVEL` environment variable.
    """
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")  # fallback for dev
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{str(DATA_DIR / 'photos.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = str("static/uploads")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
